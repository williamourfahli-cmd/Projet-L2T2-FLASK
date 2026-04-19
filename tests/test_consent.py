from models import db, User


# =========================
# HELPERS
# =========================

def login(client, email, password="password123"):
    return client.post("/login", data={
        "email": email,
        "password": password
    })


# =========================
# TESTS CONSENT
# =========================

def test_consent_success(client, create_user):
    """
    SCENARIO:
    Un utilisateur connecté donne son consentement.

    EXPECTED:
    - consent_given = True en base
    - session mise à jour
    - réponse 204
    """

    create_user("consent@test.com", verified=True)

    login(client, "consent@test.com")

    response = client.post("/consent")

    assert response.status_code == 204

    with client.application.app_context():
        user = User.query.filter_by(email="consent@test.com").first()
        assert user.consent_given is True

    with client.session_transaction() as sess:
        assert sess.get("consent_given") is True


def test_consent_not_logged_in(client):
    """
    SCENARIO:
    Utilisateur non connecté tente de donner son consentement.

    EXPECTED:
    - Accès refusé (403)
    """

    response = client.post("/consent")

    assert response.status_code == 403


def test_consent_idempotent(client, create_user):
    """
    SCENARIO:
    L'utilisateur donne son consentement plusieurs fois.

    EXPECTED:
    - consent reste True
    - pas d'erreur
    """

    create_user("consent2@test.com", verified=True)

    login(client, "consent2@test.com")

    client.post("/consent")
    response = client.post("/consent")

    assert response.status_code == 204

    with client.application.app_context():
        user = User.query.filter_by(email="consent2@test.com").first()
        assert user.consent_given is True
