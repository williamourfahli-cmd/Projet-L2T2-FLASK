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
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests
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

# ============================================================
# RESULTATS SESSION (MODE COURBE)
# ============================================================

def normalize_emotion_label(raw_emotion):
    """
    Normalise les émotions provenant :
    - des QCM (émotions en français)
    - de DeepFace (émotions en anglais)

    Le but est d'obtenir un seul jeu d'émotions cohérent
    pour le graphique en bâtons de la page résultats.

    Args:
        raw_emotion (str): émotion brute lue en base

    Returns:
        str: émotion normalisée
    """
    if not raw_emotion:
        return "inconnu"

    emotion = raw_emotion.strip().lower()

    mapping = {
        # Emotions QCM
        "motivé": "motivé",
        "neutre": "neutre",
        "ennuye": "ennuyé",
        "stresse": "stressé",
        "demotive": "démotivé",

        # Emotions DeepFace
        "happy": "motivé",
        "neutral": "neutre",
        "surprise": "motivé",
        "fear": "stressé",
        "sad": "démotivé",
        "angry": "démotivé",
        "disgust": "démotivé"
    }

    return mapping.get(emotion, emotion)


def qcm_engagement_score(response):
    """
    Convertit une réponse QCM en score d'engagement sur 100.

    Logique choisie pour la V1 :
    - chaque émotion a un score de base
    - ce score est ensuite ajusté avec la valeur du slider (1 à 5)

    Exemple :
    - motivé + slider élevé => score fort
    - démotivé + slider faible => score bas

    Args:
        response (QCMResponse): objet ORM QCMResponse

    Returns:
        float: score d'engagement sur 100
    """
    base_scores = {
        "motivé": 100,
        "neutre": 60,
        "ennuye": 30,
        "stresse": 40,
        "demotive": 10
    }

    emotion = (response.emotion or "").strip().lower()
    base_score = base_scores.get(emotion, 50)

    # Valeur du slider sécurisée
    slider = response.slider_value if response.slider_value is not None else 3
    slider = max(1, min(slider, 5))

    # Le slider pondère légèrement le score
    slider_factor = slider / 5.0

    return round(base_score * slider_factor, 2)


def webcam_engagement_score(analysis):
    """
    Convertit une analyse webcam en score d'engagement sur 100.

    Logique choisie pour la V1 :
    - chaque émotion détectée par DeepFace a un score de base
    - le score est pondéré par la confiance de détection (0 à 100)

    Args:
        analysis (WebcamAnalysis): objet ORM WebcamAnalysis

    Returns:
        float: score d'engagement sur 100
    """
    base_scores = {
        "happy": 90,
        "neutral": 60,
        "surprise": 70,
        "fear": 25,
        "sad": 20,
        "angry": 15,
        "disgust": 10
    }

    emotion = (analysis.dominant_emotion or "").strip().lower()
    base_score = base_scores.get(emotion, 50)

    confidence = analysis.confidence if analysis.confidence is not None else 50.0
    confidence = max(0.0, min(confidence, 100.0))

    confidence_factor = confidence / 100.0

    return round(base_score * confidence_factor, 2)


