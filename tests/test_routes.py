# =========================
# HELPERS
# =========================

def login(client, email, password="password123"):
    return client.post("/login", data={
        "email": email,
        "password": password
    })


def create_and_login_student(client, create_user):
    create_user("student@test.com", role="student", verified=True)
    login(client, "student@test.com")


def create_and_login_prof(client, create_user):
    create_user("prof@test.com", role="professor", verified=True)
    login(client, "prof@test.com")


# =========================
# TESTS ROUTES
# =========================

def test_home_not_logged_in(client):
    """
    SCENARIO:
    Utilisateur non connecté accède à "/"

    EXPECTED:
    - Page landing affichée (pas de redirection)
    """

    response = client.get("/")

    assert response.status_code == 200


def test_home_redirect_student(client, create_user):
    """
    SCENARIO:
    Étudiant connecté accède à "/"

    EXPECTED:
    - Redirection vers dashboard étudiant
    """

    create_and_login_student(client, create_user)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert "/dashboard/student" in response.location


def test_home_redirect_professor(client, create_user):
    """
    SCENARIO:
    Professeur connecté accède à "/"

    EXPECTED:
    - Redirection vers dashboard professeur
    """

    create_and_login_prof(client, create_user)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert "/dashboard/professor" in response.location


def test_student_dashboard_access_ok(client, create_user):
    """
    SCENARIO:
    Étudiant accède à son dashboard

    EXPECTED:
    - Accès autorisé (200)
    """

    create_and_login_student(client, create_user)

    response = client.get("/dashboard/student")

    assert response.status_code == 200


def test_student_dashboard_forbidden_prof(client, create_user):
    """
    SCENARIO:
    Professeur tente d'accéder au dashboard étudiant

    EXPECTED:
    - Redirection vers login
    """

    create_and_login_prof(client, create_user)

    response = client.get("/dashboard/student", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.location


def test_professor_dashboard_access_ok(client, create_user):
    """
    SCENARIO:
    Professeur accède à son dashboard

    EXPECTED:
    - Accès autorisé
    """

    create_and_login_prof(client, create_user)

    response = client.get("/dashboard/professor")

    assert response.status_code == 200


def test_professor_dashboard_forbidden_student(client, create_user):
    """
    SCENARIO:
    Étudiant tente d'accéder au dashboard professeur

    EXPECTED:
    - Redirection vers login
    """

    create_and_login_student(client, create_user)

    response = client.get("/dashboard/professor", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.location


def test_dashboard_not_logged_in(client):
    """
    SCENARIO:
    Utilisateur non connecté tente d'accéder aux dashboards

    EXPECTED:
    - Redirection vers login
    """

    response_student = client.get("/dashboard/student", follow_redirects=False)
    response_prof = client.get("/dashboard/professor", follow_redirects=False)

    assert response_student.status_code == 302
    assert response_prof.status_code == 302

    assert "/login" in response_student.location
    assert "/login" in response_prof.location


def test_logout_redirect(client, create_user):
    """
    SCENARIO:
    Utilisateur se déconnecte

    EXPECTED:
    - Redirection vers login
    """

    create_and_login_student(client, create_user)

    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.location
