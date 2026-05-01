/* =============================
   CONFIRMATION FIN SESSION
============================= */

document.querySelectorAll("form[action*='end_session']")
.forEach(form => {

    form.addEventListener("submit", (e) => {

        const confirmEnd = confirm("Voulez-vous vraiment terminer cette session ?");

        if (!confirmEnd) {
            e.preventDefault();
        }
    });

});

/* =============================
   SEUILS ALERTES — affichage conditionnel + valeurs live
============================= */

const checkboxAlertes  = document.getElementById("checkbox-alertes");
const seuilsContainer  = document.getElementById("alertes-seuils");
const sliderIndividuel = document.getElementById("seuil-individuel");
const sliderClasse     = document.getElementById("seuil-classe");
const valIndividuel    = document.getElementById("val-seuil-individuel");
const valClasse        = document.getElementById("val-seuil-classe");

if (checkboxAlertes && seuilsContainer) {

    // Affiche ou masque les sliders selon l'état de la checkbox
    function toggleSeuils() {
        seuilsContainer.style.display = checkboxAlertes.checked ? "block" : "none";
    }

    checkboxAlertes.addEventListener("change", toggleSeuils);
    toggleSeuils(); // état initial

    // Met à jour la valeur affichée en temps réel
    if (sliderIndividuel && valIndividuel) {
        sliderIndividuel.addEventListener("input", () => {
            valIndividuel.textContent = sliderIndividuel.value;
        });
    }

    if (sliderClasse && valClasse) {
        sliderClasse.addEventListener("input", () => {
            valClasse.textContent = sliderClasse.value;
        });
    }
}
