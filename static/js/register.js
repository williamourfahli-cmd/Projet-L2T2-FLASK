document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("roleToggle");
    const roleInput = document.getElementById("roleInput");

    const labelStudent = document.getElementById("label-student");
    const labelProfessor = document.getElementById("label-professor");

    if (!toggle) return;

    toggle.addEventListener("change", () => {
        if (toggle.checked) {
            roleInput.value = "professor";
            labelProfessor.classList.add("active");
            labelStudent.classList.remove("active");
        } else {
            roleInput.value = "student";
            labelStudent.classList.add("active");
            labelProfessor.classList.remove("active");
        }

    /* =========================================================================
    Vérification de l'orthographe de l'adresse mail entrée par l'utilisateur 
    La vérification se fait lors de la soumission du formulaire
    Comparaison des adresses mail entrées dans le champ "Entrer votre email" et le champ "Confirmer votre email */

    const form = document.querySelector("form");
    const emailInput = document.getElementById("email");
    const emailConfirm = document.getElementById("email_confirm");

    form.addEventListener("submit", (e) => {
        if (emailInput.value.trim() !== emailConfirm.value.trim()) {
            e.preventDefault();
            emailConfirm.setCustomValidity("Les adresses email ne correspondent pas.");
            emailConfirm.reportValidity();
        } else {
            emailConfirm.setCustomValidity(""); /*setCustomValidity utilise la validation native du navigateur
            pas besoin de créer un message d'erreur custom et la soumission est bloquée automatiquement. */
        }
    });

    emailConfirm.addEventListener("input", () => {
        emailConfirm.setCustomValidity("");
    });
    });
});


