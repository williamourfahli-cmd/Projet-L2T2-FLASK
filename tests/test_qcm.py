from models import db, Session, Participation, QCMResponse


# =========================
# HELPERS
# =========================

def login(client, email, password="password123"):
    return client.post("/login", data={
        "email": email,
        "password": password
    })


def setup_session_with_student(client, create_user):
    """
    Crée :
    - un prof + session
    - un étudiant inscrit à la session

    Retourne session_id
    """

    # Prof
    create_user("prof@test.com", role="professor", verified=True)
    login(client, "prof@test.com")

    client.post("/create_session", data={
        "freq_questionnaire": 5,
        "freq_webcam": 5,
        "mode_affichage": "courbe"
    })

    with client.application.app_context():
        session_obj = Session.query.first()
        session_code = session_obj.code_session

    client.get("/logout")

    # Student
    create_user("student@test.com", role="student", verified=True)
    login(client, "student@test.com")

    client.post("/join_session", data={
        "code_session": session_code
    })

    with client.session_transaction() as sess:
        return sess.get("current_session_id")


# =========================
# TESTS QCM
# =========================

def test_qcm_access_success(client, create_user):
    """
    SCENARIO:
    Étudiant accède au QCM avec une session valide.

    EXPECTED:
    - Page accessible (200)
    """

    setup_session_with_student(client, create_user)

    response = client.get("/qcm")

    assert response.status_code == 200


def test_qcm_access_no_session(client, create_user):
    """
    SCENARIO:
    Étudiant sans session active accède au QCM.

    EXPECTED:
    - Redirection vers dashboard
    """

    create_user("student@test.com", role="student", verified=True)
    login(client, "student@test.com")

    response = client.get("/qcm", follow_redirects=False)

    assert response.status_code == 302
    assert "/dashboard/student" in response.location


def test_qcm_submit_success(client, create_user):
    """
    SCENARIO:
    Envoi d'une réponse valide.

    EXPECTED:
    - Réponse enregistrée
    - occurrence = 1
    """

    session_id = setup_session_with_student(client, create_user)

    response = client.post("/qcm/submit", json={
        "emotion": "motivé",
        "slider_value": 4
    })

    assert response.status_code == 200

    with client.application.app_context():
        response_db = QCMResponse.query.first()

        assert response_db is not None
        assert response_db.session_id == session_id
        assert response_db.occurrence == 1


def test_qcm_submit_invalid_emotion(client, create_user):
    """
    SCENARIO:
    Emotion invalide.

    EXPECTED:
    - Erreur 400
    """

    setup_session_with_student(client, create_user)

    response = client.post("/qcm/submit", json={
        "emotion": "invalid_emotion",
        "slider_value": 3
    })

    assert response.status_code == 400


def test_qcm_submit_invalid_slider(client, create_user):
    """
    SCENARIO:
    Valeur slider invalide.

    EXPECTED:
    - Erreur 400
    """

    setup_session_with_student(client, create_user)

    response = client.post("/qcm/submit", json={
        "emotion": "motivé",
        "slider_value": 10
    })

    assert response.status_code == 400


def test_qcm_occurrence_increment(client, create_user):
    """
    SCENARIO:
    Plusieurs réponses envoyées.

    EXPECTED:
    - occurrence augmente correctement
    """

    setup_session_with_student(client, create_user)

    client.post("/qcm/submit", json={
        "emotion": "motivé",
        "slider_value": 3
    })

    client.post("/qcm/submit", json={
        "emotion": "neutre",
        "slider_value": 2
    })

    with client.application.app_context():
        responses = QCMResponse.query.order_by(QCMResponse.occurrence).all()

        assert len(responses) == 2
        assert responses[0].occurrence == 1
        assert responses[1].occurrence == 2


def test_qcm_phase_transition(client, create_user):
    """
    SCENARIO:
    Première réponse en phase 'avant'

    EXPECTED:
    - Phase passe à 'pendant'
    """

    setup_session_with_student(client, create_user)

    client.post("/qcm/submit", json={
        "emotion": "motivé",
        "slider_value": 3
    })

    with client.session_transaction() as sess:
        assert sess.get("phase") == "pendant"


def test_qcm_submit_after_session_end(client, create_user):
    """
    SCENARIO:
    Session terminée → phase 'apres'

    EXPECTED:
    - Réponse enregistrée avec phase 'apres'
    """

    session_id = setup_session_with_student(client, create_user)

    # désactiver session
    with client.application.app_context():
        session_obj = Session.query.get(session_id)
        session_obj.is_active = False
        db.session.commit()

    client.post("/qcm/submit", json={
        "emotion": "motivé",
        "slider_value": 3
    })

    with client.application.app_context():
        response_db = QCMResponse.query.first()
        assert response_db.phase == "apres"


def test_qcm_submit_without_auth(client):
    """
    SCENARIO:
    Utilisateur non connecté.

    EXPECTED:
    - Erreur 403
    """

    response = client.post("/qcm/submit", json={
        "emotion": "motivé",
        "slider_value": 3
    })

    assert response.status_code == 403