def build_session_curve_data(session_id):
    """
    Prépare les données nécessaires à la page résultats
    pour le mode d'affichage "courbe".

    Cette fonction construit :
    1. une série temporelle pour la courbe d'engagement
    2. une répartition émotionnelle pour l'histogramme
    3. les compteurs utiles à afficher

    Méthode V1 :
    - on récupère toutes les réponses QCM de la session
    - on récupère toutes les analyses webcam de la session
    - on regroupe les scores par minute
    - on calcule une moyenne par minute
    - on compte les émotions globales

    Args:
        session_id (int): identifiant de la session

    Returns:
        dict: données prêtes à être envoyées au template
    """

    # ========================
    # 1. Récupération données QCM
    # ========================
    qcm_rows = QCMResponse.query.filter_by(
        session_id=session_id
    ).order_by(QCMResponse.answered_at.asc()).all()

    # ========================
    # 2. Récupération données webcam
    # ========================
    webcam_rows = WebcamAnalysis.query.filter_by(
        session_id=session_id
    ).order_by(WebcamAnalysis.analyzed_at.asc()).all()

    # ========================
    # 3. Préparation structure de courbe
    # ========================
    # Dictionnaire :
    # clé   = minute au format "YYYY-MM-DD HH:MM"
    # valeur = liste des scores tombant dans cette minute
    time_buckets = {}

    # ========================
    # 4. Préparation histogramme émotions
    # ========================
    emotion_counts = {
        "motivé": 0,
        "neutre": 0,
        "ennuyé": 0,
        "stressé": 0,
        "démotivé": 0
    }

    # ========================
    # 5. Traitement des réponses QCM
    # ========================
    for row in qcm_rows:

        # Sécurité si pas de date
        if not row.answered_at:
            continue

        # Regroupement par minute
        local_dt = row.answered_at.astimezone(ZoneInfo("Europe/Paris"))
        bucket = local_dt.strftime("%Y-%m-%d %H:%M")

        if bucket not in time_buckets:
            time_buckets[bucket] = []

        # Calcul du score d'engagement pour cette réponse
        score = qcm_engagement_score(row)
        time_buckets[bucket].append(score)

        # Comptage émotion normalisée
        normalized = normalize_emotion_label(row.emotion)
        if normalized in emotion_counts:
            emotion_counts[normalized] += 1

    # ========================
    # 6. Traitement des analyses webcam
    # ========================
    for row in webcam_rows:

        # Sécurité si pas de date
        if not row.analyzed_at:
            continue

        # Regroupement par minute
        local_dt = row.analyzed_at.astimezone(ZoneInfo("Europe/Paris"))
        bucket = local_dt.strftime("%Y-%m-%d %H:%M")

        if bucket not in time_buckets:
            time_buckets[bucket] = []

        # Calcul du score d'engagement webcam
        score = webcam_engagement_score(row)
        time_buckets[bucket].append(score)

        # Comptage émotion normalisée
        normalized = normalize_emotion_label(row.dominant_emotion)
        if normalized in emotion_counts:
            emotion_counts[normalized] += 1

    # ========================
    # 7. Construction finale de la courbe
    # ========================
    # On trie les minutes dans l'ordre chronologique
    sorted_keys = sorted(time_buckets.keys())

    engagement_labels = []
    engagement_values = []

    for key in sorted_keys:
        scores = time_buckets[key]

        # Moyenne des scores de la minute
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0

        # Pour le graphe, on n'affiche que HH:MM
        display_label = key[-5:]

        engagement_labels.append(display_label)
        engagement_values.append(avg_score)

    # ========================
    # 8. Construction histogramme émotions
    # ========================
    emotion_labels = list(emotion_counts.keys())
    emotion_values = list(emotion_counts.values())

    # ========================
    # 9. Retour final
    # ========================
    return {
        "engagement_labels": engagement_labels,
        "engagement_values": engagement_values,
        "emotion_labels": emotion_labels,
        "emotion_values": emotion_values,
        "qcm_count": len(qcm_rows),
        "webcam_count": len(webcam_rows)
    }

