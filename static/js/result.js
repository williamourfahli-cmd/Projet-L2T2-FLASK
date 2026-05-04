(function () {

    /* ============================================================
       1. RÉCUPÉRATION DES DONNÉES INJECTÉES PAR FLASK
    ============================================================ */

    // Élément HTML caché contenant les données initiales envoyées par Flask
    const dataEl = document.getElementById("resultsPageData");

    // Élément HTML caché contenant les seuils d'alerte de la session
    const sessionDataEl = document.getElementById("sessionData");

    // Récupère le seuil individuel depuis le HTML, sinon prend 60% par défaut
    const seuilIndividuel = sessionDataEl
        ? parseInt(sessionDataEl.getAttribute("data-seuil-individuel"))
        : 60;

    // Récupère le seuil de classe depuis le HTML, sinon prend 50% par défaut
    const seuilClasse = sessionDataEl
        ? parseInt(sessionDataEl.getAttribute("data-seuil-classe"))
        : 50;

    /**
     * Lit une valeur JSON stockée dans un attribut data-*
     * et la convertit en tableau JavaScript.
     *
     * Exemple :
     * data-engagement-labels='["10:00", "10:01"]'
     * devient ["10:00", "10:01"] côté JavaScript.
     */
    function readJsonData(attrName) {
        // Si l'élément contenant les données n'existe pas, on retourne un tableau vide
        if (!dataEl) return [];

        // Récupère la valeur brute de l'attribut demandé
        const raw = dataEl.getAttribute(attrName);

        // Si l'attribut est absent ou vide, on retourne un tableau vide
        if (!raw) return [];

        try {
            // Convertit la chaîne JSON en vraie valeur JavaScript
            return JSON.parse(raw);
        } catch (e) {
            // En cas de problème de parsing, on évite de casser toute la page
            console.warn("Impossible de parser", attrName, e);
            return [];
        }
    }

    // Données initiales de la courbe d'engagement
    let engagementLabels = readJsonData("data-engagement-labels");
    let engagementValues = readJsonData("data-engagement-values");

    // Données initiales du donut QCM
    let qcmEmotionLabels = readJsonData("data-qcm-emotion-labels");
    let qcmEmotionValues = readJsonData("data-qcm-emotion-values");

    // Données initiales du donut webcam / DeepFace
    let webcamEmotionLabels = readJsonData("data-webcam-emotion-labels");
    let webcamEmotionValues = readJsonData("data-webcam-emotion-values");


    /* ============================================================
       2. RÉCUPÉRATION DE L'ID DE SESSION DEPUIS L'URL
    ============================================================ */

    // Exemple d'URL : /session/12/results
    // Après split("/") : ["", "session", "12", "results"]
    const pathParts = window.location.pathname.split("/");
    const sessionId = pathParts[2];

    // Sans id de session, on ne peut pas appeler la route JSON des résultats
    if (!sessionId) {
        console.warn("Session ID introuvable dans l'URL");
        return;
    }


    /* ============================================================
       3. DÉTECTION DES MODES ACTIFS
    ============================================================ */

    // Si la bannière d'alerte existe dans le DOM, cela signifie que le mode alertes est actif
    const alertBanner = document.getElementById("class-alert-banner");

    // Conteneur dans lequel les popups d'alertes individuelles seront ajoutées
    const popupContainer = document.getElementById("alert-popups-container");

    // Booléen indiquant si le mode alertes est actif
    const alertModeActive = !!alertBanner;

    // Mémorise si le professeur a fermé manuellement la bannière d'alerte de classe
    let bannerDismissed = false;

    // Mémorise l'état précédent de la bannière pour pouvoir la réafficher si l'alerte disparaît puis revient
    let lastBannerState = false;

    // Bouton de fermeture de la bannière d'alerte de classe
    const bannerCloseBtn = document.querySelector(".alert-banner-close");

    if (bannerCloseBtn) {
        bannerCloseBtn.addEventListener("click", () => {
            bannerDismissed = true;
        });
    }


    /* ============================================================
       4. RÉFÉRENCES DES GRAPHIQUES
    ============================================================ */

    // Ces variables stockent les instances Chart.js
    // Elles permettent de détruire un ancien graphique avant d'en recréer un nouveau
    let engagementChart = null;
    let qcmEmotionChart = null;
    let webcamEmotionChart = null;


    /* ===========================================================================================================
       5. MÉMOIRE DES ALERTES INDIVIDUELLES DÉJÀ AFFICHÉES

       shownAlerts est un Set, donc une liste sans doublon.
       Il évite d'afficher plusieurs fois la même popup à chaque rafraîchissement.

       Clé utilisée :
       "<user_id>_<source>_<emotion>"

       La clé est supprimée si l'étudiant repasse sous le seuil,
       ce qui permet de réafficher une popup si l'alerte revient plus tard.
    ============================================================================================================ */

    const shownAlerts = new Set();

    // Exposition volontaire pour pouvoir inspecter ou vider les alertes depuis la console si besoin
    window._shownAlerts = shownAlerts;


    /* ============================================================
       6. COURBE PRINCIPALE D'ENGAGEMENT
    ============================================================ */

    function renderEngagementChart(labels, values) {
        const canvas = document.getElementById("engagementChart");

        // Si le canvas n'existe pas, cela signifie que le mode courbes n'est pas actif
        if (!canvas) return;

        // Si un graphique existe déjà, on le détruit avant d'en créer un nouveau
        if (engagementChart) {
            engagementChart.destroy();
        }

        // Création de la courbe d'engagement avec Chart.js
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

        // Si le canvas n'existe pas, le donut QCM n'est pas affiché sur cette page
        if (!canvas) return;

        // Détruit l'ancien graphique pour éviter les superpositions
        if (qcmEmotionChart) {
            qcmEmotionChart.destroy();
        }

        // Création du donut des émotions déclarées dans les QCM
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

        // Si le canvas n'existe pas, le donut webcam n'est pas affiché
        if (!canvas) return;

        // Détruit l'ancien graphique avant de le reconstruire
        if (webcamEmotionChart) {
            webcamEmotionChart.destroy();
        }

        // Création du donut des émotions détectées par DeepFace
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
        // 2 = réponses QCM
        // 3 = analyses webcam
        if (statValues.length >= 4) {
            statValues[0].innerText = data.participants_count;
            statValues[1].innerText = data.active_participants_count || 0;
            statValues[2].innerText = data.qcm_count || 0;
            statValues[3].innerText = data.webcam_count || 0;
        }
    }


    /* ======================================================================================================================
       10. RAFRAÎCHISSEMENT DES DONNÉES DEPUIS LE BACKEND

       Cette fonction appelle la route Flask :
       /session/<id>/results/data

       Elle récupère les données fraîches et met à jour :
       - les graphiques ;
       - les cartes statistiques ;
       - les moyennes ;
       - les alertes.
    ====================================================================================================================== */

    async function refreshResultsData() {
        try {
            // Appel de la route JSON Flask
            const response = await fetch(`/session/${sessionId}/results/data`);

            // Si Flask renvoie une erreur HTTP, on interrompt le traitement
            if (!response.ok) {
                throw new Error("Erreur lors du chargement des résultats");
            }

            // Conversion de la réponse JSON en objet JavaScript
            const data = await response.json();

            // Si le backend indique que la réponse n'est pas valide, on quitte
            if (!data.ok) {
                return;
            }

            // Mise à jour des variables mémoire pour la courbe
            engagementLabels = data.engagement_labels || [];
            engagementValues = data.engagement_values || [];

            // Mise à jour des données du donut QCM
            qcmEmotionLabels = data.qcm_emotion_labels || [];
            qcmEmotionValues = data.qcm_emotion_values || [];

            // Mise à jour des données du donut webcam
            webcamEmotionLabels = data.webcam_emotion_labels || [];
            webcamEmotionValues = data.webcam_emotion_values || [];

            // Redessine les graphiques avec les nouvelles données
            renderEngagementChart(engagementLabels, engagementValues);
            renderQcmEmotionChart(qcmEmotionLabels, qcmEmotionValues);
            renderWebcamEmotionChart(webcamEmotionLabels, webcamEmotionValues);

            // Met à jour les cartes statistiques
            updateStatsCards(data);

            // Met à jour la section des moyennes si elle existe
            updateMoyennes(data);

            // Met à jour les alertes uniquement si le mode alertes est actif
            if (alertModeActive) {
                updateClassAlertBanner(data.alerts);
                processIndividualAlerts(data.alerts);
            }

        } catch (e) {
            // En cas d'erreur réseau ou JSON, on évite de casser la page
            console.warn("Impossible de rafraîchir les résultats", e);
        }
    }


    /* ==============================================================================================
       11. BANNIÈRE ALERTE DE CLASSE

       Affiche ou masque la bannière rouge selon la valeur class_alert
       renvoyée par le backend.
    ============================================================================================= */

    function updateClassAlertBanner(alertsData) {
        // Si la bannière n'existe pas, le mode alertes n'est pas actif
        if (!alertBanner) return;

        // Convertit l'état d'alerte en booléen
        const isActive = !!(alertsData && alertsData.class_alert);

        // Si l'alerte vient de disparaître, on autorise la bannière à réapparaître plus tard
        if (!isActive && lastBannerState) {
            bannerDismissed = false;
        }

        // Mémorise le dernier état connu
        lastBannerState = isActive;

        if (isActive) {
            const reasonEl = document.getElementById("class-alert-reason");

            if (reasonEl) {
                const sources = alertsData.class_sources || [];
                const reasons = [];

                // Alerte liée au dernier QCM collectif
                if (sources.includes("class_snapshot")) {
                    reasons.push(`plus de ${seuilClasse}% de la classe démotivée au dernier QCM`);
                }

                // Alerte liée à l'accumulation d'étudiants en alerte individuelle
                if (sources.includes("class_accumulation")) {
                    reasons.push(`plus de ${seuilClasse}% des étudiants en alerte individuelle`);
                }

                // Affiche les raisons dans la bannière
                reasonEl.innerText = reasons.length ? " — " + reasons.join(" et ") : "";
            }

            // Affiche la bannière uniquement si le professeur ne l'a pas fermée manuellement
            if (!bannerDismissed) {
                alertBanner.style.display = "block";
            }

        } else {
            // Masque la bannière si aucune alerte de classe n'est active
            alertBanner.style.display = "none";
        }
    }


    /* ============================================================
       12. MISE À JOUR DES MOYENNES ÉMOTIONNELLES

       Le backend renvoie des valeurs internes sans accents :
       - motive
       - stresse
       - negatif

       Cela facilite les calculs côté Python.
       Cette partie JS transforme ensuite ces valeurs en libellés propres :
       - Motivé
       - Stressé
       - Négatif
    ============================================================ */

    /**
     * Convertit une valeur interne en libellé propre pour l'affichage.
     *
     * Exemple :
     * - motive -> Motivé
     * - stresse -> Stressé
     * - negatif -> Négatif
     */
    function displayEmotionLabel(emotion) {
        if (!emotion || emotion === "Aucune donnée") {
            return "Aucune donnée";
        }

        const e = emotion.toLowerCase();

        const labels = {
            // Valeurs QCM internes
            "motive": "Motivé",
            "neutre": "Neutre",
            "ennuye": "Ennuyé",
            "stresse": "Stressé",
            "demotive": "Démotivé",

            // Valeurs DeepFace brutes éventuelles
            "happy": "Joie",
            "neutral": "Neutre",
            "surprise": "Surprise",
            "fear": "Peur",
            "sad": "Tristesse",
            "angry": "Colère",
            "disgust": "Dégoût",

            // Valeurs DeepFace traduites côté backend
            "surpris": "Surpris",
            "triste": "Triste",
            "en colere": "En colère",
            "degoute": "Dégoûté",

            // Tendances communes issues de EMOTION_MAP côté backend
            "positif": "Positif",
            "negatif": "Négatif"
        };

        return labels[e] || emotion;
    }


    /**
     * Retourne une couleur en fonction de l'émotion ou de la tendance.
     *
     * Cette fonction utilise les valeurs internes envoyées par Flask.
     * Elle ne sert pas à afficher le texte, mais seulement à colorer l'interface.
     */
    function emotionColor(emotion) {
        if (!emotion || emotion === "Aucune donnée") return "var(--muted)";

        const e = emotion.toLowerCase();

        // Tendances générales issues de EMOTION_MAP côté backend
        if (e === "positif") return "#22c55e";
        if (e === "neutre") return "#94a3b8";
        if (e === "negatif") return "#ef4444";

        // Valeurs QCM
        if (["demotiv", "démotiv"].some(v => e.includes(v))) return "#ef4444";
        if (["motiv"].some(v => e.includes(v))) return "#22c55e";
        if (["neutre", "neutral"].some(v => e.includes(v))) return "#94a3b8";
        if (["ennuy"].some(v => e.includes(v))) return "#eab308";
        if (["stress"].some(v => e.includes(v))) return "#ec4899";

        // Valeurs DeepFace ou traductions
        if (["joie", "happy"].some(v => e.includes(v))) return "#22c55e";
        if (["surpris", "surprise"].some(v => e.includes(v))) return "#818cf8";
        if (["peur", "fear"].some(v => e.includes(v))) return "#eab308";
        if (["triste", "sad"].some(v => e.includes(v))) return "#60a5fa";
        if (["colere", "angry"].some(v => e.includes(v))) return "#ef4444";
        if (["degout", "disgust"].some(v => e.includes(v))) return "#a855f7";

        return "var(--muted)";
    }


    function updateMoyennes(data) {
        // Si le mode moyennes n'est pas actif, la section est absente du DOM
        const section = document.getElementById("moyennes-section");
        if (!section) return;

        // Récupère les éléments qui affichent les trois moyennes globales
        const subjEl = document.getElementById("avg-subjective");
        const objEl = document.getElementById("avg-objective");
        const genEl = document.getElementById("avg-general");

        // Affiche les moyennes avec un libellé lisible,
        // tout en gardant la valeur brute pour calculer la couleur.
        if (subjEl) {
            subjEl.innerText = displayEmotionLabel(data.moyenne_subjective);
            subjEl.style.color = emotionColor(data.moyenne_subjective);
        }

        if (objEl) {
            objEl.innerText = displayEmotionLabel(data.moyenne_objective);
            objEl.style.color = emotionColor(data.moyenne_objective);
        }

        if (genEl) {
            genEl.innerText = displayEmotionLabel(data.moyenne_generale);
            genEl.style.color = emotionColor(data.moyenne_generale);
        }

        // Récupère le corps du tableau individuel
        const tbody = document.getElementById("tbody-individuals");
        if (!tbody) return;

        // Liste des étudiants envoyée par le backend
        const individuals = data.individuals || [];

        if (individuals.length === 0) {
            // Si aucun étudiant n'est présent, on affiche une ligne vide
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" style="padding:16px; color:var(--muted); text-align:center;">
                        Aucun étudiant connecté
                    </td>
                </tr>
            `;
            return;
        }

        // Génère une ligne HTML par étudiant
        tbody.innerHTML = individuals.map(s => `
            <tr style="border-bottom:1px solid var(--border);">

                <!-- Badge nom ou anonyme -->
                <td style="padding:10px 12px;">
                    <span style="
                        padding:3px 10px;
                        border-radius:20px;
                        font-size:0.8rem;
                        background:${s.anonymous
                            ? "rgba(255,255,255,0.05)"
                            : "rgba(79,70,229,0.2)"};
                        border:1px solid ${s.anonymous
                            ? "rgba(255,255,255,0.1)"
                            : "rgba(79,70,229,0.4)"};
                    ">
                        ${s.anonymous ? "Anonyme" : "👤 " + s.name}
                    </span>
                </td>

                <!-- Émotion dominante QCM uniquement -->
                <td style="padding:10px 12px; color:${emotionColor(s.emotion_qcm)}; font-weight:bold;">
                    ${s.emotion_qcm ? displayEmotionLabel(s.emotion_qcm) : "—"}
                </td>

                <!-- Émotion dominante DeepFace uniquement -->
                <td style="padding:10px 12px; color:${emotionColor(s.emotion_webcam)}; font-weight:bold;">
                    ${s.emotion_webcam ? displayEmotionLabel(s.emotion_webcam) : "—"}
                </td>

                <!-- Tendance dominante toutes sources confondues -->
                <td style="padding:10px 12px; color:${emotionColor(s.emotion_dominante)}; font-weight:bold;">
                    ${s.emotion_dominante ? displayEmotionLabel(s.emotion_dominante) : "—"}
                </td>

                <!-- Nombre de réponses QCM soumises -->
                <td style="padding:10px 12px; color:var(--muted);">
                    ${s.nb_qcm} réponse${s.nb_qcm > 1 ? "s" : ""}
                </td>

                <!-- Nombre d'analyses DeepFace réalisées -->
                <td style="padding:10px 12px; color:var(--muted);">
                    ${s.nb_webcam} analyse${s.nb_webcam > 1 ? "s" : ""}
                </td>

            </tr>
        `).join("");
    }


    /* ====================================================================================================================
       13. POPUP ALERTE INDIVIDUELLE
    ======================================================================================================================== */

    function showIndividualAlertPopup(alertInfo, key) {
        /*
            Crée une popup en bas à droite pour signaler une alerte individuelle.

            La popup contient :
            - le nom de l'étudiant ou "Étudiant anonyme" ;
            - la source de l'alerte ;
            - l'émotion dominante ;
            - le ratio mesuré.

            Elle disparaît automatiquement au bout de 12 secondes.
        */

        if (!popupContainer) return;

        // Affiche le nom si l'étudiant n'est pas anonyme
        const name = (alertInfo.first_name && alertInfo.last_name)
            ? `${alertInfo.first_name} ${alertInfo.last_name}`
            : "Étudiant anonyme";

        // Heure locale affichée dans la popup
        const now = new Date().toLocaleTimeString("fr-FR", {
            hour: "2-digit",
            minute: "2-digit"
        });

        // Prépare une ligne de détail pour chaque alerte de l'étudiant
        const detailLines = (alertInfo.alerts || []).map(a => {
            const src = a.source === "qcm" ? "QCM" : "Webcam";
            const emo = a.emotion ? ` · ${displayEmotionLabel(a.emotion)}` : "";
            const ratio = a.ratio !== null ? ` (${Math.round(a.ratio * 100)}%)` : "";
            return `${src}${emo}${ratio}`;
        });

        // Création de l'élément HTML de la popup
        const popup = document.createElement("div");
        popup.className = "alert-popup";

        // Stocke la clé pour identifier cette alerte
        popup.dataset.alertKey = key;

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

        // Ajoute la popup dans le conteneur prévu
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
        /*
            Parcourt les étudiants en alerte individuelle.

            Objectif :
            - afficher une popup uniquement si elle n'a pas déjà été affichée ;
            - retirer les anciennes clés si l'étudiant repasse sous le seuil.
        */

        if (!alertsData) return;

        const individuals = alertsData.individual_alerts || [];

        // Clés des alertes actuellement actives
        const currentKeys = new Set();

        for (const alertInfo of individuals) {
            // Construit une clé stable à partir des sources et émotions
            const sourcesKey = (alertInfo.alerts || [])
                .map(a => `${a.source}_${a.emotion || ""}`)
                .sort()
                .join("|");

            const key = `${alertInfo.user_id}_${sourcesKey}`;

            currentKeys.add(key);

            // Si cette alerte n'a pas encore été affichée, on crée une popup
            if (!shownAlerts.has(key)) {
                shownAlerts.add(key);
                showIndividualAlertPopup(alertInfo, key);
            }
        }

        // Nettoyage des alertes qui ne sont plus actives
        for (const key of shownAlerts) {
            if (!currentKeys.has(key)) {
                shownAlerts.delete(key);
            }
        }
    }


    /* ============================================================
       14. GESTION DE LA MODALE DES PARTICIPANTS
    ============================================================ */

    const modalParticipants = document.getElementById("active-participants-modal");
    const btnCloseModal = document.getElementById("close-modal");

    // Rend la fonction accessible depuis le onclick du HTML
    window.openParticipantsModal = function () {
        if (modalParticipants) {
            modalParticipants.style.display = "flex";
        }
    };

    // Fermeture de la modale avec le bouton X
    if (btnCloseModal) {
        btnCloseModal.addEventListener("click", () => {
            modalParticipants.style.display = "none";
        });
    }

    // Fermeture de la modale si l'utilisateur clique en dehors du contenu
    window.addEventListener("click", (event) => {
        if (event.target === modalParticipants) {
            modalParticipants.style.display = "none";
        }
    });


    /* ============================================================
       15. INITIALISATION
    ============================================================ */

    // Premier rendu immédiat des graphiques avec les données injectées par Flask
    renderEngagementChart(engagementLabels, engagementValues);
    renderQcmEmotionChart(qcmEmotionLabels, qcmEmotionValues);
    renderWebcamEmotionChart(webcamEmotionLabels, webcamEmotionValues);

    // Premier appel immédiat pour récupérer les données fraîches
    refreshResultsData();

    // Rafraîchissement automatique toutes les 10 secondes
    setInterval(refreshResultsData, 10000);

})();
