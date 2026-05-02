# EmoTrack Flask Auth

Mini-projet Flask prêt à lancer pour :
- inscription étudiant / professeur,
- validation de l'email universitaire,
- détection automatique du rôle selon la fin de l'adresse,
- vérification qu'un email n'existe pas déjà,
- connexion et redirection vers la bonne interface.

## Choix du rôle (étudiant/professeur)
L'utilisateur choisit lui même son rôle grâce à un bouton switch

## Fichiers
- `app.py` : application Flask
- `init_db.py` : initialise la base SQLite
- `schema.sql` : schéma SQL
- `templates/` : pages HTML

## Lancer le projet

### 1. Ouvrir un terminal dans le dossier du projet

### 2. Créer un environnement virtuel
```bash
python -m venv venv
```

### 3. Activer l'environnement
Sous Windows :
```bash
venv\Scripts\activate
```

Sous macOS / Linux :
```bash
source venv/bin/activate
```

### 4. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 5. Initialiser la base
```bash
python init_db.py
```

### 6. Lancer l'application
```bash
python app.py
```

### 7. Ouvrir le navigateur
Aller sur :
```text
http://127.0.0.1:5000
```

## Comportement
- Si l'email existe déjà à l'inscription, message + redirection vers connexion.
- Si l'inscription réussit, message de succès + demande de connexion.
- Après connexion :
  - email `@etu.u-paris.fr` → dashboard étudiant
  - email `@u-paris.fr` → dashboard professeur

## Suite possible
Vous pourrez ensuite ajouter :
- consentement données,
- anonymat par session,
- webcam,
- rejoindre / créer une session,
- dashboard émotions.
