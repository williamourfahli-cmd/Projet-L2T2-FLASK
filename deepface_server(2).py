import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'   # Cache les warnings TensorFlow
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'   # Force le mode CPU

import base64
import numpy as np
import cv2
import json
from flask import Flask, request, jsonify
from deepface import DeepFace

# ============================================================
# SERVEUR DEEPFACE - Déployé sur Hugging Face Spaces
#
# Ce serveur reçoit une image base64 depuis app.py (Render),
# analyse l'émotion avec DeepFace, et renvoie le résultat.
#
# Variables d'environnement à définir sur Hugging Face :
#   DEEPFACE_SECRET_KEY : clé secrète partagée avec app.py
# ============================================================

app = Flask(__name__)

DEEPFACE_SECRET_KEY = os.environ.get("DEEPFACE_SECRET_KEY", "deepface-secret-key")


@app.route("/", methods=["GET"])
@app.route("/health", methods=["GET"])
def health():
    """
    Route de vérification que le serveur est bien démarré.
    Ouvre cette URL avant la démo pour réveiller le Space !
    """
    return jsonify({
        "status": "ok",
        "message": "DeepFace server is running on Hugging Face Spaces"
    })


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Reçoit une image base64, analyse l'émotion avec DeepFace.

    Body JSON attendu :
        - image (str)      : image encodée en base64
        - secret_key (str) : clé secrète partagée avec app.py

    Returns:
        JSON avec l'émotion dominante, le score de confiance,
        et toutes les émotions détectées.
    """

    payload = request.get_json()

    if not payload:
        return jsonify({"error": "Missing JSON payload"}), 400

    # Vérification de la clé secrète
    if payload.get("secret_key") != DEEPFACE_SECRET_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    image_data = payload.get("image")
    if not image_data:
        return jsonify({"error": "Missing image"}), 400

    try:
        # Décodage de l'image base64
        header, encoded = image_data.split(",", 1)
        img_bytes = base64.b64decode(encoded)
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # Analyse DeepFace
        # opencv est le backend le plus léger pour limiter la RAM
        # enforce_detection=False évite un crash si aucun visage détecté
        results = DeepFace.analyze(
            img,
            actions=["emotion"],
            enforce_detection=False,
            detector_backend="opencv"
        )

        dominant_emotion = results[0]["dominant_emotion"]
        emotions_dict    = results[0]["emotion"]
        confidence       = emotions_dict[dominant_emotion]

        return jsonify({
            "status":       "success",
            "emotion":      dominant_emotion,
            "confidence":   round(confidence, 2),
            "all_emotions": emotions_dict
        })

    except Exception as e:
        print(f"DeepFace error: {e}")
        return jsonify({
            "status":  "error",
            "message": "Analysis failed"
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))  # 7860 = port par défaut Hugging Face
    app.run(host="0.0.0.0", port=port)
