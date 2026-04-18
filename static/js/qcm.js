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

})();
