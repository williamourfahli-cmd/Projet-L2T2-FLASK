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
    password_hash = db.Column(db.String(128), nullable=False)

    # Rôle utilisateur (student ou professor)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)

    # Consentement RGPD (important pour la webcam)
    consent_given = db.Column(db.Boolean, default=False, nullable=False)

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
    anonyme = db.Column(db.Boolean, default=False)

    # Webcam activée ou non
    webcam_active = db.Column(db.Boolean, default=False)

    # Date de participation (UTC)
    date_join = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
