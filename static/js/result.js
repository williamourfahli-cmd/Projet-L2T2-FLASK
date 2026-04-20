(function () {

    /* ============================================================
       1. RÉCUPÉRATION DES DONNÉES INJECTÉES PAR LE TEMPLATE
    ============================================================ */

    // Élément HTML caché contenant les tableaux JSON
    const dataEl = document.getElementById("resultsPageData");

    // Si l'élément n'existe pas, on arrête le script
    // (par exemple si on affiche un autre mode que "courbe")
    if (!dataEl) return;

    /**
     * Lit une valeur JSON stockée dans un attribut data-*
     * et la convertit en tableau JS.
     *
     * Exemple :
     * data-engagement-labels='["20:10","20:11"]'
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

    // Données pour la courbe d'engagement
    const engagementLabels = readJsonData("data-engagement-labels");
    const engagementValues = readJsonData("data-engagement-values");

    // Données pour l'histogramme émotionnel
    const emotionLabels = readJsonData("data-emotion-labels");
    const emotionValues = readJsonData("data-emotion-values");

    /* ============================================================
       2. CRÉATION DU GRAPHIQUE D'ENGAGEMENT GÉNÉRAL
    ============================================================ */

    // Canvas du graphique de courbe
    const engagementCanvas = document.getElementById("engagementChart");

    // On vérifie qu'il existe bien dans le HTML
    if (engagementCanvas) {
        new Chart(engagementCanvas, {
            type: "line", // type courbe
            data: {
                labels: engagementLabels,
                datasets: [
                    {
                        label: "Engagement général",
                        data: engagementValues,

                        // Couleurs du tracé
                        borderColor: "#8b5cf6",
                        backgroundColor: "rgba(139, 92, 246, 0.18)",

                        // Remplissage sous la courbe
                        fill: true,

                        // Arrondit légèrement la courbe
                        tension: 0.35,

                        // Style des points
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

                // Interaction utilisateur au survol
                interaction: {
                    mode: "index",
                    intersect: false
                },

                plugins: {
                    // Style de la légende
                    legend: {
                        labels: {
                            color: "#e2e8f0"
                        }
                    },

                    // Style des bulles au survol
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        titleColor: "#ffffff",
                        bodyColor: "#e2e8f0",
                        borderColor: "rgba(255,255,255,0.08)",
                        borderWidth: 1
                    }
                },

                // Style des axes
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
       3. CRÉATION DU GRAPHIQUE DE RÉPARTITION ÉMOTIONNELLE
    ============================================================ */

    // Canvas du graphique en bâtons
    const emotionCanvas = document.getElementById("emotionChart");

    // On vérifie qu'il existe bien dans le HTML
    if (emotionCanvas) {
        new Chart(emotionCanvas, {
            type: "bar", // histogramme vertical
            data: {
                labels: emotionLabels,
                datasets: [
                    {
                        label: "Nombre d'occurrences",
                        data: emotionValues,

                        // Couleur de chaque barre
                        backgroundColor: [
                            "rgba(34, 197, 94, 0.75)",   // motivé
                            "rgba(148, 163, 184, 0.75)", // neutre
                            "rgba(245, 158, 11, 0.75)",  // ennuyé
                            "rgba(236, 72, 153, 0.75)",  // stressé
                            "rgba(239, 68, 68, 0.75)"    // démotivé
                        ],

                        // Bordure de chaque barre
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
                    // Style de la légende
                    legend: {
                        labels: {
                            color: "#e2e8f0"
                        }
                    },

                    // Style du tooltip
                    tooltip: {
                        backgroundColor: "rgba(15, 23, 42, 0.95)",
                        titleColor: "#ffffff",
                        bodyColor: "#e2e8f0",
                        borderColor: "rgba(255,255,255,0.08)",
                        borderWidth: 1
                    }
                },

                // Style des axes
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

})();
