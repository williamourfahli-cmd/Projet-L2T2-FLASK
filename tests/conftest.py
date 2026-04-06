import pytest
from app import app as flask_app
from models import db

@pytest.fixture
def app():
    """
    Initialise une application Flask de test avec une base en mémoire.
    """

    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["SECRET_KEY"] = "test"

    # Création des tables
    with flask_app.app_context():
        db.create_all()

    yield flask_app

    # Nettoyage après les tests
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """
    Client de test Flask permettant de simuler des requêtes HTTP.
    """
    return app.test_client()
