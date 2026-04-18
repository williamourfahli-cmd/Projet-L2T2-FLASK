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
    });
});
