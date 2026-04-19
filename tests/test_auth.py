from models import db, User


def test_register_success(client):
    """
    SCENARIO:
    Un utilisateur s'inscrit avec des données valides.

    EXPECTED:
    - L'utilisateur est créé en base
    - email_verified = False
    - Un token est généré
    """

    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean@test.com",
        "password": "password123",
        "role": "student"
    })

    with client.application.app_context():
        user = User.query.filter_by(email="jean@test.com").first()

        assert user is not None
        assert user.email_verified is False
        assert user.verification_token is not None


def test_register_missing_fields(client):
    """
    SCENARIO:
    Formulaire incomplet.

    EXPECTED:
    - Aucun utilisateur créé
    """

    client.post("/register", data={
        "first_name": "Jean",
        "email": "jean@test.com",
        "password": "password123"
    })

    with client.application.app_context():
        user = User.query.filter_by(email="jean@test.com").first()
        assert user is None


def test_register_duplicate_email(client, create_user):
    """
    SCENARIO:
    Email déjà existant.

    EXPECTED:
    - Aucun doublon créé
    """

    create_user("duplicate@test.com")

    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "duplicate@test.com",
        "password": "password123",
        "role": "student"
    })

    with client.application.app_context():
        users = User.query.filter_by(email="duplicate@test.com").all()
        assert len(users) == 1


def test_login_success(client, create_user):
    """
    SCENARIO:
    Login avec utilisateur valide et vérifié.

    EXPECTED:
    - Session initialisée
    """

    create_user("login@test.com", verified=True)

    client.post("/login", data={
        "email": "login@test.com",
        "password": "password123"
    })

    with client.session_transaction() as sess:
        assert sess.get("user_id") is not None
        assert sess.get("role") == "student"


def test_login_wrong_password(client, create_user):
    """
    SCENARIO:
    Mauvais mot de passe.

    EXPECTED:
    - Pas de session
    """

    create_user("wrong@test.com", verified=True)

    client.post("/login", data={
        "email": "wrong@test.com",
        "password": "badpassword"
    })

    with client.session_transaction() as sess:
        assert sess.get("user_id") is None


def test_login_unverified_email(client, create_user):
    """
    SCENARIO:
    Email non vérifié.

    EXPECTED:
    - Refus de connexion
    """

    create_user("notverified@test.com", verified=False)

    client.post("/login", data={
        "email": "notverified@test.com",
        "password": "password123"
    })

    with client.session_transaction() as sess:
        assert sess.get("user_id") is None


def test_logout(client, create_user):
    """
    SCENARIO:
    Déconnexion utilisateur.

    EXPECTED:
    - Session vidée
    """

    create_user("logout@test.com", verified=True)

    client.post("/login", data={
        "email": "logout@test.com",
        "password": "password123"
    })

    client.get("/logout")

    with client.session_transaction() as sess:
        assert sess.get("user_id") is None
