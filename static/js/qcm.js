(function() {

    /* ============================================================
       1. CONFIGURATION & DONNÉES
    ============================================================ */

    const containerEl = document.querySelector(".container");

    let SESSION_ID    = null;
    let FREQUENCE     = 0;
    let CURRENT_PHASE = "pendant";

    let selectedEmotion = null;
    let sessionHandled  = false;

    // Si la fin de session a déjà été traitée (évite boucle reload)
    if (sessionStorage.getItem("sessionEndedHandled")) {
        sessionHandled = true;
    }

    if (containerEl) {
        SESSION_ID    = Number(containerEl.dataset.sessionId);
        FREQUENCE     = Number(containerEl.dataset.freq) * 60;
        CURRENT_PHASE = containerEl.dataset.phase;

        window.sessionId = SESSION_ID;
    }

    /* ============================================================
       2. TEXTES DYNAMIQUES
    ============================================================ */

    const title       = document.getElementById("qcmTitle");
    const subtitle    = document.getElementById("qcmSubtitle");
    const sliderLabel = document.getElementById("sliderLabel");

    if (title && subtitle && sliderLabel) {
        const texts = {
            "avant":   ["Avant le cours", "Comment vous sentez-vous ?", "Lien avec le cours ?"],
            "pendant": ["Pendant le cours", "Votre état actuel ?", "Intensité"],
            "apres":   ["Après le cours", "Votre ressenti ?", "Impact du cours ?"]
        };

        const [t, s, l] = texts[CURRENT_PHASE] || texts["pendant"];

        title.innerText       = t;
        subtitle.innerText    = s;
        sliderLabel.innerText = l;
    }

    /* ============================================================
       3. QCM (EMOJIS + SLIDER)
    ============================================================ */

    document.querySelectorAll(".emoji").forEach(el => {
        el.addEventListener("click", () => {
            document.querySelectorAll(".emoji").forEach(e => e.classList.remove("selected"));
            el.classList.add("selected");

            selectedEmotion = el.dataset.value;

            const sliderStep = document.getElementById("sliderStep");
            if (sliderStep) sliderStep.style.display = "block";
        });
    });

    const slider  = document.getElementById("intensitySlider");
    const display = document.getElementById("sliderValue");

    if (slider && display) {
        slider.addEventListener("input", () => {
            display.innerText = slider.value;
        });
    }

    /* ============================================================
       4. ENVOI QCM
    ============================================================ */

    window.submitQCM = async function() {

        if (!selectedEmotion) {
            alert("Veuillez choisir une émotion avant de valider.");
            return;
        }

        try {
            const response = await fetch("/qcm/submit", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    session_id: SESSION_ID,
                    emotion: selectedEmotion,
                    slider_value: slider ? Number(slider.value) : 3
                })
            });

            if (!response.ok) throw new Error("Erreur serveur");

            // Si phase finale → retour dashboard
            if (CURRENT_PHASE === "apres") {

                sessionStorage.removeItem("sessionEndedHandled");

                alert("Merci ! Vos réponses ont été enregistrées.");
                window.location.href = "/student_dashboard";

            } else {
                document.getElementById("qcmCard").style.display = "none";
                document.getElementById("countdownStep").style.display = "block";
                startCountdown();
            }

        } catch (e) {
            alert("Impossible d'envoyer vos réponses.");
        }
    };
    /*===========================================================
    5.BIP SONORE
    ============================================================*/
    function playBip() {
        const ctx  = new (window.AudioContext || window.webkitAudioContext)();
        const gain = ctx.createGain();
        gain.connect(ctx.destination);
        gain.gain.value = 0.35;

        [0, 0.18].forEach(offset => {
            const osc = ctx.createOscillator();
            osc.type = "sine";
            osc.frequency.value = 520;
            osc.connect(gain);
            osc.start(ctx.currentTime + offset);
            osc.stop(ctx.currentTime + offset + 0.12);
        });

        setTimeout(() => ctx.close(), 600);
    }


    /* ============================================================
       6. COUNTDOWN ENTRE QCM
    ============================================================ */

    function startCountdown() {
        let timeLeft = FREQUENCE;
        const displayCb = document.getElementById("countdown");

        const interval = setInterval(() => {

            if (sessionHandled) {
                clearInterval(interval);
                return;
            }

            let min = Math.floor(timeLeft / 60);
            let sec = timeLeft % 60;

            if (displayCb) {
                displayCb.innerText = `${min}:${sec.toString().padStart(2,'0')}`;
            }

            if (timeLeft <= 0) {
                clearInterval(interval);
                playBip() // Appelle la fonction playBit() pour qu'un bip sonore se déclenche à chaque nouveau QCM
                showNextQCM();
            }

            timeLeft--;

        }, 1000);
    }

    /* ============================================================
       7. FIN DE SESSION (CÔTÉ PROF)
    ============================================================ */

    async function checkSessionStatus() {

        // Si déjà traité ou déjà en phase finale → stop
        if (sessionHandled || CURRENT_PHASE === "apres") return;

        try {
            const res = await fetch("/check_session_status");
            const data = await res.json();

            if (data.status === "ended") {

                sessionHandled = true;

                if (!sessionStorage.getItem("sessionEndedHandled")) {
                    sessionStorage.setItem("sessionEndedHandled", "true");
                    window.location.reload();
                }
            }

        } catch (e) {
            console.warn("Erreur vérification session");
        }
    }

    /* ============================================================
       8. AFFICHAGE QCM SUIVANT
    ============================================================ */

    function showNextQCM() {

        document.getElementById("countdownStep").style.display = "none";

        selectedEmotion = null;

        document.querySelectorAll(".emoji").forEach(e => e.classList.remove("selected"));
        document.getElementById("sliderStep").style.display = "none";

        CURRENT_PHASE = "pendant";

        const title = document.getElementById("qcmTitle");
        if (title) title.innerText = "Pendant le cours";

        document.getElementById("qcmCard").style.display = "block";
    }

    /* ============================================================
       9. INITIALISATION
    ============================================================ */

    setInterval(checkSessionStatus, 5000);


    /* ============================================================
   10. WEBCAM FLOTTANTE
============================================================ */

