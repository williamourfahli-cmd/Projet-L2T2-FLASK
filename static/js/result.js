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
       3. RÉFÉRENCES DES GRAPHIQUES
    ============================================================ */

    let engagementChart = null;
    let qcmEmotionChart = null;
    let webcamEmotionChart = null;

    /* ============================================================
       4. COURBE PRINCIPALE D'ENGAGEMENT
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
       5. DONUT DES ÉMOTIONS QCM
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
       6. DONUT DES ÉMOTIONS DEEPFACE
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
       7. MISE À JOUR DES CARTES STATS
    ============================================================ */

   function updateStatsCards(data) {
    // On récupère précisément chaque élément par son ID
    const pCount = document.getElementById("count-participants");
    const qCount = document.getElementById("count-qcm");
    const wCount = document.getElementById("count-webcam");
    const aCount = document.getElementById("count-active");

    // On met à jour les textes seulement si les éléments existent
    if (pCount) pCount.innerText = data.participants_count || 0;
    if (qCount) qCount.innerText = data.qcm_count || 0;
    if (wCount) wCount.innerText = data.webcam_count || 0;
    if (aCount) aCount.innerText = data.active_participants_count || 0;
}
    /* ============================================================
       8. RAFRAÎCHISSEMENT DES DONNÉES DEPUIS LE BACKEND
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

        } catch (e) {
            console.warn("Impossible de rafraîchir les résultats", e);
        }
    }

    /* ============================================================
       9. INITIALISATION
    ============================================================ */

    // Premier rendu immédiat
    renderEngagementChart(engagementLabels, engagementValues);
    renderQcmEmotionChart(qcmEmotionLabels, qcmEmotionValues);
    renderWebcamEmotionChart(webcamEmotionLabels, webcamEmotionValues);

    // Rafraîchissement automatique toutes les 10 secondes
    setInterval(refreshResultsData, 10000);

})();
