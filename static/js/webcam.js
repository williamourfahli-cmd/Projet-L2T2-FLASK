/* ============================================================
   WEBCAM FLOTTANTE + DEEPFACE
============================================================ */

const body = document.querySelector(".container");

const WC_SESSION_ID  = Number(body.dataset.sessionId);
const WEBCAM_FREQ    = Number(body.dataset.freqWebcam) * 1000;
const webcamActive   = body.dataset.webcamActive === "True";
const consentGiven   = body.dataset.consent === "True";

let webcamStream   = null;
let webcamInterval = null;

const emotionEmojis = {
    "happy":    "😊",
    "sad":      "😢",
    "angry":    "😠",
    "fear":     "😨",
    "surprise": "😲",
    "disgust":  "🤢",
    "neutral":  "😐"
};

/* ============================================================
   DÉMARRAGE WEBCAM
============================================================ */

async function startWebcam() {
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.getElementById("webcamVideo");
        video.srcObject = webcamStream;
        document.getElementById("webcamFloat").style.display = "block";
        webcamInterval = setInterval(captureAndAnalyze, WEBCAM_FREQ);
    } catch (err) {
        console.warn("Webcam non disponible :", err);
    }
}

/* ============================================================
   CAPTURE ET ANALYSE
============================================================ */

async function captureAndAnalyze() {
    const video  = document.getElementById("webcamVideo");
    const canvas = document.getElementById("webcamCanvas");

    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);

    const imageData = canvas.toDataURL("image/jpeg", 0.7);

    try {
        const res = await fetch("/analyze_webcam", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: WC_SESSION_ID,
                image: imageData
            })
        });

        const data = await res.json();

        if (data.ok) {
            const emoji = emotionEmojis[data.emotion] || "😐";
            document.getElementById("webcamEmotionBadge").innerText =
                `${emoji} ${data.emotion}`;
        }

    } catch (e) {
        console.warn("Erreur analyse webcam :", e);
    }
}

/* ============================================================
   ARRÊT WEBCAM
============================================================ */

function stopWebcam() {
    if (webcamStream)   webcamStream.getTracks().forEach(t => t.stop());
    if (webcamInterval) clearInterval(webcamInterval);
}

window.addEventListener("beforeunload", stopWebcam);

/* ============================================================
   DRAG & DROP
============================================================ */

const floatEl  = document.getElementById("webcamFloat");
const headerEl = document.getElementById("webcamHeader");

let isDragging = false;
let offsetX = 0;
let offsetY = 0;

headerEl.addEventListener("mousedown", (e) => {
    isDragging = true;
    offsetX = e.clientX - floatEl.getBoundingClientRect().left;
    offsetY = e.clientY - floatEl.getBoundingClientRect().top;
    floatEl.style.cursor = "grabbing";
    e.preventDefault();
});

document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;

    let newX = e.clientX - offsetX;
    let newY = e.clientY - offsetY;

    newX = Math.max(0, Math.min(window.innerWidth  - floatEl.offsetWidth,  newX));
    newY = Math.max(0, Math.min(window.innerHeight - floatEl.offsetHeight, newY));

    floatEl.style.left   = newX + "px";
    floatEl.style.top    = newY + "px";
    floatEl.style.right  = "auto";
    floatEl.style.bottom = "auto";
});

document.addEventListener("mouseup", () => {
    isDragging = false;
    floatEl.style.cursor = "grab";
});

/* ============================================================
   LANCEMENT AUTO
============================================================ */

if (webcamActive && consentGiven) {
    startWebcam();
}