@app.template_filter('heure_fr')
def heure_fr(dt):
    """
    Traduit l'heure universelle en heure fr
    """
    if dt is None:
        return "En cours"
    return dt.astimezone(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y à %Hh%M")

def validate_email(email: str):
    """
    Valide une adresse email de manière générique.

    Règles :
    - Pas d'espaces
    - Format standard : texte@texte.domaine
    - Longueur raisonnable
    - Normalisation en minuscules

    Args:
        email (str): email saisi par l'utilisateur

    Returns:
        tuple:
            - bool : validité
            - str : email normalisé
            - str : message d'erreur éventuel
    """

    if not email:
        return False, None, "Email requis."

    # Nettoyage
    email = email.strip().lower()

    # Pas d'espaces
    if " " in email:
        return False, None, "L'adresse email ne doit pas contenir d'espaces."

    # Longueur
    if len(email) > 254:
        return False, None, "Email trop long."

    # Regex standard
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(pattern, email):
        return False, None, "Format d'email invalide."

    return True, email, None


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

        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role_input = request.form.get("role")

        # Validation basique
        if not all([first_name, last_name, email, password, role_input]):
            flash("Tous les champs sont obligatoires.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Mot de passe trop court.", "error")
            return render_template("register.html")

        # Validation email
        is_valid, email, error = validate_email(email)
        if not is_valid:
            flash(error, "error")
            return render_template("register.html")

        # Validation rôle
        if role_input == "student":
            role = UserRole.STUDENT
        elif role_input == "professor":
            role = UserRole.PROFESSOR
        else:
            flash("Rôle invalide.", "error")
            return render_template("register.html")

        # Vérif doublon
        if User.query.filter_by(email=email).first():
            flash("Un compte existe déjà.", "warning")
            return redirect(url_for("login"))

        # Création user
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

        # Envoi email
        confirm_url = url_for("confirm_email", token=token, _external=True)

        try:
            msg = Message(
                subject="Confirme ton compte",
                recipients=[email]
            )
            msg.html = render_template(
                "email_confirmation.html",
                first_name=first_name,
                confirm_url=confirm_url
            )
            mail.send(msg)

            flash("Inscription réussie ! Vérifie ta boîte mail.", "success")
            return redirect(url_for("login"))

        except Exception as e:
            print(e)
            flash("Compte créé mais email non envoyé.", "warning")
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
        date_debut = datetime.now(timezone.utc),
        frequence_questionnaire=freq_q,
        frequence_webcam=freq_w,
        mode_affichage=mode
    )

    db.session.add(new_session)
    db.session.commit()

    session.modified = True

    flash(f"Session créée ! Code : {code}", "success")

    return redirect(url_for("session_results", session_id=new_session.id))

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
    - Enregistre l'id de session dans la session Flask
    - Redirige vers le QCM
    """

    print("=== /join_session called ===")
    print(f"user_id = {session.get('user_id')}")
    print(f"role = {session.get('role')}")

    # Vérification du rôle
    if session.get("role") != "student":
        print("Erreur: utilisateur non étudiant")
        return redirect(url_for("login"))

    # Récupération des données du formulaire
    code = request.form.get("code_session", "").strip().upper()
    anonymous = "anonymous" in request.form
    webcam_enabled = "webcam_enabled" in request.form

    print(f"code_session = {code}")
    print(f"anonymous = {anonymous}")
    print(f"webcam_enabled = {webcam_enabled}")

    if not code:
        print("Erreur: code session vide")
        flash("Veuillez entrer un code session.", "error")
        return redirect(url_for("student_dashboard"))

    # Recherche de la session
    session_obj = Session.query.filter_by(code_session=code).first()

    if session_obj is None:
        print("Erreur: session introuvable")
        flash("Code session invalide.", "error")
        return redirect(url_for("student_dashboard"))

    print(f"session_obj.id = {session_obj.id}")
    print(f"session_obj.is_active = {session_obj.is_active}")

    # Vérification que la session est active
    if not session_obj.is_active:
        print("Erreur: session inactive")
        flash("Cette session est terminée.", "error")
        return redirect(url_for("student_dashboard"))

    # Vérification d'inscription existante
    existing = Participation.query.filter_by(
        session_id=session_obj.id,
        student_id=session["user_id"]
    ).first()

    if existing:
        print("Erreur: participation déjà existante")
        flash("Vous êtes déjà inscrit à cette session.", "warning")
        return redirect(url_for("student_dashboard"))

    # Création de la participation
    try:
        participation = Participation(
            session_id=session_obj.id,
            student_id=session["user_id"],
            anonymous=anonymous,
            webcam_enabled=webcam_enabled
        )

        db.session.add(participation)
        db.session.commit()

        print("Participation enregistrée en base")
        print(f"participation.id = {participation.id}")

    except Exception as e:
        db.session.rollback()
        print(f"Erreur DB join_session: {e}")
        flash("Erreur lors de l'inscription à la session.", "error")
        return redirect(url_for("student_dashboard"))

    # Initialisation session Flask
    session["phase"] = "avant"
    session["current_session_id"] = session_obj.id
    session.modified = True

    print(f"session['phase'] = {session.get('phase')}")
    print(f"session['current_session_id'] = {session.get('current_session_id')}")
    print("Redirection vers /qcm")

    return redirect(url_for("qcm"))
    

# ============================================================
# Questionnaires (Mesure subjective)
# ============================================================   


@app.route("/qcm")
def qcm():
    """
    Affiche le questionnaire étudiant en fonction de la phase.

    Fonctionnement :
    - Vérifie que l'utilisateur est authentifié et est un étudiant
    - Vérifie qu'une session est en cours côté serveur
    - Vérifie que l'utilisateur participe à la session
    - Récupère la session en base
    - Si la session est terminée, force la phase "apres"
    - Si le QCM "avant" a déjà été répondu, passe automatiquement en "pendant"
    - Envoie les données nécessaires au template
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

    # Récupération session en base
    session_obj = Session.query.get(session_id)
    if not session_obj:
        return redirect(url_for("student_dashboard"))

    # Si le professeur a terminé la session → phase finale
    if not session_obj.is_active:
        session["phase"] = "apres"

    # Récupération de la phase actuelle (source de vérité serveur)
    phase = session.get("phase", "avant")

    # Transition automatique : si "avant" déjà répondu → passer en "pendant"
    if phase == "avant":
        already_answered = QCMResponse.query.filter_by(
            session_id=session_id,
            user_id=session["user_id"],
            phase="avant"
        ).first()

        if already_answered:
            phase = "pendant"
            session["phase"] = "pendant"

    # Envoi des données au template
    return render_template(
        "qcm.html",
        session_id=session_id,
        freq=session_obj.frequence_questionnaire,
        freq_webcam=session_obj.frequence_webcam,
        phase=phase,
        webcam_active=participation.webcam_enabled
    )

