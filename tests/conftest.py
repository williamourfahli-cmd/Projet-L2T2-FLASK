import pytest
from app import app as flask_app
from models import db
import os


@pytest.fixture
def app():
    """
    Initialise une application Flask de test avec une base SQLite temporaire.
    """

    test_db_path = "test.db"

    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{test_db_path}"
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["MAIL_SUPPRESS_SEND"] = True

    # Lier SQLAlchemy à l'app
    db.init_app(flask_app)

    with flask_app.app_context():
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()

    # Supprimer le fichier de test
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture
def client(app):
    """
    Client Flask pour simuler des requêtes HTTP.
    """
    return app.test_client()


@pytest.fixture
def create_user(app):
    """
    Factory pour créer des utilisateurs en base.

    SCENARIOS :
    - utilisateur vérifié / non vérifié
    - rôle student / professor
    """

    from models import User, UserRole
    from werkzeug.security import generate_password_hash

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
