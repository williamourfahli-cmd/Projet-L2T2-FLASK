# ============================================================
# IMPORTS
# ============================================================

# Module standard Python : accès aux variables d'environnement
import os

# Module standard Python : expressions régulières, utilisé pour valider le format des emails
import re

# Module standard Python : génération aléatoire, utilisé pour créer les codes de session
import random

# Module standard Python : accès aux lettres/chiffres, utilisé avec random pour les codes de session
import string

# Module standard Python : génération sécurisée de tokens, utilisé pour les liens de confirmation email
import secrets

# Module standard Python : manipulation de dates/heures avec fuseau horaire UTC
from datetime import datetime, timezone, timedelta

# Module standard Python : comptage d'occurrences, utilisé pour trouver les émotions dominantes
from collections import Counter

# Module standard Python : gestion des fuseaux horaires, utilisé pour convertir UTC vers heure française
from zoneinfo import ZoneInfo

# Module standard Python : conversion d'objets Python en JSON, utilisé pour stocker all_emotions en base
import json

# Chargement des variables d'environnement depuis un fichier .env en local
from dotenv import load_dotenv

# Flask : coeur de l'application web
from flask import Flask

# Flask : affichage des templates HTML
from flask import render_template

# Flask : récupération des données envoyées par les formulaires ou requêtes JSON
from flask import request

# Flask : redirections entre les routes
from flask import redirect

# Flask : génération dynamique des URLs des routes
from flask import url_for

# Flask : messages temporaires affichés à l'utilisateur
from flask import flash

# Flask : gestion de la session utilisateur côté serveur
from flask import session

# Flask : réponses JSON pour les routes AJAX/API
from flask import jsonify

# Werkzeug : hashage sécurisé des mots de passe à l'inscription
from werkzeug.security import generate_password_hash

# Werkzeug : vérification du mot de passe à la connexion
from werkzeug.security import check_password_hash

# SQLAlchemy : gestion des erreurs d'intégrité, par exemple doublon en base
from sqlalchemy.exc import IntegrityError

# SQLAlchemy : exécution de requêtes SQL brutes, utilisé pour ALTER TABLE
from sqlalchemy import text

# Requests : appels HTTP vers Brevo et vers le serveur DeepFace Hugging Face
import requests

# Modèles SQLAlchemy de l'application
from models import (
    db,
    User,
    Session,
    Participation,
    UserRole,
    QCMResponse,
    WebcamAnalysis,
    Alert
)

# Fonction du chatbot Groq utilisée par la route /chatbot
from chatbot import get_chatbot_response


# Charger les variables d'environnement dès le démarrage
load_dotenv()


# ============================================================
# INITIALISATION & CONFIGURATION OPTIMISÉE POUR RENDER
# ============================================================

# Création de l'application Flask
app = Flask(__name__)

# Récupère l'URL de la base de données depuis les variables d'environnement.
# Sur Render, cette variable est automatiquement fournie pour PostgreSQL.
uri = os.environ.get("DATABASE_URL")

if uri:
    # Render peut fournir une URL qui commence par postgres://.
    # SQLAlchemy attend plutôt postgresql://, donc on corrige le préfixe si besoin.
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    # En production, PostgreSQL sur Render demande généralement une connexion SSL.
    # Si sslmode=require n'est pas déjà présent dans l'URL, on l'ajoute.
    if "sslmode" not in uri:
        if "?" in uri:
            uri += "&sslmode=require"
        else:
            uri += "?sslmode=require"

    # Configuration de SQLAlchemy avec l'URL PostgreSQL de Render
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
else:
    # Si aucune URL PostgreSQL n'est trouvée, on utilise SQLite en local.
    # Cela permet de lancer l'application sur son PC sans config Render.
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

# Désactive le suivi automatique des modifications SQLAlchemy.
# Cela évite des warnings et économise un peu de mémoire.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Options de connexion à la base.
# Elles permettent de rendre la connexion PostgreSQL plus stable sur Render.
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    # Vérifie que la connexion est encore active avant de l'utiliser.
    "pool_pre_ping": True,

    # Recycle les connexions régulièrement pour éviter les connexions expirées.
    "pool_recycle": 300,

    # Temps maximum d'attente pour récupérer une connexion disponible.
    "pool_timeout": 30,

    # Nombre de connexions gardées ouvertes dans le pool.
    "pool_size": 5,

    # Nombre de connexions supplémentaires autorisées temporairement.
    "max_overflow": 2,
}

# Clé secrète utilisée par Flask pour sécuriser les sessions utilisateur.
# En production, elle doit venir d'une variable d'environnement.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-a-changer-en-prod")

# Protection du cookie de session.
# Lax permet de garder un comportement compatible tout en limitant certains risques CSRF.
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Durée de validité d'une session permanente, ici 7200 secondes = 2 heures.
app.config["PERMANENT_SESSION_LIFETIME"] = 7200


# ============================================================
# CONFIGURATION BASE DE DONNÉES
# ============================================================

# Lie l'objet SQLAlchemy à l'application Flask.
# À partir de ce moment, db peut utiliser la configuration de l'application.
db.init_app(app)

# Crée automatiquement les tables au démarrage si elles n'existent pas.
# Ce bloc est utile sur Render pour éviter d'avoir à lancer une commande manuelle.
with app.app_context():
    try:
        # Crée les tables définies dans models.py si elles n'existent pas encore.
        db.create_all()

        print("Base de données connectée et tables créées/vérifiées !")

        # Inspecte la structure actuelle de la base de données.
        # Cela permet de vérifier si certaines colonnes existent déjà.
        inspector = db.inspect(db.engine)

        # Récupère la liste des colonnes présentes dans la table users.
        existing_columns = [col["name"] for col in inspector.get_columns("users")]

        # Ouvre une connexion directe pour exécuter des requêtes SQL brutes.
        with db.engine.connect() as conn:

            # Ajoute la colonne email_verified si elle n'existe pas encore.
            # Elle permet de savoir si l'utilisateur a confirmé son email.
            if "email_verified" not in existing_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE"))
                print("Colonne email_verified ajoutée.")

            # Ajoute la colonne verification_token si elle n'existe pas encore.
            # Elle sert à stocker le token envoyé par mail pour confirmer le compte.
            if "verification_token" not in existing_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN verification_token VARCHAR(100)"))
                print("Colonne verification_token ajoutée.")

            # Valide les éventuelles modifications SQL effectuées dans ce bloc.
            conn.commit()

    except Exception as e:
        # Affiche l'erreur dans les logs sans faire planter immédiatement l'application.
        # Utile pour diagnostiquer un problème de connexion ou de migration.
        print(f"Erreur lors de l'initialisation de la base : {e}")


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

# ============================================================
# RESULTATS SESSION (MODE COURBE)
# ============================================================

def normalize_qcm_emotion_label(raw_emotion):
    """
    Normalise les émotions provenant des QCM.

    Objectif :
    - homogénéiser les libellés
    - éviter les différences d'écriture
    - préparer des labels propres pour le donut QCM

    Args:
        raw_emotion (str): émotion brute stockée en base

    Returns:
        str: émotion normalisée
    """

    # Si aucune émotion n'est reçue, on retourne une valeur par défaut
    if not raw_emotion:
        return "Inconnu"

    # Nettoie la valeur reçue pour éviter les problèmes de majuscules ou d'espaces
    emotion = raw_emotion.strip().lower()

    # Association entre les valeurs stockées en base et les libellés affichés côté professeur
    mapping = {
        "motive": "Motivé",
        "neutre": "Neutre",
        "ennuye": "Ennuyé",
        "stresse": "Stressé",
        "demotive": "Démotivé"
    }

    # Retourne le libellé normalisé si connu, sinon retourne la valeur brute
    return mapping.get(emotion, raw_emotion)


def normalize_webcam_emotion_label(raw_emotion):
    """
    Normalise les émotions provenant de DeepFace
    pour afficher une légende en français dans le donut webcam.

    Args:
        raw_emotion (str): émotion brute détectée par DeepFace

    Returns:
        str: émotion normalisée en français
    """

    # Si DeepFace ne renvoie aucune émotion, on affiche une valeur neutre
    if not raw_emotion:
        return "Inconnu"

    # Nettoie l'émotion pour faciliter la comparaison avec le mapping
    emotion = raw_emotion.strip().lower()

    # Traduction des émotions DeepFace en libellés français pour l'affichage
    mapping = {
        "happy": "Joie",
        "neutral": "Neutre",
        "surprise": "Surprise",
        "fear": "Peur",
        "sad": "Tristesse",
        "angry": "Colère",
        "disgust": "Dégoût"
    }

    # Retourne la traduction si elle existe, sinon garde la valeur d'origine
    return mapping.get(emotion, raw_emotion)


def qcm_engagement_score(response):
    """
    Convertit une réponse QCM en score d'engagement sur 100.

    Logique V1 :
    - émotion de base -> score de base
    - slider -> pondération légère

    Args:
        response (QCMResponse): ligne ORM de réponse QCM

    Returns:
        float: score d'engagement sur 100
    """

    # Score de base associé à chaque émotion QCM
    # Plus l'émotion est positive, plus le score est élevé
    base_scores = {
        "motive": 100,
        "neutre": 60,
        "ennuye": 30,
        "stresse": 40,
        "demotive": 10
    }

    # Récupère l'émotion de la réponse en évitant les erreurs si elle est vide
    emotion = (response.emotion or "").strip().lower()

    # Si l'émotion n'est pas reconnue, on applique un score neutre par défaut
    base_score = base_scores.get(emotion, 50)

    # Récupère l'intensité choisie par l'étudiant.
    # Si aucune valeur n'existe, on prend 3 comme intensité neutre.
    slider = response.slider_value if response.slider_value is not None else 3

    # Sécurise la valeur pour qu'elle reste toujours entre 1 et 5
    slider = max(1, min(slider, 5))

    # Transforme le slider en coefficient entre 0.2 et 1.0
    slider_factor = slider / 5.0

    # Applique la pondération et arrondit le résultat à 2 décimales
    return round(base_score * slider_factor, 2)


def webcam_engagement_score(analysis):
    """
    Convertit une analyse webcam en score d'engagement sur 100.

    Logique V1 :
    - émotion DeepFace -> score de base
    - confiance -> pondération

    Args:
        analysis (WebcamAnalysis): ligne ORM d'analyse webcam

    Returns:
        float: score d'engagement sur 100
    """

    # Score de base attribué à chaque émotion détectée par DeepFace
    base_scores = {
        "happy": 90,
        "neutral": 60,
        "surprise": 70,
        "fear": 25,
        "sad": 20,
        "angry": 15,
        "disgust": 10
    }

    # Récupère l'émotion dominante détectée par DeepFace
    emotion = (analysis.dominant_emotion or "").strip().lower()

    # Si l'émotion n'est pas reconnue, on utilise un score neutre par défaut
    base_score = base_scores.get(emotion, 50)

    # Récupère le niveau de confiance DeepFace.
    # Si la confiance est absente, on prend 50 % par défaut.
    confidence = analysis.confidence if analysis.confidence is not None else 50.0

    # Sécurise la confiance pour qu'elle reste entre 0 et 100
    confidence = max(0.0, min(confidence, 100.0))

    # Transforme la confiance en coefficient entre 0 et 1
    confidence_factor = confidence / 100.0

    # Applique la pondération par confiance et arrondit le résultat
    return round(base_score * confidence_factor, 2)


