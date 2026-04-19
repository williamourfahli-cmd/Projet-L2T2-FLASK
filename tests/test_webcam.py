from models import db, WebcamAnalysis
from unittest.mock import patch


# =========================
# HELPERS
# =========================

def login(client, email, password="password123"):
    return client.post("/login", data={
        "email": email,
        "password": password
    })


# =========================
# TESTS WEBCAM
# =========================

def test_webcam_not_logged_in(client):
    """
    SCENARIO:
    Utilisateur non connecté.

    EXPECTED:
    - 403
    """

    response = client.post("/analyze_webcam", json={
        "image": "fake_base64"
    })

    assert response.status_code == 403


def test_webcam_missing_image(client, create_user):
    """
    SCENARIO:
    Pas d'image envoyée.

    EXPECTED:
    - 400
    """

    create_user("user@test.com", verified=True)
    login(client, "user@test.com")

    response = client.post("/analyze_webcam", json={})

    assert response.status_code == 400


@patch("app.http_requests.post")
def test_webcam_success(mock_post, client, create_user):
    """
    SCENARIO:
    Analyse réussie.

    EXPECTED:
    - Données sauvegardées en DB
    - Réponse OK
    """

    # Mock réponse DeepFace
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "status": "success",
        "emotion": "happy",
        "confidence": 0.95,
        "all_emotions": {"happy": 0.95}
    }

    create_user("user@test.com", verified=True)
    login(client, "user@test.com")

    # Simuler session active
    with client.session_transaction() as sess:
        sess["current_session_id"] = 1

    response = client.post("/analyze_webcam", json={
        "image": "fake_base64"
    })

    assert response.status_code == 200

    with client.application.app_context():
        analysis = WebcamAnalysis.query.first()
        assert analysis is not None
        assert analysis.dominant_emotion == "happy"


@patch("app.http_requests.post")
def test_webcam_server_error(mock_post, client, create_user):
    """
    SCENARIO:
    DeepFace renvoie une erreur.

    EXPECTED:
    - 500
    """

    mock_post.return_value.status_code = 500

    create_user("user@test.com", verified=True)
    login(client, "user@test.com")

    with client.session_transaction() as sess:
        sess["current_session_id"] = 1

    response = client.post("/analyze_webcam", json={
        "image": "fake_base64"
    })

    assert response.status_code == 500


@patch("app.http_requests.post")
def test_webcam_timeout(mock_post, client, create_user):
    """
    SCENARIO:
    Timeout serveur DeepFace.

    EXPECTED:
    - 504
    """

    import requests

    mock_post.side_effect = requests.exceptions.Timeout()

    create_user("user@test.com", verified=True)
    login(client, "user@test.com")

    with client.session_transaction() as sess:
        sess["current_session_id"] = 1

    response = client.post("/analyze_webcam", json={
        "image": "fake_base64"
    })

    assert response.status_code == 504
