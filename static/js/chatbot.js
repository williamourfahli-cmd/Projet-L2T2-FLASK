/**
 * EMOTRACK CHATBOT CORE JS
 * Total Rebuild with Word-by-Word Streaming Effect
 */

const chatbotToggler = document.querySelector(".chatbot-toggler");
const closeBtn = document.querySelector(".close-btn");
const chatbox = document.querySelector(".chatbox");
const chatInput = document.querySelector(".chat-input textarea");
const sendChatBtn = document.querySelector("#send-btn");

let userMessage = null;
let chatHistory = [];
const typingSpeed = 40; // Vitesse en ms entre chaque mot

/**
 * Crée un élément de message (bulle)
 */
const createChatLi = (message, className) => {
    const chatLi = document.createElement("li");
    chatLi.classList.add("chat", className);
    
    // Structure interne : on met un conteneur vide pour la réponse
    let content = className === "outgoing" 
        ? `<p>${message}</p>` 
        : `<p><span class="typing-indicator"><span></span><span></span><span></span></span></p>`;
    
    chatLi.innerHTML = content;
    return chatLi;
};

/**
 * Simule un "thread.sleep" asynchrone
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Affiche le texte mot par mot (Streaming effect)
 */
const streamText = async (element, fullText) => {
    element.innerHTML = ""; // On enlève l'indicateur de frappe
    
    // Découpage par mots pour l'effet fluide
    const words = fullText.split(" ");
    let currentText = "";

    for (const word of words) {
        currentText += word + " ";
        // Rendu Markdown partiel via marked.js
        element.innerHTML = marked.parse(currentText);
        
        // Auto-scroll pendant que ça écrit
        chatbox.scrollTo({ top: chatbox.scrollHeight, behavior: 'smooth' });
        
        // Délai "Thread.sleep"
        await sleep(typingSpeed);
    }
};

/**
 * Appelle l'API Groq et gère la réponse
 */
const generateResponse = async (incomingChatLi) => {
    const messageElement = incomingChatLi.querySelector("p");

    try {
        const response = await fetch("/chatbot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: userMessage,
                history: chatHistory
            })
        });

        const data = await response.json();

        if (data.error) {
            messageElement.classList.add("error");
            messageElement.textContent = data.error;
        } else {
            // Effet de streaming mot par mot
            await streamText(messageElement, data.reply);
            
            // Sauvegarde dans l'historique local
            chatHistory.push({ role: "user", content: userMessage });
            chatHistory.push({ role: "assistant", content: data.reply });
        }
    } catch (error) {
        messageElement.classList.add("error");
        messageElement.textContent = "Désolé, une erreur de connexion est survenue.";
    } finally {
        chatbox.scrollTo(0, chatbox.scrollHeight);
    }
};

/**
 * Gère l'envoi d'un message
 */
const handleChat = () => {
    userMessage = chatInput.value.trim();
    if (!userMessage) return;

    // Reset input
    chatInput.value = "";
    chatInput.style.height = "auto";

    // Afficher message utilisateur
    chatbox.appendChild(createChatLi(userMessage, "outgoing"));
    chatbox.scrollTo(0, chatbox.scrollHeight);

    // Préparer la réponse (avec indicateur de frappe)
    setTimeout(() => {
        const incomingChatLi = createChatLi("...", "incoming");
        chatbox.appendChild(incomingChatLi);
        chatbox.scrollTo(0, chatbox.scrollHeight);
        generateResponse(incomingChatLi);
    }, 500);
};

// Auto-resize textarea
chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = `${chatInput.scrollHeight}px`;
});

// Touche Entrée pour envoyer
chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && window.innerWidth > 800) {
        e.preventDefault();
        handleChat();
    }
});

// Événements boutons
sendChatBtn.addEventListener("click", handleChat);
closeBtn.addEventListener("click", () => document.body.classList.remove("show-chatbot"));
chatbotToggler.addEventListener("click", () => document.body.classList.toggle("show-chatbot"));