def build_session_curve_data(session_id):
    """
    Prépare toutes les données de la page résultats.

    Cette fonction construit :
    - la courbe principale d'engagement général
    - le donut QCM
    - le donut DeepFace
    - les compteurs utiles

    Pour la courbe :
    - on regroupe les données par minute
    - on convertit les dates en heure française
    - on calcule une moyenne des scores dans chaque minute

    Args:
        session_id (int): id de la session

    Returns:
        dict: données prêtes à envoyer au template / JSON
    """

    # ========================
    # 1. Récupération QCM
    # ========================

    # Récupère toutes les réponses QCM de la session, triées de la plus ancienne à la plus récente
    qcm_rows = QCMResponse.query.filter_by(
        session_id=session_id
    ).order_by(QCMResponse.answered_at.asc()).all()

    # ========================
    # 2. Récupération webcam
    # ========================

    # Récupère toutes les analyses webcam de la session, triées chronologiquement
    webcam_rows = WebcamAnalysis.query.filter_by(
        session_id=session_id
    ).order_by(WebcamAnalysis.analyzed_at.asc()).all()

    # ========================
    # 3. Structure de la courbe
    # ========================

    # Dictionnaire utilisé pour regrouper les scores par minute
    # clé = minute locale "YYYY-MM-DD HH:MM"
    # valeur = liste des scores calculés pendant cette minute
    time_buckets = {}

    # ========================
    # 4. Structures des donuts
    # ========================

    # Initialise toutes les émotions QCM à 0 pour garantir leur présence dans le graphique
    qcm_emotion_counts = {
        "Motivé": 0,
        "Neutre": 0,
        "Ennuyé": 0,
        "Stressé": 0,
        "Démotivé": 0
    }

    # Initialise toutes les émotions webcam à 0 pour le donut DeepFace
    webcam_emotion_counts = {
        "Joie": 0,
        "Neutre": 0,
        "Surprise": 0,
        "Peur": 0,
        "Tristesse": 0,
        "Colère": 0,
        "Dégoût": 0
    }

    # ========================
    # 5. Traitement QCM
    # ========================

    for row in qcm_rows:

        # Ignore les réponses sans date pour éviter une erreur de conversion horaire
        if not row.answered_at:
            continue

        # Convertit la date UTC stockée en base vers l'heure française
        local_dt = row.answered_at.astimezone(ZoneInfo("Europe/Paris"))

        # Regroupe les données par minute pour lisser la courbe
        bucket = local_dt.strftime("%Y-%m-%d %H:%M")

        # Crée la liste de scores pour cette minute si elle n'existe pas encore
        if bucket not in time_buckets:
            time_buckets[bucket] = []

        # Convertit la réponse QCM en score d'engagement
        score = qcm_engagement_score(row)

        # Ajoute le score dans le groupe correspondant à sa minute
        time_buckets[bucket].append(score)

        # Normalise l'émotion pour l'afficher correctement dans le donut QCM
        normalized = normalize_qcm_emotion_label(row.emotion)

        # Incrémente le compteur uniquement si l'émotion fait partie des labels prévus
        if normalized in qcm_emotion_counts:
            qcm_emotion_counts[normalized] += 1

    # ========================
    # 6. Traitement webcam
    # ========================

    for row in webcam_rows:

        # Ignore les analyses sans date pour éviter une erreur de conversion horaire
        if not row.analyzed_at:
            continue

        # Convertit la date UTC de l'analyse en heure française
        local_dt = row.analyzed_at.astimezone(ZoneInfo("Europe/Paris"))

        # Regroupe les analyses par minute, comme pour les réponses QCM
        bucket = local_dt.strftime("%Y-%m-%d %H:%M")

        # Crée le groupe de scores si cette minute n'existe pas encore
        if bucket not in time_buckets:
            time_buckets[bucket] = []

        # Convertit l'analyse webcam en score d'engagement
        score = webcam_engagement_score(row)

        # Ajoute le score webcam dans la même structure que les scores QCM
        time_buckets[bucket].append(score)

        # Traduit l'émotion DeepFace pour l'affichage dans le donut webcam
        normalized = normalize_webcam_emotion_label(row.dominant_emotion)

        # Incrémente le compteur si l'émotion fait partie des catégories prévues
        if normalized in webcam_emotion_counts:
            webcam_emotion_counts[normalized] += 1

    # ========================
    # 7. Construction courbe finale
    # ========================

    # Trie les minutes dans l'ordre chronologique
    sorted_keys = sorted(time_buckets.keys())

    # Labels affichés sur l'axe X du graphique
    engagement_labels = []

    # Valeurs moyennes affichées sur la courbe
    engagement_values = []

    for key in sorted_keys:
        scores = time_buckets[key]

        # Calcule la moyenne des scores de la minute
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0

        # Pour l'affichage, on garde uniquement l'heure et les minutes
        display_label = key[-5:]

        engagement_labels.append(display_label)
        engagement_values.append(avg_score)

    # ========================
    # 8. Retour final
    # ========================

    # Retourne toutes les données nécessaires aux graphiques et aux compteurs
    return {
        "engagement_labels": engagement_labels,
        "engagement_values": engagement_values,
        "qcm_emotion_labels": list(qcm_emotion_counts.keys()),
        "qcm_emotion_values": list(qcm_emotion_counts.values()),
        "webcam_emotion_labels": list(webcam_emotion_counts.keys()),
        "webcam_emotion_values": list(webcam_emotion_counts.values()),
        "qcm_count": len(qcm_rows),
        "webcam_count": len(webcam_rows)
    }

def build_session_average_data(session_id):
    """
    Calcule les moyennes émotionnelles pour le mode moyennes.

    Retourne :
    - moyenne_subjective : émotion dominante QCM de la session
    - moyenne_objective  : émotion dominante DeepFace de la session
    - moyenne_generale   : tendance dominante combinée (positif / neutre / negatif)
    - individuals        : liste des étudiants avec leurs stats individuelles
    """

    # Récupère tous les participants de la session
    participations = Participation.query.filter_by(session_id=session_id).all()

    # Listes pour calculer les moyennes globales de la session
    all_qcm_emotions = []
    all_webcam_emotions = []

    individuals = []

    for p in participations:
        user_id = p.student_id
        user = User.query.get(user_id)

        # Récupère toutes les réponses QCM de l'étudiant pour cette session
        qcm_responses = QCMResponse.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).all()

        # Récupère toutes les analyses webcam de l'étudiant pour cette session
        webcam_analyses = WebcamAnalysis.query.filter_by(
            session_id=session_id,
            user_id=user_id
        ).all()

        # Émotions brutes QCM de cet étudiant
        qcm_emotions = [
            r.emotion.strip().lower()
            for r in qcm_responses
            if r.emotion
        ]

        # Émotions brutes webcam de cet étudiant
        webcam_emotions = [
            a.dominant_emotion.strip().lower()
            for a in webcam_analyses
            if a.dominant_emotion
        ]

        # Émotion QCM dominante de cet étudiant
        emotion_qcm = compute_dominant(qcm_emotions) if qcm_emotions else None

        # Émotion webcam dominante de cet étudiant
        emotion_webcam = compute_dominant(webcam_emotions) if webcam_emotions else None

        # Combine QCM et webcam traduit pour calculer la tendance générale
        toutes_emotions = qcm_emotions + [
            translate_emotion(e) for e in webcam_emotions if translate_emotion(e)
        ]
        
        emotion_dominante = compute_dominant(toutes_emotions) if toutes_emotions else None

        # Ajoute aux listes globales pour les moyennes de session
        all_qcm_emotions.extend(qcm_emotions)
        all_webcam_emotions.extend(webcam_emotions)

        # Détermine si l'étudiant est anonyme
        anonymous = p.anonymous if hasattr(p, "anonymous") else False

        # Construit le nom affiché
        name = "Anonyme"
        if user and not anonymous:
            name = f"{user.first_name} {user.last_name}"

        individuals.append({
            "user_id": user_id,
            "name": name,
            "anonymous": anonymous,
            "emotion_qcm": emotion_qcm,
            "emotion_webcam": emotion_webcam,
            "emotion_dominante": emotion_dominante,
            "nb_qcm": len(qcm_responses),
            "nb_webcam": len(webcam_analyses),
        })

    # Calcule la moyenne subjective globale (QCM)
    moyenne_subjective = compute_dominant(all_qcm_emotions) if all_qcm_emotions else None

    # Calcule la moyenne objective globale (DeepFace)
    all_webcam_translated = [
        translate_emotion(e) for e in all_webcam_emotions if translate_emotion(e)
    ]
    moyenne_objective = compute_dominant(all_webcam_translated) if all_webcam_translated else None

    # Calcule la tendance générale de la session
    all_emotions_reelles = all_qcm_emotions + all_webcam_translated
    moyenne_generale = compute_dominant(all_emotions_reelles) if all_emotions_reelles else None

    return {
        "moyenne_subjective": moyenne_subjective,
        "moyenne_objective": moyenne_objective,
        "moyenne_generale": moyenne_generale,
        "individuals": individuals,
    }
    
# ============================================================
# MOYENNES ÉMOTIONNELLES (MODE MOYENNES)
# ============================================================

# Mapping des émotions vers une tendance commune.
# On garde des valeurs internes sans accents pour éviter les incohérences dans les calculs.
"""EMOTION_MAP = {
    # Émotions QCM stockées en base
    "motive": "positif",
    "neutre": "neutre",
    "ennuye": "negatif",
    "stresse": "negatif",
    "demotive": "negatif",

    # Émotions DeepFace brutes
    "happy": "positif",
    "neutral": "neutre",
    "surprise": "neutre",
    "sad": "negatif",
    "angry": "negatif",
    "disgust": "negatif",
    "fear": "negatif",

    # Émotions DeepFace traduites sans accents
    "surpris": "neutre",
    "triste": "negatif",
    "en colere": "negatif",
    "degoute": "negatif",
}
""""

def compute_dominant(emotions_list):
    """
    Retourne l'émotion ou la tendance la plus fréquente d'une liste.

    Args:
        emotions_list (list[str]): liste d'émotions ou de tendances

    Returns:
        str: valeur dominante, ou "Aucune donnée" si la liste est vide
    """

    # Si la liste est vide, aucune dominante ne peut être calculée
    if not emotions_list:
        return "Aucune donnée"

    # Dictionnaire utilisé pour compter le nombre d'apparitions de chaque valeur
    counts = {}

    # Parcourt toutes les émotions et incrémente leur compteur
    for e in emotions_list:
        counts[e] = counts.get(e, 0) + 1

    # Retourne la valeur qui possède le compteur le plus élevé
    return max(counts, key=counts.get)


"""def emotion_category(emotion):
    """
    Convertit une émotion brute ou traduite en tendance commune.

    Exemples :
    - motive / happy -> positif
    - neutre / neutral -> neutre
    - stresse / fear -> negatif

    Args:
        emotion (str): émotion brute ou traduite

    Returns:
        str | None: tendance commune, ou None si l'émotion est vide/inconnue
    """

    # Si aucune émotion n'est fournie, on ne peut pas la catégoriser
    if not emotion:
        return None

    # Nettoie l'émotion pour éviter les problèmes de majuscules ou d'espaces
    emotion = emotion.strip().lower()

    # Retourne la tendance commune si l'émotion existe dans le mapping
    return EMOTION_MAP.get(emotion)"""


# ============================================================
# TRADUCTION DES ÉMOTIONS DEEPFACE
# ============================================================

# Traduction des émotions DeepFace vers les valeurs internes du projet.
# Les valeurs restent sans accents pour faciliter les calculs et comparaisons.
EMOTION_TRANSLATIONS = {
    "angry":    "en colere",
    "disgust":  "degoute",
    "fear":     "stresse",
    "happy":    "motive",
    "sad":      "triste",
    "surprise": "surpris",
    "neutral":  "neutre",
}


def translate_emotion(emotion):
    """
    Traduit une émotion DeepFace en valeur interne utilisée par l'application.

    Args:
        emotion (str): émotion renvoyée par DeepFace

    Returns:
        str | None: émotion traduite, émotion originale si inconnue, ou None si vide
    """

    # Si aucune émotion n'est reçue, on ne retourne rien
    if not emotion:
        return None

    # Convertit en minuscule puis cherche la traduction correspondante
    return EMOTION_TRANSLATIONS.get(emotion.lower(), emotion)


