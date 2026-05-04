# Module standard Python : permet de récupérer les variables d'environnement
import os

# Client OpenAI utilisé ici pour appeler l'API Groq compatible avec le format OpenAI
from openai import OpenAI

# Permet de charger les variables définies dans le fichier .env en local
from dotenv import load_dotenv


# Charge les variables d'environnement dès le démarrage du fichier
load_dotenv()


# ============================================================
# CONFIGURATION DU CLIENT GROQ
# ============================================================

# Création du client API.
# Groq utilise une API compatible avec OpenAI, donc on peut utiliser le client OpenAI
# en changeant simplement le base_url.
client = OpenAI(
    # Clé API Groq récupérée depuis les variables d'environnement
    api_key=os.environ.get("GROQ_API_KEY"),

    # URL de base de l'API Groq compatible OpenAI
    base_url="https://api.groq.com/openai/v1",
)


# ============================================================
# PROMPT SYSTÈME DU CHATBOT
# ============================================================

# Le prompt système définit le rôle du chatbot et ses limites.
# Il sert à guider le modèle pour qu'il réponde uniquement dans le contexte d'EmoTrack.
SYSTEM_PROMPT = """
Tu es l'Assistant EmoTrack, une intelligence artificielle spécialisée pour accompagner les utilisateurs de la plateforme EmoTrack. 
EmoTrack est un outil de suivi émotionnel en temps réel utilisé dans l'enseignement supérieur, cette application a été concue par quatre étudiants de l'Université Paris Cité.

Tes missions :
1. Aider les ÉTUDIANTS : Expliquer comment rejoindre une session avec un code, rassurer sur l'anonymat des données, expliquer le fonctionnement des QCM et de l'analyse webcam (DeepFace).
2. Aider les PROFESSEURS : Expliquer comment créer une session, comment interpréter les tableaux de bord (courbes d'engagement, donuts émotionnels), et comment gérer les alertes de baisse d'engagement.
3. Support Technique : Guider les utilisateurs en cas de problème de connexion ou de caméra.

Ton ton doit être :
- Professionnel et bienveillant.
- Clair et concis.
- Empathique vis-à-vis du stress étudiant.
- Évite les réponses trop longues, va à l'essentiel pour aider l'utilisateur.

Informations clés :
- Le développeur de cette application : Aymen Herda 
- Le rôle étudiant ou professeur est choisi par l'utilisateur via un bouton switch lors de l'inscription
- Technologie : Flask, SQLAlchemy, DeepFace (pour l'analyse faciale), Groq (pour ton intelligence).

Si une question dépasse le cadre d'EmoTrack, recentre poliment la conversation sur la plateforme.
"""


# ============================================================
# FONCTION PRINCIPALE DU CHATBOT
# ============================================================

def get_chatbot_response(user_input, history=None):
    """
    Génère une réponse via l'API Groq.

    Fonctionnement :
    - vérifie que la clé API Groq est disponible
    - construit la liste des messages envoyés au modèle
    - ajoute le prompt système
    - ajoute l'historique de conversation si disponible
    - ajoute le nouveau message utilisateur
    - appelle le modèle Groq
    - retourne la réponse générée

    Args:
        user_input (str): message envoyé par l'utilisateur
        history (list | None): historique de conversation envoyé par le front

    Returns:
        str: réponse générée par le chatbot ou message d'erreur
    """

    # Récupère la clé API Groq depuis les variables d'environnement
    api_key = os.environ.get("GROQ_API_KEY")

    # Si aucune clé n'est configurée, l'appel à Groq est impossible
    if not api_key:
        return "Clé API Groq manquante dans le fichier .env"

    # Initialise la conversation avec le prompt système
    # Ce message indique au modèle comment il doit se comporter
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Si un historique est fourni, on l'ajoute pour garder le contexte de la conversation
    if history:
        for msg in history:
            # Chaque message doit contenir un rôle et un contenu
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    # Ajoute le nouveau message de l'utilisateur à la fin de la conversation
    messages.append({
        "role": "user",
        "content": user_input
    })

    try:
        # Appelle le modèle Groq avec la conversation complète
        response = client.chat.completions.create(
            # Modèle utilisé pour générer la réponse
            model="llama-3.3-70b-versatile",

            # Liste des messages envoyés au modèle
            messages=messages,

            # Température : plus elle est élevée, plus les réponses peuvent varier
            temperature=0.7,

            # Limite maximale de tokens générés pour éviter des réponses trop longues
            max_tokens=1024
        )

        # Récupère et retourne uniquement le texte de la réponse du modèle
        return response.choices[0].message.content

    except Exception as e:
        # Affiche l'erreur complète dans les logs serveur pour faciliter le débogage
        print(f"Erreur détaillée Groq API : {type(e).__name__}: {e}")

        # Retourne un message simple à l'utilisateur sans exposer trop de détails techniques
        return f"Désolé, je rencontre une difficulté technique (Groq {type(e).__name__}). Réessaie dans un instant."
