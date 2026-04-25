from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import enum

# ============================================================
# INITIALISATION DE L'ORM
# ============================================================
# SQLAlchemy permet de manipuler la base de données sous forme
# d'objets Python (ORM : Object Relational Mapping)
db = SQLAlchemy()


# ============================================================
# ENUMERATION DES ROLES UTILISATEUR
# ============================================================
# Permet d'éviter les erreurs de chaînes de caractères
# et garantit que seuls les rôles autorisés sont utilisés
class UserRole(enum.Enum):
    STUDENT = "student"
    PROFESSOR = "professor"


# ============================================================
# TABLE USERS
# ============================================================
class User(db.Model):
    """
    Représente un utilisateur de l'application (étudiant ou professeur).
    """

    __tablename__ = 'users'  # Nom de la table en base

    # ========================
    # COLONNES
    # ========================

    # Clé primaire unique
    id = db.Column(db.Integer, primary_key=True)

    # Nom de famille (obligatoire)
    last_name = db.Column(db.String(50), nullable=False)

    # Prénom (obligatoire)
    first_name = db.Column(db.String(50), nullable=False)

    # Email unique (identifiant logique)
    email = db.Column(db.String(120), unique=True, nullable=False)

    # Mot de passe stocké sous forme hashée (sécurité)
    password_hash = db.Column(db.String(512), nullable=False)

    # Rôle utilisateur (student ou professor)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)

    # Consentement RGPD (important pour la webcam)
    consent_given = db.Column(db.Boolean, default=False, nullable=False) 

    # Vérification d'email : False jusqu'à ce que l'utilisateur clique sur le lien
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
 
    # Token unique envoyé par email pour confirmer l'inscription
    verification_token = db.Column(db.String(100), nullable=True)

    # Date de création du compte (en UTC)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # ========================
    # RELATIONS ORM
    # ========================

    # Un professeur peut créer plusieurs sessions
    sessions_created = db.relationship(
        'Session',
        backref='professor',
        lazy=True
    )

    # Un utilisateur (étudiant) peut avoir plusieurs participations
    participations = db.relationship(
        'Participation',
        backref='student',
        lazy=True
    )


# ============================================================
# TABLE SESSIONS
# ============================================================
class Session(db.Model):
    """
    Représente une session pédagogique créée par un professeur.
    """

    __tablename__ = 'sessions'

    # ========================
    # COLONNES
    # ========================

    # Identifiant unique
    id = db.Column(db.Integer, primary_key=True)

    # Code unique permettant aux étudiants de rejoindre la session
    code_session = db.Column(db.String(6), unique=True, nullable=False)

    # Clé étrangère vers le professeur créateur
    professor_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    # Date de début et de fin (optionnelles)
    date_debut = db.Column(db.DateTime)
    date_fin = db.Column(db.DateTime)

    # Fréquence d'analyse webcam (en secondes)
    frequence_webcam = db.Column(db.Integer, nullable=False)

    # Fréquence d'envoi des questionnaires (en secondes)
    frequence_questionnaire = db.Column(db.Integer, nullable=False)

    # Mode d'affichage des résultats (graph, moyenne, alerte)
    mode_affichage = db.Column(db.String(50), nullable=False)

    # Bool montrant si la session est encore active
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ========================
    # RELATIONS ORM
    # ========================

    # Une session possède plusieurs participations (étudiants)
    participations = db.relationship(
        'Participation',
        backref='session',
        lazy=True
    )


# ============================================================
# TABLE PARTICIPATIONS
# ============================================================
class Participation(db.Model):
    """
    Représente la participation d'un étudiant à une session.
    """

    __tablename__ = 'participations'

    # ========================
    # CONTRAINTES
    # ========================

    # Empêche un étudiant de rejoindre plusieurs fois la même session
    __table_args__ = (
        db.UniqueConstraint(
            'session_id',
            'student_id',
            name='unique_participation'
        ),
    )

    # ========================
    # COLONNES
    # ========================

    # Identifiant unique
    id = db.Column(db.Integer, primary_key=True)

    # Clé étrangère vers la session
    session_id = db.Column(
        db.Integer,
        db.ForeignKey('sessions.id'),
        nullable=False
    )

    # Clé étrangère vers l'étudiant
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    # Participation anonyme ou non
    anonymous = db.Column(db.Boolean, default=False)

    # Webcam activée ou non
    webcam_enabled = db.Column(db.Boolean, default=False)

    # Date de participation (UTC)
    date_join = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