@app.template_filter('heure_fr')
def heure_fr(dt):
    """
    Convertit une date UTC en heure française pour l'affichage dans les templates.

    Args:
        dt (datetime): date stockée en base

    Returns:
        str: date formatée en heure française
    """

    # Si la date n'existe pas, cela signifie généralement que la session est encore en cours
    if dt is None:
        return "En cours"

    # Convertit la date vers le fuseau horaire de Paris puis la formate lisiblement
    return dt.astimezone(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y à %Hh%M")


def validate_email(email: str):
    """
    Valide une adresse email de manière générique.

    Règles :
    - Pas d'espaces
    - Format standard : texte@texte.domaine
    - Longueur raisonnable
    - Normalisation en minuscules

    Args:
        email (str): email saisi par l'utilisateur

    Returns:
        tuple:
            - bool : validité
            - str : email normalisé
            - str : message d'erreur éventuel
    """

    # Vérifie qu'une adresse email a bien été saisie
    if not email:
        return False, None, "Email requis."

    # Nettoie l'adresse et force les minuscules pour éviter les doublons liés à la casse
    email = email.strip().lower()

    # Refuse les espaces, car ils rendent l'adresse invalide
    if " " in email:
        return False, None, "L'adresse email ne doit pas contenir d'espaces."

    # Limite standard d'une adresse email complète
    if len(email) > 254:
        return False, None, "Email trop long."

    # Expression régulière qui vérifie un format email classique
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    # Vérifie que l'adresse respecte le format attendu
    if not re.match(pattern, email):
        return False, None, "Format d'email invalide."

    # Retourne l'email normalisé si tout est valide
    return True, email, None


def generate_session_code():
    """
    Génère un code de session aléatoire.

    Le code est composé de 6 caractères alphanumériques (A-Z, 0-9).

    Returns:
        str: code session unique
    """

    # Génère une suite aléatoire de 6 caractères en majuscules et chiffres
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def send_confirmation_email(email, first_name, confirm_url):
    """
    Envoie l'email de confirmation via l'API Brevo.

    Args:
        email (str): adresse du destinataire
        first_name (str): prénom du destinataire
        confirm_url (str): lien de confirmation du compte

    Returns:
        bool: True si l'email a été envoyé, False sinon
    """

    # Récupère la clé API Brevo depuis les variables d'environnement
    api_key = os.environ.get("BREVO_API_KEY")

    # Récupère l'adresse expéditeur, avec une valeur par défaut si elle n'est pas définie
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "emotrack@gmail.com")

    # Récupère le nom affiché de l'expéditeur
    sender_name = os.environ.get("BREVO_SENDER_NAME", "EmoTrack")

    # Sans clé API, l'appel à Brevo est impossible
    if not api_key:
        print("[BREVO] BREVO_API_KEY manquante.")
        return False

    # Génère le contenu HTML de l'email à partir du template dédié
    html_body = render_template(
        "email_confirmation.html",
        first_name=first_name,
        confirm_url=confirm_url
    )

    # Prépare une version texte simple pour les clients mail qui n'affichent pas le HTML
    text_body = (
        f"Bonjour {first_name},\n\n"
        "Merci de confirmer ton compte EmoTrack en cliquant sur le lien suivant :\n"
        f"{confirm_url}\n\n"
        "Si tu n'es pas à l'origine de cette inscription, ignore ce message."
    )

    # Corps de la requête envoyé à l'API Brevo
    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email
        },
        "to": [
            {
                "email": email,
                "name": first_name
            }
        ],
        "subject": "Confirme ton compte EmoTrack",
        "htmlContent": html_body,
        "textContent": text_body
    }

    # Headers nécessaires pour authentifier et envoyer la requête à Brevo
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }

    try:
        # Envoie la requête HTTP à Brevo avec un timeout pour éviter de bloquer l'application
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers=headers,
            timeout=10
        )

        # Brevo peut retourner plusieurs codes de succès selon le traitement de l'email
        if response.status_code in [200, 201, 202]:
            print(f"[BREVO] Email de confirmation envoyé à {email}.")
            return True

        # Si Brevo répond mais refuse l'envoi, on log le code et le détail
        print(f"[BREVO] Erreur API status={response.status_code} body={response.text}")
        return False

    except requests.RequestException as e:
        # Gère les erreurs réseau : timeout, problème DNS, serveur inaccessible, etc.
        print(f"[BREVO] Erreur réseau : {repr(e)}")
        return False


# ============================================================
# DEFINITION DES EMOTIONS "NEGATIVES"
# ============================================================

# Émotions QCM considérées comme négatives.
# Ces valeurs correspondent aux émotions stockées en base après réponse au questionnaire.
QCM_EMOTIONS_NEGATIVES = {"demotive", "ennuye", "stresse"}

# Émotions DeepFace considérées comme négatives.
# Ces valeurs correspondent aux émotions brutes renvoyées par le serveur DeepFace.
WEBCAM_EMOTIONS_NEGATIVES = {"angry", "fear"}

# ============================================================
# FONCTIONS DE DÉTECTION
# ============================================================

def check_individual_alert_qcm(session_id, user_id, seuil=0.60):
    """
    Vérifie si un étudiant dépasse le seuil QCM individuel.

    Calcule le ratio des réponses négatives sur l'ensemble de ses réponses
    pendant la session.

    Le ratio est pondéré par l'intensité :
    - une réponse négative avec un slider élevé pèse plus lourd ;
    - une réponse négative avec un slider faible pèse moins lourd.

    Si le ratio dépasse le seuil fixé par le professeur, une alerte est déclenchée.

    Args:
        session_id (int): identifiant de la session
        user_id (int): identifiant de l'étudiant
        seuil (float): seuil d'alerte individuel

    Returns:
        tuple (bool, float, str): alerte déclenchée, ratio calculé, émotion dominante
    """

    # Récupère toutes les réponses QCM de l'étudiant pour cette session
    responses = QCMResponse.query.filter_by(
        session_id=session_id,
        user_id=user_id
    ).all()

    # Si aucune réponse n'existe, il n'y a pas assez de données pour déclencher une alerte
    if not responses:
        print(f"[ALERT QCM] user={user_id} -> {len(responses)} réponse(s) trouvée(s)")
        return False, 0.0, None

    # Sépare les réponses négatives des autres réponses
    negatives = [
        r for r in responses
        if (r.emotion or "").strip().lower() in QCM_EMOTIONS_NEGATIVES
    ]

    # Les réponses positives/neutres correspondent à toutes les réponses non négatives
    positives = [
        r for r in responses
        if r not in negatives
    ]

    # Calcule le poids des réponses négatives selon l'intensité choisie.
    # Si le slider est absent, on prend 3 comme valeur neutre par défaut.
    poids_negatifs = sum(
        (r.slider_value if r.slider_value is not None else 3) / 5.0
        for r in negatives
    )

    # Calcule aussi le poids des réponses non négatives pour obtenir un total comparable
    poids_positifs = sum(
        (r.slider_value if r.slider_value is not None else 3) / 5.0
        for r in positives
    )

    # Poids total de toutes les réponses prises en compte
    poids_total = poids_negatifs + poids_positifs

    # Sécurité pour éviter une division par zéro
    if poids_total == 0:
        return False, 0.0, None

    # Ratio pondéré d'émotions négatives
    ratio = poids_negatifs / poids_total

    # Initialisation de l'émotion négative dominante
    dominant = None

    # Si des émotions négatives existent, on cherche celle qui revient le plus souvent
    if negatives:
        counts = Counter(
            r.emotion.strip().lower()
            for r in negatives
            if r.emotion
        )
        dominant = counts.most_common(1)[0][0] if counts else None

    # Log utile pour vérifier le déclenchement des alertes pendant les tests
    print(
        f"[ALERT QCM] user={user_id} "
        f"-> ratio_pondere={round(ratio, 2)}, "
        f"dominant={dominant}, "
        f"alerte={ratio >= seuil}"
    )

    # Retourne True si le ratio dépasse le seuil configuré
    return ratio >= seuil, round(ratio, 2), dominant
    


def check_individual_alert_webcam(session_id, user_id, seuil=0.60):
    """
    Vérifie si un étudiant dépasse le seuil webcam individuel.

    Calcule le ratio d'analyses négatives sur l'ensemble de ses analyses
    DeepFace pendant la session.

    Contrairement au QCM, ce calcul n'est pas pondéré par un slider.
    On compte simplement la proportion d'émotions négatives détectées.

    Args:
        session_id (int): identifiant de la session
        user_id (int): identifiant de l'étudiant
        seuil (float): seuil d'alerte individuel

    Returns:
        tuple (bool, float, str): alerte déclenchée, ratio calculé, émotion dominante
    """

    # Récupère toutes les analyses webcam de l'étudiant pour cette session
    analyses = WebcamAnalysis.query.filter_by(
        session_id=session_id,
        user_id=user_id
    ).all()

    # Si aucune analyse n'existe, on ne peut pas calculer d'alerte webcam
    if not analyses:
        print(f"[ALERT WEBCAM] user={user_id} -> {len(analyses)} analyse(s) trouvée(s)")
        return False, 0.0, None

    # Sélectionne uniquement les analyses dont l'émotion est considérée comme négative
    negatives = [
        a for a in analyses
        if (a.dominant_emotion or "").strip().lower() in WEBCAM_EMOTIONS_NEGATIVES
    ]

    # Calcule la proportion d'analyses négatives
    ratio = len(negatives) / len(analyses)

    # Initialisation de l'émotion négative dominante
    dominant = None

    # Si des émotions négatives existent, on cherche celle qui revient le plus souvent
    if negatives:
        counts = Counter(
            a.dominant_emotion.strip().lower()
            for a in negatives
            if a.dominant_emotion
        )
        dominant = counts.most_common(1)[0][0] if counts else None

    # Log utile pour suivre les alertes webcam pendant les tests
    print(
        f"[ALERT WEBCAM] user={user_id} "
        f"-> ratio={round(ratio, 2)}, "
        f"dominant={dominant}, "
        f"alerte={ratio >= seuil}"
    )

    # Retourne True si le ratio dépasse le seuil configuré
    return ratio >= seuil, round(ratio, 2), dominant


