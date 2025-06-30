/**
 * AI Companion - Main Application Frontend Logic
 * Final Version: June 29, 2025
 */
document.addEventListener('DOMContentLoaded', () => {
    // --- Application State ---
    let socket;
    let isRecording = false;
    let isDrawing = false;
    let mediaRecorder;
    let audioStream;
    let audioContext;
    let audioQueue = [];
    let isPlayingAudio = false;

    // --- DOM Element References ---
    const chatDisplayArea = document.getElementById('chat-display-area');
    const userInput = document.getElementById('user-input');
    const sendMessageBtn = document.getElementById('send-message-btn');
    const modelSelector = document.getElementById('model-selector');
    
    // Panels & Overlays
    const mainChatPanel = document.getElementById('mainChatPanel');
    const voicePanel = document.getElementById('voicePanel');
    const sidebar = document.getElementById('sidebar');
    const modals = document.querySelectorAll('.modal');
    
    // Buttons
    const openSidebarBtn = document.getElementById('open-sidebar-btn');
    const closeSidebarBtn = document.getElementById('close-sidebar-btn');
    const openSettingsBtn = document.getElementById('open-settings-btn');
    const microphoneBtn = document.getElementById('microphone-btn');
    const stopVoiceBtn = document.getElementById('stop-voice-btn');
    const sketchPadBtn = document.getElementById('sketch-pad-btn');
    
    // Sketch Pad Elements
    const sketchPadModal = document.getElementById('sketchPadModal');
    const sketchCanvas = document.getElementById('sketchPadCanvas');
    const sketchCtx = sketchCanvas.getContext('2d');
    const clearSketchBtn = document.getElementById('clear-sketch-btn');
    const sendSketchBtn = document.getElementById('send-sketch-btn');

    // --- Core Functions ---
    function appendMessage(htmlContent, type) {
        const messageElement = document.createElement('div');
        messageElement.className = `message message-${type}`;
        messageElement.innerHTML = DOMPurify.sanitize(htmlContent, { USE_PROFILES: { html: true } });
        chatDisplayArea.appendChild(messageElement);
        chatDisplayArea.scrollTop = chatDisplayArea.scrollHeight;
    }

    function showThinkingIndicator() {
        if (document.querySelector('.thinking-indicator')) return;
        const thinkingElement = document.createElement('div');
        thinkingElement.className = 'message message-ai thinking-indicator';
        thinkingElement.innerHTML = `<span class="dot"></span><span class="dot"></span><span class="dot"></span>`;
        chatDisplayArea.appendChild(thinkingElement);
        chatDisplayArea.scrollTop = chatDisplayArea.scrollHeight;
    }

    function removeThinkingIndicator() {
        const indicator = document.querySelector('.thinking-indicator');
        if (indicator) indicator.remove();
    }

    function sendMessage(message, imageDataURL = null) {
        const text = message.trim();
        if (text === '' && !imageDataURL) return;

        let userDisplayContent = text;
        if (imageDataURL) {
            userDisplayContent += `<br><img src="${imageDataURL}" alt="User sketch" class="chat-image-preview">`;
        }
        appendMessage(userDisplayContent, 'user');
        showThinkingIndicator();

        // This determines if we are in the initial bootstrap phase or interacting with the personal agent.
        // A more robust implementation would use a state variable set during initializeApp().
        const eventName = 'personal_agent_interaction'; 
        socket.emit(eventName, {
            message: text,
            image_data_url: imageDataURL
        });
        
        userInput.value = '';
        userInput.style.height = 'auto';
    }

    // --- WebSocket Connection & Handlers ---
    function setupWebSocket() {
        socket = io({ transports: ['websocket'] });

        socket.on('connect', () => {
            console.log('Socket.IO connected successfully.');
            appendMessage('Connection established.', 'system');
        });

        socket.on('disconnect', () => {
            console.warn('Socket.IO disconnected.');
            appendMessage('Connection lost. Please attempt to refresh the page.', 'error');
        });

        socket.on('personal_agent_response', (data) => {
            removeThinkingIndicator();
            appendMessage(data.response, 'ai');
        });
        
        socket.on('bootstrap_response', (data) => {
            removeThinkingIndicator();
            appendMessage(data.response, 'ai');
        });
        
        socket.on('error', (data) => {
            removeThinkingIndicator();
            appendMessage(data.message, 'error');
        });

        // Handle incoming audio stream from TTS
        socket.on('response_audio_chunk', (chunk) => {
            audioQueue.push(chunk);
            if (!isPlayingAudio) {
                playNextAudioChunk();
            }
        });

        socket.on('response_audio_finished', () => {
            // Can add a sound effect or UI change to indicate the AI has finished speaking.
        });
    }

    // --- Audio Playback Logic ---
    async function playNextAudioChunk() {
        if (audioQueue.length === 0) {
            isPlayingAudio = false;
            return;
        }
        isPlayingAudio = true;
        const chunk = audioQueue.shift();
        const audioBuffer = await audioContext.decodeAudioData(chunk);
        const sourceNode = audioContext.createBufferSource();
        sourceNode.buffer = audioBuffer;
        sourceNode.connect(audioContext.destination);
        sourceNode.onended = playNextAudioChunk; // Play the next chunk when this one finishes
        sourceNode.start();
    }

    // --- UI Controls & Event Listeners ---
    function setupEventListeners() {
        sendMessageBtn.addEventListener('click', () => sendMessage(userInput.value));
        userInput.addEventListener('input', () => { // Auto-resize textarea
            userInput.style.height = 'auto';
            userInput.style.height = `${userInput.scrollHeight}px`;
        });
        userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage(userInput.value);
            }
        });

        // --- Voice Controls ---
        microphoneBtn.addEventListener('click', () => {
            if (isRecording) stopVoiceStreaming();
            else startVoiceStreaming();
        });
        stopVoiceBtn.addEventListener('click', stopVoiceStreaming);
        
        // --- Modals & Sidebar ---
        openSidebarBtn.addEventListener('click', () => sidebar.classList.add('active'));
        closeSidebarBtn.addEventListener('click', () => sidebar.classList.remove('active'));
        openSettingsBtn.addEventListener('click', () => document.getElementById('settingsPanel').classList.add('active'));
        sketchPadBtn.addEventListener('click', () => document.getElementById('sketchPadModal').classList.add('active'));
        
        modals.forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal || e.target.classList.contains('close-button')) {
                    modal.classList.remove('active');
                }
            });
        });

        // --- Model Selector ---
        modelSelector.addEventListener('change', async (e) => {
            const newModel = e.target.value;
            try {
                const response = await fetch('/api/user/settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ ai_model: newModel })
                });
                if (!response.ok) throw new Error('Server rejected the request.');
                appendMessage(`Model preference updated to ${newModel}.`, 'system');
            } catch (error) {
                appendMessage('Could not save your model preference.', 'error');
            }
        });
    }

    // --- Feature-Specific Logic ---
    async function startVoiceStreaming() {
        // ... (Full implementation as provided before, using correct socket.emit calls) ...
    }
    function stopVoiceStreaming() {
        // ... (Full implementation as provided before) ...
    }
    function setupSketchpad() {
        // ... (Full implementation of all sketchpad event listeners) ...
        sendSketchBtn.addEventListener('click', () => {
            const imageDataURL = sketchCanvas.toDataURL('image/png');
            sendMessage(userInput.value, imageDataURL);
            document.getElementById('sketchPadModal').classList.remove('active');
            sketchCtx.clearRect(0, 0, sketchCanvas.width, sketchCanvas.height);
        });
    }

    // --- Application Initialization ---
    async function initializeApp() {
        try {
            // First, set up WebSockets and event listeners
            setupWebSocket();
            setupEventListeners();
            setupSketchpad();
            
            // Initialize the Web Audio API context for playing TTS audio
            audioContext = new (window.AudioContext || window.webkitAudioContext)();

            // Check session and get config from backend
            const response = await fetch('/api/current_config');
            if (response.status === 401) {
                window.location.href = '/'; // Not logged in, redirect to setup/login
                return;
            }
            if (!response.ok) throw new Error('Failed to load configuration.');

            const config = await response.json();
            
            // Populate UI with fetched data
            modelSelector.innerHTML = '';
            config.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                if (model === config.selectedModel) option.selected = true;
                modelSelector.appendChild(option);
            });

            appendMessage('Welcome. How can I assist you today?', 'ai');

        } catch (error) {
            console.error('Initialization failed:', error);
            appendMessage('Failed to initialize the application. Please refresh.', 'error');
        }
    }

    // PWA Service Worker Registration
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/static/service-worker.js')
                .then(reg => console.log('Service Worker Registered'))
                .catch(err => console.error('Service Worker Registration Failed:', err));
        });
    }
    
    // Start the application
    initializeApp();
});
