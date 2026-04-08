import os  
import re
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Session, Participation, UserRole

# ============================================================
# INITIALISATION DE L'APPLICATION
# ============================================================

app = Flask(__name__)

# ==========================================
# 1. CONFIGURATION DYNAMIQUE 
# ==========================================
uri = os.environ.get("DATABASE_URL", "sqlite:///database.db")

# Correction du bug de dialecte Postgres (Heroku/Render)
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")

# ==========================================
# 2. INITIALISATION 
# ==========================================
db.init_app(app)

# ==========================================
# 3. CRÉATION DES TABLES 
# ==========================================
with app.app_context():
    db.create_all()  # Ici, Flask connaît enfin l'URI et db est lié à l'app

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def validate_email(email: str):
    """
    Valide une adresse email universitaire et détermine le rôle associé.

    Une adresse est valide si :
    - elle ne contient pas d'espaces
    - elle se termine par @etu.u-paris.fr (étudiant)
    - elle se termine par @u-paris.fr (professeur)

    Args:
        email (str): email saisi par l'utilisateur

    Returns:
        tuple:
            - bool : validité
            - UserRole : rôle associé
            - str : message d'erreur éventuel
    """

    email = email.strip().lower()

    # Vérification des espaces
    if " " in email:
        return False, None, "L'adresse email ne doit pas contenir d'espaces."

    # Expression régulière pour email universitaire
    pattern = r"^[a-zA-Z0-9._%+-]+@(etu\.u-paris\.fr|u-paris\.fr)$"
    if not re.match(pattern, email):
        return False, None, "Email universitaire requis."

    # Attribution du rôle
    if email.endswith("@etu.u-paris.fr"):
        return True, UserRole.STUDENT, None
    return True, UserRole.PROFESSOR, None


