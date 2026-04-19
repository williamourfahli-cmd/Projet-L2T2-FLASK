import pytest
from app import app as flask_app, db
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    """
    Initialise une application Flask de test avec une base SQLite en mémoire.
    
    ```
    OBJECTIF :
    - Isoler totalement les tests
    - Recréer une base propre à chaque test
    """
    
    flask_app.config["TESTING"] = True
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    flask_app.config["WTF_CSRF_ENABLED"] = False
    flask_app.config["MAIL_SUPPRESS_SEND"] = True  # évite envoi réel
    
    with flask_app.app_context():
        db.create_all()
    
    yield flask_app
    
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()
    
@pytest.fixture
def client(app):
    """
    Client Flask permettant de simuler des requêtes HTTP.
    """
    return app.test_client()

@pytest.fixture
def create_user(app):
    """
    Factory pour créer facilement des utilisateurs en base.
    
    ```
    SCENARIOS POSSIBLES :
    - utilisateur vérifié / non vérifié
    - rôle student / professor
    
    UTILISATION :
    user = create_user("test@mail.com", role="student", verified=True)
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
```