def check_class_snapshot_alert(session_id, seuil=0.50):
    """
    Vérifie si le dernier QCM collectif dépasse le seuil de classe.

    La fonction se concentre uniquement sur le dernier questionnaire
    de phase "pendant".

    Elle calcule le ratio de réponses négatives sur les réponses
    de cette dernière occurrence.

    Comme pour l'alerte QCM individuelle, le calcul est pondéré
    par l'intensité du slider.

    Args:
        session_id (int): identifiant de la session
        seuil (float): seuil d'alerte collectif

    Returns:
        tuple (bool, float): alerte déclenchée, ratio calculé
    """

    # Récupère le numéro d'occurrence le plus élevé pour les QCM de phase "pendant"
    # Cela correspond au questionnaire collectif le plus récent.
    last_occ = db.session.query(
        db.func.max(QCMResponse.occurrence)
    ).filter_by(
        session_id=session_id,
        phase="pendant"
    ).scalar()

    # Si aucune occurrence n'existe, aucun QCM "pendant" n'a encore été répondu
    if last_occ is None:
        print("[ALERT CLASSE SNAPSHOT] aucune occurrence pendant trouvée")
        return False, 0.0

    # Récupère toutes les réponses correspondant au dernier QCM collectif
    responses = QCMResponse.query.filter_by(
        session_id=session_id,
        phase="pendant",
        occurrence=last_occ
    ).all()

    # Si aucune réponse n'est récupérée, on ne peut pas calculer d'alerte collective
    if not responses:
        return False, 0.0

    # Sépare les réponses négatives des autres réponses
    negatives = [
        r for r in responses
        if (r.emotion or "").strip().lower() in QCM_EMOTIONS_NEGATIVES
    ]

    # Les réponses positives/neutres correspondent aux réponses non négatives
    positives = [
        r for r in responses
        if r not in negatives
    ]

    # Calcule le poids des réponses négatives en tenant compte de l'intensité
    poids_negatifs = sum(
        (r.slider_value if r.slider_value is not None else 3) / 5.0
        for r in negatives
    )

    # Calcule le poids des réponses non négatives avec la même logique
    poids_positifs = sum(
        (r.slider_value if r.slider_value is not None else 3) / 5.0
        for r in positives
    )

    # Additionne les deux poids pour obtenir le total des réponses prises en compte
    poids_total = poids_negatifs + poids_positifs

    # Sécurité pour éviter une division par zéro
    if poids_total == 0:
        return False, 0.0

    # Calcule le ratio pondéré de réponses négatives dans le dernier QCM collectif
    ratio = poids_negatifs / poids_total

    # Log utile pour vérifier le comportement des alertes de classe
    print(
        f"[ALERT CLASSE SNAPSHOT] occurrence={last_occ}, "
        f"{len(responses)} réponse(s), "
        f"ratio_pondere={round(ratio, 2)}, "
        f"alerte={ratio >= seuil}"
    )

    # Retourne True si le ratio dépasse le seuil collectif configuré
    return ratio >= seuil, round(ratio, 2)


def save_alert(session_id, level, source, user_id=None, emotion=None, ratio=None):
    """
    Sauvegarde une alerte en base avec une fenêtre anti-doublon.

    La fenêtre anti-doublon dépend de la source :
    - webcam : fréquence webcam de la session ;
    - qcm / classe : fréquence questionnaire de la session.

    Cela évite d'enregistrer plusieurs fois la même alerte en quelques secondes.

    Args:
        session_id (int): session concernée
        level (str): niveau de l'alerte, "individual" ou "class"
        source (str): source de l'alerte, ex: "qcm", "webcam", "class_snapshot"
        user_id (int | None): étudiant concerné, None pour une alerte de classe
        emotion (str | None): émotion déclenchante
        ratio (float | None): ratio mesuré
    """

    # Récupère la session pour connaître les fréquences configurées par le professeur
    session_obj = Session.query.get(session_id)

    # Utilise la fréquence webcam si l'alerte vient de DeepFace
    if source == "webcam":
        freq = session_obj.frequence_webcam if session_obj else 60

    # Sinon, on utilise la fréquence des questionnaires
    else:
        freq = session_obj.frequence_questionnaire if session_obj else 60

    # Définit une fenêtre anti-doublon entre 60 et 600 secondes.
    # Cela évite une fenêtre trop courte ou trop longue.
    fenetre = max(60, min(600, freq))

    # Toute alerte identique après cette date sera considérée comme récente
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=fenetre)

    # Recherche une alerte similaire déjà créée récemment
    existing = Alert.query.filter(
        Alert.session_id == session_id,
        Alert.level == level,
        Alert.source == source,
        Alert.user_id == user_id,
        Alert.triggered_at >= cutoff
    ).first()

    # Si une alerte similaire existe déjà dans la fenêtre, on ne l'enregistre pas
    if existing:
        return

    # Crée une nouvelle alerte avec les informations calculées
    alert = Alert(
        session_id=session_id,
        user_id=user_id,
        level=level,
        source=source,
        emotion=emotion,
        ratio=ratio
    )

    # Ajoute puis sauvegarde l'alerte en base de données
    db.session.add(alert)
    db.session.commit()


def compute_alerts(session_id):
    """
    Calcule et persiste toutes les alertes actives pour une session.

    Appelée uniquement si le mode "alertes" est sélectionné.
    Utilise les seuils paramétrés par le professeur à la création de la session.

    Returns:
        dict :
        {
            "class_alert"        : bool,
            "class_sources"      : list[str],
            "individual_alerts"  : list[dict]
        }
    """

    # Structure de réponse par défaut.
    # Elle sera enrichie si des alertes sont détectées.
    result = {
        "class_alert": False,
        "class_sources": [],
        "individual_alerts": []
    }

    # Récupère la session pour accéder aux seuils définis par le professeur
    session_obj = Session.query.get(session_id)

    # Récupère les seuils paramétrés pour cette session.
    # Si la session est introuvable, on utilise des valeurs par défaut.
    seuil_ind = session_obj.seuil_individuel if session_obj else 0.60
    seuil_classe = session_obj.seuil_classe if session_obj else 0.50

    # Récupère tous les étudiants ayant rejoint la session
    participations = Participation.query.filter_by(session_id=session_id).all()

    # Compteur utilisé pour savoir combien d'étudiants sont individuellement en alerte
    students_in_alert_count = 0

    # ========================================================
    # Alertes individuelles
    # ========================================================

    for p in participations:

        # Récupère l'utilisateur lié à la participation
        user = User.query.get(p.student_id)

        # Si l'utilisateur n'existe plus, on ignore cette participation
        if not user:
            continue

        # Liste des alertes détectées pour cet étudiant
        student_alerts = []

        # Vérifie l'alerte individuelle basée sur les réponses QCM
        triggered_qcm, ratio_qcm, emotion_qcm = check_individual_alert_qcm(
            session_id,
            p.student_id,
            seuil_ind
        )

        # Si le seuil QCM est dépassé, on sauvegarde l'alerte et on l'ajoute au résultat
        if triggered_qcm:
            save_alert(
                session_id=session_id,
                level="individual",
                source="qcm",
                user_id=p.student_id,
                emotion=emotion_qcm,
                ratio=ratio_qcm
            )

            student_alerts.append({
                "source": "qcm",
                "emotion": emotion_qcm,
                "ratio": ratio_qcm
            })

        # Vérifie l'alerte individuelle basée sur les analyses webcam
        triggered_webcam, ratio_webcam, emotion_webcam = check_individual_alert_webcam(
            session_id,
            p.student_id,
            seuil_ind
        )

        # Si le seuil webcam est dépassé, on sauvegarde l'alerte et on l'ajoute au résultat
        if triggered_webcam:
            save_alert(
                session_id=session_id,
                level="individual",
                source="webcam",
                user_id=p.student_id,
                emotion=emotion_webcam,
                ratio=ratio_webcam
            )

            student_alerts.append({
                "source": "webcam",
                "emotion": emotion_webcam,
                "ratio": ratio_webcam
            })

        # Si au moins une alerte a été détectée pour cet étudiant
        if student_alerts:

            # Incrémente le nombre d'étudiants individuellement en alerte
            students_in_alert_count += 1

            # Ajoute l'étudiant et ses alertes dans la réponse finale
            result["individual_alerts"].append({
                "user_id": p.student_id,

                # Conserve l'information d'anonymat pour l'affichage côté professeur
                "anonymous": p.anonymous,

                # Affiche l'identité uniquement si l'étudiant n'est pas anonyme
                "first_name": user.first_name if not p.anonymous else None,
                "last_name": user.last_name if not p.anonymous else None,

                # Liste des alertes détectées pour cet étudiant
                "alerts": student_alerts
            })

    # ========================================================
    # Alerte de classe : dernier QCM collectif
    # ========================================================

    # Vérifie si le dernier QCM collectif dépasse le seuil de classe
    triggered_snapshot, ratio_snapshot = check_class_snapshot_alert(
        session_id,
        seuil_classe
    )

    # Si le seuil est dépassé, on sauvegarde une alerte de classe
    if triggered_snapshot:
        save_alert(
            session_id=session_id,
            level="class",
            source="class_snapshot",
            ratio=ratio_snapshot
        )

        # Indique qu'au moins une alerte collective est active
        result["class_alert"] = True

        # Précise que l'alerte vient du dernier QCM collectif
        result["class_sources"].append("class_snapshot")

    # ========================================================
    # Alerte de classe : accumulation d'alertes individuelles
    # ========================================================

    # Si la session contient des participants, on peut calculer un ratio de classe
    if participations:

        # Calcule la proportion d'étudiants ayant au moins une alerte individuelle
        ratio_accum = students_in_alert_count / len(participations)

        # Si trop d'étudiants sont en alerte individuelle, on déclenche une alerte collective
        if ratio_accum >= seuil_classe:
            save_alert(
                session_id=session_id,
                level="class",
                source="class_accumulation",
                ratio=round(ratio_accum, 2)
            )

            # Indique qu'une alerte collective est active
            result["class_alert"] = True

            # Précise que l'alerte vient de l'accumulation individuelle
            result["class_sources"].append("class_accumulation")

    # Retourne toutes les alertes calculées pour affichage dans la page résultats
    return result


# ============================================================
# ROUTE PRINCIPALE
# ============================================================

@app.route("/")
def home():
    """
    Route principale de l'application.

    Redirige automatiquement l'utilisateur :
    - vers le dashboard professeur si connecté en tant que professeur
    - vers le dashboard étudiant si connecté en tant qu'étudiant
    - vers la page landing si l'utilisateur n'est pas connecté

    Returns:
        Redirection Flask ou template HTML
    """

    # Si un utilisateur est déjà connecté, son id est stocké dans la session Flask
    if "user_id" in session:

        # Redirige les professeurs vers leur tableau de bord
        if session.get("role") == "professor":
            return redirect(url_for("professor_dashboard"))

        # Tous les autres utilisateurs connectés sont redirigés vers le dashboard étudiant
        return redirect(url_for("student_dashboard"))

    # Si personne n'est connecté, on affiche la page d'accueil publique
    return render_template("landing.html")