def generate_session_code():
    """
    Génère un code de session aléatoire.

    Le code est composé de 6 caractères alphanumériques (A-Z, 0-9).

    Returns:
        str: code session unique
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ============================================================
# ROUTE PRINCIPALE
# ============================================================

@app.route("/")
def home():
    """
    Route principale de l'application.

    Redirige automatiquement l'utilisateur :
    - vers le dashboard professeur si connecté en tant que professeur
    - vers le dashboard étudiant si connecté en tant qu'étudiant
    - vers la page de connexion sinon

    Returns:
        Redirection Flask
    """

    if "user_id" in session:
        if session.get("role") == "professor":
            return redirect(url_for("professor_dashboard"))
        return redirect(url_for("student_dashboard"))

    return redirect(url_for("login"))


# ============================================================
# INSCRIPTION
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Gère l'inscription d'un nouvel utilisateur.

    Méthode GET :
        - Affiche le formulaire d'inscription

    Méthode POST :
        - Récupère les données du formulaire
        - Valide les champs
        - Vérifie l'unicité de l'email
        - Hash le mot de passe
        - Crée un utilisateur en base via SQLAlchemy

    Returns:
        HTML ou redirection
    """

    if request.method == "POST":

        # Récupération des données
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Validation des champs
        if not first_name or not last_name or not email or not password:
            flash("Tous les champs sont obligatoires.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Le mot de passe doit contenir au moins 8 caractères.", "error")
            return render_template("register.html")

        # Validation email
        is_valid, role, error = validate_email(email)
        if not is_valid:
            flash(error, "error")
            return render_template("register.html")

        # Vérification existence utilisateur
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Un compte existe déjà avec cet email.", "warning")
            return redirect(url_for("login"))

        # Création utilisateur
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )

        db.session.add(user)
        db.session.commit()

        flash("Inscription réussie.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ============================================================
# CONNEXION
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Gère l'authentification utilisateur.

    - Vérifie email et mot de passe
    - Initialise la session Flask
    - Injecte les données utilisateur dans la session (utile pour les templates)
    """

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Merci de remplir tous les champs.", "error")
            return render_template("login.html")

        user = User.query.filter_by(email=email).first()

        if user is None or not check_password_hash(user.password_hash, password):
            flash("Email ou mot de passe incorrect.", "error")
            return render_template("login.html")

        # Initialisation session complète
        session.clear()
        session["user_id"] = user.id
        session["role"] = user.role.value
        session["consent_given"] = user.consent_given

        # communication avec les templates
        session["first_name"] = user.first_name
        session["last_name"] = user.last_name
        session["email"] = user.email

        flash("Connexion réussie.", "success")

        if user.role == UserRole.PROFESSOR:
            return redirect(url_for("professor_dashboard"))

        return redirect(url_for("student_dashboard"))

    return render_template("login.html")


# ============================================================
# CONSENTEMENT RGPD
# ============================================================

@app.route("/consent", methods=["POST"])
def consent():
    """
    Enregistre le consentement RGPD de l'utilisateur.

    Fonctionnement :
    - Vérifie que l'utilisateur est connecté
    - Met à jour la base de données
    - Met à jour la session

    Returns:
        tuple: ("", 204) si succès, 403 sinon
    """

    if "user_id" not in session:
        return "", 403

    user = User.query.get(session["user_id"])
    user.consent_given = True
    db.session.commit()

    session["consent_given"] = True

    return "", 204


# ============================================================
# DECONNEXION
# ============================================================

@app.route("/logout")
def logout():
    """
    Déconnecte l'utilisateur.

    - Supprime toutes les données de session
    - Redirige vers la page de connexion
    """

    session.clear()
    flash("Vous avez été déconnecté.", "success")
    return redirect(url_for("login"))


# ============================================================
# DASHBOARDS
# ============================================================

@app.route("/dashboard/student")
def student_dashboard():
    """
    Dashboard étudiant.

    - Vérifie le rôle
    - Récupère les participations
    - Permet d'afficher les sessions rejointes
    """

    if session.get("role") != "student":
        flash("Accès refusé.", "error")
        return redirect(url_for("login"))

    # récupérer participations
    participations = Participation.query.filter_by(
        student_id=session["user_id"]
    ).all()

    return render_template(
        "student_dashboard.html",
        participations=participations
    )

@app.route("/dashboard/professor")
def professor_dashboard():
    """
    Dashboard professeur.

    - Vérifie le rôle
    - Récupère les sessions créées par le professeur
    - Envoie les données au template
    """

    if session.get("role") != "professor":
        flash("Accès refusé.", "error")
        return redirect(url_for("login"))

    # récupération sessions du professeur
    sessions = Session.query.filter_by(
        professor_id=session["user_id"]
    ).all()

    return render_template(
        "professor_dashboard.html",
        sessions=sessions
    )

# ============================================================
# CREATION DE SESSION
# ============================================================

@app.route("/create_session", methods=["POST"])
def create_session():
    """
    Création d'une session par un professeur.

    - Valide les données
    - Génère un code unique
    - Sauvegarde en base
    """

    if session.get("role") != "professor":
        return redirect(url_for("login"))

    freq_q = int(request.form["freq_questionnaire"])
    freq_w = int(request.form["freq_webcam"])
    mode = request.form["mode_affichage"]

    if freq_q <= 0 or freq_w <= 0:
        flash("Valeurs invalides.", "error")
        return redirect(url_for("professor_dashboard"))

    code = generate_session_code()

    new_session = Session(
        code_session=code,
        professor_id=session["user_id"],
        frequence_questionnaire=freq_q,
        frequence_webcam=freq_w,
        mode_affichage=mode
    )

    db.session.add(new_session)
    db.session.commit()

    flash(f"Session créée ! Code : {code}", "success")

    return redirect(url_for("professor_dashboard"))

# ============================================================
# REJOINDRE SESSION
# ============================================================

@app.route("/join_session", methods=["POST"])
def join_session():
    """
    Permet à un étudiant de rejoindre une session.

    - Vérifie le code session
    - Vérifie doublon
    - Insère participation
    """

    if session.get("role") != "student":
        return redirect(url_for("login"))

    code = request.form["code_session"].strip().upper()
    anonyme = "anonyme" in request.form
    webcam = "webcam" in request.form

    session_obj = Session.query.filter_by(code_session=code).first()

    if session_obj is None:
        flash("Code session invalide.", "error")
        return redirect(url_for("student_dashboard"))

    existing = Participation.query.filter_by(
        session_id=session_obj.id,
        student_id=session["user_id"]
    ).first()

    if existing:
        flash("Vous êtes déjà inscrit à cette session.", "warning")
        return redirect(url_for("student_dashboard"))

    participation = Participation(
        session_id=session_obj.id,
        student_id=session["user_id"],
        anonyme=anonyme,
        webcam_active=webcam
    )

    db.session.add(participation)
    db.session.commit()

    flash("Vous avez rejoint la session.", "success")
    return redirect(url_for("student_dashboard"))


# ============================================================
# LANCEMENT
# ============================================================




if __name__ == "__main__":
    # On récupère le port dynamique de Render, sinon 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    # On force l'hôte à 0.0.0.0 pour accepter les connexions externes
    app.run(host="0.0.0.0", port=port)