document.addEventListener('DOMContentLoaded', () => {
    // Elementos del DOM
    const chatPopout = document.getElementById('chat-popout');
    const chatLauncher = document.getElementById('chat-launcher');
    const launcherToggleBtn = document.getElementById('launcher-toggle-btn');
    const closePopoutBtn = document.getElementById('close-popout-btn');
    const launcherBadge = document.getElementById('launcher-badge');
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const newChatBtn = document.getElementById('new-chat-btn');

    // Historial local de conversación
    let chatHistory = [];

    // Determinar la URL del API Backend (relativa si es el mismo servidor o localhost si es dev)
    const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://localhost:8000'
        : '';

    // =========================================================================
    // CONTROL DEL POPOUT (ABRIR / CERRAR)
    // =========================================================================
    function togglePopout() {
        const isOpen = chatPopout.classList.contains('open');
        if (isOpen) {
            closePopout();
        } else {
            openPopout();
        }
    }

    function openPopout() {
        chatPopout.classList.add('open');
        chatPopout.setAttribute('aria-hidden', 'false');
        chatLauncher.classList.add('active');
        
        // Ocultar badge de notificación al abrir
        if (launcherBadge) {
            launcherBadge.style.display = 'none';
        }

        // Auto-focus en el input
        setTimeout(() => {
            if (userInput) userInput.focus();
        }, 200);

        scrollToBottom();
    }

    function closePopout() {
        chatPopout.classList.remove('open');
        chatPopout.setAttribute('aria-hidden', 'true');
        chatLauncher.classList.remove('active');
    }

    if (launcherToggleBtn) {
        launcherToggleBtn.addEventListener('click', togglePopout);
    }

    if (closePopoutBtn) {
        closePopoutBtn.addEventListener('click', closePopout);
    }

    // Permitir cerrar con Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && chatPopout.classList.contains('open')) {
            closePopout();
        }
    });

    window.sendQuickQuery = function(text) {
        sendMessage(text);
    };

    // =========================================================================
    // GESTIÓN DE SESIONES & HISTORIAL
    // =========================================================================
    let sessionId = localStorage.getItem('uba_agent_session_id');
    if (!sessionId) {
        createNewSession();
    } else {
        loadSessionHistory();
    }

    function createNewSession() {
        sessionId = 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
        localStorage.setItem('uba_agent_session_id', sessionId);
        chatHistory = [];
    }

    async function loadSessionHistory() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/history/${sessionId}`);
            if (response.ok) {
                const data = await response.json();
                if (data.history && data.history.length > 0) {
                    chatHistory = data.history;
                    
                    // Ocultar sugerencias si ya hay conversación previa
                    const quickSuggestions = document.getElementById('quick-suggestions');
                    if (quickSuggestions) {
                        quickSuggestions.style.display = 'none';
                    }

                    // Renderizar mensajes del historial
                    data.history.forEach(msg => {
                        appendMessage(msg.role === 'user' ? 'user' : 'bot', msg.content);
                    });
                }
            }
        } catch (e) {
            console.warn('No se pudo cargar el historial previo:', e);
        }
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            createNewSession();
            resetChatUI();
        });
    }

    function resetChatUI() {
        chatMessages.innerHTML = `
            <div class="message bot-message">
                <div class="avatar">🏛️</div>
                <div class="bubble">
                    <p><strong>¡Nueva conversación iniciada!</strong></p>
                    <p>Soy UBA Orienta. ¿En qué tema universitario te puedo orientar hoy?</p>
                </div>
            </div>
            <div class="quick-suggestions" id="quick-suggestions">
                <button class="pill-btn" onclick="sendQuickQuery('¿Cómo me inscribo al CBC y cuál es la web oficial?')">📝 Inscripción CBC</button>
                <button class="pill-btn" onclick="sendQuickQuery('¿Dónde legalizar mi título secundario en TAD-UBA?')">📜 Legalizaciones</button>
                <button class="pill-btn" onclick="sendQuickQuery('¿Cómo accedo al SIU Guaraní?')">🎓 SIU Guaraní</button>
                <button class="pill-btn" onclick="sendQuickQuery('¿Qué diferencia hay entre CBC presencial y UBA XXI?')">💻 CBC vs UBA XXI</button>
            </div>
        `;
        if (userInput) userInput.focus();
    }

    // =========================================================================
    // ENVÍO DE MENSAJES AL BACKEND
    // =========================================================================
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        sendMessage(message);
        userInput.value = '';
    });

    async function sendMessage(messageText) {
        // Renderizar mensaje del usuario
        appendMessage('user', messageText);

        // Ocultar pills de sugerencia
        const quickSuggestions = document.getElementById('quick-suggestions');
        if (quickSuggestions) {
            quickSuggestions.style.display = 'none';
        }

        // Indicador de escritura
        const loadingMessageId = appendLoadingIndicator();

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: messageText,
                    history: chatHistory,
                    session_id: sessionId
                })
            });

            removeLoadingIndicator(loadingMessageId);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Error en el servidor');
            }

            const data = await response.json();
            const botReply = data.response;

            // Actualizar historial
            chatHistory.push({ role: 'user', content: messageText });
            chatHistory.push({ role: 'assistant', content: botReply });

            // Renderizar respuesta
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
            if (typeof marked !== 'undefined') {
                bubble.innerHTML = marked.parse(text);
                
                // Abrir enlaces en nueva pestaña
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