# ============================================================
# INSCRIPTION
# ============================================================

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Gère l'inscription d'un nouvel utilisateur.

    Fonctionnement :
    - vérifie les champs du formulaire
    - valide le format de l'email
    - vérifie que l'email n'existe pas déjà
    - crée le compte utilisateur en base
    - génère un token de confirmation
    - envoie un email de confirmation
    """

    # Le traitement d'inscription se fait uniquement lors de l'envoi du formulaire
    if request.method == "POST":

        # Récupère les données du formulaire et nettoie les chaînes de caractères
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role_input = request.form.get("role")

        # Vérifie que tous les champs obligatoires sont présents
        if not all([first_name, last_name, email, password, role_input]):
            flash("Tous les champs sont obligatoires.", "error")
            return render_template("register.html")

        # Vérifie que le mot de passe respecte la longueur minimale
        if len(password) < 8:
            flash("Mot de passe trop court.", "error")
            return render_template("register.html")

        # Vérifie et normalise l'adresse email
        is_valid, email, error = validate_email(email)

        # Si l'email est invalide, on affiche le message d'erreur correspondant
        if not is_valid:
            flash(error, "error")
            return render_template("register.html")

        # Convertit le rôle reçu depuis le formulaire en valeur attendue par le modèle User
        if role_input == "student":
            role = UserRole.STUDENT
        elif role_input == "professor":
            role = UserRole.PROFESSOR
        else:
            flash("Rôle invalide.", "error")
            return render_template("register.html")

        # Vérifie en base qu'aucun compte n'existe déjà avec cet email
        try:
            existing_user = User.query.filter_by(email=email).first()

        except Exception as e:
            # En cas d'erreur de base, on évite de continuer l'inscription
            print(f"[REGISTER] Erreur vérification email existant : {e}")
            flash("Erreur temporaire lors de la vérification du compte.", "error")
            return render_template("register.html")

        # Si l'utilisateur existe déjà, on le renvoie vers la connexion
        if existing_user:
            flash("Un compte existe déjà.", "warning")
            return redirect(url_for("login"))

        # Génère un token sécurisé pour le lien de confirmation email
        token = secrets.token_urlsafe(32)

        # Crée l'objet utilisateur sans stocker le mot de passe en clair
        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            email_verified=False,
            verification_token=token
        )

        # Enregistre le compte en base avant l'envoi de l'email
        try:
            db.session.add(user)
            db.session.commit()

        except Exception as e:
            # En cas d'erreur, on annule l'insertion pour garder une base cohérente
            db.session.rollback()
            print(f"[REGISTER] Erreur création compte : {e}")
            flash("Erreur lors de la création du compte. Réessaie.", "error")
            return render_template("register.html")

        # Génère une URL complète vers la route de confirmation email
        confirm_url = url_for("confirm_email", token=token, _external=True)

        # Envoie l'email de confirmation via Brevo
        email_sent = send_confirmation_email(
            email=email,
            first_name=first_name,
            confirm_url=confirm_url
        )

        # Message affiché selon le résultat de l'envoi email
        if email_sent:
            flash("Inscription réussie ! Vérifie ta boîte mail.", "success")
        else:
            flash(
                "Compte créé, mais l'email de confirmation n'a pas pu être envoyé. Contacte un administrateur.",
                "warning"
            )

        # Après inscription, l'utilisateur est renvoyé vers la page de connexion
        return redirect(url_for("login"))

    # En GET, on affiche simplement le formulaire d'inscription
    return render_template("register.html")


# ============================================================
# CONFIRMATION D'EMAIL
# ============================================================
 
@app.route("/confirm/<token>")
def confirm_email(token):
    """
    Valide l'adresse email de l'utilisateur via le token reçu par mail.

    Fonctionnement :
    - cherche l'utilisateur correspondant au token
    - passe email_verified à True
    - supprime le token pour éviter sa réutilisation
    - redirige vers la connexion

    Returns:
        Redirection Flask
    """

    # Recherche l'utilisateur associé au token de confirmation
    user = User.query.filter_by(verification_token=token).first()

    # Si aucun utilisateur n'est trouvé, le lien est invalide ou déjà utilisé
    if user is None:
        flash("Lien de confirmation invalide ou déjà utilisé.", "error")
        return redirect(url_for("login"))

    # Si l'email est déjà confirmé, inutile de modifier de nouveau le compte
    if user.email_verified:
        flash("Ton adresse email est déjà confirmée. Tu peux te connecter.", "success")
        return redirect(url_for("login"))

    # Active le compte utilisateur
    user.email_verified = True

    # Supprime le token pour qu'il ne puisse pas être utilisé une deuxième fois
    user.verification_token = None

    # Sauvegarde les modifications en base
    db.session.commit()

    flash("Adresse email confirmée ! Tu peux maintenant te connecter.", "success")
    return redirect(url_for("login"))
 

# ============================================================
# CONNEXION
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Gère l'authentification utilisateur.

    Fonctionnement :
    - récupère l'email et le mot de passe
    - vérifie les identifiants
    - bloque la connexion si l'email n'est pas confirmé
    - initialise la session Flask
    - redirige selon le rôle utilisateur
    """

    # Le traitement de connexion se fait uniquement lors de l'envoi du formulaire
    if request.method == "POST":

        # Récupère les identifiants saisis dans le formulaire
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Vérifie que les deux champs sont remplis
        if not email or not password:
            flash("Merci de remplir tous les champs.", "error")
            return render_template("login.html")

        # Recherche l'utilisateur correspondant à l'email
        user = User.query.filter_by(email=email).first()

        # Vérifie l'existence du compte et la validité du mot de passe hashé
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Email ou mot de passe incorrect.", "error")
            return render_template("login.html")

        # Bloque la connexion tant que l'adresse email n'a pas été confirmée
        if not user.email_verified:
            flash("Tu dois confirmer ton adresse email avant de te connecter. Vérifie ta boîte mail.", "warning")
            return render_template("login.html")

        # Nettoie l'ancienne session avant de créer une nouvelle session utilisateur
        session.clear()

        # Rend la session permanente pour appliquer PERMANENT_SESSION_LIFETIME
        session.permanent = True

        # Stocke les informations essentielles de l'utilisateur dans la session Flask
        session["user_id"] = user.id
        session["role"] = user.role.value
        session["consent_given"] = user.consent_given

        # Ces informations sont utilisées côté templates pour personnaliser l'affichage
        session["first_name"] = user.first_name
        session["last_name"] = user.last_name
        session["email"] = user.email

        flash("Connexion réussie.", "success")

        # Redirige l'utilisateur vers le dashboard correspondant à son rôle
        if user.role == UserRole.PROFESSOR:
            return redirect(url_for("professor_dashboard"))

        return redirect(url_for("student_dashboard"))

    # En GET, on affiche simplement le formulaire de connexion
    return render_template("login.html")

# ============================================================
# CONSENTEMENT RGPD
# ============================================================

@app.route("/consent", methods=["POST"])
def consent():
    """
    Enregistre le consentement RGPD de l'utilisateur.

    Fonctionnement :
    - vérifie que l'utilisateur est connecté
    - met à jour la base de données
    - met à jour la session Flask

    Returns:
        tuple: ("", 204) si succès, 403 sinon
    """

    # Refuse l'action si aucun utilisateur n'est connecté
    if "user_id" not in session:
        return "", 403

    # Récupère l'utilisateur connecté
    user = User.query.get(session["user_id"])

    # Enregistre le consentement en base
    user.consent_given = True
    db.session.commit()

    # Met aussi à jour la session Flask pour éviter d'afficher encore la popup
    session["consent_given"] = True

    # Réponse vide avec code 204 : succès sans contenu à renvoyer
    return "", 204


# ============================================================
# DECONNEXION
# ============================================================

@app.route("/logout")
def logout():
    """
    Déconnecte l'utilisateur.

    Fonctionnement :
    - supprime toutes les données stockées dans la session Flask
    - redirige vers la page de connexion
    """

    # Supprime toutes les informations de session de l'utilisateur
    session.clear()

    flash("Vous avez été déconnecté.", "success")

    # Redirige vers la page de connexion après déconnexion
    return redirect(url_for("login"))


# ============================================================
# DASHBOARDS
# ============================================================

@app.route("/dashboard/student")
def student_dashboard():
    """
    Dashboard étudiant.

    Fonctionnement :
    - vérifie que l'utilisateur connecté est bien un étudiant
    - récupère les dernières sessions rejointes
    - envoie les participations au template étudiant
    """

    # Bloque l'accès si l'utilisateur connecté n'est pas un étudiant
    if session.get("role") != "student":
        flash("Accès refusé.", "error")
        return redirect(url_for("login"))

    # Récupère les 7 dernières participations de l'étudiant connecté
    participations = Participation.query.filter_by(
        student_id=session["user_id"]
    ).order_by(
        Participation.date_join.desc()
    ).limit(7).all()

    # Affiche le dashboard étudiant avec l'historique des participations
    return render_template(
        "student_dashboard.html",
        participations=participations
    )


@app.route("/dashboard/professor")
def professor_dashboard():
    """
    Dashboard professeur.

    Fonctionnement :
    - vérifie que l'utilisateur connecté est bien un professeur
    - récupère les sessions créées par ce professeur
    - envoie ces sessions au template professeur
    """

    # Bloque l'accès si l'utilisateur connecté n'est pas un professeur
    if session.get("role") != "professor":
        flash("Accès refusé.", "error")
        return redirect(url_for("login"))

    # Récupère toutes les sessions créées par le professeur connecté
    sessions = Session.query.filter_by(
        professor_id=session["user_id"]
    ).all()

    # Affiche le dashboard professeur avec la liste de ses sessions
    return render_template(
        "professor_dashboard.html",
        sessions=sessions
    )


# ============================================================
# CREATION DE SESSION
# ============================================================

@app.route("/create_session", methods=["POST"])
def create_session():
    """
    Création d'une session par un professeur.

    Fonctionnement :
    - vérifie que l'utilisateur est un professeur
    - récupère les paramètres du formulaire
    - récupère les modes d'affichage sélectionnés
    - applique les seuils d'alerte si le mode alertes est activé
    - génère un code de session
    - sauvegarde la session en base
    - redirige vers la page de résultats
    """

    # Seul un professeur peut créer une session
    if session.get("role") != "professor":
        return redirect(url_for("login"))

    # Récupère les fréquences choisies dans le formulaire
    freq_q = int(request.form["freq_questionnaire"])
    freq_w = int(request.form["freq_webcam"])

    # Récupère tous les modes cochés par le professeur
    selected_modes = request.form.getlist("modes_affichage")

    # Valeurs par défaut des seuils d'alerte
    seuil_individuel = 0.60
    seuil_classe = 0.50

    # Si le mode alertes est activé, on récupère les seuils personnalisés
    if "alertes" in selected_modes:
        try:
            # Les valeurs du formulaire sont en pourcentage, donc on divise par 100
            seuil_individuel = int(request.form.get("seuil_individuel", 60)) / 100
            seuil_classe = int(request.form.get("seuil_classe", 50)) / 100

            # Sécurise les seuils pour éviter des valeurs trop basses ou trop hautes
            seuil_individuel = max(0.10, min(0.90, seuil_individuel))
            seuil_classe = max(0.10, min(0.90, seuil_classe))

        except (ValueError, TypeError):
            # En cas de valeur invalide, on garde les seuils par défaut
            pass

    # Les fréquences doivent être strictement positives
    if freq_q <= 0 or freq_w <= 0:
        flash("Valeurs invalides.", "error")
        return redirect(url_for("professor_dashboard"))

    # Le professeur doit sélectionner au moins un mode d'affichage
    if not selected_modes:
        flash("Veuillez sélectionner au moins un mode d'affichage.", "error")
        return redirect(url_for("professor_dashboard"))

    # Stocke les modes sélectionnés sous forme de chaîne séparée par des virgules
    mode = ",".join(selected_modes)

    # Génère un code court que les étudiants utiliseront pour rejoindre la session
    code = generate_session_code()

    # Crée l'objet Session avec tous les paramètres choisis par le professeur
    new_session = Session(
        code_session=code,
        professor_id=session["user_id"],
        date_debut=datetime.now(timezone.utc),
        frequence_questionnaire=freq_q,
        frequence_webcam=freq_w,
        mode_affichage=mode,
        seuil_individuel=seuil_individuel,
        seuil_classe=seuil_classe
    )

    # Sauvegarde la nouvelle session en base
    db.session.add(new_session)
    db.session.commit()

    # Indique à Flask que la session utilisateur a été modifiée
    session.modified = True

    flash(f"Session créée ! Code : {code}", "success")

    # Redirige directement le professeur vers la page de résultats de la session
    return redirect(url_for("session_results", session_id=new_session.id))

# ============================================================
# REJOINDRE SESSION
# ============================================================

