(function () {

    /* ============================================================
       1. RÉCUPÉRATION DES DONNÉES INJECTÉES PAR FLASK
    ============================================================ */

    const dataEl = document.getElementById("resultsPageData");

    // Si l'élément n'existe pas, on quitte
    if (!dataEl) return;

    /**
     * Lit une valeur JSON stockée dans un attribut data-*
     * et la convertit en tableau JavaScript.
     */
    function readJsonData(attrName) {
        const raw = dataEl.getAttribute(attrName);

        if (!raw) return [];

        try {
            return JSON.parse(raw);
        } catch (e) {
            console.warn("Impossible de parser", attrName, e);
            return [];
        }
    }

    // Données initiales
    let engagementLabels = readJsonData("data-engagement-labels");
    let engagementValues = readJsonData("data-engagement-values");

    let qcmEmotionLabels = readJsonData("data-qcm-emotion-labels");
    let qcmEmotionValues = readJsonData("data-qcm-emotion-values");

    let webcamEmotionLabels = readJsonData("data-webcam-emotion-labels");
    let webcamEmotionValues = readJsonData("data-webcam-emotion-values");

    /* ============================================================
       2. RÉCUPÉRATION DE L'ID DE SESSION DEPUIS L'URL
    ============================================================ */

    const pathParts = window.location.pathname.split("/");
    const sessionId = pathParts[2];

    if (!sessionId) {
        console.warn("Session ID introuvable dans l'URL");
        return;
    }
    /* ============================================================
       3. DÉTECTION DES MODES ACTIFS
    ============================================================ */

    // On détecte si le mode alertes est actif côté DOM
    // plutôt que de le lire depuis Flask pour éviter le couplage
    const alertBanner   = document.getElementById("class-alert-banner");
    const popupContainer = document.getElementById("alert-popups-container");
    const alertModeActive = !!alertBanner;
    

    /* ============================================================
       4. RÉFÉRENCES DES GRAPHIQUES
    ============================================================ */

    let engagementChart = null;
    let qcmEmotionChart = null;
    let webcamEmotionChart = null;

    /* ============================================================
       5. MÉMOIRE DES ALERTES INDIVIDUELLES DÉJÀ AFFICHÉES
       Clé : "<user_id>_<source>_<emotion>"
       Réinitialisée si l'étudiant repasse sous le seuil
    ============================================================ */

    const shownAlerts = new Set();

    
    /* ============================================================
       6. COURBE PRINCIPALE D'ENGAGEMENT
    ============================================================ */

    function renderEngagementChart(labels, values) {
        const canvas = document.getElementById("engagementChart");
        if (!canvas) return;

        // Si le graphique existe déjà, on le détruit
        if (engagementChart) {
            engagementChart.destroy();
        }

        engagementChart = new Chart(canvas, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Engagement général",
                        data: values,
                        borderColor: "#8b5cf6",
                        backgroundColor: "rgba(139, 92, 246, 0.18)",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        pointBackgroundColor: "#ec4899",
                        pointBorderColor: "#ffffff",
                        pointBorderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: "index",
                    intersect: false
                },
                plugins: {
                    legend: {
                        labels: {
                            color: "#e2e8f0"
                        }
                    },
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        titleColor: "#ffffff",
                        bodyColor: "#e2e8f0",
                        borderColor: "rgba(255,255,255,0.08)",
                        borderWidth: 1
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: "#94a3b8"
                        },
                        grid: {
                            color: "rgba(255,255,255,0.06)"
                        }
                    },
                    y: {
                        min: 0,
                        max: 100,
                        ticks: {
                            color: "#94a3b8"
                        },
                        grid: {
                            color: "rgba(255,255,255,0.06)"
                        },
                        title: {
                            display: true,
                            text: "Score d'engagement / 100",
                            color: "#e2e8f0"
                        }
                    }
                }
            }
        });
    }

    /* ============================================================
       7. DONUT DES ÉMOTIONS QCM
    ============================================================ */

    function renderQcmEmotionChart(labels, values) {
        const canvas = document.getElementById("qcmEmotionChart");
        if (!canvas) return;

        if (qcmEmotionChart) {
            qcmEmotionChart.destroy();
        }

        qcmEmotionChart = new Chart(canvas, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [
                    {
                        data: values,
                        backgroundColor: [
                            "rgba(34, 197, 94, 0.75)",
                            "rgba(148, 163, 184, 0.75)",
                            "rgba(245, 158, 11, 0.75)",
                            "rgba(236, 72, 153, 0.75)",
                            "rgba(239, 68, 68, 0.75)"
                        ],
                        borderColor: [
                            "rgba(34, 197, 94, 1)",
                            "rgba(148, 163, 184, 1)",
                            "rgba(245, 158, 11, 1)",
                            "rgba(236, 72, 153, 1)",
                            "rgba(239, 68, 68, 1)"
                        ],
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "58%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#e2e8f0",
                            padding: 18
                        }
                    },
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        titleColor: "#ffffff",
                        bodyColor: "#e2e8f0",
                        borderColor: "rgba(255,255,255,0.08)",
                        borderWidth: 1
                    }
                }
            }
        });
    }

    /* ============================================================
       8. DONUT DES ÉMOTIONS DEEPFACE
    ============================================================ */

    function renderWebcamEmotionChart(labels, values) {
        const canvas = document.getElementById("webcamEmotionChart");
        if (!canvas) return;

        if (webcamEmotionChart) {
            webcamEmotionChart.destroy();
        }

        webcamEmotionChart = new Chart(canvas, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [
                    {
                        data: values,
                        backgroundColor: [
                            "rgba(34, 197, 94, 0.75)",
                            "rgba(148, 163, 184, 0.75)",
                            "rgba(99, 102, 241, 0.75)",
                            "rgba(245, 158, 11, 0.75)",
                            "rgba(59, 130, 246, 0.75)",
                            "rgba(239, 68, 68, 0.75)",
                            "rgba(168, 85, 247, 0.75)"
                        ],
                        borderColor: [
                            "rgba(34, 197, 94, 1)",
                            "rgba(148, 163, 184, 1)",
                            "rgba(99, 102, 241, 1)",
                            "rgba(245, 158, 11, 1)",
                            "rgba(59, 130, 246, 1)",
                            "rgba(239, 68, 68, 1)",
                            "rgba(168, 85, 247, 1)"
                        ],
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "58%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            color: "#e2e8f0",
                            padding: 18
                        }
                    },
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        titleColor: "#ffffff",
                        bodyColor: "#e2e8f0",
                        borderColor: "rgba(255,255,255,0.08)",
                        borderWidth: 1
                    }
                }
            }
        });
    }

    /* ============================================================
       9. MISE À JOUR DES CARTES STATS
    ============================================================ */
   function updateStatsCards(data) {
       
        const statValues = document.querySelectorAll(".stat-value");
        // Ordre des cartes dans le HTML :
        // 0 = participants
        // 1 = participants actifs
        // 2 = QCM
        // 3 = webcam
        if (statValues.length >= 4) {
            statValues[0].innerText = data.participants_count;
            statValues[1].innerText = data.active_participants_count || 0;
            statValues[2].innerText = data.webcam_count;
            statValues[3].innerText = data.session_is_active ? "En cours" : "Terminée";

        }

    } 
    /* ============================================================
       10. RAFRAÎCHISSEMENT DES DONNÉES DEPUIS LE BACKEND
    ============================================================ */

    async function refreshResultsData() {
        try {
            const response = await fetch(`/session/${sessionId}/results/data`);

            if (!response.ok) {
                throw new Error("Erreur lors du chargement des résultats");
            }

            const data = await response.json();

            if (!data.ok) {
                return;
            }

            // Mise à jour des variables mémoire
            engagementLabels = data.engagement_labels || [];
            engagementValues = data.engagement_values || [];

            qcmEmotionLabels = data.qcm_emotion_labels || [];
            qcmEmotionValues = data.qcm_emotion_values || [];

            webcamEmotionLabels = data.webcam_emotion_labels || [];
            webcamEmotionValues = data.webcam_emotion_values || [];

            // Redessin des graphiques
            renderEngagementChart(engagementLabels, engagementValues);
            renderQcmEmotionChart(qcmEmotionLabels, qcmEmotionValues);
            renderWebcamEmotionChart(webcamEmotionLabels, webcamEmotionValues);

            // Mise à jour des cartes
            updateStatsCards(data);

            // Mise à jour des moyennes si le mode est actif
            updateMoyennes(data);

        } catch (e) {
            console.warn("Impossible de rafraîchir les résultats", e);
        }
    }

    /* ============================================================
       11. BANNIÈRE ALERTE DE CLASSE
    ============================================================ */

    function updateClassAlertBanner(alertsData) {
        if (!alertBanner) return;

        if (alertsData && alertsData.class_alert) {
            const reasonEl = document.getElementById("class-alert-reason");
            if (reasonEl) {
                const sources = alertsData.class_sources || [];
                const reasons = [];
                if (sources.includes("class_snapshot")) {
                    reasons.push("plus de 50% de la classe démotivée au dernier QCM");
                }
                if (sources.includes("class_accumulation")) {
                    reasons.push("plus de 40% des étudiants en alerte individuelle");
                }
                reasonEl.innerText = reasons.length ? " — " + reasons.join(" et ") : "";
            }
            alertBanner.style.display = "block";
        } else {
            // Condition non remplie : masquage automatique
            alertBanner.style.display = "none";
        }
    }

    /* ============================================================
       12. POPUP ALERTE INDIVIDUELLE
    ============================================================ */

    function showIndividualAlertPopup(alertInfo) {
        if (!popupContainer) return;

        const name = (alertInfo.first_name && alertInfo.last_name)
            ? `${alertInfo.first_name} ${alertInfo.last_name}`
            : "Étudiant anonyme";

        const now = new Date().toLocaleTimeString("fr-FR", {
            hour: "2-digit", minute: "2-digit"
        });

        const detailLines = (alertInfo.alerts || []).map(a => {
            const src   = a.source === "qcm" ? "QCM" : "Webcam";
            const emo   = a.emotion ? ` · ${a.emotion}` : "";
            const ratio = a.ratio !== null ? ` (${Math.round(a.ratio * 100)}%)` : "";
            return `${src}${emo}${ratio}`;
        });

        const popup = document.createElement("div");
        popup.className = "alert-popup";
        popup.innerHTML = `
            <div class="alert-popup-header">
                <span class="alert-popup-title">⚠ Alerte individuelle</span>
                <button class="alert-popup-close" onclick="this.closest('.alert-popup').remove()">✕</button>
            </div>
            <div class="alert-popup-name">${name}</div>
            <div class="alert-popup-detail">
                ${detailLines.map(l => `<span>${l}</span>`).join("")}
            </div>
            <span class="alert-popup-tag">${now}</span>
        `;

        popupContainer.appendChild(popup);

        // Auto-fermeture après 12 secondes
        setTimeout(() => {
            if (popup.parentNode) {
                popup.style.opacity = "0";
                popup.style.transition = "opacity 0.4s ease";
                setTimeout(() => popup.remove(), 400);
            }
        }, 12000);
    }

    function processIndividualAlerts(alertsData) {
        if (!alertsData) return;

        const individuals = alertsData.individual_alerts || [];

        // Construction des clés actuellement en alerte
        const currentKeys = new Set();

        for (const alertInfo of individuals) {
            const sourcesKey = (alertInfo.alerts || [])
                .map(a => `${a.source}_${a.emotion || ""}`)
                .sort()
                .join("|");
            const key = `${alertInfo.user_id}_${sourcesKey}`;
            currentKeys.add(key);

            if (!shownAlerts.has(key)) {
                shownAlerts.add(key);
                showIndividualAlertPopup(alertInfo);
            }
        }

        // Nettoyage : retire les clés d'étudiants repassés sous le seuil
        // pour qu'ils puissent déclencher une nouvelle popup s'ils y reviennent
        for (const key of shownAlerts) {
            if (!currentKeys.has(key)) {
                shownAlerts.delete(key);
            }
        }
    }


    /* ============================================================
       13. INITIALISATION
    ============================================================ */

    // Premier rendu immédiat
    renderEngagementChart(engagementLabels, engagementValues);
    renderQcmEmotionChart(qcmEmotionLabels, qcmEmotionValues);
    renderWebcamEmotionChart(webcamEmotionLabels, webcamEmotionValues);

    // Rafraîchissement automatique toutes les 10 secondes
    setInterval(refreshResultsData, 10000);

})();
