/* =============================
   INPUT CODE SESSION
============================= */

const codeInput = document.getElementById("codeInput");

if (codeInput) {
    codeInput.addEventListener("input", () => {
        codeInput.value = codeInput.value.toUpperCase();
    });
}

/* =============================
   VALIDATION FORMULAIRE
============================= */

const form = document.getElementById("joinForm");
const errorMsg = document.getElementById("errorMsg");

if (form) {
    form.addEventListener("submit", (e) => {

        if (codeInput.value.trim().length !== 6) {
            e.preventDefault();

            errorMsg.innerText = "Le code doit contenir 6 caractères.";
            errorMsg.style.display = "block";
        }
    });
}

/* =============================
   UX
============================= */

window.onload = () => {
    if (codeInput) {
        codeInput.focus();
    }
};