@app.route("/join_session", methods=["POST"])
def join_session():
    """
    Permet à un étudiant de rejoindre une session.

    Fonctionnement :
    - vérifie que l'utilisateur connecté est un étudiant
    - récupère le code session envoyé par le formulaire
    - vérifie que la session existe et est active
    - vérifie que l'étudiant n'est pas déjà inscrit
    - crée une participation
    - initialise la phase QCM à "avant"
    - stocke l'id de session dans la session Flask
    - redirige vers le questionnaire
    """

    print("=== /join_session called ===")
    print(f"user_id = {session.get('user_id')}")
    print(f"role = {session.get('role')}")

    # Seul un étudiant peut rejoindre une session
    if session.get("role") != "student":
        print("Erreur: utilisateur non étudiant")
        return redirect(url_for("login"))

    # Récupère le code session saisi et le met en majuscules
    code = request.form.get("code_session", "").strip().upper()

    # Vérifie si l'étudiant a coché le mode anonyme
    anonymous = "anonymous" in request.form

    # Vérifie si l'étudiant a autorisé l'utilisation de la webcam
    webcam_enabled = "webcam_enabled" in request.form

    print(f"code_session = {code}")
    print(f"anonymous = {anonymous}")
    print(f"webcam_enabled = {webcam_enabled}")

    # Empêche de continuer si aucun code n'a été saisi
    if not code:
        print("Erreur: code session vide")
        flash("Veuillez entrer un code session.", "error")
        return redirect(url_for("student_dashboard"))

    # Recherche la session correspondant au code fourni
    session_obj = Session.query.filter_by(code_session=code).first()

    # Si aucune session ne correspond, le code est invalide
    if session_obj is None:
        print("Erreur: session introuvable")
        flash("Code session invalide.", "error")
        return redirect(url_for("student_dashboard"))

    print(f"session_obj.id = {session_obj.id}")
    print(f"session_obj.is_active = {session_obj.is_active}")

    # Empêche de rejoindre une session déjà terminée
    if not session_obj.is_active:
        print("Erreur: session inactive")
        flash("Cette session est terminée.", "error")
        return redirect(url_for("student_dashboard"))

    # Vérifie si l'étudiant est déjà inscrit à cette session
    existing = Participation.query.filter_by(
        session_id=session_obj.id,
        student_id=session["user_id"]
    ).first()

    # Empêche les doublons de participation pour une même session
    if existing:
        print("Erreur: participation déjà existante")
        flash("Vous êtes déjà inscrit à cette session.", "warning")
        return redirect(url_for("student_dashboard"))

    try:
        # Crée la participation avec les choix de l'étudiant
        participation = Participation(
            session_id=session_obj.id,
            student_id=session["user_id"],
            anonymous=anonymous,
            webcam_enabled=webcam_enabled
        )

        # Sauvegarde la participation en base
        db.session.add(participation)
        db.session.commit()

        print("Participation enregistrée en base")
        print(f"participation.id = {participation.id}")

    except Exception as e:
        # En cas d'erreur, on annule l'insertion pour éviter une base incohérente
        db.session.rollback()
        print(f"Erreur DB join_session: {e}")
        flash("Erreur lors de l'inscription à la session.", "error")
        return redirect(url_for("student_dashboard"))

    # Initialise la première phase du questionnaire
    session["phase"] = "avant"

    # Stocke l'id de la session active dans la session Flask
    session["current_session_id"] = session_obj.id

    # Indique à Flask que la session utilisateur a changé
    session.modified = True

    print(f"session['phase'] = {session.get('phase')}")
    print(f"session['current_session_id'] = {session.get('current_session_id')}")
    print("Redirection vers /qcm")

    # Redirige l'étudiant vers le questionnaire initial
    return redirect(url_for("qcm"))


# ============================================================
# Questionnaires (Mesure subjective)
# ============================================================   

@app.route("/qcm")
def qcm():
    """
    Affiche le questionnaire étudiant en fonction de la phase.

    Fonctionnement :
    - vérifie que l'utilisateur est authentifié et est un étudiant
    - vérifie qu'une session est en cours côté serveur
    - vérifie que l'utilisateur participe à la session
    - récupère la session en base
    - si la session est terminée, force la phase "apres"
    - si le QCM "avant" a déjà été répondu, passe automatiquement en "pendant"
    - envoie les données nécessaires au template
    """

    # Vérifie qu'un utilisateur est bien connecté
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Seuls les étudiants peuvent accéder au questionnaire
    if session.get("role") != "student":
        return redirect(url_for("login"))

    # Récupère l'id de la session actuellement suivie par l'étudiant
    session_id = session.get("current_session_id")

    # Si aucune session n'est active côté Flask, retour au dashboard étudiant
    if not session_id:
        return redirect(url_for("student_dashboard"))

    # Vérifie que l'étudiant participe réellement à cette session
    participation = Participation.query.filter_by(
        session_id=session_id,
        student_id=session["user_id"]
    ).first()

    # Si aucune participation n'est trouvée, l'accès au QCM est refusé
    if not participation:
        return redirect(url_for("student_dashboard"))

    # Récupère la session en base de données
    session_obj = Session.query.get(session_id)

    # Si la session n'existe plus, retour au dashboard
    if not session_obj:
        return redirect(url_for("student_dashboard"))

    # Si le professeur a terminé la session, on force le questionnaire final
    if not session_obj.is_active:
        session["phase"] = "apres"

    # Récupère la phase courante stockée côté serveur
    # Par défaut, un étudiant commence par la phase "avant"
    phase = session.get("phase", "avant")

    # Si l'étudiant est encore en phase "avant",
    # on vérifie s'il a déjà répondu au questionnaire initial
    if phase == "avant":
        already_answered = QCMResponse.query.filter_by(
            session_id=session_id,
            user_id=session["user_id"],
            phase="avant"
        ).first()

        # Si le QCM initial a déjà été répondu, on passe automatiquement en phase "pendant"
        if already_answered:
            phase = "pendant"
            session["phase"] = "pendant"

    # Affiche le template QCM avec les paramètres nécessaires au JavaScript
    return render_template(
        "qcm.html",
        session_id=session_id,
        freq=session_obj.frequence_questionnaire,
        freq_webcam=session_obj.frequence_webcam,
        phase=phase,
        webcam_active=participation.webcam_enabled
    )


@app.route("/qcm/submit", methods=["POST"])
def submit_qcm():
    """
    Enregistre une réponse QCM de manière sécurisée.

    Fonctionnement :
    - vérifie que l'utilisateur est authentifié
    - récupère la session active côté serveur
    - vérifie que la session existe
    - vérifie que l'utilisateur participe à la session
    - détermine la phase côté serveur
    - valide les données reçues
    - calcule automatiquement l'occurrence
    - enregistre la réponse en base
    - met à jour la phase si nécessaire
    """

    # Vérifie qu'un utilisateur est connecté avant d'accepter une réponse
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    # Récupère la session active depuis la session Flask
    session_id = session.get("current_session_id")

    # Si aucune session active n'est trouvée, la réponse ne peut pas être enregistrée
    if not session_id:
        return jsonify({"error": "No active session"}), 400

    # Récupère les données JSON envoyées par le front
    payload = request.get_json()

    # Refuse la requête si aucun JSON n'a été envoyé
    if not payload:
        return jsonify({"error": "Missing JSON payload"}), 400

    # Récupère la session correspondante en base
    session_obj = Session.query.get(session_id)

    # Si la session n'existe pas, on arrête le traitement
    if not session_obj:
        return jsonify({"error": "Session not found"}), 404

    # Vérifie que l'étudiant connecté participe bien à cette session
    participant = Participation.query.filter_by(
        session_id=session_id,
        student_id=session["user_id"]
    ).first()

    # Si l'étudiant ne participe pas à la session, il ne peut pas envoyer de réponse
    if not participant:
        return jsonify({"error": "Unauthorized"}), 403

    # La phase est déterminée côté serveur pour éviter qu'un utilisateur la modifie depuis le front
    if not session_obj.is_active:
        # Si la session est terminée, toute réponse envoyée devient une réponse de phase "apres"
        phase = "apres"
        session["phase"] = "apres"
    else:
        # Sinon, on utilise la phase courante stockée dans la session Flask
        phase = session.get("phase", "avant")

    # Récupère l'émotion et l'intensité envoyées par le questionnaire
    emotion = payload.get("emotion")
    slider_value = payload.get("slider_value")

    # Liste blanche des émotions acceptées par l'application
    allowed_emotions = [
        "motive", "neutre", "ennuye", "stresse", "demotive"
    ]

    # Refuse toute émotion inconnue pour éviter d'enregistrer des valeurs incohérentes
    if emotion not in allowed_emotions:
        return jsonify({"error": "Invalid emotion"}), 400

    # Convertit et valide la valeur du slider
    try:
        slider_value = int(slider_value)

        # Le slider doit rester dans l'échelle prévue par le questionnaire
        if not (1 <= slider_value <= 5):
            raise ValueError

    except (TypeError, ValueError):
        return jsonify({"error": "Invalid slider value"}), 400

    # Récupère la dernière réponse de cet étudiant dans cette session
    last_response = QCMResponse.query.filter_by(
        session_id=session_id,
        user_id=session["user_id"]
    ).order_by(
        QCMResponse.occurrence.desc()
    ).first()

    # Calcule l'occurrence suivante.
    # Si c'est la première réponse, l'occurrence commence à 1.
    occurrence = (last_response.occurrence + 1) if last_response else 1

    # Crée l'objet réponse QCM qui sera enregistré en base
    response = QCMResponse(
        session_id=session_id,
        user_id=session["user_id"],
        phase=phase,
        emotion=emotion,
        slider_value=slider_value,
        occurrence=occurrence
    )

    try:
        # Ajoute la réponse à la transaction SQLAlchemy
        db.session.add(response)

        # Sauvegarde définitivement la réponse en base
        db.session.commit()

    except IntegrityError:
        # En cas de doublon ou contrainte d'intégrité, on annule la transaction
        db.session.rollback()
        return jsonify({"error": "Already submitted"}), 400

    except Exception:
        # En cas d'erreur serveur, on annule aussi la transaction
        db.session.rollback()
        return jsonify({"error": "Server error"}), 500

    # Après le questionnaire initial, l'étudiant passe en phase "pendant"
    if session.get("phase") == "avant":
        session["phase"] = "pendant"

    # Si la réponse correspond au questionnaire final, on nettoie la session active
    if phase == "apres":
        session.pop("current_session_id", None)
        session.pop("phase", None)

    # Réponse JSON de succès pour le JavaScript côté front
    return jsonify({"ok": True})

# ============================================================
# Fermer une session en cours (coté professeur)
# ============================================================

@app.route("/end_session/<int:session_id>", methods=["POST"])
def end_session(session_id):
    """
    Clôture une session côté professeur.

    Fonctionnement :
    - vérifie que l'utilisateur connecté est un professeur
    - récupère la session concernée
    - passe la session en inactive
    - enregistre la date de fin en UTC
    - sauvegarde les modifications en base
    """

    # Seul un professeur peut fermer une session
    if session.get("role") != "professor":
        flash("Accès non autorisé.", "danger")
        return redirect(url_for("login"))

    try:
        # Récupère la session à fermer grâce à l'id présent dans l'URL
        current_sess = Session.query.get(session_id)

        # Vérifie que la session existe bien
        if current_sess:

            # Passe la session en inactive pour empêcher les nouveaux envois de données
            current_sess.is_active = False

            # Stocke la date de fin en UTC pour rester cohérent avec les autres dates en base
            current_sess.date_fin = datetime.now(timezone.utc)

            # Sauvegarde les modifications en base
            db.session.commit()

            # Si cette session était aussi stockée dans la session Flask, on la retire
            if session.get("current_session_id") == session_id:
                session.pop("current_session_id", None)

            flash(f"La session '{current_sess.code_session}' a été fermée avec succès.", "success")

        else:
            flash("Session introuvable.", "warning")

    except Exception as e:
        # En cas d'erreur, on annule les modifications non sauvegardées
        db.session.rollback()

        # Log utile pour comprendre l'erreur dans les logs serveur
        print(f"Erreur lors de la fermeture : {str(e)}")

        flash("Erreur critique lors de la fermeture de la session.", "danger")

    # Retour au dashboard professeur pour afficher l'état mis à jour des sessions
    return redirect(url_for("professor_dashboard"))

# ============================================================
# TÉLÉCHARGEMENT DU RAPPORT DE SESSION (PDF texte)
# ============================================================

