/* =============================
   VARIABLES
============================= */

// On utilise un nom plus précis pour éviter les conflits
const containerEl = document.querySelector(".container");

// On vérifie que l'élément existe avant de lire les données
if (containerEl) {
    const SESSION_ID = Number(containerEl.dataset.sessionId);
    const FREQUENCE = Number(containerEl.dataset.freq) * 60;
    const CURRENT_PHASE = containerEl.dataset.phase;
    const WEBCAM_FREQ = Number(containerEl.dataset.freqWebcam) * 1000; // Conversion en ms
    
    //Déclaration des variables globales 
    window.sessionId = SESSION_ID; 
}

/* =============================
   TITRES
============================= */

const title = document.getElementById("qcmTitle");
const subtitle = document.getElementById("qcmSubtitle");
const sliderLabel = document.getElementById("sliderLabel");

if (CURRENT_PHASE === "avant") {
    title.innerText = "Avant le cours";
    subtitle.innerText = "Comment vous sentez-vous ?";
    sliderLabel.innerText = "Lien avec le cours ?";
}
else if (CURRENT_PHASE === "pendant") {
    title.innerText = "Pendant le cours";
    subtitle.innerText = "Votre état actuel ?";
    sliderLabel.innerText = "Intensité";
}
else {
    title.innerText = "Après le cours";
    subtitle.innerText = "Votre ressenti ?";
    sliderLabel.innerText = "Impact du cours ?";
}

/* =============================
   EMOJIS
============================= */

document.querySelectorAll(".emoji").forEach(el => {
    el.addEventListener("click", () => {

        document.querySelectorAll(".emoji")
            .forEach(e => e.classList.remove("selected"));

        el.classList.add("selected");

        selectedEmotion = el.dataset.value;

        document.getElementById("sliderStep").style.display = "block";
    });
});

/* =============================
   SLIDER
============================= */

const slider = document.getElementById("intensitySlider");
const display = document.getElementById("sliderValue");

slider.addEventListener("input", () => {
    display.innerText = slider.value;
});

/* =============================
   SUBMIT
============================= */

async function submitQCM() {

    if (!selectedEmotion) {
        showAlert("Choisis une émotion");
        return;
    }

    try {

        const response = await fetch("/qcm/submit", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                session_id: SESSION_ID,
                phase: CURRENT_PHASE,
                emotion: selectedEmotion,
                intensity: Number(slider.value),
                slider_value: Number(slider.value),
                occurrence: occurrence
            })
        });

        const result = await response.json();

        if (!response.ok) {

            if (result.error === "Session terminée") {
                showAlert("Session terminée");
                window.location.href = "/dashboard/student";
                return;
            }

            if (result.error === "Already submitted") {
                showAlert("Déjà répondu");
                return;
            }

            showAlert(result.error);
            return;
        }

        occurrence++;

        if (CURRENT_PHASE === "apres") {
            showAlert("Merci !");
            setTimeout(() => {
                window.location.href = "/dashboard/student";
            }, 2000);
            return;
        }

        document.getElementById("qcmCard").style.display = "none";
        document.getElementById("countdownStep").style.display = "block";

        startCountdown();

    } catch {
        showAlert("Erreur réseau");
    }
}

/* =============================
   COUNTDOWN
============================= */

function startCountdown() {

    let timeLeft = FREQUENCE;
    const display = document.getElementById("countdown");

    const interval = setInterval(async () => {

        if (sessionHandled) {
            clearInterval(interval);
            return;
        }

        try {
            const res = await fetch("/check_session_status");
            const data = await res.json();

            if (data.status === "ended") {
                sessionHandled = true;
                clearInterval(interval);

                showAlert("Session terminée");

                setTimeout(() => {
                    window.location.href = "/dashboard/student";
                }, 2000);

                return;
            }

        } catch {}

        let min = Math.floor(timeLeft / 60);
        let sec = timeLeft % 60;

        display.innerText = `${min}:${sec.toString().padStart(2,'0')}`;

        timeLeft--;

        if (timeLeft < 0) {
            clearInterval(interval);
            showNextQCM();
        }

    }, 1000);
}

/* =============================
   RESET
============================= */

function showNextQCM() {

    document.getElementById("qcmCard").style.display = "block";
    document.getElementById("countdownStep").style.display = "none";

    selectedEmotion = null;

    document.querySelectorAll(".emoji")
        .forEach(e => e.classList.remove("selected"));

    slider.value = 3;
    display.innerText = 3;

    document.getElementById("sliderStep").style.display = "none";
}

/* =============================
   QUITTER
============================= */

async function leaveSession() {
    try {
        const response = await fetch("/leave_session", { 
            method: "POST" 
        });
        const data = await response.json();

        if (data.redirect) {
            // Le JavaScript effectue la redirection ici
            window.location.href = data.redirect;
        }
    } catch (error) {
        console.error("Erreur lors de la sortie :", error);
        // Au pire, on redirige de force
        window.location.href = "/student_dashboard";
    }
}



/* ============================================================
   WEBCAM FLOTTANTE + DEEPFACE
============================================================ */

const containerEl = document.querySelector(".container");

// 2. Initialisation des variables avec des valeurs par défaut sécurisées
let WC_SESSION_ID  = null;
let WEBCAM_FREQ    = 3000; // 3 secondes par défaut
let webcamActive   = false;
let consentGiven   = false;

let webcamStream   = null;
let webcamInterval = null;

// 3. Extraction sécurisée des données depuis le HTML
if (containerEl) {
    WC_SESSION_ID = Number(containerEl.dataset.sessionId);
    
    // On multiplie par 1000 pour passer des secondes (prof) aux millisecondes (JS)
    WEBCAM_FREQ   = Number(containerEl.dataset.freqWebcam) * 1000;
    
    // Conversion des chaînes "True"/"False" du template Jinja en vrais booléens JS
    webcamActive  = containerEl.dataset.webcamActive === "True";
    consentGiven  = containerEl.dataset.consent === "True";
} else {
    console.error("Erreur critique : L'élément .container est introuvable dans le DOM.");
}

// 4. Dictionnaire des émojis (Note : "happy" devient "motivé" pour coller à ton projet L2T2)
const emotionEmojis = {
    "happy":    "😊",
    "sad":      "😞",
    "angry":    "😰",
    "fear":     "😰",
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

// Fonction qui vérifie l'état de la session en temps réel
async function checkSessionStatus() {
    try {
        const response = await fetch("/check_session_status");
        const data = await response.json();

        // Si le serveur dit que la session est terminée ("ended")
        if (data.status === "ended") {
            console.log("La session a été fermée par le professeur.");
            
            // 1. On arrête la webcam pour libérer les ressources
            if (typeof stopWebcam === "function") {
                stopWebcam();
            }

            // 2. On affiche un petit message avant de partir (optionnel mais propre)
            alert("La session est terminée. Vous allez être redirigé vers votre tableau de bord.");

            // 3. Redirection immédiate
            window.location.href = "/student_dashboard";
        }
    } catch (error) {
        console.error("Erreur lors de la vérification du statut :", error);
    }
}

// On lance la vérification toutes les 5 secondes
setInterval(checkSessionStatus, 5000);


