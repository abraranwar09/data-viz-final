// Initialize marked library for markdown rendering
marked.setOptions({
    breaks: true,
    gfm: true,
    tables: true,
    smartLists: true,
    smartypants: true
});

function initializeAIAssistant() {
    const aiContainer = document.querySelector('.ai-container');
    if (!aiContainer) return;

    // Create chat container structure
    aiContainer.innerHTML = `
        <div class="chat-container">
            <div class="chat-messages" id="chatMessages"></div>
            <div class="chat-input">
                <div class="input-group">
                    <textarea class="form-control" id="aiQuestion" 
                            placeholder="Ask a question about your data..."
                            rows="2"></textarea>
                    <button class="btn btn-primary" type="button" id="askAI">
                        <i class="bi bi-send me-1"></i>Ask
                    </button>
                </div>
            </div>
        </div>
    `;

    const askButton = document.getElementById('askAI');
    const questionInput = document.getElementById('aiQuestion');
    const chatMessages = document.getElementById('chatMessages');

    // Add keyboard event listener for Enter key
    questionInput.addEventListener('keypress', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            await handleAIQuestion();
        }
    });

    askButton.addEventListener('click', handleAIQuestion);

    // Initialize loading indicator
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'loading-indicator d-none';
    loadingIndicator.innerHTML = `
        <div class="loading-bar"></div>
        <div class="loading-bar"></div>
        <div class="loading-bar"></div>
        <div class="loading-bar"></div>
        <div class="loading-bar"></div>
    `;
    chatMessages.appendChild(loadingIndicator);
}

async function handleAIQuestion() {
    const questionInput = document.getElementById('aiQuestion');
    const chatMessages = document.getElementById('chatMessages');
    const loadingIndicator = document.querySelector('.loading-indicator');
    const question = questionInput.value.trim();
    
    if (!question) return;

    try {
        // Add user message
        addMessage('user', question);

        // Show loading indicator
        loadingIndicator.classList.remove('d-none');

        const response = await askAIQuestion(question);
        addMessage('assistant', response.response.answer);

        // Clear input after successful response
        questionInput.value = '';

        // Scroll to bottom
        scrollToBottom();
    } catch (error) {
        console.error('AI Error:', error);
        addMessage('error', `Error: ${error.message}`);
    } finally {
        // Hide loading indicator
        loadingIndicator.classList.add('d-none');
    }
}

function addMessage(type, content) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    
    const renderedContent = type === 'user' ? content : marked.parse(content);
    
    messageDiv.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="me-2">
                <i class="bi ${type === 'user' ? 'bi-person-circle' : 'bi-robot'} fs-4"></i>
            </div>
            <div class="message-content flex-grow-1">
                ${renderedContent}
            </div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function askAIQuestion(question) {
    const context = {
        data: window.appState?.currentData,
        question: question
    };

    const response = await fetch('/ai/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            question: question,
            context: context
        })
    });

    if (!response.ok) throw new Error('Failed to get AI response');
    return await response.json();
}
