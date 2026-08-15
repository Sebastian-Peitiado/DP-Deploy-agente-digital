document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');

    // Historial local de conversación
    let chatHistory = [];

    // Determinar la URL del API Backend (relativa si es el mismo servidor o localhost si es dev)
    const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://localhost:8000'
        : '';

    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        sendMessage(message);
        userInput.value = '';
    });

    window.sendQuickQuery = function(text) {
        sendMessage(text);
    };

    async function sendMessage(messageText) {
        // Renderizar mensaje del usuario
        appendMessage('user', messageText);

        // Ocultar pills de sugerencia al iniciar conversación activa
        const quickSuggestions = document.getElementById('quick-suggestions');
        if (quickSuggestions) {
            quickSuggestions.style.display = 'none';
        }

        // Mostrar indicador de carga/escritura
        const loadingMessageId = appendLoadingIndicator();

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: messageText,
                    history: chatHistory
                })
            });

            removeLoadingIndicator(loadingMessageId);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error en el servidor');
            }

            const data = await response.json();
            const botReply = data.response;

            // Actualizar el historial
            chatHistory.push({ role: 'user', content: messageText });
            chatHistory.push({ role: 'assistant', content: botReply });

            // Renderizar respuesta del bot con marcado Markdown
            appendMessage('bot', botReply);

        } catch (error) {
            removeLoadingIndicator(loadingMessageId);
            appendMessage('bot', `⚠️ **Ocurrió un error:** ${error.message}. Por favor, verifica la conexión o inténtalo nuevamente.`);
        }
    }

    function appendMessage(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', `${sender}-message`);

        const avatar = document.createElement('div');
        avatar.classList.add('avatar');
        avatar.textContent = sender === 'user' ? '👤' : '🏛️';

        const bubble = document.createElement('div');
        bubble.classList.add('bubble');

        if (sender === 'bot') {
            // Utilizar Marked.js para renderizar respuestas con Markdown y enlaces
            if (typeof marked !== 'undefined') {
                bubble.innerHTML = marked.parse(text);
                
                // Asegurar que los enlaces se abran en nueva pestaña
                const links = bubble.querySelectorAll('a');
                links.forEach(link => {
                    link.setAttribute('target', '_blank');
                    link.setAttribute('rel', 'noopener noreferrer');
                });
            } else {
                bubble.textContent = text;
            }
        } else {
            bubble.textContent = text;
        }

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(bubble);

        chatMessages.appendChild(msgDiv);
        scrollToBottom();
    }

    function appendLoadingIndicator() {
        const id = 'loading-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', 'bot-message');
        msgDiv.id = id;

        const avatar = document.createElement('div');
        avatar.classList.add('avatar');
        avatar.textContent = '🏛️';

        const bubble = document.createElement('div');
        bubble.classList.add('bubble');
        bubble.innerHTML = `
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;

        msgDiv.appendChild(avatar);
        msgDiv.appendChild(bubble);

        chatMessages.appendChild(msgDiv);
        scrollToBottom();
        return id;
    }

    function removeLoadingIndicator(id) {
        const el = document.getElementById(id);
        if (el) {
            el.remove();
        }
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
