/* =============================
   VARIABLES
============================= */

const body = document.querySelector(".container");

const SESSION_ID = Number(body.dataset.sessionId);
const FREQUENCE = Number(body.dataset.freq) * 60;
const CURRENT_PHASE = body.dataset.phase;

let occurrence = 1;
let selectedEmotion = null;
let sessionHandled = false;

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

function leaveSession() {
    fetch("/leave_session", {method:"POST"})
        .then(() => window.location.href = "/dashboard/student");
}