from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import enum


# ============================================================
# INITIALISATION DE L'ORM
# ============================================================

# SQLAlchemy permet de manipuler la base de données sous forme d'objets Python.
# Chaque classe ci-dessous représente une table de la base de données.
db = SQLAlchemy()


# ============================================================
# ENUMERATION DES ROLES UTILISATEUR
# ============================================================

class UserRole(enum.Enum):
    """
    Définit les rôles possibles dans l'application.

    L'utilisation d'une énumération évite d'écrire directement
    des chaînes de caractères partout dans le code.
    """

    STUDENT = "student"
    PROFESSOR = "professor"


# ============================================================
# TABLE USERS
# ============================================================

class User(db.Model):
    """
    Représente un utilisateur de l'application.

    Un utilisateur peut être :
    - étudiant ;
    - professeur.

    Cette table contient les informations d'identification,
    le rôle, le consentement RGPD et la vérification email.
    """

    # Nom réel de la table en base de données
    __tablename__ = "users"

    # ========================
    # COLONNES
    # ========================

    # Identifiant unique de l'utilisateur
    id = db.Column(db.Integer, primary_key=True)

    # Nom de famille de l'utilisateur
    last_name = db.Column(db.String(50), nullable=False)

    # Prénom de l'utilisateur
    first_name = db.Column(db.String(50), nullable=False)

    # Adresse email utilisée comme identifiant de connexion
    # unique=True empêche deux comptes d'utiliser la même adresse
    email = db.Column(db.String(120), unique=True, nullable=False)

    # Mot de passe hashé.
    # On ne stocke jamais le mot de passe en clair en base.
    password_hash = db.Column(db.String(512), nullable=False)

    # Rôle de l'utilisateur : student ou professor
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)

    # Indique si l'utilisateur a accepté le consentement RGPD
    consent_given = db.Column(db.Boolean, default=False, nullable=False)

    # Indique si l'utilisateur a confirmé son adresse email
    email_verified = db.Column(db.Boolean, default=False, nullable=False)

    # Token envoyé par email pour confirmer le compte
    verification_token = db.Column(db.String(100), nullable=True)

    # Date de création du compte, stockée en UTC
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc)
    )

    # ========================
    # RELATIONS ORM
    # ========================

    # Liste des sessions créées par ce professeur.
    # Le backref "professor" permet d'accéder au professeur depuis une session.
    sessions_created = db.relationship(
        "Session",
        backref="professor",
        lazy=True
    )

    # Liste des participations de cet utilisateur en tant qu'étudiant.
    # Le backref "student" permet d'accéder à l'étudiant depuis une participation.
    participations = db.relationship(
        "Participation",
        backref="student",
        lazy=True
    )


# ============================================================
# TABLE SESSIONS
# ============================================================

class Session(db.Model):
    """
    Représente une session pédagogique créée par un professeur.

    Une session possède :
    - un code que les étudiants utilisent pour la rejoindre ;
    - des fréquences de questionnaire et de webcam ;
    - des modes d'affichage ;
    - des seuils d'alerte ;
    - un état actif ou terminé.
    """

    __tablename__ = "sessions"

    # ========================
    # COLONNES
    # ========================

    # Identifiant unique de la session
    id = db.Column(db.Integer, primary_key=True)

    # Code court permettant aux étudiants de rejoindre la session
    code_session = db.Column(db.String(6), unique=True, nullable=False)

    # Identifiant du professeur créateur de la session
    professor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Date de début de la session
    date_debut = db.Column(db.DateTime)

    # Date de fin de la session, renseignée lorsque le professeur la ferme
    date_fin = db.Column(db.DateTime)

    # Fréquence d'analyse webcam
    frequence_webcam = db.Column(db.Integer, nullable=False)

    # Fréquence d'affichage des questionnaires
    frequence_questionnaire = db.Column(db.Integer, nullable=False)

    # Modes d'affichage sélectionnés par le professeur
    # Exemple : "courbes,moyennes,alertes"
    mode_affichage = db.Column(db.String(50), nullable=False)

    # Seuil individuel utilisé pour déclencher une alerte étudiant
    # Exemple : 0.60 signifie 60 %
    seuil_individuel = db.Column(db.Float, nullable=False, default=0.60)

    # Seuil collectif utilisé pour déclencher une alerte de classe
    # Exemple : 0.50 signifie 50 %
    seuil_classe = db.Column(db.Float, nullable=False, default=0.50)

    # Indique si la session est encore active
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ========================
    # RELATIONS ORM
    # ========================

    # Liste des participations liées à cette session
    participations = db.relationship(
        "Participation",
        backref="session",
        lazy=True
    )


# ============================================================
# TABLE PARTICIPATIONS
# ============================================================

