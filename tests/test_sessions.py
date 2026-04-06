from models import Session, Participation


def test_create_session(client):
    """
    Vérifie qu'un professeur peut créer une session.
    """

    # Création du professeur
    client.post("/register", data={
        "first_name": "Prof",
        "last_name": "Test",
        "email": "prof@u-paris.fr",
        "password": "password123"
    })

    # Connexion
    client.post("/login", data={
        "email": "prof@u-paris.fr",
        "password": "password123"
    })

    # Création session
    client.post("/create_session", data={
        "freq_questionnaire": 5,
        "freq_webcam": 5,
        "mode_affichage": "graph"
    })

    # 🔥 Accès DB avec contexte
    with client.application.app_context():
        session_db = Session.query.first()

        assert session_db is not None


def test_join_session(client):
    """
    Vérifie qu'un étudiant peut rejoindre une session.
    """

    # Création prof + session
    client.post("/register", data={
        "first_name": "Prof",
        "last_name": "Test",
        "email": "prof@u-paris.fr",
        "password": "password123"
    })

    client.post("/login", data={
        "email": "prof@u-paris.fr",
        "password": "password123"
    })

    client.post("/create_session", data={
        "freq_questionnaire": 5,
        "freq_webcam": 5,
        "mode_affichage": "graph"
    })

    # 🔥 Récupération du code session
    with client.application.app_context():
        session_code = Session.query.first().code_session

    # Déconnexion prof
    client.get("/logout")

    # Création étudiant
    client.post("/register", data={
        "first_name": "Student",
        "last_name": "Test",
        "email": "student@etu.u-paris.fr",
        "password": "password123"
    })

    client.post("/login", data={
        "email": "student@etu.u-paris.fr",
        "password": "password123"
    })

    # Rejoindre session
    client.post("/join_session", data={
        "code_session": session_code,
        "anonyme": "on",
        "webcam": "on"
    })

    # 🔥 Vérification en base
    with client.application.app_context():
        participation = Participation.query.first()

        assert participation is not None
