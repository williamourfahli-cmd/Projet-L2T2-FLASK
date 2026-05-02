import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configuration du client Groq
client = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

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
- Évite les réponses trop longues, va à l"essentiel pour aide l'utilisateur.

Informations clés :
- Le développeur de cette application : Aymen Herda 
- Le role étudiant ou professeur est choisit par l'utilisateur via un bouton switch lors de l'inscription
- Technologie : Flask, SQLAlchemy, DeepFace (pour l'analyse faciale), Groq (pour ton intelligence).

Si une question dépasse le cadre d'EmoTrack, recentre poliment la conversation sur la plateforme.
"""

def get_chatbot_response(user_input, history=None):
    """
    Génère une réponse via l'API Groq.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Clé API Groq manquante dans le fichier .env"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": user_input})
    
    try:
        # Modèle haute performance demandé
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1024
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Erreur détaillée Groq API : {type(e).__name__}: {e}")
        return f"Désolé, je rencontre une difficulté technique (Groq {type(e).__name__}). Réessaie dans un instant."