// Récupération des éléments HTML de la webcam
const webcamFloat  = document.getElementById("webcamFloat");   // div flottante
const webcamVideo  = document.getElementById("webcamVideo");   // balise video
const webcamCanvas = document.getElementById("webcamCanvas");  // canvas caché pour capturer
const emotionBadge = document.getElementById("webcamEmotionBadge"); // badge émotion

// Récupération des paramètres depuis le HTML (data attributes)
// WEBCAM_ACTIVE : true si le prof a activé la webcam pour cette session
// FREQ_WEBCAM   : fréquence d'analyse en millisecondes
const WEBCAM_ACTIVE = containerEl?.dataset.webcamActive === "True";
const FREQ_WEBCAM   = Number(containerEl?.dataset.freqWebcam) * 60 * 1000;

/* -----------------------------------------------------------
   Démarre la webcam si elle est activée pour cette session
----------------------------------------------------------- */
async function startWebcam() {
    // Si webcam désactivée par le prof → on ne fait rien
    if (!WEBCAM_ACTIVE) return;

    try {
        // Demande l'accès à la caméra de l'étudiant
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });

        // Connecte le flux vidéo à la balise <video>
        webcamVideo.srcObject = stream;

        // Affiche la div flottante (elle est cachée par défaut)
        webcamFloat.style.display = "block";

        // Lance une analyse à intervalle régulier (fréquence définie par le prof)
        // Si FREQ_WEBCAM est 0 ou invalide → toutes les 30 secondes par défaut
        setInterval(captureAndAnalyze, FREQ_WEBCAM || 30000);

    } catch (e) {
        // L'étudiant a refusé l'accès ou la caméra est indisponible
        console.warn("Webcam non disponible", e);
    }
}

/* -----------------------------------------------------------
   Capture une image de la webcam et l'envoie à DeepFace
   pour analyser l'émotion de l'étudiant
----------------------------------------------------------- */
async function captureAndAnalyze() {
    // Sécurité : on ne fait rien si webcam désactivée
    if (!WEBCAM_ACTIVE) return;

    // Prépare le canvas avec les mêmes dimensions que la vidéo
    const ctx = webcamCanvas.getContext("2d");
    webcamCanvas.width  = webcamVideo.videoWidth;
    webcamCanvas.height = webcamVideo.videoHeight;

    // Dessine la frame actuelle de la vidéo sur le canvas
    ctx.drawImage(webcamVideo, 0, 0);

    // Convertit le canvas en image base64 (format JPEG, qualité 70%)
    // C'est ce format qu'attend le serveur DeepFace sur HuggingFace
    const imageData = webcamCanvas.toDataURL("image/jpeg", 0.7);

    try {
        // Envoie l'image à la route Flask /analyze_webcam sur Render
        // qui la transmet ensuite au Space HuggingFace
        const res = await fetch("/analyze_webcam", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                image: imageData, 
                session_id: SESSION_ID  // pour associer l'analyse à la bonne session
            })
        });

        const data = await res.json();

        // Si une émotion est détectée → on l'affiche dans le badge
        if (data.emotion) {
            emotionBadge.innerText = data.emotion;
        }

    } catch (e) {
        // Erreur réseau ou serveur → on log sans bloquer l'étudiant
        console.warn("Erreur analyse webcam", e);
    }
}

/* -----------------------------------------------------------
   DRAG & DROP — permet à l'étudiant de déplacer
   la fenêtre webcam flottante sur l'écran
----------------------------------------------------------- */
const webcamHeader = document.getElementById("webcamHeader");
let isDragging = false, startX, startY, initX, initY;

// Quand l'étudiant clique sur le header → début du déplacement
webcamHeader.addEventListener("mousedown", (e) => {
    isDragging = true;
    startX = e.clientX;  // position souris au moment du clic
    startY = e.clientY;
    initX  = webcamFloat.offsetLeft;  // position de la div au moment du clic
    initY  = webcamFloat.offsetTop;
    webcamFloat.style.cursor = "grabbing";  // change le curseur
});

// Quand la souris bouge → déplace la div si on est en train de drag
document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    // Calcule la nouvelle position : position initiale + déplacement souris
    webcamFloat.style.left   = (initX + e.clientX - startX) + "px";
    webcamFloat.style.top    = (initY + e.clientY - startY) + "px";
    // Désactive right/bottom pour que left/top prennent le contrôle
    webcamFloat.style.right  = "auto";
    webcamFloat.style.bottom = "auto";
});

// Quand l'étudiant relâche le clic → fin du déplacement
document.addEventListener("mouseup", () => {
    isDragging = false;
    webcamFloat.style.cursor = "grab";  // remet le curseur normal
});

// Lance la webcam au chargement de la page
startWebcam();

})();
