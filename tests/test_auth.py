from models import User
# Importe la table User de la base de données

#==================================================================================================================================
#UT-APP-register-001
"""Vérifie qu'un utilisateur peut s'inscrire correctement."""
def test_register(client):
    #Execute la fonction register avec un exemple 
    # Ici Jean Dupont, dont l'adresse mail jean@etu.u-paris.fr et le mot de passe est password123, est un étudiant qui s'inscrit
    client.post("/register", data={
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean@etu.u-paris.fr",
        "password": "password123"
    })

    # Accès à la base via app_context
    with client.application.app_context():
        user = User.query.filter_by(email="jean@etu.u-paris.fr").first()

        assert user is not None,"TEST ECHOUE : l'étudiant inscrit n'est pas enregistré dans la base de données."
        assert user.role.value == "student","TEST ECHOUE : le rôle assigné est différent du rôle étudiant."
    # Nous vérifions que l'utilisateur Jean Dupont a bien été enregistré dans la base de données avec le bon rôle

#==============================================================================================================================
#UT-APP-login-001
""" Vérifie qu'un utilisateur peut se connecter."""
def test_login(client):
    # Création utilisateur
    client.post("/register", data={
        "first_name": "Alice",
        "last_name": "Test",
        "email": "alice@etu.u-paris.fr",
        "password": "password123"
    })

    #response est une variable contenant l'execution de login
    response = client.post("/login", data={
        "email": "alice@etu.u-paris.fr",
        "password": "password123"
    }, follow_redirects=True) #Vérifique la redirection est correcte

    assert response.status_code == 200,"TEST ECHOUE : problemes dans les redirections."
    #Vérifie que l'ensemble des requêtes HTTP sont valides 

#=======================================================================================================================================================================
#UT-APP-login-002
"""Vérifie qu'un login échoue avec un mauvais mot de passe."""
def test_login_failure(client): 
    # Execute la fonction register pour créer un nouvel élève appelé Bob Smith qui a pour adresse mail "bob@etu.u-paris.fr" et qui a pour mot de passe "password123"
    client.post("/register", data={
        "first_name": "Bob",
        "last_name": "SMITH",
        "email": "bob@etu.u-paris.fr",
        "password": "password123"
    })

    # Execute la fontion login avec un mode passe différent que celui dans la base de données (mot de passe incorect)
    response = client.post("/login", data={
        "email": "bob@etu.u-paris.fr",
        "password": "wrongpassword"
    }, follow_redirects=True)

    assert b"incorrect" in response.data.lower(), "TEST ECHOUE : La page retournée ne contient pas le mot 'incorrect'"

#=====================================================================================================================================================
#Explications supplémentaires du code :
""" Prenons le morceau de code suivant : 
response = client.post("/login", data={
        "email": "bob@etu.u-paris.fr",
        "password": "wrongpassword"
    }, follow_redirects=True)

-> client :  est un objet Flask qui simule un client HTTP pour intéragir avec notre application*

-> post : envoie une requête HTTP POST à l'URL "/login" pour executé la fontion login

-> data : est un dictionnaire contennant les données du formulaire envoyé avec la requête. 
          Ici on envoie un email et un mot de passe incorrect

-> follow_redirects = True : Indique au client de suivre automatiquement les redirections HTTP.
                            Cela permet de récupérer la réponse finale après toutes les redirections et non pas seulement la première réponse

-> assert b."incorrect" in response.data.lower : Permet de vérifier que la fonction redirige vers une page contenant la chaine  "incorrect"
                         response.data contient le corps de la réponse HTTP (ici le contenu de la page HTML) sous forme de byte
                        .lower permet de convertir les caractères de la réponse en miniscules pour rendre la recherche du mot "incorrect" dans la page insensible à la casse
"""