class Participation(db.Model):
    """
    Représente la participation d'un étudiant à une session.

    Cette table fait le lien entre :
    - un étudiant ;
    - une session ;
    - ses choix de participation : anonymat et webcam.
    """

    __tablename__ = "participations"

    # ========================
    # CONTRAINTES
    # ========================

    # Empêche un même étudiant de rejoindre plusieurs fois la même session
    __table_args__ = (
        db.UniqueConstraint(
            "session_id",
            "student_id",
            name="unique_participation"
        ),
    )

    # ========================
    # COLONNES
    # ========================

    # Identifiant unique de la participation
    id = db.Column(db.Integer, primary_key=True)

    # Identifiant de la session rejointe
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("sessions.id"),
        nullable=False
    )

    # Identifiant de l'étudiant participant
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Indique si l'étudiant souhaite apparaître anonymement côté professeur
    anonymous = db.Column(db.Boolean, default=False)

    # Indique si l'étudiant autorise l'analyse webcam pendant la session
    webcam_enabled = db.Column(db.Boolean, default=False)

    # Date à laquelle l'étudiant a rejoint la session, stockée en UTC
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
    Représente une réponse d'un étudiant à un questionnaire QCM.

    Une réponse est liée :
    - à une session ;
    - à un étudiant ;
    - à une phase : avant, pendant ou apres ;
    - à une occurrence de questionnaire.

    Cette table sert à suivre l'évolution des émotions déclarées
    par les étudiants pendant une session.
    """

    __tablename__ = "qcm_responses"

    # ========================
    # CONTRAINTES
    # ========================

    # Empêche un étudiant d'envoyer plusieurs réponses pour la même session,
    # la même phase et la même occurrence.
    __table_args__ = (
        db.UniqueConstraint(
            "session_id",
            "user_id",
            "phase",
            "occurrence",
            name="unique_qcm_response"
        ),
    )

    # ========================
    # COLONNES
    # ========================

    # Identifiant unique de la réponse QCM
    id = db.Column(db.Integer, primary_key=True)

    # Identifiant de la session concernée
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("sessions.id"),
        nullable=False
    )

    # Identifiant de l'étudiant ayant répondu
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Phase du questionnaire : "avant", "pendant" ou "apres"
    phase = db.Column(
        db.String(20),
        nullable=False
    )

    # Émotion sélectionnée par l'étudiant
    # Exemple : "motive", "neutre", "stresse"
    emotion = db.Column(
        db.String(50),
        nullable=True
    )

    # Intensité choisie avec le slider
    slider_value = db.Column(
        db.Integer,
        nullable=True
    )

    # Numéro du questionnaire dans la session.
    # Utile surtout pour les questionnaires répétés pendant le cours.
    occurrence = db.Column(
        db.Integer,
        default=1,
        nullable=False
    )

    # Date d'envoi de la réponse, stockée en UTC
    answered_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ========================
    # RELATIONS ORM
    # ========================

    # Permet d'accéder à la session depuis une réponse QCM
    session = db.relationship(
        "Session",
        backref="qcm_responses",
        lazy=True
    )

    # Permet d'accéder à l'utilisateur depuis une réponse QCM
    user = db.relationship(
        "User",
        backref="qcm_responses",
        lazy=True
    )


# ============================================================
# TABLE WEBCAM ANALYSIS
# ============================================================

class WebcamAnalysis(db.Model):
    """
    Stocke les résultats d'analyse d'émotions via DeepFace.

    Chaque ligne correspond à une analyse webcam réalisée
    pour un étudiant pendant une session.
    """

    __tablename__ = "webcam_analysis"

    # ========================
    # COLONNES
    # ========================

    # Identifiant unique de l'analyse webcam
    id = db.Column(db.Integer, primary_key=True)

    # Identifiant de la session concernée
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("sessions.id"),
        nullable=False
    )

    # Identifiant de l'étudiant analysé
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    # Émotion dominante détectée par DeepFace
    dominant_emotion = db.Column(db.String(50), nullable=False)

    # Score de confiance de l'émotion dominante
    confidence = db.Column(db.Float, nullable=True)

    # Détail de toutes les émotions détectées, stocké sous forme de texte JSON
    all_emotions = db.Column(db.Text, nullable=True)

    # Date de l'analyse webcam, stockée en UTC
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
    Stocke les alertes déclenchées pendant une session.

    Une alerte peut être :
    - individuelle : liée à un étudiant précis ;
    - collective : liée à toute la classe.

    Sources possibles :
    - "qcm" : alerte individuelle issue des réponses QCM ;
    - "webcam" : alerte individuelle issue de DeepFace ;
    - "class_snapshot" : alerte de classe sur le dernier QCM collectif ;
    - "class_accumulation" : alerte de classe par accumulation d'alertes individuelles.
    """

    __tablename__ = "alerts"

    # ========================
    # COLONNES
    # ========================

    # Identifiant unique de l'alerte
    id = db.Column(db.Integer, primary_key=True)

    # Identifiant de la session concernée
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("sessions.id"),
        nullable=False
    )

    # Identifiant de l'étudiant concerné.
    # Peut être NULL pour une alerte de classe.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    # Niveau de l'alerte : "individual" ou "class"
    level = db.Column(db.String(20), nullable=False)

    # Source de l'alerte : "qcm", "webcam", "class_snapshot" ou "class_accumulation"
    source = db.Column(db.String(30), nullable=False)

    # Émotion dominante ou déclenchante liée à l'alerte
    emotion = db.Column(db.String(50), nullable=True)

    # Ratio mesuré au moment du déclenchement
    # Exemple : 0.65 signifie 65 %
    ratio = db.Column(db.Float, nullable=True)

    # Date de déclenchement de l'alerte, stockée en UTC
    triggered_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ========================
    # RELATIONS ORM
    # ========================

    # Permet d'accéder à la session depuis une alerte
    session = db.relationship(
        "Session",
        backref="alerts",
        lazy=True
    )

    # Permet d'accéder à l'utilisateur depuis une alerte individuelle
    user = db.relationship(
        "User",
        backref="alerts",
        lazy=True
    )
