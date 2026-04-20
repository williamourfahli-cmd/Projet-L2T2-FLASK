(function () {

    /* ============================================================
       1. RÉCUPÉRATION DES DONNÉES INITIALES INJECTÉES PAR FLASK
    ============================================================ */

    // Élément HTML caché contenant les tableaux JSON
    const dataEl = document.getElementById("resultsPageData");

    // Si on n'est pas en mode courbe, on quitte le script
    if (!dataEl) return;

    /**
     * Lit une valeur JSON stockée dans un attribut data-*
     * puis la convertit en tableau JavaScript.
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

    // Données initiales envoyées par Flask
    let engagementLabels = readJsonData("data-engagement-labels");
    let engagementValues = readJsonData("data-engagement-values");
    let emotionLabels = readJsonData("data-emotion-labels");
    let emotionValues = readJsonData("data-emotion-values");

    /* ============================================================
       2. RÉCUPÉRATION DE L'ID SESSION DEPUIS L'URL
    ============================================================ */

    // Exemple d'URL :
    // /session/13/results
    const pathParts = window.location.pathname.split("/");
    const sessionId = pathParts[2];

    if (!sessionId) {
        console.warn("Session ID introuvable dans l'URL");
        return;
    }

    /* ============================================================
       3. VARIABLES GLOBALES DES GRAPHIQUES
    ============================================================ */

    let engagementChart = null;
    let emotionChart = null;

    /* ============================================================
       4. FONCTION DE CRÉATION / MISE À JOUR DU GRAPHIQUE COURBE
    ============================================================ */

    function renderEngagementChart(labels, values) {
        const engagementCanvas = document.getElementById("engagementChart");
        if (!engagementCanvas) return;

        // Si le graphique existe déjà, on le détruit avant recréation
        if (engagementChart) {
            engagementChart.destroy();
        }

        engagementChart = new Chart(engagementCanvas, {
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
       5. FONCTION DE CRÉATION / MISE À JOUR DU GRAPHIQUE BARRES
    ============================================================ */

    function renderEmotionChart(labels, values) {
        const emotionCanvas = document.getElementById("emotionChart");
        if (!emotionCanvas) return;

        // Si le graphique existe déjà, on le détruit avant recréation
        if (emotionChart) {
            emotionChart.destroy();
        }

        emotionChart = new Chart(emotionCanvas, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Nombre d'occurrences",
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
                        borderWidth: 1.5,
                        borderRadius: 10
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
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
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: "#94a3b8",
                            precision: 0
                        },
                        grid: {
                            color: "rgba(255,255,255,0.06)"
                        }
                    }
                }
            }
        });
    }

    /* ============================================================
       6. MISE À JOUR DES CARTES DE STATS
    ============================================================ */

    function updateStatsCards(data) {
        const statValues = document.querySelectorAll(".stat-value");

        // Ordre actuel dans le HTML :
        // 0 = participants
        // 1 = qcm_count
        // 2 = webcam_count
        // 3 = statut
        if (statValues.length >= 4) {
            statValues[0].innerText = data.participants_count;
            statValues[1].innerText = data.qcm_count;
            statValues[2].innerText = data.webcam_count;
            statValues[3].innerText = data.session_is_active ? "En cours" : "Terminée";
        }
    }

    /* ============================================================
       7. CHARGEMENT DES DONNÉES DEPUIS LA ROUTE JSON
    ============================================================ */

    async function refreshResultsData() {
        try {
            const response = await fetch(`/session/${sessionId}/results/data`);

            if (!response.ok) {
                throw new Error("Erreur lors du chargement des résultats");
            }

            const data = await response.json();

            if (!data.ok) {
                console.warn("Réponse JSON invalide");
                return;
            }

            // Mise à jour des tableaux en mémoire
            engagementLabels = data.engagement_labels || [];
            engagementValues = data.engagement_values || [];
            emotionLabels = data.emotion_labels || [];
            emotionValues = data.emotion_values || [];

            // Mise à jour des graphiques
            renderEngagementChart(engagementLabels, engagementValues);
            renderEmotionChart(emotionLabels, emotionValues);

            // Mise à jour des cartes statistiques
            updateStatsCards(data);

        } catch (e) {
            console.warn("Impossible de rafraîchir les résultats", e);
        }
    }

    /* ============================================================
       8. INITIALISATION
    ============================================================ */

    // Premier affichage immédiat avec les données injectées par Flask
    renderEngagementChart(engagementLabels, engagementValues);
    renderEmotionChart(emotionLabels, emotionValues);

    // Rafraîchissement automatique toutes les 10 secondes
    setInterval(refreshResultsData, 10000);

})();
