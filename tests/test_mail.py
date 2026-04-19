from unittest.mock import patch
from models import User


@patch("app.mail.send")
def test_register_sends_email(mock_send, client):
    """
    SCENARIO:
    Un utilisateur s'inscrit correctement.

    EXPECTED:
    - mail.send est appelé
    - le destinataire est correct
    - le sujet est correct
    """

    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "mail@test.com",
        "password": "password123",
        "role": "student"
    })

    # Vérifie que mail.send a été appelé
    assert mock_send.called

    # Vérifie le contenu du message
    args, _ = mock_send.call_args
    message = args[0]

    assert "mail@test.com" in message.recipients
    assert "Confirme ton compte" in message.subject


@patch("app.mail.send", side_effect=Exception("SMTP error"))
def test_register_email_failure(mock_send, client):
    """
    SCENARIO:
    Erreur lors de l'envoi du mail.

    EXPECTED:
    - L'utilisateur est quand même créé en base
    """

    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "fail@test.com",
        "password": "password123",
        "role": "student"
    })

    with client.application.app_context():
        user = User.query.filter_by(email="fail@test.com").first()
        assert user is not None
