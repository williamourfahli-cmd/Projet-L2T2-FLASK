from models import User


def test_register(client):
    """
    Vérifie qu'un utilisateur peut s'inscrire correctement.
    """

    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean@etu.u-paris.fr",
        "password": "password123"
    })

    # 🔥 Accès à la base via app_context
    with client.application.app_context():
        user = User.query.filter_by(email="jean@etu.u-paris.fr").first()

        assert user is not None
        assert user.role.value == "student"


def test_login(client):
    """
    Vérifie qu'un utilisateur peut se connecter.
    """

    # Création utilisateur
    client.post("/register", data={
        "first_name": "Alice",
        "last_name": "Test",
        "email": "alice@etu.u-paris.fr",
        "password": "password123"
    })

    response = client.post("/login", data={
        "email": "alice@etu.u-paris.fr",
        "password": "password123"
    }, follow_redirects=True)

    assert response.status_code == 200


def test_login_failure(client):
    """
    Vérifie qu'un login échoue avec un mauvais mot de passe.
    """

    client.post("/register", data={
        "first_name": "Bob",
        "last_name": "Test",
        "email": "bob@etu.u-paris.fr",
        "password": "password123"
    })

    response = client.post("/login", data={
        "email": "bob@etu.u-paris.fr",
        "password": "wrongpassword"
    }, follow_redirects=True)

    assert b"incorrect" in response.data.lower()
