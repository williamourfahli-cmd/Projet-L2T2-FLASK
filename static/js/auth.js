function togglePassword(inputId, button) {
    const input = document.getElementById(inputId);

    if (!input) return;

    if (input.type === "password") {
        input.type = "text";
        button.textContent = "Cacher";
    } else {
        input.type = "password";
        button.textContent = "Voir";
    }
}
