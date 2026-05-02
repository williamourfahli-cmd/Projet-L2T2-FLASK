# EmoTrack — Plateforme de Suivi Émotionnel

EmoTrack est une solution innovante permettant de mesurer l'engagement et l'état émotionnel des étudiants en temps réel lors de sessions pédagogiques. En combinant des questionnaires interactifs (QCM) et une analyse facultative par webcam (via DeepFace), EmoTrack offre aux professeurs des tableaux de bord précis pour adapter leur enseignement.

## 🚀 Fonctionnalités Clés

- **Authentification Sécurisée** : Inscription et connexion pour Étudiants et Professeurs avec vérification d'email universitaire (@u-paris.fr).
- **Sessions en Temps Réel** : Création de sessions avec codes uniques, fréquences paramétrables et modes d'affichage personnalisés.
- **Mesure Subjective (QCM)** : Questionnaires périodiques (Avant, Pendant, Après) pour recueillir le ressenti des étudiants.
- **Mesure Objective (Webcam)** : Analyse faciale temps réel pour détecter les émotions (Joie, Neutre, Surprise, Peur, etc.) via un service DeepFace distant.
- **Tableaux de Bord Avancés** : Visualisation des courbes d'engagement, donuts émotionnels et moyennes globales/individuelles.
- **Système d'Alertes** : Détection automatique des baisses d'engagement (individuelles ou collectives) selon des seuils définis.
- **🤖 EmoTrack Assistant** : Chatbot intelligent intégré, propulsé par l'API Groq (Llama 3), pour assister les utilisateurs dans l'utilisation de la plateforme.

## 🛠️ Installation et Configuration

### 1. Prérequis
- Python 3.10+
- Un compte [Groq](https://console.groq.com/) pour la clé API.

### 2. Installation
```bash
git clone <url-du-repo>
cd Projet-L2T2-FLASK
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration de l'environnement
Créez un fichier `.env` à la racine du projet et complétez les variables suivantes :
```env
SECRET_KEY=votre_cle_secrete
DATABASE_URL=sqlite:///database.db
GROQ_API_KEY=votre_cle_groq
MAIL_USERNAME=votre_email@gmail.com
MAIL_PASSWORD=votre_mot_de_passe_app
BREVO_API_KEY=votre_cle_brevo
DEEPFACE_URL=votre_url_service_deepface
DEEPFACE_SECRET_KEY=votre_secret_deepface
```

### 4. Initialisation de la base de données
```bash
python reset_db.py
```

### 5. Lancement
```bash
python app.py
```

## 🏗️ Architecture
- `app.py` : Cœur de l'application Flask et gestion des routes.
- `models.py` : Définition des schémas de base de données avec SQLAlchemy.
- `templates/` : Interfaces utilisateur (HTML/Jinja2).
- `static/` : Ressources statiques (CSS, JS, Images).

---
*Développé dans le cadre du projet L2T2 - Université Paris Cité.*
