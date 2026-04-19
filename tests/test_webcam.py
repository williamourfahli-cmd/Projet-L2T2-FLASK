import os
import json

from flask import request, jsonify, session

import requests as http_requests
from requests.exceptions import Timeout

from models import db, WebcamAnalysis

@app.route("/analyze_webcam", methods=["POST"])
def analyze_webcam():
    """
    Analyse webcam via serveur DeepFace externe + sauvegarde DB
    Compatible prod + tests (mock)
    """

    # =========================
    # AUTH
    # =========================
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    payload = request.get_json()

    if not payload or "image" not in payload:
        return jsonify({"error": "Missing image"}), 400

    # =========================
    # CONFIG
    # =========================
    deepface_url = os.environ.get("DEEPFACE_SERVER_URL")

    if not deepface_url:
        # en prod → erreur
        # en test → sera bypass par mock
        deepface_url = "http://mock-server"

    try:
        # =========================
        # CALL API
        # =========================
        response = http_requests.post(
            f"{deepface_url}/analyze",
            json={
                "image": payload["image"],
                "secret_key": os.environ.get("DEEPFACE_SECRET_KEY", "test-key")
            },
            timeout=120
        )

        # =========================
        # CHECK STATUS
        # =========================
        if response.status_code != 200:
            return jsonify({"error": "DeepFace error"}), 500

        result = response.json()

        # =========================
        # VALIDATION RESULT
        # =========================
        if result.get("status") != "success":
            return jsonify({"error": "Analysis failed"}), 500

        emotion = result.get("emotion")
        confidence = result.get("confidence")
        all_emotions = result.get("all_emotions", {})

        if not emotion:
            return jsonify({"error": "Invalid response"}), 500

        # =========================
        # DB (aligné avec ton model)
        # =========================
        analysis = WebcamAnalysis(
            session_id=session.get("current_session_id"),
            user_id=session["user_id"],
            dominant_emotion=emotion,
            confidence=confidence,
            all_emotions=json.dumps(all_emotions)
        )

        db.session.add(analysis)
        db.session.commit()

        # =========================
        # RESPONSE
        # =========================
        return jsonify({
            "status": "success",
            "emotion": emotion,
            "confidence": confidence
        }), 200

    except http_requests.exceptions.Timeout:
        return jsonify({"error": "timeout"}), 504

    except Exception as e:
        db.session.rollback()
        print(f"analyze_webcam error: {e}")
        return jsonify({"error": "server"}), 500