@app.route("/session/<int:session_id>/download")
def download_session_report(session_id):
    """
    Génère et retourne un fichier texte récapitulatif de la session.

    Accessible uniquement par le professeur créateur de la session.

    Le rapport contient :
    - les informations générales de la session
    - les compteurs QCM / webcam
    - les moyennes émotionnelles
    - le détail par étudiant
    """

    # Import local utilisé uniquement dans cette route pour construire une réponse fichier
    from flask import make_response

    # Vérifie que l'utilisateur connecté est bien un professeur
    if session.get("role") != "professor":
        flash("Accès réservé au professeur.", "error")
        return redirect(url_for("login"))

    # Récupère la session demandée en base
    session_obj = Session.query.get(session_id)

    # Vérifie que la session existe et qu'elle appartient au professeur connecté
    if not session_obj or session_obj.professor_id != session.get("user_id"):
        flash("Session introuvable ou accès non autorisé.", "error")
        return redirect(url_for("professor_dashboard"))

    # Calcule les données de moyenne utilisées dans le rapport
    average_data = build_session_average_data(session_id)

    # Compte le nombre total de participants à la session
    participants_count = Participation.query.filter_by(
        session_id=session_id
    ).count()

    # Compte le nombre total de réponses QCM enregistrées
    qcm_count = QCMResponse.query.filter_by(
        session_id=session_id
    ).count()

    # Compte le nombre total d'analyses webcam enregistrées
    webcam_count = WebcamAnalysis.query.filter_by(
        session_id=session_id
    ).count()

    # Fuseau horaire utilisé pour afficher les dates en heure française
    paris = ZoneInfo("Europe/Paris")

    # Formate la date de début si elle existe
    date_debut = (
        session_obj.date_debut.astimezone(paris).strftime("%d/%m/%Y à %Hh%M")
        if session_obj.date_debut
        else "—"
    )

    # Formate la date de fin si elle existe, sinon indique que la session est en cours
    date_fin = (
        session_obj.date_fin.astimezone(paris).strftime("%d/%m/%Y à %Hh%M")
        if session_obj.date_fin
        else "En cours"
    )

    # Liste de lignes qui sera ensuite transformée en texte complet
    lignes = []

    # En-tête du rapport
    lignes.append("=" * 60)
    lignes.append("        RAPPORT DE SESSION — EMOTRACK")
    lignes.append("=" * 60)

    # Informations générales de la session
    lignes.append(f"  Code session     : {session_obj.code_session}")
    lignes.append(f"  Début            : {date_debut}")
    lignes.append(f"  Fin              : {date_fin}")
    lignes.append(f"  Participants     : {participants_count}")
    lignes.append(f"  Réponses QCM     : {qcm_count}")
    lignes.append(f"  Analyses webcam  : {webcam_count}")
    lignes.append("")

    # Bloc des moyennes générales
    lignes.append("=" * 60)
    lignes.append("  MOYENNES GÉNÉRALES")
    lignes.append("=" * 60)
    lignes.append(f"  Subjective (QCM)      : {average_data['moyenne_subjective'] or 'Aucune donnée'}")
    lignes.append(f"  Objective (DeepFace)  : {average_data['moyenne_objective'] or 'Aucune donnée'}")
    lignes.append(f"  Générale              : {average_data['moyenne_generale'] or 'Aucune donnée'}")
    lignes.append("")

    # Bloc du détail par étudiant
    lignes.append("=" * 60)
    lignes.append("  DÉTAIL PAR ÉTUDIANT")
    lignes.append("=" * 60)

    # En-tête du tableau texte
    lignes.append(f"  {'Étudiant':<25} {'Émotion dominante':<20} {'QCM':>5} {'Webcam':>8}")
    lignes.append("  " + "-" * 58)

    # Ajoute une ligne par étudiant dans le rapport
    for ind in average_data["individuals"]:

        # Respecte l'anonymat si l'étudiant a choisi ce mode
        nom = "Anonyme" if ind["anonymous"] else ind["name"]

        # Utilise un tiret si aucune émotion dominante n'est disponible
        emotion = ind["emotion_dominante"] or "—"

        # Ligne formatée pour garder un tableau lisible dans un fichier texte
        lignes.append(f"  {nom:<25} {emotion:<20} {ind['nb_qcm']:>5} {ind['nb_webcam']:>8}")

    # Pied de rapport
    lignes.append("")
    lignes.append("=" * 60)
    lignes.append("  Généré par EmoTrack")
    lignes.append("=" * 60)

    # Transforme la liste de lignes en contenu texte final
    contenu = "\n".join(lignes)

    # Crée une réponse Flask contenant le fichier texte
    response = make_response(contenu)

    # Indique au navigateur qu'il s'agit d'un fichier texte en UTF-8
    response.headers["Content-Type"] = "text/plain; charset=utf-8"

    # Force le téléchargement avec un nom de fichier basé sur le code session
    response.headers["Content-Disposition"] = (
        f"attachment; filename=rapport_{session_obj.code_session}.txt"
    )

    return response

# ============================================================
# Quitter une session (coté étudiant)
# ============================================================


@app.route("/leave_session", methods=["POST"])
def leave_session():
    """
    Permet à un étudiant de quitter une session proprement.

    Fonctionnement :
    - vérifie que l'utilisateur est connecté
    - vérifie qu'une session est en cours
    - force la phase "apres"
    - redirige vers le QCM final
    """

    # Si aucun utilisateur n'est connecté, retour à la connexion
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Si aucune session active n'est stockée côté Flask, retour au dashboard étudiant
    if not session.get("current_session_id"):
        return redirect(url_for("student_dashboard"))

    # Force la prochaine page QCM à afficher le questionnaire final
    session["phase"] = "apres"

    # Indique à Flask que la session utilisateur a été modifiée
    session.modified = True

    # Redirige vers la route QCM, qui affichera le questionnaire de phase "apres"
    return redirect(url_for("qcm"))


# ============================================================
# Vérification de l'état de la session
# ============================================================

@app.route("/check_session_status")
def check_session_status():
    """
    Vérifie l'état de la session actuellement suivie par l'étudiant.

    Cette route est appelée côté front pour savoir si :
    - aucune session n'est active ;
    - la session n'existe plus ;
    - la session est terminée ;
    - la session est toujours active.

    Returns:
        JSON: statut de la session
    """

    # Récupère l'id de la session active depuis la session Flask
    session_id = session.get("current_session_id")

    # Aucun id en session signifie que l'étudiant n'est dans aucune session
    if not session_id:
        return jsonify({"status": "no_session"})

    # Récupère la session correspondante en base
    session_obj = Session.query.get(session_id)

    # Si la session n'existe plus en base, on le signale au front
    if not session_obj:
        return jsonify({"status": "not_found"})

    # Si le professeur a fermé la session, le front doit déclencher la phase finale
    if not session_obj.is_active:
        return jsonify({"status": "ended"})

    # Sinon, la session est toujours active
    return jsonify({"status": "active"})


# ============================================================
# ANALYSE WEBCAM DEEPFACE
# ============================================================

@app.route("/analyze_webcam", methods=["POST"])
def analyze_webcam():
    """
    Reçoit une image webcam depuis le front,
    l'envoie au serveur DeepFace Hugging Face,
    puis enregistre le résultat en base.

    Sécurités ajoutées :
    - vérification utilisateur connecté
    - vérification session active côté Flask
    - vérification payload JSON
    - vérification image présente et non vide
    - vérification configuration DeepFace
    - gestion propre des erreurs réseau / réponse HF / base de données
    """

    print("=== /analyze_webcam called ===")

    # Vérifie qu'un utilisateur est connecté avant d'accepter une analyse webcam
    if "user_id" not in session:
        print("Erreur: utilisateur non authentifié")
        return jsonify({"error": "Non authentifié"}), 401

    # Récupère l'utilisateur connecté et la session actuellement suivie
    user_id = session.get("user_id")
    current_session_id = session.get("current_session_id")

    print(f"user_id = {user_id}")
    print(f"current_session_id = {current_session_id}")

    # Refuse l'analyse si l'étudiant n'est dans aucune session active côté Flask
    if not current_session_id:
        print("Erreur: aucune session active dans la session Flask")
        return jsonify({"error": "Aucune session active"}), 400

    # Récupère le JSON envoyé par le JavaScript côté front.
    # silent=True évite une erreur Flask si le JSON est mal formé.
    data = request.get_json(silent=True)

    # Vérifie qu'un payload JSON a bien été reçu
    if not data:
        print("Erreur: payload JSON absent")
        return jsonify({"error": "Payload JSON invalide"}), 400

    # Récupère l'image encodée en base64 envoyée par le navigateur
    image_b64 = data.get("image")

    # Vérifie que l'image est bien présente dans la requête
    if not image_b64:
        print("Erreur: image absente du payload")
        return jsonify({"error": "Image manquante"}), 400

    # Sécurité minimale : une image base64 valide doit avoir une certaine longueur.
    # Cela évite d'envoyer une image vide ou presque vide au serveur DeepFace.
    if len(image_b64.strip()) < 50:
        print("Erreur: image vide ou trop courte")
        return jsonify({"error": "Image vide"}), 400

    # Récupère l'URL du serveur DeepFace depuis les variables d'environnement
    deepface_url = os.environ.get("DEEPFACE_URL", "").strip()

    # Récupère la clé secrète partagée entre Flask et le serveur DeepFace
    deepface_secret = os.environ.get("DEEPFACE_SECRET_KEY", "").strip()

    print(f"deepface_url = {deepface_url}")
    print(f"deepface_secret_present = {bool(deepface_secret)}")

    # Sans URL DeepFace, l'application ne sait pas où envoyer l'image
    if not deepface_url:
        print("Erreur: DEEPFACE_URL manquant")
        return jsonify({"error": "Configuration DeepFace manquante"}), 500

    # Sans clé secrète, l'appel au serveur DeepFace est refusé par sécurité
    if not deepface_secret:
        print("Erreur: DEEPFACE_SECRET_KEY manquant")
        return jsonify({"error": "Clé secrète DeepFace manquante"}), 500

    try:
        # Prépare les données envoyées au serveur DeepFace.
        # L'image reste encodée en base64 pour être transmise facilement en JSON.
        payload = {
            "image": image_b64,
            "secret_key": deepface_secret
        }

        print("Envoi de la requête au serveur DeepFace...")

        # Envoie l'image au serveur DeepFace hébergé sur Hugging Face
        response = requests.post(
            f"{deepface_url}/analyze",
            json=payload,
            timeout=30
        )

        print(f"HF status_code = {response.status_code}")
        print(f"HF response text = {response.text}")

    except requests.RequestException as e:
        # Gère les erreurs réseau : timeout, serveur inaccessible, URL incorrecte, etc.
        print(f"Erreur réseau vers DeepFace: {e}")
        return jsonify({"error": "Impossible de contacter le serveur DeepFace"}), 502

    # Vérifie que le serveur DeepFace a bien répondu avec un statut de succès
    if response.status_code != 200:
        print("Erreur: réponse non 200 du serveur DeepFace")
        return jsonify({
            "error": "Erreur serveur DeepFace",
            "details": response.text
        }), 502

    try:
        # Convertit la réponse DeepFace en dictionnaire Python
        result = response.json()

    except Exception as e:
        # Si la réponse n'est pas un JSON valide, on ne peut pas l'exploiter
        print(f"Erreur parsing JSON HF: {e}")
        return jsonify({"error": "Réponse JSON DeepFace invalide"}), 502

    # Récupère les informations principales renvoyées par DeepFace
    emotion = result.get("emotion")
    confidence = result.get("confidence")
    all_emotions = result.get("all_emotions", {})

    print(f"emotion = {emotion}")
    print(f"confidence = {confidence}")
    print(f"all_emotions = {all_emotions}")

    # Vérifie que DeepFace a bien renvoyé une émotion dominante
    if not emotion:
        print("Erreur: emotion absente dans la réponse HF")
        return jsonify({"error": "Emotion absente dans la réponse DeepFace"}), 502

    try:
        # Prépare l'objet WebcamAnalysis à enregistrer en base.
        # all_emotions est converti en JSON texte pour être stocké facilement.
        analysis = WebcamAnalysis(
            session_id=current_session_id,
            user_id=user_id,
            dominant_emotion=emotion,
            confidence=float(confidence) if confidence is not None else None,
            all_emotions=json.dumps(all_emotions)
        )

        print("Tentative d'enregistrement en base...")

        # Ajoute l'analyse webcam à la transaction SQLAlchemy
        db.session.add(analysis)

        # Sauvegarde définitivement l'analyse en base
        db.session.commit()

        print("Enregistrement DB OK")
        print(f"analysis.id = {analysis.id}")

        # Renvoie le résultat au front pour confirmer que l'analyse a réussi
        return jsonify({
            "ok": True,
            "emotion": emotion,
            "confidence": confidence,
            "all_emotions": all_emotions
        }), 200

    except Exception as e:
        # En cas d'erreur base de données, on annule la transaction
        db.session.rollback()

        print(f"Erreur DB: {e}")

        return jsonify({"error": "Erreur lors de l'enregistrement en base"}), 500


