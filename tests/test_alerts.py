from datetime import datetime, timezone, timedelta
from models import db, Session, Participation, QCMResponse, WebcamAnalysis, Alert
from app import check_individual_alert_qcm, check_individual_alert_webcam, check_class_snapshot_alert, save_alert
 
 
# =========================
# HELPERS
# =========================
 
def login(client, email, password="password123"):
    return client.post("/login", data={
        "email": email,
        "password": password
    })
 
 
def setup_session_with_student(client, create_user, seuil_individuel=60, seuil_classe=50):
    """
    Crée un prof + session alertes + un étudiant inscrit.
    Retourne (session_id, student_id)
    """
 
    create_user("prof@test.com", role="professor", verified=True)
    login(client, "prof@test.com")
 
    client.post("/create_session", data={
        "freq_questionnaire": 60,
        "freq_webcam": 30,
        "modes_affichage": "alertes",
        "seuil_individuel": seuil_individuel,
        "seuil_classe": seuil_classe
    })
 
    with client.application.app_context():
        session_obj  = Session.query.first()
        session_code = session_obj.code_session
        session_id   = session_obj.id
 
    client.get("/logout")
 
    student = create_user("student@test.com", role="student", verified=True)
    login(client, "student@test.com")
 
    client.post("/join_session", data={"code_session": session_code})
 
    return session_id, student.id
 
 
# =========================
# ALERTES INDIVIDUELLES QCM
# =========================
 
def test_alert_qcm_triggered(client, create_user):
    """
    ID: UT-APP-ALERT-QCM-001
 
    SCENARIO:
    Un étudiant soumet plusieurs réponses très négatives avec une forte
    intensité (slider=5). Le ratio pondéré dépasse le seuil individuel (60%).
 
    DONNÉES D'ENTRÉE:
    - 4 réponses négatives (demotive) avec slider=5
    - 1 réponse positive avec slider=1
    - Seuil individuel : 0.60
 
    EXPECTED:
    - check_individual_alert_qcm retourne True
    - ratio > 0.60
    - émotion dominante = "demotive"
    """
 
    session_id, student_id = setup_session_with_student(client, create_user)
 
    with client.application.app_context():
        for i in range(4):
            db.session.add(QCMResponse(
                session_id=session_id,
                user_id=student_id,
                phase="pendant",
                emotion="demotive",
                slider_value=5,
                occurrence=i + 1
            ))
        db.session.add(QCMResponse(
            session_id=session_id,
            user_id=student_id,
            phase="pendant",
            emotion="motive",
            slider_value=1,
            occurrence=5
        ))
        db.session.commit()
 
        triggered, ratio, emotion = check_individual_alert_qcm(session_id, student_id, seuil=0.60)
 
        assert triggered is True
        assert ratio > 0.60
        assert emotion == "demotive"
 
 
def test_alert_qcm_not_triggered_low_intensity(client, create_user):
    """
    ID: UT-APP-ALERT-QCM-002
 
    SCENARIO:
    Un étudiant soumet des réponses négatives avec une très faible intensité
    (slider=1). Grâce à la pondération, le ratio reste sous le seuil.
 
    DONNÉES D'ENTRÉE:
    - 3 réponses négatives (demotive) avec slider=1
    - 2 réponses positives avec slider=5
    - Seuil individuel : 0.60
 
    EXPECTED:
    - check_individual_alert_qcm retourne False
    - ratio < 0.60
    """
 
    session_id, student_id = setup_session_with_student(client, create_user)
 
    with client.application.app_context():
        for i in range(3):
            db.session.add(QCMResponse(
                session_id=session_id,
                user_id=student_id,
                phase="pendant",
                emotion="demotive",
                slider_value=1,
                occurrence=i + 1
            ))
        for i in range(2):
            db.session.add(QCMResponse(
                session_id=session_id,
                user_id=student_id,
                phase="pendant",
                emotion="motive",
                slider_value=5,
                occurrence=i + 4
            ))
        db.session.commit()
 
        triggered, ratio, _ = check_individual_alert_qcm(session_id, student_id, seuil=0.60)
 
        assert triggered is False
        assert ratio < 0.60
 
 
