def test_home_not_logged_in(client):
    """
    Vérifie que l'utilisateur non connecté est redirigé.
    """

    response = client.get("/")
    assert response.status_code == 302


def test_home_logged_in_student(client):
    """
    Vérifie la redirection vers dashboard étudiant.
    """

    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean@etu.u-paris.fr",
        "password": "password123"
    })

    client.post("/login", data={
        "email": "jean@etu.u-paris.fr",
        "password": "password123"
    })

    response = client.get("/", follow_redirects=True)

    assert response.status_code == 200


def test_access_dashboard_permissions(client):
    """
    Vérifie qu'un professeur ne peut pas accéder au dashboard étudiant.
    """

    client.post("/register", data={
        "first_name": "Marie",
        "last_name": "Curie",
        "email": "marie@u-paris.fr",
        "password": "password123"
    })

    client.post("/login", data={
        "email": "marie@u-paris.fr",
        "password": "password123"
    })

    response = client.get("/dashboard/student")

    assert response.status_code in [302, 403]
