from models import db, Session, Participation


# =========================
# HELPERS
# =========================

def login(client, email, password="password123"):
    return client.post("/login", data={
        "email": email,
        "password": password
    })


def create_and_login_prof(client, create_user):
    create_user("prof@test.com", role="professor", verified=True)
    login(client, "prof@test.com")


def create_and_login_student(client, create_user):
    create_user("student@test.com", role="student", verified=True)
    login(client, "student@test.com")
    

def setup_active_session(client, create_user):
    """
    Crée un prof, une session active et retourne l'id de la session.
    """
    create_and_login_prof(client, create_user)
 
    client.post("/create_session", data={
        "freq_questionnaire": 5,
        "freq_webcam": 5,
        "mode_affichage": "courbe"
    })
 
    with client.application.app_context():
        return Session.query.first().id
 

# =========================
# CREATE SESSION
# =========================

def test_create_session_success(client, create_user):
    """
    SCENARIO:
    Un professeur crée une session valide.

    EXPECTED:
    - Session créée en base
    - is_active = True
    - mode correct
    """

    create_and_login_prof(client, create_user)

    client.post("/create_session", data={
        "freq_questionnaire": 5,
        "freq_webcam": 5,
        "mode_affichage": "courbe"
    })

    with client.application.app_context():
        session_db = Session.query.first()

        assert session_db is not None
        assert session_db.is_active is True
        assert session_db.mode_affichage == "courbe"


def test_create_session_forbidden_student(client, create_user):
    """
    SCENARIO:
    Un étudiant tente de créer une session.

    EXPECTED:
    - Aucune session créée
    """

    create_and_login_student(client, create_user)

    client.post("/create_session", data={
        "freq_questionnaire": 5,
        "freq_webcam": 5,
        "mode_affichage": "courbe"
    })

    with client.application.app_context():
        session_db = Session.query.first()
        assert session_db is None


def test_create_session_all_modes(client, create_user):
    """
    SCENARIO:
    Création de sessions avec tous les modes métier.

    EXPECTED:
    - 3 sessions créées
    - Chaque mode correctement enregistré
    """

    create_and_login_prof(client, create_user)

    modes = ["courbe", "moyenne", "alerte"]

    for mode in modes:
        client.post("/create_session", data={
            "freq_questionnaire": 5,
            "freq_webcam": 5,
            "mode_affichage": mode
        })

    with client.application.app_context():
        sessions = Session.query.all()

        assert len(sessions) == 3

        saved_modes = [s.mode_affichage for s in sessions]

        for mode in modes:
            assert mode in saved_modes

#==================================
#JOIN SESSION
#===================================
def test_join_session_success(client, create_user):
    """
    SCENARIO:
    Un étudiant rejoint une session valide.

    EXPECTED:
    - Participation créée
    - Session Flask mise à jour
    """

    create_and_login_prof(client, create_user)

    client.post("/create_session", data={
        "freq_questionnaire": 5,
        "freq_webcam": 5,
        "mode_affichage": "courbe"
    })

    with client.application.app_context():
        session_code = Session.query.first().code_session

    client.get("/logout")

    create_and_login_student(client, create_user)

    client.post("/join_session", data={
        "code_session": session_code,
        "anonymous": "on",
        "webcam_enabled": "on"
    })

    with client.application.app_context():
        participation = Participation.query.first()
        assert participation is not None

    with client.session_transaction() as sess:
        assert sess.get("current_session_id") is not None
        assert sess.get("phase") == "avant"


def test_join_session_invalid_code(client, create_user):
    """
    SCENARIO:
    Code session invalide.

    EXPECTED:
    - Aucune participation créée
    """

    create_and_login_student(client, create_user)

    client.post("/join_session", data={
        "code_session": "FAKE01"
    })

    with client.application.app_context():
        participation = Participation.query.first()
        assert participation is None


def test_join_session_already_joined(client, create_user):
    """
    SCENARIO:
    Double inscription à une session.

    EXPECTED:
    - Une seule participation en base
    """

    create_and_login_prof(client, create_user)

    client.post("/create_session", data={
        "freq_questionnaire": 5,
        "freq_webcam": 5,
        "mode_affichage": "courbe"
    })

    with client.application.app_context():
        session_code = Session.query.first().code_session

    client.get("/logout")

    create_and_login_student(client, create_user)

    client.post("/join_session", data={
        "code_session": session_code
    })

    # deuxième tentative
    client.post("/join_session", data={
        "code_session": session_code
    })

    with client.application.app_context():
        participations = Participation.query.all()
        assert len(participations) == 1


def test_join_session_inactive(client, create_user):
    """
    SCENARIO:
    Session terminée.

    EXPECTED:
    - Impossible de rejoindre
    """

    create_and_login_prof(client, create_user)

    client.post("/create_session", data={
        "freq_questionnaire": 5,
        "freq_webcam": 5,
        "mode_affichage": "courbe"
    })

    with client.application.app_context():
        session_obj = Session.query.first()
        session_obj.is_active = False
        db.session.commit()
        session_code = session_obj.code_session

    client.get("/logout")

    create_and_login_student(client, create_user)

    client.post("/join_session", data={
        "code_session": session_code
    })

    with client.application.app_context():
        participation = Participation.query.first()
        assert participation is None

# =========================
# TESTS END SESSION
# =========================
def test_end_session_success(client, create_user):
    """
    ID: UT-APP-SESSION-008
 
    SCENARIO:
    Un professeur termine une session active.
 
    EXPECTED:
    - is_active passe à False
    - date_fin est renseignée
    - redirection vers le dashboard
    """
 
    session_id = setup_active_session(client, create_user)
 
    response = client.post(f"/end_session/{session_id}")
 
    assert response.status_code == 302
 
    with client.application.app_context():
        session_db = Session.query.get(session_id)
        assert session_db.is_active is False
        assert session_db.date_fin is not None
 
 
def test_end_session_forbidden_student(client, create_user):
    """
    ID: UT-APP-SESSION-009
 
    SCENARIO:
    Un étudiant tente de terminer une session.
 
    EXPECTED:
    - Accès refusé
    - Session reste active
    """
 
    session_id = setup_active_session(client, create_user)
 
    client.get("/logout")
 
    create_and_login_student(client, create_user)
 
    client.post(f"/end_session/{session_id}")
 
    with client.application.app_context():
        session_db = Session.query.get(session_id)
        assert session_db.is_active is True
 
 
def test_end_session_not_logged_in(client, create_user):
    """
    ID: UT-APP-SESSION-010
 
    SCENARIO:
    Un utilisateur non connecté tente de terminer une session.
 
    EXPECTED:
    - Redirection vers /login
    - Session reste active
    """
 
    session_id = setup_active_session(client, create_user)
 
    client.get("/logout")
 
    response = client.post(f"/end_session/{session_id}")
 
    assert response.status_code == 302
    assert "/login" in response.location
 
    with client.application.app_context():
        session_db = Session.query.get(session_id)
        assert session_db.is_active is True