@app.route("/qcm/submit", methods=["POST"])
def submit_qcm():
    """
    Enregistre une réponse QCM de manière sécurisée.

    Fonctionnement :
    - Vérifie que l'utilisateur est authentifié
    - Récupère la session active côté serveur
    - Vérifie que la session existe et est active (ou en phase finale)
    - Vérifie que l'utilisateur participe à la session
    - Détermine la phase côté serveur (ignore le client)
    - Valide les données reçues (emotion, slider_value)
    - Calcule automatiquement l'occurrence
    - Enregistre la réponse en base
    - Gère les erreurs (doublons, erreurs serveur)
    - Met à jour la phase si nécessaire
    """

    # Vérification authentification
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    # Récupération session active
    session_id = session.get("current_session_id")
    if not session_id:
        return jsonify({"error": "No active session"}), 400

    # Récupération JSON
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "Missing JSON payload"}), 400

    # Récupération session DB
    session_obj = Session.query.get(session_id)
    if not session_obj:
        return jsonify({"error": "Session not found"}), 404

    # Vérification participation
    participant = Participation.query.filter_by(
        session_id=session_id,
        student_id=session["user_id"]
    ).first()

    if not participant:
        return jsonify({"error": "Unauthorized"}), 403

    # Détermination de la phase côté serveur
    # Si session terminée → phase "apres"
    if not session_obj.is_active:
        phase = "apres"
        session["phase"] = "apres"
    else:
        phase = session.get("phase", "avant")

    # Récupération des données
    emotion = payload.get("emotion")
    slider_value = payload.get("slider_value")

    # Validation des émotions autorisées
    allowed_emotions = [
        "motivé", "neutre", "ennuye", "stresse", "demotive"
    ]

    if emotion not in allowed_emotions:
        return jsonify({"error": "Invalid emotion"}), 400

    # Validation slider
    try:
        slider_value = int(slider_value)
        if not (1 <= slider_value <= 5):
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid slider value"}), 400

    # Calcul sécurisé de l'occurrence
    last_response = QCMResponse.query.filter_by(
        session_id=session_id,
        user_id=session["user_id"]
    ).order_by(QCMResponse.occurrence.desc()).first()

    occurrence = (last_response.occurrence + 1) if last_response else 1

    # Création réponse
    response = QCMResponse(
        session_id=session_id,
        user_id=session["user_id"],
        phase=phase,
        emotion=emotion,
        slider_value=slider_value,
        occurrence=occurrence
    )

    # Sauvegarde DB
    try:
        db.session.add(response)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Already submitted"}), 400

    except Exception:
        db.session.rollback()
        return jsonify({"error": "Server error"}), 500

    # Transition de phase (avant → pendant uniquement)
    if session.get("phase") == "avant":
        session["phase"] = "pendant"
    # Si c'était le QCM final → on nettoie la session
    if phase == "apres":
        session.pop("current_session_id", None)
        session.pop("phase", None)

    return jsonify({"ok": True})

# ============================================================
# Fermer une session en cours (coté professeur)
# ============================================================


@app.route("/end_session/<int:session_id>", methods=["POST"])
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

            current_sess.date_fin = datetime.now(timezone.utc) 

            
            # Validation des modifications dans la base de données SQL
            db.session.commit()
            
            # Nettoyage de la variable de session Flask pour éviter les conflits d'ID
            if session.get("current_session_id") == session_id:
                session.pop("current_session_id", None)
            
            flash(f"La session '{current_sess.code_session}' a été fermée avec succès.", "success")
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


