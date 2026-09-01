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
    let sessionId = null;
    const welcomeScreen = document.getElementById('welcome-screen');
    const chatScreen = document.getElementById('chat-screen');
    const btnLoginSession = document.getElementById('btn-login-session');
    const btnNewChat = document.getElementById('btn-new-chat');
    const inputLoginSession = document.getElementById('login-session-id');
    const generateSessionCheckbox = document.getElementById('generate-session-checkbox');

    // Mostrar siempre el welcome screen al cargar
    if (welcomeScreen && chatScreen) {
        welcomeScreen.style.display = 'flex';
        chatScreen.style.display = 'none';
    }

    function showChatScreen() {
        welcomeScreen.style.display = 'none';
        chatScreen.style.display = 'flex';
        if (userInput) userInput.focus();
    }

    function showWelcomeScreen() {
        welcomeScreen.style.display = 'flex';
        chatScreen.style.display = 'none';
        chatHistory = [];
        sessionId = null;
        resetChatUI();
    }

    // Login Flow
    if (btnLoginSession) {
        btnLoginSession.addEventListener('click', async () => {
            const id = inputLoginSession.value.trim();
            if (!id) {
                alert('Por favor, ingresá un Session ID válido.');
                return;
            }

            try {
                const response = await fetch(`${API_BASE_URL}/api/history/${id}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.history && data.history.length > 0) {
                        sessionId = id;
                        chatHistory = data.history;
                        
                        // Renderizar
                        resetChatUI(false);
                        const quickSuggestions = document.getElementById('quick-suggestions');
                        if (quickSuggestions) quickSuggestions.style.display = 'none';

                        data.history.forEach(msg => {
                            appendMessage(msg.role === 'user' ? 'user' : 'bot', msg.content);
                        });
                        showChatScreen();
                    } else {
                        alert('No se encontró historial para ese Session ID.');
                    }
                } else {
                    alert('Error al buscar el Session ID.');
                }
            } catch (e) {
                console.warn('No se pudo cargar el historial:', e);
                alert('Error de conexión.');
            }
        });
    }

    // New Chat Flow
    if (btnNewChat) {
        btnNewChat.addEventListener('click', () => {
            chatHistory = [];
            if (generateSessionCheckbox.checked) {
                sessionId = 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
                resetChatUI(true, sessionId);
            } else {
                sessionId = null;
                resetChatUI(true);
            }
            showChatScreen();
        });
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            showWelcomeScreen();
        });
    }

    function resetChatUI(isNew = true, newSessionId = null) {
        chatMessages.innerHTML = '';
        if (isNew) {
            let sessionMessage = newSessionId 
                ? `<p style="margin-top: 10px; padding: 8px; background: rgba(0, 163, 224, 0.1); border-radius: 6px; border: 1px solid rgba(0, 163, 224, 0.3); font-size: 12px;">Tu Session ID para retomar este chat en el futuro es:<br><strong style="color: #38BDF8; font-size: 14px; user-select: all;">${newSessionId}</strong></p>`
                : '';

            chatMessages.innerHTML = `
                <div class="message bot-message">
                    <div class="avatar">🏛️</div>
                    <div class="bubble">
                        <p><strong>¡Hola! Soy UBA Orienta.</strong></p>
                        <p>Te ayudo con preguntas frecuentes sobre inscripciones, CBC, UBA XXI, SIU Guaraní, facultades y trámites oficiales.</p>
                        ${sessionMessage}
                    </div>
                </div>
                <div class="quick-suggestions" id="quick-suggestions">
                    <button class="pill-btn" onclick="sendQuickQuery('¿Cómo me inscribo al CBC?')">📝 Inscripción CBC</button>
                    <button class="pill-btn" onclick="sendQuickQuery('¿Dónde legalizar el título secundario?')">📜 Legalizar Título</button>
                    <button class="pill-btn" onclick="sendQuickQuery('¿Cómo ingresar al SIU Guaraní?')">🎓 SIU Guaraní</button>
                    <button class="pill-btn" onclick="sendQuickQuery('Inscripción a materias UBA XXI')">💻 Cursar UBA XXI</button>
                </div>
            `;
        }
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
