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