def test_alert_qcm_no_response(client, create_user):
    """
    ID: UT-APP-ALERT-QCM-003
 
    SCENARIO:
    Un étudiant n'a soumis aucune réponse QCM.
    La fonction ne doit pas planter.
 
    DONNÉES D'ENTRÉE:
    - Aucune réponse QCM en base
 
    EXPECTED:
    - check_individual_alert_qcm retourne False
    - ratio = 0.0
    - emotion = None
    - Aucune alerte en base
    """
 
    session_id, student_id = setup_session_with_student(client, create_user)
 
    with client.application.app_context():
        triggered, ratio, emotion = check_individual_alert_qcm(session_id, student_id, seuil=0.60)
 
        assert triggered is False
        assert ratio == 0.0
        assert emotion is None
        assert len(Alert.query.all()) == 0
 
 
# =========================
# ALERTES INDIVIDUELLES WEBCAM
# =========================
 
def test_alert_webcam_triggered(client, create_user):
    """
    ID: UT-APP-ALERT-WEBCAM-001
 
    SCENARIO:
    Un étudiant a plusieurs analyses DeepFace avec des émotions négatives
    (angry) dépassant le seuil individuel (60%).
 
    DONNÉES D'ENTRÉE:
    - 4 analyses avec dominant_emotion="angry"
    - 1 analyse avec dominant_emotion="happy"
    - Seuil individuel : 0.60
 
    EXPECTED:
    - check_individual_alert_webcam retourne True
    - emotion dominante = "angry"
    """
 
    session_id, student_id = setup_session_with_student(client, create_user)
 
    with client.application.app_context():
        for _ in range(4):
            db.session.add(WebcamAnalysis(
                session_id=session_id,
                user_id=student_id,
                dominant_emotion="angry",
                confidence=90.0
            ))
        db.session.add(WebcamAnalysis(
            session_id=session_id,
            user_id=student_id,
            dominant_emotion="happy",
            confidence=80.0
        ))
        db.session.commit()
 
        triggered, ratio, emotion = check_individual_alert_webcam(session_id, student_id, seuil=0.60)
 
        assert triggered is True
        assert ratio > 0.60
        assert emotion == "angry"
 
 
def test_alert_webcam_no_analysis(client, create_user):
    """
    ID: UT-APP-ALERT-WEBCAM-002
 
    SCENARIO:
    Aucune analyse webcam en base pour cet étudiant.
 
    DONNÉES D'ENTRÉE:
    - Aucune analyse webcam
 
    EXPECTED:
    - check_individual_alert_webcam retourne False
    - ratio = 0.0
    - emotion = None
    """
 
    session_id, student_id = setup_session_with_student(client, create_user)
 
    with client.application.app_context():
        triggered, ratio, emotion = check_individual_alert_webcam(session_id, student_id, seuil=0.60)
 
        assert triggered is False
        assert ratio == 0.0
        assert emotion is None
 
 
# =========================
# ALERTES DE CLASSE
# =========================
 
def test_alert_class_snapshot_triggered(client, create_user):
    """
    ID: UT-APP-ALERT-CLASS-001
 
    SCENARIO:
    Au dernier QCM collectif, plus de 50% de la classe a répondu
    négativement avec une forte intensité.
 
    DONNÉES D'ENTRÉE:
    - 3 étudiants avec réponses négatives (demotive, slider=5)
    - 1 étudiant avec réponse positive
    - Seuil classe : 0.50
 
    EXPECTED:
    - check_class_snapshot_alert retourne True
    - ratio > 0.50
    """
 
    session_id, _ = setup_session_with_student(client, create_user)
 
    with client.application.app_context():
        from models import User, UserRole
        from werkzeug.security import generate_password_hash
 
        for i in range(3):
            u = User(
                first_name="Etu",
                last_name=str(i),
                email=f"etu{i}@test.com",
                password_hash=generate_password_hash("password123"),
                role=UserRole.STUDENT,
                email_verified=True
            )
            db.session.add(u)
            db.session.flush()
            db.session.add(QCMResponse(
                session_id=session_id,
                user_id=u.id,
                phase="pendant",
                emotion="demotive",
                slider_value=5,
                occurrence=1
            ))
 
        u_pos = User(
            first_name="Pos", last_name="Etu", email="pos@test.com",
            password_hash=generate_password_hash("password123"),
            role=UserRole.STUDENT, email_verified=True
        )
        db.session.add(u_pos)
        db.session.flush()
        db.session.add(QCMResponse(
            session_id=session_id,
            user_id=u_pos.id,
            phase="pendant",
            emotion="motive",
            slider_value=1,
            occurrence=1
        ))
        db.session.commit()
 
        triggered, ratio = check_class_snapshot_alert(session_id, seuil=0.50)
 
        assert triggered is True
        assert ratio > 0.50
 
 
