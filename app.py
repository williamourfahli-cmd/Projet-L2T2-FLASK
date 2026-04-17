import os
#os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' # Cache les warnings TF
#os.environ['CUDA_VISIBLE_DEVICES'] = '-1' # Force le mode CPU uniquement
import re
import random
import string
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from models import db, User, Session, Participation, UserRole, QCMResponse, WebcamAnalysis
import base64
import numpy as np
#import cv2
import json
#from deepface import DeepFace
from datetime import datetime
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
app.config["SESSION_COOKIE_SAMESITE"] = 'Lax'
app.config["PERMANENT_SESSION_LIFETIME"] = 7200

# ============================================================
# CONFIGURATION FLASK-MAIL
# ============================================================
# Ces variables doivent être définies dans les variables d'environnement Render :
# MAIL_USERNAME : votre adresse Gmail (ex: emotrack.noreply@gmail.com)
# MAIL_PASSWORD : mot de passe d'application Gmail (pas votre vrai mdp)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")
 
mail = Mail(app)

# Liaison de SQLAlchemy à l'application
db.init_app(app)

# Création automatique des tables au démarrage du serveur
with app.app_context():
    try:
        db.create_all()
        print("Base de données connectée et tables créées/vérifiées !")
        inspector = db.inspect(db.engine)
        existing_columns = [col["name"] for col in inspector.get_columns("users")]
 
        with db.engine.connect() as conn:
            if "email_verified" not in existing_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE"))
                print(" Colonne email_verified ajoutée.")
            if "verification_token" not in existing_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN verification_token VARCHAR(100)"))
                print("Colonne verification_token ajoutée.")
            conn.commit()
 
    except Exception as e:
        print(f" Erreur lors de l'initialisation de la base : {e}")

# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def analyze_face(image_data):
    """
    Simule l'analyse DeepFace pour alléger le serveur Render.
    """
    # On définit une émotion fixe pour les tests
    dominant_emotion = "neutral"
    emotions_dict = {
        "angry": 0.0, "disgust": 0.0, "fear": 0.0, 
        "happy": 0.0, "sad": 0.0, "surprise": 0.0, "neutral": 100.0
    }
    confidence = 100.0

    return dominant_emotion, confidence, emotions_dict
    

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
    - vers la page landing (page d'accueil) sinon

    Returns:
        Redirection Flask
    """
    if "user_id" in session:
        if session.get("role") == "professor":
            return redirect(url_for("professor_dashboard"))
        return redirect(url_for("student_dashboard"))

    return render_template("landing.html")


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
        token = secrets.token_urlsafe(32)
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            email_verified=False,
            verification_token=token
        )

        db.session.add(user)
        db.session.commit()

         # Envoi de l'email de confirmation
        confirm_url = url_for("confirm_email", token=token, _external=True)
        try:
            msg = Message(
                subject="Confirmez votre inscription sur EmoTrack",
                recipients=[email]
            )
            msg.html = render_template(
                "email_confirmation.html",
                first_name=first_name,
                confirm_url=confirm_url
            )    
            mail.send(msg)
            flash("Inscription réussie ! Vérifie ta boîte mail pour confirmer ton adresse.", "success")
        except Exception as e:
            print(f" Erreur envoi email : {e}")
            flash("Compte créé mais l'email de confirmation n'a pas pu être envoyé. Contacte un administrateur.", "warning")

        return redirect(url_for("login"))

    return render_template("register.html")

# ============================================================
# CONFIRMATION D'EMAIL
# ============================================================
 
@app.route("/confirm/<token>")
def confirm_email(token):
    """
    Valide l'adresse email de l'utilisateur via le token reçu par mail.
 
    - Cherche l'utilisateur correspondant au token
    - Passe email_verified à True
    - Supprime le token (usage unique)
    - Redirige vers la connexion
 
    Returns:
        Redirection Flask
    """
    user = User.query.filter_by(verification_token=token).first()
 
    if user is None:
        flash("Lien de confirmation invalide ou déjà utilisé.", "error")
        return redirect(url_for("login"))
 
    if user.email_verified:
        flash("Ton adresse email est déjà confirmée. Tu peux te connecter.", "success")
        return redirect(url_for("login"))
 
    # Activation du compte
    user.email_verified = True
    user.verification_token = None  # Token à usage unique : on le supprime
    db.session.commit()
 
    flash(" Adresse email confirmée ! Tu peux maintenant te connecter.", "success")
    return redirect(url_for("login"))
 

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

        # Vérification que l'email a été confirmé
        if not user.email_verified:
            flash("Tu dois confirmer ton adresse email avant de te connecter. Vérifie ta boîte mail.", "warning")
            return render_template("login.html")    

        # Initialisation session complète
        session.clear()

        session.permanent = True

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

    session.modified = True

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

    session.modified = True

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

    # Si déjà répondu au "avant", on passe en "pendant"
    if phase == "avant":
        already_answered = QCMResponse.query.filter_by(
            session_id=session_id,
            user_id=session["user_id"],
            phase="avant"
        ).first()

        if already_answered:
            phase = "pendant"
            session["phase"] = "pendant"

    return render_template(
        "mesures.html",
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


@app.route("/end_session/<int:session_id>")
def end_session(session_id):
    """
    Clôture une session d'examen et met à jour les états côté serveur et client.
    """
    # Vérification de sécurité : seul un utilisateur avec le rôle 'professor' peut fermer une session
    if session.get("role") != "professor":
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("login"))

    try:
        # Récupération de l'objet Session via l'ID passé dans l'URL
        current_sess = Session.query.get(session_id)
        
        if current_sess:
            # Mise à jour du statut en base de données pour stopper les flux de données
            current_sess.is_active = False
            
            # Enregistrement de l'horodatage de fin (utilise l'import datetime)
<<<<<<< Updated upstream
            current_sess.date_fin = datetime.now() 
=======
            current_sess.date_fin= datetime.now() 
>>>>>>> Stashed changes
            
            # Validation des modifications dans la base de données SQL
            db.session.commit()
            
            # Nettoyage de la variable de session Flask pour éviter les conflits d'ID
            if session.get("current_session_id") == session_id:
                session.pop("current_session_id", None)
            
            flash(f"La session '{current_sess.name}' a été fermée avec succès.", "success")
        else:
            flash("Session introuvable.", "warning")

    except Exception as e:
        # En cas d'erreur (ex: perte de connexion DB), on annule les modifications en cours
        db.session.rollback()
        # Log de l'erreur dans la console pour le débogage technique
        print(f"Erreur lors de la fermeture : {str(e)}")
        flash("Erreur critique lors de la fermeture de la session.", "danger")

    # Redirection vers le tableau de bord pour rafraîchir la liste des sessions
    return redirect(url_for("professor_dashboard"))



# ============================================================
# Quitter une session (coté étudiant)
# ============================================================


@app.route("/leave_session") 
def leave_session():
    """
    Permet à un étudiant de quitter une session proprement.
    """
    # 1. Nettoyage des variables de session
    session.pop("current_session_id", None)
    session.pop("phase", None)
    
    # 2. On force la sauvegarde de la session (pour éviter l'anomalie de reconnexion)
    session.modified = True
    
    # 3. Redirection directe vers le dashboard
    flash("Vous avez quitté la session.", "info")
    return redirect(url_for("student_dashboard"))


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

    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    payload = request.get_json()

    if not payload or "image" not in payload:
        return jsonify({"error": "Missing image"}), 400

    try:
        emotion, confidence, emotions_dict = analyze_face(payload["image"])

        # SAVE DB ICI (séparation)
        analysis = WebcamAnalysis(
            session_id=session.get("current_session_id"),
            user_id=session["user_id"],
            emotion=emotion,
            confidence=confidence,
            all_emotions=json.dumps(emotions_dict),
            timestamp=datetime.now()
        )

        db.session.add(analysis)
        db.session.commit()

        return jsonify({
            "status": "success",
            "emotion": emotion,
            "confidence": round(confidence, 2)
        })

    except Exception as e:
        db.session.rollback()
        print(f"DeepFace error: {e}")

        return jsonify({
            "status": "error",
            "message": "Analysis failed"
        }), 500
    

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

    participation = Participation.query.filter_by(
        session_id=session_id,
        student_id=session["user_id"]
    ).first()

    return render_template(
        "deepface.html",
        session_id=session_id,
        freq_webcam=session_obj.frequence_webcam,
        webcam_active=participation.webcam_active
)


# ============================================================
# LANCEMENT
# ============================================================




if __name__ == "__main__":
    # On récupère le port dynamique de Render, sinon 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    # On force l'hôte à 0.0.0.0 pour accepter les connexions externes
    app.run(host="0.0.0.0", port=port)
