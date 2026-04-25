/* ===== LOGIQUE DE FILTRAGE ===== */
const filterBtns = document.querySelectorAll(".filter-btn");
const alertItems = document.querySelectorAll(".alert-item");

filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {

        // Mise à jour des boutons actifs
        filterBtns.forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        const filter = btn.dataset.filter;

        alertItems.forEach(item => {
            const level  = item.dataset.level;
            const source = item.dataset.source;

            let visible = true;

            if (filter === "level-individual") visible = level === "individual";
            else if (filter === "level-class")  visible = level === "class";
            else if (filter === "source-qcm")   visible = source === "qcm";
            else if (filter === "source-webcam") visible = source === "webcam";

            item.style.display = visible ? "flex" : "none";
        });
    });
});
