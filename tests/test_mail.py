from unittest.mock import patch
from models import User
 
# =========================
# HELPERS
# =========================
def login(client, email, password="password123"):
    return client.post("/login", data={
        "email": email,
        "password": password
    })
 

# =================================
# TESTS ENVOI MAIL DE CONFIRMATION
# =================================
@patch("app.mail.send")
def test_register_sends_email(mock_send, client):
    """
    ID: UT-APP-mail-001
     
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
    ID: UT-APP-mail-002
    
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

#================================
#TOKEN ENVOIE EMAIL
#================================
@patch("app.mail.send")
def test_confirm_email_valid_token(mock_send, client):
    """
    ID: UT-APP-mail-003
 
    SCENARIO:
    Un utilisateur clique sur le lien de confirmation avec un token valide.
 
    EXPECTED:
    - email_verified passe à True
    - verification_token est supprimé (None)
    - redirection vers /login
    """
 
    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "confirm@test.com",
        "password": "password123",
        "role": "student"
    })
 
    with client.application.app_context():
        user = User.query.filter_by(email="confirm@test.com").first()
        token = user.verification_token
 
    response = client.get(f"/confirm/{token}")
 
    assert response.status_code == 302
    assert "/login" in response.location
 
    with client.application.app_context():
        user = User.query.filter_by(email="confirm@test.com").first()
        assert user.email_verified is True
        assert user.verification_token is None
 
 
@patch("app.mail.send")
def test_confirm_email_invalid_token(mock_send, client):
    """
    ID: UT-APP-mail-004
 
    SCENARIO:
    Un utilisateur clique sur un lien de confirmation avec un token invalide.
 
    EXPECTED:
    - Redirection vers /login
    - email_verified reste False
    """
 
    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "invalid@test.com",
        "password": "password123",
        "role": "student"
    })
 
    response = client.get("/confirm/token-invalide-xyz")
 
    assert response.status_code == 302
    assert "/login" in response.location
 
    with client.application.app_context():
        user = User.query.filter_by(email="invalid@test.com").first()
        assert user.email_verified is False


#=============================
#DOUBLON : mail déjà confirmé 
#=============================
 
@patch("app.mail.send")
def test_confirm_email_already_verified(mock_send, client):
    """
    ID: UT-APP-mail-005
 
    SCENARIO:
    Un utilisateur tente de confirmer un email déjà confirmé
    (réutilisation du lien).
 
    EXPECTED:
    - Redirection vers /login
    - email_verified reste True
    - token reste None
    """
 
    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "already@test.com",
        "password": "password123",
        "role": "student"
    })
 
    with client.application.app_context():
        user = User.query.filter_by(email="already@test.com").first()
        token = user.verification_token
 
    # Premier clic — confirme le compte
    client.get(f"/confirm/{token}")
 
    # Deuxième clic — token déjà utilisé
    response = client.get(f"/confirm/{token}")
 
    assert response.status_code == 302
    assert "/login" in response.location
 
    with client.application.app_context():
        user = User.query.filter_by(email="already@test.com").first()
        assert user.email_verified is True
 
