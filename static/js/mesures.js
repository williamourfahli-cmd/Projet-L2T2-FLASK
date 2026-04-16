/**
 * EmoTrack - Système de suivi émotionnel (L2T2)
 * Ce script gère l'interface QCM, le compte à rebours et l'analyse webcam.
 * Tout est encapsulé dans une IIFE pour éviter les conflits de variables globales.
 */
(function() {
    /* ============================================================
       1. CONFIGURATION & RÉCUPÉRATION DES DONNÉES (DOM)
       ============================================================ */
    // On cible le container principal qui porte les attributs 'data-' de Jinja2
    const containerEl = document.querySelector(".container");

    // Initialisation des variables techniques (portée : cette fonction)
    let SESSION_ID    = null;  // ID unique de la session de cours
    let FREQUENCE     = 0;     // Temps d'attente entre deux QCM (en secondes)
    let CURRENT_PHASE = "pendant"; // Phase actuelle (avant/pendant/après)
    let WEBCAM_FREQ   = 3000;  // Intervalle d'analyse webcam (ms)
    let webcamActive  = false; // Le prof a-t-il activé la webcam ?
    let consentGiven  = false; // L'élève a-t-il accepté d'être filmé ?
    
    let occurrence      = 1;    // Compteur de réponses envoyées
    let selectedEmotion = null; // Stocke l'émotion cliquée dans le QCM
    let sessionHandled  = false; // Flag pour arrêter les boucles si la session finit
    let webcamStream    = null; // Flux vidéo de la caméra
    let webcamInterval  = null; // Timer de l'analyse récurrente

    // Extraction sécurisée des données injectées par Flask/Jinja
    if (containerEl) {
        SESSION_ID    = Number(containerEl.dataset.sessionId);
        FREQUENCE     = Number(containerEl.dataset.freq) * 60; // Conversion min -> sec
        CURRENT_PHASE = containerEl.dataset.phase;
        WEBCAM_FREQ   = Number(containerEl.dataset.freqWebcam) * 1000; // sec -> ms
        webcamActive  = containerEl.dataset.webcamActive === "True";
        consentGiven  = containerEl.dataset.consent === "True";
        
        // Exportation de l'ID pour d'autres scripts externes si besoin
        window.sessionId = SESSION_ID;
    }

    /* ============================================================
       2. ADAPTATION DE L'INTERFACE (TEXTES DYNAMIQUES)
       ============================================================ */
    const title       = document.getElementById("qcmTitle");
    const subtitle    = document.getElementById("qcmSubtitle");
    const sliderLabel = document.getElementById("sliderLabel");

    // On change les textes selon si on est au début, au milieu ou à la fin du cours
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
       3. GESTION DU QCM (EMOJIS & SLIDER)
       ============================================================ */
    // Gestion du clic sur les émojis du formulaire
    document.querySelectorAll(".emoji").forEach(el => {
        el.addEventListener("click", () => {
            // Désélectionne les autres émojis
            document.querySelectorAll(".emoji").forEach(e => e.classList.remove("selected"));
            // Sélectionne l'émoji cliqué
            el.classList.add("selected");
            selectedEmotion = el.dataset.value;
            // Affiche l'étape suivante (le slider d'intensité)
            const sliderStep = document.getElementById("sliderStep");
            if (sliderStep) sliderStep.style.display = "block";
        });
    });

    // Mise à jour de la valeur numérique affichée à côté du slider
    const slider  = document.getElementById("intensitySlider");
    const display = document.getElementById("sliderValue");
    if (slider && display) {
        slider.addEventListener("input", () => { display.innerText = slider.value; });
    }

    /**
     * Envoie les données du QCM au serveur Flask via une requête POST (AJAX)
     */
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
                    phase:      CURRENT_PHASE,
                    emotion:    selectedEmotion,
                    intensity:  Number(slider.value),
                    occurrence: occurrence
                })
            });

            if (!response.ok) throw new Error("Erreur serveur");

            occurrence++;
            
            // Si c'est la phase finale, on quitte. Sinon, on lance le compte à rebours.
            if (CURRENT_PHASE === "apres") {
                alert("Merci ! Vos réponses ont été enregistrées.");
                window.location.href = "/student_dashboard";
            } else {
                document.getElementById("qcmCard").style.display = "none";
                document.getElementById("countdownStep").style.display = "block";
                startCountdown();
            }
        } catch (e) {
            alert("Impossible d'envoyer vos réponses. Vérifiez votre connexion.");
        }
    };

    /* ============================================================
       4. ANALYSE WEBCAM (INTELLIGENCE ARTIFICIELLE)
       ============================================================ */
    /**
     * Active la caméra et lance l'analyse récurrente via DeepFace
     */
    async function startWebcam() {
        try {
            webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
            const video = document.getElementById("webcamVideo");
            if (video) {
                video.srcObject = webcamStream;
                document.getElementById("webcamFloat").style.display = "block";
                // Lance l'analyse à la fréquence définie par le professeur
                webcamInterval = setInterval(captureAndAnalyze, WEBCAM_FREQ);
            }
        } catch (err) {
            console.warn("L'accès à la webcam a été refusé ou n'est pas disponible.");
        }
    }

    /**
     * Capture une image de la webcam, la convertit en base64 et l'envoie au serveur
     */
    async function captureAndAnalyze() {
        const video  = document.getElementById("webcamVideo");
        const canvas = document.getElementById("webcamCanvas");
        if (!video || !canvas) return;

        // Dessine l'image de la vidéo sur un canvas invisible pour extraction
        canvas.width  = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        
        // Compression en JPEG (qualité 70%) pour alléger la requête
        const imageData = canvas.toDataURL("image/jpeg", 0.7);

        try {
            const res = await fetch("/analyze_webcam", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: imageData })
            });
            const data = await res.json();
            
            // Si l'analyse DeepFace réussit, on met à jour le badge sous la webcam
            if (data.status === "success") {
                const emotionEmojis = {
                    "happy": "😊", "sad": "😞", "angry": "😰",
                    "fear": "😰", "surprise": "😲", "disgust": "🤢", "neutral": "😐"
                };
                const emoji = emotionEmojis[data.emotion] || "😐";
                document.getElementById("webcamEmotionBadge").innerText = `${emoji} ${data.emotion}`;
            }
        } catch (e) {
            console.warn("Échec de la communication avec le module IA.");
        }
    }

    /**
     * Libère les ressources (arrête la caméra et les timers)
     */
    window.stopWebcam = function() {
        if (webcamStream) webcamStream.getTracks().forEach(t => t.stop());
        if (webcamInterval) clearInterval(webcamInterval);
    };

    /* ============================================================
       5. LOGIQUE DE TEMPS & STATUT DE LA SESSION
       ============================================================ */
    /**
     * Gère le timer visuel entre deux QCM
     */
    function startCountdown() {
        let timeLeft = FREQUENCE;
        const displayCb = document.getElementById("countdown");
        const interval = setInterval(() => {
            if (sessionHandled) { clearInterval(interval); return; }
            
            let min = Math.floor(timeLeft / 60);
            let sec = timeLeft % 60;
            if (displayCb) displayCb.innerText = `${min}:${sec.toString().padStart(2,'0')}`;
            
            if (timeLeft <= 0) {
                clearInterval(interval);
                showNextQCM(); // Affiche le nouveau QCM quand le temps est écoulé
            }
            timeLeft--;
        }, 1000);
    }

    /**
     * Vérifie si le professeur a mis fin à la session à distance
     */
    async function checkSessionStatus() {
        if (sessionHandled) return;
        try {
            const res = await fetch("/check_session_status");
            const data = await res.json();
            if (data.status === "ended") {
                sessionHandled = true;
                stopWebcam();
                alert("Le professeur a clôturé la session.");
                window.location.href = "/student_dashboard";
            }
        } catch (e) {}
    }

    /* ============================================================
       6. UX : DRAG & DROP DE LA FENÊTRE WEBCAM
       ============================================================ */
    const floatEl  = document.getElementById("webcamFloat");
    const headerEl = document.getElementById("webcamHeader");
    let isDragging = false;
    let offsetX, offsetY;

    if (headerEl && floatEl) {
        // Détection du clic pour commencer le déplacement
        headerEl.addEventListener("mousedown", (e) => {
            isDragging = true;
            offsetX = e.clientX - floatEl.getBoundingClientRect().left;
            offsetY = e.clientY - floatEl.getBoundingClientRect().top;
            floatEl.style.cursor = "grabbing";
        });

        // Suivi du mouvement de la souris
        document.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            floatEl.style.left  = (e.clientX - offsetX) + "px";
            floatEl.style.top   = (e.clientY - offsetY) + "px";
            floatEl.style.right = "auto"; floatEl.style.bottom = "auto";
        });

        // Relâchement du clic
        document.addEventListener("mouseup", () => { 
            isDragging = false; 
            floatEl.style.cursor = "grab"; 
        });
    }

    /* ============================================================
       LANCEMENT DES SERVICES AU CHARGEMENT
       ============================================================ */
    if (webcamActive && consentGiven) startWebcam();
    setInterval(checkSessionStatus, 5000); // Check session toutes les 5 sec
    window.addEventListener("beforeunload", stopWebcam); // Nettoyage en quittant

})();