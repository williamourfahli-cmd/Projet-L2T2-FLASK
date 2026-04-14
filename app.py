import os  
import re
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from models import db, User, Session, Participation, UserRole, QCMResponse, WebcamAnalysis
# ============================================================
# INITIALISATION & CONFIGURATION OPTIMISÉE POUR RENDER
# ============================================================

app = Flask(__name__)

# Récupération de l'URL Render (Variable d'environnement)
uri = os.environ.get("DATABASE_URL")

if uri:
    # Correction indispensable du dialecte pour PostgreSQL
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
else:
    # Fallback sur SQLite pour tes tests en local sur ton PC
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Utilisation d'une variable d'env pour la sécurité (Cybersécurité)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-a-changer-en-prod")

# Liaison de SQLAlchemy à l'application
db.init_app(app)

# Création automatique des tables au démarrage du serveur
with app.app_context():
    try:
        db.create_all()
        print("✅ Base de données connectée et tables créées/vérifiées !")
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation de la base : {e}")

# ============================================================
# FONCTIONS UTILITAIRES (Le reste de ton code commence ici)
# ============================================================

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

    Fonctionnement :
    - Vérifie que l'utilisateur est un étudiant
    - Vérifie que la session existe et est active
    - Vérifie qu'il n'est pas déjà inscrit
    - Crée une participation
    - Initialise la phase à "avant"
    - Redirige vers le QCM
    """

    # Vérification du rôle
    if session.get("role") != "student":
        return redirect(url_for("login"))

    # Récupération des données du formulaire
    code = request.form["code_session"].strip().upper()
    anonyme = "anonyme" in request.form
    webcam = "webcam" in request.form

    # Recherche de la session
    session_obj = Session.query.filter_by(code_session=code).first()

    if session_obj is None:
        flash("Code session invalide.", "error")
        return redirect(url_for("student_dashboard"))

    # Vérification que la session est active
    if not session_obj.is_active:
        flash("Cette session est terminée.", "error")
        return redirect(url_for("student_dashboard"))

    # Vérification d'inscription existante
    existing = Participation.query.filter_by(
        session_id=session_obj.id,
        student_id=session["user_id"]
    ).first()

    if existing:
        flash("Vous êtes déjà inscrit à cette session.", "warning")
        return redirect(url_for("student_dashboard"))

    # Création de la participation
    participation = Participation(
        session_id=session_obj.id,
        student_id=session["user_id"],
        anonyme=anonyme,
        webcam_active=webcam
    )

    db.session.add(participation)
    db.session.commit()

    # Initialisation de la phase (IMPORTANT)
    session["phase"] = "avant"
    session["current_session_id"] = session_obj.id

    return redirect(url_for("qcm"))
    

# ============================================================
# Questionnaires (Mesure subjective)
# ============================================================   


@app.route("/qcm")
def qcm():
    """
    Affiche le questionnaire étudiant en fonction de la phase.

    Fonctionnement :
    - Vérifie authentification et rôle
    - Vérifie participation à la session
    - Récupère la session en base
    - Si session terminée → force phase "apres"
    - Sinon récupère la phase actuelle (avant / pendant)
    - Envoie les données au template
    """

    # Vérification authentification
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Vérification rôle
    if session.get("role") != "student":
        return redirect(url_for("login"))

    # Récupération session en cours
    session_id = session.get("current_session_id")

    if not session_id:
        return redirect(url_for("student_dashboard"))

    # Vérification participation
    participation = Participation.query.filter_by(
        session_id=session_id,
        student_id=session["user_id"]
    ).first()

    if not participation:
        return redirect(url_for("student_dashboard"))

    # Récupération session DB
    session_obj = Session.query.get(session_id)

    if not session_obj:
        return redirect(url_for("student_dashboard"))

    # Gestion des phases des questionnaires
    # Si le prof a terminé la session → phase finale
    if not session_obj.is_active:
        session["phase"] = "apres"

    # Sinon récupérer la phase actuelle
    phase = session.get("phase", "avant")

    return render_template(
        "qcm.html",
        session_id=session_id,
        freq=session_obj.frequence_questionnaire,
        freq_webcam=session_obj.frequence_webcam,
        phase=phase,
        webcam_active=participation.webcam_active
)

@app.route("/qcm/submit", methods=["POST"])
def submit_qcm():
    """
    Enregistre une réponse QCM.

    Fonctionnement :
    - Vérifie authentification
    - Vérifie validité des données
    - Vérifie que la session est active
    - Vérifie participation
    - Enregistre la réponse
    - Gère les doublons
    - Gère la transition de phase (avant → pendant)
    """

    # Vérification authentification
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    # Récupération JSON
    payload = request.get_json()

    if not payload:
        return jsonify({"error": "Missing JSON payload"}), 400

    # Extraction des données
    try:
        session_id = int(payload.get("session_id"))
        occurrence = int(payload.get("occurrence", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid session_id or occurrence"}), 400

    phase     = payload.get("phase")
    emotion   = payload.get("emotion")
    intensity = payload.get("intensity")
    slider    = payload.get("slider_value")

    if not phase:
        return jsonify({"error": "Missing phase"}), 400

    # ================================
    # Vérification session active
    # ================================

    session_obj = Session.query.get(session_id)

    if not session_obj:
        return jsonify({"error": "Session not found"}), 404

    if not session_obj.is_active:
        return jsonify({"error": "Session terminée"}), 403

    # ================================
    # Vérification participation
    # ================================

    participant = Participation.query.filter_by(
        session_id=session_id,
        student_id=session["user_id"]
    ).first()

    if not participant:
        return jsonify({"error": "Unauthorized"}), 403

    # ================================
    # Création réponse
    # ================================

    response = QCMResponse(
        session_id=session_id,
        user_id=session["user_id"],
        phase=phase,
        emotion=emotion,
        intensity=intensity,
        slider_value=slider,
        occurrence=occurrence
    )

    # ================================
    # Sauvegarde DB
    # ================================

    try:
        db.session.add(response)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Already submitted"}), 400

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Server error"}), 500

    # ================================
    # TRANSITION DE PHASE
    # ================================

    # Si c'était le QCM "avant" → passer en "pendant"
    if session.get("phase") == "avant":
        session["phase"] = "pendant"

    return jsonify({"ok": True})


# ============================================================
# Fermer une session en cours (coté professeur)
# ============================================================


@app.route("/end_session/<int:session_id>", methods=["POST"])
def end_session(session_id):
    """
    Permet à un professeur de terminer une session.

    Fonctionnement :
    - Vérifie que l'utilisateur est un professeur
    - Récupère la session concernée
    - Passe la session en inactive (is_active = False)
    - Enregistre la date de fin
    - Empêche toute nouvelle interaction des étudiants

    Args:
        session_id (int): identifiant de la session à fermer

    Returns:
        Redirection vers le dashboard professeur
    """

    # Vérification du rôle utilisateur
    if session.get("role") != "professor":
        return redirect(url_for("login"))

    # Récupération de la session
    session_obj = Session.query.get(session_id)

    if not session_obj:
        return redirect(url_for("professor_dashboard"))

    # Mise à jour de l'état de la session
    session_obj.is_active = False
    session_obj.date_fin = datetime.utcnow()

    # Sauvegarde en base
    db.session.commit()

    flash("Session terminée.", "success")

    return redirect(url_for("professor_dashboard"))



# ============================================================
# Quitter une session (coté étudiant)
# ============================================================


@app.route("/leave_session", methods=["POST"])
def leave_session():
    """
    Permet à un étudiant de quitter une session.

    Fonctionnement :
    - Vérifie authentification
    - Vérifie qu'une session est active
    - Passe la phase à "apres"
    - Redirige vers le QCM final
    """

    # Vérification authentification
    if "user_id" not in session:
        return redirect(url_for("login"))

    session_id = session.get("current_session_id")

    if not session_id:
        return redirect(url_for("student_dashboard"))

    # Passage en phase finale
    session["phase"] = "apres"

    return redirect(url_for("qcm"))


# ============================================================
# Vérification de l'état de la session
# ============================================================

@app.route("/check_session_status")
def check_session_status():
    """
    Vérifie si la session est active et si l'utilisateur est dans une session.
    """

    session_id = session.get("current_session_id")

    if not session_id:
        return {"status": "no_session"}

    session_obj = Session.query.get(session_id)

    if not session_obj:
        return {"status": "not_found"}

    if not session_obj.is_active:
        return {"status": "ended"}

    return {"status": "active"}

# ============================================================
# ANALYSE WEBCAM DEEPFACE
# ============================================================

@app.route("/analyze_webcam", methods=["POST"])
def analyze_webcam():
    """
    Reçoit une image base64 depuis le frontend,
    analyse l'émotion avec DeepFace et sauvegarde le résultat.
    """

    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    payload = request.get_json()
    if not payload or "image" not in payload:
        return jsonify({"error": "Missing image"}), 400

    session_id = payload.get("session_id")
    image_data = payload.get("image")

    try:
        import base64
        import numpy as np
        import cv2
        from deepface import DeepFace

        # Décoder l'image base64
        header, encoded = image_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # Analyse DeepFace
        result = DeepFace.analyze(
            img,
            actions=["emotion"],
            enforce_detection=False,
            detector_backend="opencv"
        )

        dominant_emotion = result[0]["dominant_emotion"]
        emotions = result[0]["emotion"]
        confidence = emotions[dominant_emotion]

        import json
        analysis = WebcamAnalysis(
            session_id=session_id,
            user_id=session["user_id"],
            emotion=dominant_emotion,
            confidence=confidence,
            all_emotions=json.dumps(emotions)
        )

        db.session.add(analysis)
        db.session.commit()

        return jsonify({
            "ok": True,
            "emotion": dominant_emotion,
            "confidence": round(confidence, 2)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/deepface")
def deepface():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("role") != "student":
        return redirect(url_for("login"))
    
    session_id = session.get("current_session_id")
    if not session_id:
        return redirect(url_for("student_dashboard"))

    session_obj = Session.query.get(session_id)

    return render_template(
        "deepface.html",
        session_id=session_id,
        freq_webcam=session_obj.frequence_webcam
    )

# ============================================================
# LANCEMENT
# ============================================================




if __name__ == "__main__":
    # On récupère le port dynamique de Render, sinon 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    # On force l'hôte à 0.0.0.0 pour accepter les connexions externes
    app.run(host="0.0.0.0", port=port)