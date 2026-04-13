from app import validate_email
from models import UserRole

""" TESTS DE LA FONCTION validate_email DE app.py"""

#===========================================================================
#UT-APP-validate_email-001
"""Test de la fonction avec une adresse mail étudiante valide"""
def test_email_étudiant_valide():
    ok, role, _ = validate_email("test@etu.u-paris.fr")
    assert ok is True,"TEST ECHOUE : La fonction validate_email ne s'est pas correctement executée."
    #Vérifie que la fonction c'est correctement executée
    assert role == UserRole.STUDENT, "TEST ECHOUE : Le rôle enregistré dans la base de données est différent du rôle STUDENT"
    # Vérifie que le rôle de l'utilisateur fans la table User de la base de données est bien "Student"

#============================================================================
 # UT-APP-validate_email-002
""" Test avec une adresse mail professeur valide """
def test_email_professeur_valide():
    ok, role, _ = validate_email("prof@u-paris.fr")
    assert ok is True,"TEST ECHOUE : la fonction validate_email ne s'est pas correctement executée."
    assert role == UserRole.PROFESSOR,"TEST ECHOUE : le rôle assigné est différent de PROFESSOR"

#========================================================================
#UT-APP-validate_email-004
""" Test avec une adresse mail dont le domaine est invalide = cas d'erreur"""
def test_email_domaine_invalide():
    ok, role, _ = validate_email("test@gmail.com")
    assert ok is False
    assert role is None,"TEST ECHOUE : L'instance rôle dans la table User n'est pas vide."

#=========================================================================
#UT-APP-validate_email-003
"""Test la fonction avec une adresse mail contenant un espace = cas d'erreur"""
def test_email_avec_espaces():
    ok, role, _ = validate_email("test test@etu.u-paris.fr")
    assert ok is False
    assert role is None,"TEST ECHOUE : L'instance rôle dans la table User n'est pas vide "