# ============================================================
# TABLE QCM RESPONSES
# ============================================================
class QCMResponse(db.Model):
    """
    Représente une réponse d'un étudiant à un questionnaire (QCM).

    Une réponse est liée :
    - à une session
    - à un étudiant
    - à un moment (avant / pendant / après)

    Cette table permet de suivre l'évolution des émotions
    pendant toute la durée d'une session.
    """

    __tablename__ = 'qcm_responses'

    # ========================
    # CONTRAINTES
    # ========================

    # Empêche un étudiant d'envoyer plusieurs réponses
    # pour la même phase et occurrence
    __table_args__ = (
        db.UniqueConstraint(
            'session_id',
            'user_id',
            'phase',
            'occurrence',
            name='unique_qcm_response'
        ),
    )

    # ========================
    # COLONNES
    # ========================

    # Identifiant unique
    id = db.Column(db.Integer, primary_key=True)

    # Clé étrangère vers la session
    session_id = db.Column(
        db.Integer,
        db.ForeignKey('sessions.id'),
        nullable=False
    )

    # Clé étrangère vers l'utilisateur (étudiant)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    # Type de questionnaire :
    # "avant", "pendant", "apres"
    phase = db.Column(
        db.String(20),
        nullable=False
    )

    # Emotion sélectionnée (ex : "motivé", "fatigué")
    emotion = db.Column(
        db.String(50),
        nullable=True
    )

    # Valeur du slider (1 à 5 par exemple)
    slider_value = db.Column(
        db.Integer,
        nullable=True
    )

    # Numéro d'occurrence (utile pour les QCM "pendant")
    occurrence = db.Column(
        db.Integer,
        default=1,
        nullable=False
    )

    # Date de réponse
    answered_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ========================
    # RELATIONS ORM
    # ========================

    # Lien vers la session
    session = db.relationship(
        'Session',
        backref='qcm_responses',
        lazy=True
    )

    # Lien vers l'utilisateur
    user = db.relationship(
        'User',
        backref='qcm_responses',
        lazy=True
    )


 # ============================================================
# TABLE WEBCAM ANALYSIS
# ============================================================
class WebcamAnalysis(db.Model):
    """
    Stocke les résultats d'analyse d'émotions via DeepFace.
    """

    __tablename__ = 'webcam_analysis'

    id = db.Column(db.Integer, primary_key=True)

    session_id = db.Column(
        db.Integer,
        db.ForeignKey('sessions.id'),
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False
    )

    # Emotion dominante détectée par DeepFace
    dominant_emotion = db.Column(db.String(50), nullable=False)

    # Score de confiance (0 à 100)
    confidence = db.Column(db.Float, nullable=True)

    # Toutes les émotions avec leurs scores (JSON)
    all_emotions = db.Column(db.Text, nullable=True)

    # Date d'analyse
    analyzed_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
# ============================================================
# TABLE ALERTS                                                 
# ============================================================
class Alert(db.Model):
    """
    Stocke chaque alerte déclenchée pendant une session.

    level  : "individual" ou "class"
    source : "qcm"                 → alerte individuelle QCM
             "webcam"              → alerte individuelle DeepFace
             "class_snapshot"      → alerte de classe snapshot QCM
             "class_accumulation"  → alerte de classe accumulation individuelle
    """

    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)

    # Session concernée
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)

    # Étudiant concerné — NULL pour les alertes de classe
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # "individual" ou "class"
    level = db.Column(db.String(20), nullable=False)

    # "qcm", "webcam", "class_snapshot", "class_accumulation"
    source = db.Column(db.String(30), nullable=False)

    # Émotion dominante ayant déclenché l'alerte
    emotion = db.Column(db.String(50), nullable=True)

    # Ratio mesuré au déclenchement (ex: 0.65 = 65%)
    ratio = db.Column(db.Float, nullable=True)

    # Date de déclenchement UTC
    triggered_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    session = db.relationship('Session', backref='alerts', lazy=True)
    user = db.relationship('User', backref='alerts', lazy=True)