@app.route("/leave_session", methods=["POST"])
def leave_session():
    """
    Permet à un étudiant de quitter une session proprement.

    Fonctionnement :
    - Ne supprime PAS immédiatement la session
    - Force la phase "apres"
    - Redirige vers le QCM final
    """

    if "user_id" not in session:
        return redirect(url_for("login"))

    # Si pas de session → retour dashboard
    if not session.get("current_session_id"):
        return redirect(url_for("student_dashboard"))

    # On force la phase finale
    session["phase"] = "apres"
    session.modified = True

    # On renvoie vers le QCM final
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
        return jsonify({"status": "no_session"})

    session_obj = Session.query.get(session_id)

    if not session_obj:
        return jsonify({"status": "not_found"})

    if not session_obj.is_active:
        return jsonify({"status": "ended"})

    return jsonify({"status": "active"})

# ============================================================
# ANALYSE WEBCAM DEEPFACE
# ============================================================

@app.route("/analyze_webcam", methods=["POST"])
def analyze_webcam():
    """
    Reçoit une image webcam depuis le front,
    l'envoie au serveur DeepFace Hugging Face,
    puis enregistre le résultat en base.

    Sécurités ajoutées :
    - vérification utilisateur connecté
    - vérification session active côté Flask
    - vérification payload JSON
    - vérification image présente et non vide
    - vérification configuration DeepFace
    - gestion propre des erreurs réseau / réponse HF / base de données
    """

    print("=== /analyze_webcam called ===")

    # Vérification authentification
    if "user_id" not in session:
        print("Erreur: utilisateur non authentifié")
        return jsonify({"error": "Non authentifié"}), 401

    user_id = session.get("user_id")
    current_session_id = session.get("current_session_id")

    print(f"user_id = {user_id}")
    print(f"current_session_id = {current_session_id}")

    # Vérification session active
    if not current_session_id:
        print("Erreur: aucune session active dans la session Flask")
        return jsonify({"error": "Aucune session active"}), 400

    # Vérification présence payload JSON
    data = request.get_json(silent=True)
    if not data:
        print("Erreur: payload JSON absent")
        return jsonify({"error": "Payload JSON invalide"}), 400

    # Vérification présence image
    image_b64 = data.get("image")
    if not image_b64:
        print("Erreur: image absente du payload")
        return jsonify({"error": "Image manquante"}), 400

    # Sécurité minimale : évite d'envoyer à HF une image vide ou quasi vide
    if len(image_b64.strip()) < 50:
        print("Erreur: image vide ou trop courte")
        return jsonify({"error": "Image vide"}), 400

    # Vérification configuration DeepFace
    deepface_url = os.environ.get("DEEPFACE_URL", "").strip()
    deepface_secret = os.environ.get("DEEPFACE_SECRET_KEY", "").strip()

    print(f"deepface_url = {deepface_url}")
    print(f"deepface_secret_present = {bool(deepface_secret)}")

    if not deepface_url:
        print("Erreur: DEEPFACE_URL manquant")
        return jsonify({"error": "Configuration DeepFace manquante"}), 500

    if not deepface_secret:
        print("Erreur: DEEPFACE_SECRET_KEY manquant")
        return jsonify({"error": "Clé secrète DeepFace manquante"}), 500

    # Appel au serveur Hugging Face
    try:
        payload = {
            "image": image_b64,
            "secret_key": deepface_secret
        }

        print("Envoi de la requête au serveur DeepFace...")

        response = requests.post(
            f"{deepface_url}/analyze",
            json=payload,
            timeout=30
        )

        print(f"HF status_code = {response.status_code}")
        print(f"HF response text = {response.text}")

    except requests.RequestException as e:
        print(f"Erreur réseau vers DeepFace: {e}")
        return jsonify({"error": "Impossible de contacter le serveur DeepFace"}), 502

    # Vérification réponse HF
    if response.status_code != 200:
        print("Erreur: réponse non 200 du serveur DeepFace")
        return jsonify({
            "error": "Erreur serveur DeepFace",
            "details": response.text
        }), 502

    # Vérification parsing JSON de la réponse HF
    try:
        result = response.json()
    except Exception as e:
        print(f"Erreur parsing JSON HF: {e}")
        return jsonify({"error": "Réponse JSON DeepFace invalide"}), 502

    emotion = result.get("emotion")
    confidence = result.get("confidence")
    all_emotions = result.get("all_emotions", {})

    print(f"emotion = {emotion}")
    print(f"confidence = {confidence}")
    print(f"all_emotions = {all_emotions}")

    # Vérification minimale du contenu renvoyé par HF
    if not emotion:
        print("Erreur: emotion absente dans la réponse HF")
        return jsonify({"error": "Emotion absente dans la réponse DeepFace"}), 502

    # Sauvegarde en base
    try:
        analysis = WebcamAnalysis(
            session_id=current_session_id,
            user_id=user_id,
            dominant_emotion=emotion,
            confidence=float(confidence) if confidence is not None else None,
            all_emotions=json.dumps(all_emotions)
        )

        print("Tentative d'enregistrement en base...")

        db.session.add(analysis)
        db.session.commit()

        print("Enregistrement DB OK")
        print(f"analysis.id = {analysis.id}")

        return jsonify({
            "ok": True,
            "emotion": emotion,
            "confidence": confidence,
            "all_emotions": all_emotions
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Erreur DB: {e}")
        return jsonify({"error": "Erreur lors de l'enregistrement en base"}), 500


@app.route("/session/<int:session_id>/results")
def session_results(session_id):
    """
    Affiche la page de résultats d'une session côté professeur.

    Fonctionnement :
    - vérifie que l'utilisateur connecté est bien un professeur
    - vérifie que la session demandée existe
    - vérifie que le professeur connecté est bien le créateur de la session
    - récupère les statistiques générales de la session
    - construit les données nécessaires au mode "courbe"
    - affiche le template result.html

    Args:
        session_id (int): identifiant de la session demandé dans l'URL

    Returns:
        HTML: page de résultats ou redirection sécurisée
    """

    # Vérification du rôle utilisateur
    if session.get("role") != "professor":
        flash("Accès réservé au professeur.", "error")
        return redirect(url_for("login"))

    # Recherche de la session en base
    session_obj = Session.query.get(session_id)

    if not session_obj:
        flash("Session introuvable.", "error")
        return redirect(url_for("professor_dashboard"))

    # Vérification de sécurité :
    # seul le professeur qui a créé la session peut voir ses résultats
    if session_obj.professor_id != session.get("user_id"):
        flash("Accès non autorisé à cette session.", "error")
        return redirect(url_for("professor_dashboard"))

    # Comptage du nombre d'étudiants participants
    participants_count = Participation.query.filter_by(
        session_id=session_id
    ).count()

    # Récupération du mode d'affichage choisi à la création
    mode = (session_obj.mode_affichage or "").strip().lower()

    # Construction des données pour les graphiques
    curve_data = build_session_curve_data(session_id)

    # Envoi de toutes les données au template HTML
    return render_template(
        "result.html",
        session_obj=session_obj,
        mode=mode,
        participants_count=participants_count,
        engagement_labels=curve_data["engagement_labels"],
        engagement_values=curve_data["engagement_values"],
        emotion_labels=curve_data["emotion_labels"],
        emotion_values=curve_data["emotion_values"],
        qcm_count=curve_data["qcm_count"],
        webcam_count=curve_data["webcam_count"]
    )

@app.route("/session/<int:session_id>/results/data")
def session_results_data(session_id):
    """
    Retourne les données JSON de la page résultats.

    Cette route est utilisée par le JavaScript pour rafraîchir
    automatiquement les graphiques sans recharger toute la page.
    """

    # Sécurité : accès réservé au professeur
    if session.get("role") != "professor":
        return jsonify({"error": "Accès refusé"}), 403

    # Recherche de la session
    session_obj = Session.query.get(session_id)

    if not session_obj:
        return jsonify({"error": "Session introuvable"}), 404

    # Vérification de sécurité :
    # seul le professeur créateur peut consulter les données
    if session_obj.professor_id != session.get("user_id"):
        return jsonify({"error": "Accès non autorisé"}), 403

    # Nombre de participants
    participants_count = Participation.query.filter_by(
        session_id=session_id
    ).count()

    # Récupération des données de courbe
    curve_data = build_session_curve_data(session_id)

    return jsonify({
        "ok": True,
        "participants_count": participants_count,
        "qcm_count": curve_data["qcm_count"],
        "webcam_count": curve_data["webcam_count"],
        "session_is_active": session_obj.is_active,
        "engagement_labels": curve_data["engagement_labels"],
        "engagement_values": curve_data["engagement_values"],
        "emotion_labels": curve_data["emotion_labels"],
        "emotion_values": curve_data["emotion_values"]
    })
        
# ============================================================
# LANCEMENT
# ============================================================




if __name__ == "__main__":
    # On récupère le port dynamique de Render, sinon 5000 par défaut
    port = int(os.environ.get("PORT", 5000))
    # On force l'hôte à 0.0.0.0 pour accepter les connexions externes
    app.run(host="0.0.0.0", port=port)