# ============================================================
# RESULTATS DE LA SESSION
# ============================================================

@app.route("/session/<int:session_id>/results")
def session_results(session_id):
    """
    Affiche la page résultats d'une session.

    Fonctionnement :
    - accès réservé au professeur
    - vérifie que la session existe
    - vérifie que le professeur connecté est bien le créateur
    - prépare les données des graphiques
    - affiche result.html

    Args:
        session_id (int): identifiant de la session

    Returns:
        HTML: page résultats ou redirection sécurisée
    """

    # Vérifie que l'utilisateur connecté est bien un professeur
    if session.get("role") != "professor":
        flash("Accès réservé au professeur.", "error")
        return redirect(url_for("login"))

    # Récupère la session demandée en base
    session_obj = Session.query.get(session_id)

    # Si aucune session n'est trouvée, retour au dashboard professeur
    if not session_obj:
        flash("Session introuvable.", "error")
        return redirect(url_for("professor_dashboard"))

    # Vérifie que le professeur connecté est bien le créateur de cette session
    if session_obj.professor_id != session.get("user_id"):
        flash("Accès non autorisé à cette session.", "error")
        return redirect(url_for("professor_dashboard"))

    # Compte tous les étudiants ayant rejoint la session
    participants_count = Participation.query.filter_by(
        session_id=session_id
    ).count()

    # Compte uniquement les participants encore actifs.
    # Un étudiant est considéré comme inactif s'il a déjà envoyé un QCM de phase "apres".
    active_participants_count = Participation.query.filter(
        Participation.session_id == session_id,
        ~Participation.student_id.in_(
            db.session.query(QCMResponse.user_id).filter(
                QCMResponse.session_id == session_id,
                QCMResponse.phase == "apres"
            )
        )
    ).count()

    # Récupère les modes d'affichage stockés sous forme de chaîne en base
    raw_modes = (session_obj.mode_affichage or "").strip().lower()

    # Transforme la chaîne "courbes,moyennes,alertes" en liste exploitable
    selected_modes = [
        m.strip()
        for m in raw_modes.split(",")
        if m.strip()
    ]

    # Prépare les données nécessaires aux graphiques de la page résultats
    curve_data = build_session_curve_data(session_id)

    # Affiche la page résultats avec toutes les données nécessaires au premier chargement
    return render_template(
        "result.html",
        session_obj=session_obj,
        selected_modes=selected_modes,
        participants_count=participants_count,
        active_participants_count=active_participants_count,
        engagement_labels=curve_data["engagement_labels"],
        engagement_values=curve_data["engagement_values"],
        qcm_emotion_labels=curve_data["qcm_emotion_labels"],
        qcm_emotion_values=curve_data["qcm_emotion_values"],
        webcam_emotion_labels=curve_data["webcam_emotion_labels"],
        webcam_emotion_values=curve_data["webcam_emotion_values"],
        qcm_count=curve_data["qcm_count"],
        webcam_count=curve_data["webcam_count"]
    )


@app.route("/session/<int:session_id>/results/data")
def session_results_data(session_id):
    """
    Retourne les données JSON des résultats.

    Cette route sert au rafraîchissement automatique de la page résultats
    sans recharger tout le HTML.

    Args:
        session_id (int): identifiant de la session

    Returns:
        JSON: données des graphiques, cartes statistiques, moyennes et alertes
    """

    # Accès réservé aux professeurs
    if session.get("role") != "professor":
        return jsonify({"error": "Accès refusé"}), 403

    # Récupère la session demandée en base
    session_obj = Session.query.get(session_id)

    # Si la session n'existe pas, on renvoie une erreur JSON
    if not session_obj:
        return jsonify({"error": "Session introuvable"}), 404

    # Vérifie que le professeur connecté est bien propriétaire de la session
    if session_obj.professor_id != session.get("user_id"):
        return jsonify({"error": "Accès non autorisé"}), 403

    # Compte tous les étudiants ayant rejoint la session
    participants_count = Participation.query.filter_by(
        session_id=session_id
    ).count()

    # Compte les participants actifs.
    # Les étudiants ayant déjà répondu au QCM final "apres" sont exclus.
    active_participants_count = Participation.query.filter(
        Participation.session_id == session_id,
        ~Participation.student_id.in_(
            db.session.query(QCMResponse.user_id).filter(
                QCMResponse.session_id == session_id,
                QCMResponse.phase == "apres"
            )
        )
    ).count()

    # Récupère les modes d'affichage choisis à la création de la session
    raw_modes = (session_obj.mode_affichage or "").strip().lower()

    # Convertit les modes en liste pour faciliter les tests avec "in"
    selected_modes = [
        m.strip()
        for m in raw_modes.split(",")
        if m.strip()
    ]

    # Prépare les données des courbes et donuts
    curve_data = build_session_curve_data(session_id)

    # Les alertes ne sont calculées que si le mode "alertes" est activé
    alerts_data = None
    if "alertes" in selected_modes:
        alerts_data = compute_alerts(session_id)

    # Les moyennes ne sont calculées que si le mode "moyennes" est activé
    average_data = None
    if "moyennes" in selected_modes:
        average_data = build_session_average_data(session_id)

    # Renvoie toutes les données au JavaScript de la page résultats
    return jsonify({
        "ok": True,

        # Compteurs généraux
        "participants_count": participants_count,
        "active_participants_count": active_participants_count,
        "qcm_count": curve_data["qcm_count"],
        "webcam_count": curve_data["webcam_count"],

        # Informations sur la session
        "selected_modes": selected_modes,
        "session_is_active": session_obj.is_active,

        # Données de la courbe d'engagement
        "engagement_labels": curve_data["engagement_labels"],
        "engagement_values": curve_data["engagement_values"],

        # Données du donut QCM
        "qcm_emotion_labels": curve_data["qcm_emotion_labels"],
        "qcm_emotion_values": curve_data["qcm_emotion_values"],

        # Données du donut webcam
        "webcam_emotion_labels": curve_data["webcam_emotion_labels"],
        "webcam_emotion_values": curve_data["webcam_emotion_values"],

        # Données d'alertes si le mode est actif
        "alerts": alerts_data,

        # Données de moyennes si le mode est actif
        "moyenne_subjective": average_data["moyenne_subjective"] if average_data else None,
        "moyenne_objective": average_data["moyenne_objective"] if average_data else None,
        "moyenne_generale": average_data["moyenne_generale"] if average_data else None,
        "individuals": average_data["individuals"] if average_data else [],
    })

# ============================================================
# ROUTE : HISTORIQUE DES ALERTES
# ============================================================


@app.route("/session/<int:session_id>/alerts")
def session_alerts(session_id):
    """
    Affiche la page historique des alertes d'une session.

    Fonctionnement :
    - vérifie que l'utilisateur connecté est un professeur
    - récupère la session demandée
    - vérifie que le professeur connecté est bien le créateur de la session
    - récupère toutes les alertes de la session
    - enrichit les alertes avec les informations étudiant si nécessaire
    - affiche le template alerts.html

    Args:
        session_id (int): identifiant de la session

    Returns:
        HTML: page historique des alertes ou redirection sécurisée
    """

    # L'historique des alertes est réservé aux professeurs
    if session.get("role") != "professor":
        flash("Accès réservé au professeur.", "error")
        return redirect(url_for("login"))

    # Récupère la session concernée
    session_obj = Session.query.get(session_id)

    # Si la session n'existe pas, on retourne au dashboard professeur
    if not session_obj:
        flash("Session introuvable.", "error")
        return redirect(url_for("professor_dashboard"))

    # Vérifie que le professeur connecté est bien le créateur de la session
    if session_obj.professor_id != session.get("user_id"):
        flash("Accès non autorisé.", "error")
        return redirect(url_for("professor_dashboard"))

    # Récupère toutes les alertes de la session, de la plus récente à la plus ancienne
    alerts = Alert.query.filter_by(
        session_id=session_id
    ).order_by(
        Alert.triggered_at.desc()
    ).all()

    # Liste finale envoyée au template avec les informations utiles pour l'affichage
    alerts_enriched = []

    for alert in alerts:

        # Récupère l'utilisateur concerné si l'alerte est individuelle
        user = User.query.get(alert.user_id) if alert.user_id else None

        # Par défaut, une alerte est considérée comme non anonyme
        anonymous = False

        if user:
            # Récupère la participation pour savoir si l'étudiant était anonyme dans cette session
            participation = Participation.query.filter_by(
                session_id=session_id,
                student_id=alert.user_id
            ).first()

            # Si la participation existe, on récupère le choix d'anonymat de l'étudiant
            anonymous = participation.anonymous if participation else False

        # Construit une version enrichie de l'alerte pour simplifier le template
        alerts_enriched.append({
            "id": alert.id,
            "level": alert.level,
            "source": alert.source,
            "emotion": alert.emotion,
            "ratio": alert.ratio,
            "triggered_at": alert.triggered_at,

            # Information utilisée pour masquer ou afficher l'identité de l'étudiant
            "anonymous": anonymous,

            # Nom et prénom affichés uniquement si l'alerte concerne un étudiant non anonyme
            "first_name": user.first_name if user and not anonymous else None,
            "last_name": user.last_name if user and not anonymous else None,
        })

    # Affiche la page d'historique des alertes
    return render_template(
        "alerts.html",
        session_obj=session_obj,
        alerts=alerts_enriched
    )


# ============================================================
# CHATBOT EMO-TRACK
# ============================================================

@app.route("/chatbot", methods=["POST"])
def chat():
    """
    Route pour le chatbot assistant.

    Fonctionnement :
    - reçoit un message utilisateur en JSON
    - récupère éventuellement l'historique de conversation
    - appelle la fonction get_chatbot_response
    - retourne la réponse du chatbot au format JSON
    """

    # Récupère le JSON envoyé par le front
    data = request.get_json()

    # Récupère le message utilisateur
    user_message = data.get("message")

    # Récupère l'historique de conversation si le front l'envoie
    history = data.get("history", [])

    # Refuse la requête si aucun message n'a été saisi
    if not user_message:
        return jsonify({"error": "Message vide."}), 400

    # Appelle la fonction qui communique avec le chatbot Groq
    response = get_chatbot_response(user_message, history)

    # Retourne la réponse au JavaScript côté front
    return jsonify({"reply": response})


# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":

    # Récupère le port fourni par Render.
    # En local, si PORT n'existe pas, Flask utilisera le port 5000.
    port = int(os.environ.get("PORT", 5000))

    # host="0.0.0.0" permet à l'application d'être accessible depuis l'extérieur,
    # ce qui est nécessaire sur Render.
    app.run(host="0.0.0.0", port=port)
