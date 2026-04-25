document.addEventListener("DOMContentLoaded", () => {

    /* =========================================================================
    Gestion du switch étudiant / professeur
    ========================================================================= */

    const toggle = document.getElementById("roleToggle");
    const roleInput = document.getElementById("roleInput");
    const labelStudent = document.getElementById("label-student");
    const labelProfessor = document.getElementById("label-professor");

    if (toggle) {
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
        });
    }

    /* =========================================================================
    Vérification de la confirmation d'adresse email.
    Comparaison des deux champs email à la soumission du formulaire.
    Si les deux adresses sont différentes, la soumission est bloquée
    côté navigateur — aucune donnée n'est envoyée au serveur.
    ========================================================================= */

    const form = document.querySelector("form");
    const emailInput = document.getElementById("email");
    const emailConfirm = document.getElementById("email_confirm");

    if (form && emailInput && emailConfirm) {
        form.addEventListener("submit", (e) => {
            if (emailInput.value.trim() !== emailConfirm.value.trim()) {
                e.preventDefault();
                emailConfirm.setCustomValidity("Les adresses email ne correspondent pas.");
                emailConfirm.reportValidity();
            } else {
                emailConfirm.setCustomValidity("");
            }
        });

        emailConfirm.addEventListener("input", () => {
            emailConfirm.setCustomValidity("");
        });
    }

});
