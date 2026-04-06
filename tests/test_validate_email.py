from app import validate_email
from models import UserRole


def test_email_student_valid():
    ok, role, _ = validate_email("test@etu.u-paris.fr")
    assert ok is True
    assert role == UserRole.STUDENT


def test_email_prof_valid():
    ok, role, _ = validate_email("prof@u-paris.fr")
    assert ok is True
    assert role == UserRole.PROFESSOR


def test_email_invalid():
    ok, role, _ = validate_email("test@gmail.com")
    assert ok is False
    assert role is None
