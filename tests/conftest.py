import pytest
from app import app as flask_app
from models import db
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """
    Initialise l'application Flask pour les tests.

    OBJECTIFS :
    - Base isolée
    - Contexte Flask actif
    - Pas d'envoi d'emails
    """

    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test.db"
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["MAIL_SUPPRESS_SEND"] = True

    # 🔥 Activation du contexte Flask (FIX principal)
    ctx = flask_app.app_context()
    ctx.push()

    # Création des tables
    db.create_all()

    yield flask_app

    # Nettoyage après test
    db.session.remove()
    db.drop_all()

    # 🔥 Désactivation du contexte
    ctx.pop()


@pytest.fixture
def client(app):
    """
    Client Flask pour simuler les requêtes HTTP.
    """
    return app.test_client()


@pytest.fixture
def create_user(app):
    """
    Factory pour créer des utilisateurs facilement.

    SCENARIOS :
    - user vérifié / non vérifié
    - student / professor
    """

    from models import User, UserRole

    def _create_user(
        email,
        password="password123",
        role="student",
        verified=True
    ):
        user = User(
            first_name="Test",
            last_name="User",
            email=email,
            password_hash=generate_password_hash(password),
            role=UserRole.STUDENT if role == "student" else UserRole.PROFESSOR,
            email_verified=verified
        )

        db.session.add(user)
        db.session.commit()

        return user

    return _create_user
