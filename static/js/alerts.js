/* ============================================================
   FILTRAGE DE L'HISTORIQUE DES ALERTES
============================================================ */

/*
    Ce script gère les boutons de filtre de la page alerts.html.

    Il permet d'afficher uniquement :
    - toutes les alertes ;
    - les alertes individuelles ;
    - les alertes de classe ;
    - les alertes QCM ;
    - les alertes webcam.
*/

// Récupère tous les boutons de filtre
const filterBtns = document.querySelectorAll(".filter-btn");

// Récupère toutes les alertes affichées sur la page
const alertItems = document.querySelectorAll(".alert-item");


// Ajoute un événement de clic sur chaque bouton de filtre
filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {

        // Retire l'état actif de tous les boutons
        filterBtns.forEach(b => b.classList.remove("active"));

        // Active uniquement le bouton cliqué
        btn.classList.add("active");

        // Récupère le filtre demandé depuis l'attribut data-filter
        const filter = btn.dataset.filter;

        // Parcourt toutes les alertes pour décider lesquelles afficher
        alertItems.forEach(item => {

            // Niveau de l'alerte : "individual" ou "class"
            const level = item.dataset.level;

            // Source de l'alerte : "qcm", "webcam", "class_snapshot", etc.
            const source = item.dataset.source;

            // Par défaut, l'alerte reste visible
            let visible = true;

            // Filtre : alertes individuelles uniquement
            if (filter === "level-individual") {
                visible = level === "individual";
            }

            // Filtre : alertes de classe uniquement
            else if (filter === "level-class") {
                visible = level === "class";
            }

            // Filtre : alertes issues des QCM uniquement
            else if (filter === "source-qcm") {
                visible = source === "qcm";
            }

            // Filtre : alertes issues de la webcam uniquement
            else if (filter === "source-webcam") {
                visible = source === "webcam";
            }

            // Affiche ou masque l'alerte selon le filtre sélectionné
            item.style.display = visible ? "flex" : "none";
        });
    });
});
