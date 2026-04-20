/* ============================================
   session_active.js
   Polling toutes les 5s → /api/session/<id>/students
   ============================================ */

const POLL_INTERVAL = 5000; // ms
let knownStudentIds = new Set();

/* ---- Initialisation ---- */
document.addEventListener("DOMContentLoaded", () => {
    fetchStudents();
    setInterval(fetchStudents, POLL_INTERVAL);
});

/* ---- Fetch principal ---- */
async function fetchStudents() {
    try {
        const res = await fetch(`/api/session/${SESSION_ID}/students`);
        if (!res.ok) throw new Error("Erreur réseau");
        const data = await res.json();
        renderStudents(data.students);
        updateStats(data.students);
        updateTimestamp();
    } catch (err) {
        console.error("Erreur lors de la récupération des étudiants :", err);
    }
}

/* ---- Rendu de la liste ---- */
function renderStudents(students) {
    const container = document.getElementById("students-container");
    const emptyState = document.getElementById("empty-state");

    if (!students || students.length === 0) {
        container.innerHTML = "";
        container.appendChild(buildEmptyState());
        knownStudentIds.clear();
        return;
    }

    // Supprimer les cartes des étudiants déconnectés
    const currentIds = new Set(students.map(s => String(s.id)));
    document.querySelectorAll(".student-card").forEach(card => {
        if (!currentIds.has(card.dataset.studentId)) {
            card.remove();
            knownStudentIds.delete(card.dataset.studentId);
        }
    });

    // Ajouter les nouveaux
    students.forEach(student => {
        const idStr = String(student.id);
        if (!knownStudentIds.has(idStr)) {
            knownStudentIds.add(idStr);
            container.appendChild(buildStudentCard(student));
        }
    });
}

/* ---- Construction d'une carte étudiant ---- */
function buildStudentCard(student) {
    const isAnon = student.anonymous;
    const card = document.createElement("div");
    card.className = "student-card";
    card.dataset.studentId = String(student.id);

    const avatar = document.createElement("div");
    avatar.className = `student-avatar ${isAnon ? "anonymous" : "identified"}`;
    avatar.textContent = isAnon
        ? "🎭"
        : getInitials(student.first_name, student.last_name);

    const name = document.createElement("div");
    name.className = "student-name";
    name.textContent = isAnon
        ? "Anonyme"
        : `${student.first_name} ${student.last_name}`;

    const tag = document.createElement("span");
    tag.className = `student-tag ${isAnon ? "anonymous" : "identified"}`;
    tag.textContent = isAnon ? "🎭 Anonyme" : "✅ Identifié";

    const time = document.createElement("div");
    time.className = "student-time";
    time.textContent = `Connecté à ${formatTime(student.joined_at)}`;

    card.appendChild(avatar);
    card.appendChild(name);
    card.appendChild(tag);
    card.appendChild(time);

    return card;
}

/* ---- État vide ---- */
function buildEmptyState() {
    const div = document.createElement("div");
    div.className = "empty-state";
    div.id = "empty-state";
    div.innerHTML = `
        <div class="empty-icon">🎓</div>
        <p>En attente d'étudiants…</p>
        <p style="font-size:0.8rem;">
            Partagez le code 
            <strong style="color:var(--text)">${SESSION_CODE}</strong> 
            à vos étudiants
        </p>
    `;
    return div;
}

/* ---- Mise à jour des stats ---- */
function updateStats(students) {
    const total = students ? students.length : 0;
    const named = students ? students.filter(s => !s.anonymous).length : 0;
    const anon  = total - named;

    animateValue("stat-total", total);
    animateValue("stat-named", named);
    animateValue("stat-anon",  anon);
}

/* Compteur animé */
function animateValue(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const current = parseInt(el.textContent) || 0;
    if (current === target) return;

    const step = target > current ? 1 : -1;
    let val = current;
    const interval = setInterval(() => {
        val += step;
        el.textContent = val;
        if (val === target) clearInterval(interval);
    }, 40);
}

/* ---- Horodatage dernière mise à jour ---- */
function updateTimestamp() {
    const el = document.getElementById("last-update");
    if (el) {
        const now = new Date();
        el.textContent = `Mis à jour à ${now.getHours().toString().padStart(2,"0")}:${now.getMinutes().toString().padStart(2,"0")}:${now.getSeconds().toString().padStart(2,"0")}`;
    }
}

/* ---- Copier le code ---- */
function copyCode(code) {
    navigator.clipboard.writeText(code).then(() => showToast("✅ Code copié !"));
}

/* ---- Toast ---- */
function showToast(message) {
    let toast = document.getElementById("toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "toast";
        toast.className = "toast";
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2500);
}

/* ---- Utilitaires ---- */
function getInitials(firstName, lastName) {
    return ((firstName?.[0] ?? "") + (lastName?.[0] ?? "")).toUpperCase() || "?";
}

function formatTime(isoString) {
    if (!isoString) return "—";
    const d = new Date(isoString);
    return `${d.getHours().toString().padStart(2,"0")}:${d.getMinutes().toString().padStart(2,"0")}`;
}