def test_alert_class_accumulation_triggered(client, create_user):
    """
    ID: UT-APP-ALERT-CLASS-002
 
    SCENARIO:
    Plusieurs étudiants sont individuellement en alerte QCM.
    Le pourcentage (75%) dépasse le seuil classe (40%).
 
    DONNÉES D'ENTRÉE:
    - 3 étudiants sur 4 avec réponses très négatives
    - Seuil classe : 0.40
 
    EXPECTED:
    - compute_alerts déclenche une alerte "class_accumulation"
    """
 
    session_id, _ = setup_session_with_student(client, create_user, seuil_classe=40)
 
    with client.application.app_context():
        from models import User, UserRole
        from werkzeug.security import generate_password_hash
        from app import compute_alerts
 
        for i in range(3):
            u = User(
                first_name="Etu", last_name=str(i),
                email=f"etu_accum{i}@test.com",
                password_hash=generate_password_hash("password123"),
                role=UserRole.STUDENT, email_verified=True
            )
            db.session.add(u)
            db.session.flush()
            db.session.add(Participation(session_id=session_id, student_id=u.id))
            db.session.flush()
            for j in range(4):
                db.session.add(QCMResponse(
                    session_id=session_id,
                    user_id=u.id,
                    phase="pendant",
                    emotion="demotive",
                    slider_value=5,
                    occurrence=j + 1
                ))
        db.session.commit()
 
        result = compute_alerts(session_id)
 
        assert result["class_alert"] is True
        assert "class_accumulation" in result["class_sources"]
 
 
# =========================
# ANTI-DOUBLON
# =========================
 
def test_alert_no_duplicate(client, create_user):
    """
    ID: UT-APP-ALERT-DEDUP-001
 
    SCENARIO:
    La même alerte est sauvegardée deux fois de suite dans la fenêtre
    temporelle anti-doublon.
 
    DONNÉES D'ENTRÉE:
    - Deux appels consécutifs à save_alert avec les mêmes paramètres
 
    EXPECTED:
    - Une seule alerte en base (pas de doublon)
    """
 
    session_id, student_id = setup_session_with_student(client, create_user)
 
    with client.application.app_context():
        save_alert(
            session_id=session_id,
            level="individual",
            source="qcm",
            user_id=student_id,
            emotion="demotive",
            ratio=0.75
        )
        save_alert(
            session_id=session_id,
            level="individual",
            source="qcm",
            user_id=student_id,
            emotion="demotive",
            ratio=0.75
        )
 
        alerts = Alert.query.all()
        assert len(alerts) == 1
 
 
# =========================
# SEUILS PARAMÉTRABLES
# =========================
 
def test_alert_custom_threshold_not_triggered(client, create_user):
    """
    ID: UT-APP-ALERT-THRESHOLD-001
 
    SCENARIO:
    Session créée avec un seuil individuel élevé (80%).
    Les réponses produisent un ratio ~75% qui aurait déclenché une alerte
    avec le seuil par défaut (60%) mais pas avec 80%.
 
    DONNÉES D'ENTRÉE:
    - 3 réponses négatives slider=5 sur 4 réponses total
    - Seuil individuel : 0.80
 
    EXPECTED:
    - check_individual_alert_qcm retourne False
    - ratio < 0.80
    """
 
    session_id, student_id = setup_session_with_student(
        client, create_user, seuil_individuel=80
    )
 
    with client.application.app_context():
        for i in range(3):
            db.session.add(QCMResponse(
                session_id=session_id,
                user_id=student_id,
                phase="pendant",
                emotion="demotive",
                slider_value=5,
                occurrence=i + 1
            ))
        db.session.add(QCMResponse(
            session_id=session_id,
            user_id=student_id,
            phase="pendant",
            emotion="motive",
            slider_value=5,
            occurrence=4
        ))
        db.session.commit()
 
        triggered, ratio, _ = check_individual_alert_qcm(session_id, student_id, seuil=0.80)
 
        assert triggered is False
        assert ratio < 0.80
