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
    if (!aiContainer) {
        console.error('AI container not found');
        return;
    }

    // Create chat container with loading indicator
    aiContainer.innerHTML = `
        <div class="chat-container">
            <div class="chat-messages" id="chatMessages">
                <div class="message message-system">
                    <div class="d-flex align-items-start">
                        <div class="me-2">
                            <i class="bi bi-robot fs-4"></i>
                        </div>
                        <div class="message-content flex-grow-1">
                            Hello! I'm your AI assistant. I can help you analyze your data and create visualizations.
                            Try asking me questions about your data or request specific visualizations.
                        </div>
                    </div>
                </div>
                <div class="loading-indicator d-none">
                    <div class="loading-bar"></div>
                    <div class="loading-bar"></div>
                    <div class="loading-bar"></div>
                </div>
            </div>
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

    if (!askButton || !questionInput) {
        console.error('Required AI assistant elements not found');
        return;
    }

    // Add keyboard event listener for Enter key
    questionInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            console.log('Enter key pressed, handling question');
            const button = document.getElementById('askAI');
            if (button) button.disabled = true;
            await handleAIQuestion();
            if (button) button.disabled = false;
        }
    });

    // Add click event listener for ask button
    askButton.addEventListener('click', async () => {
        console.log('Ask button clicked, handling question');
        askButton.disabled = true;
        await handleAIQuestion();
        askButton.disabled = false;
    });

    // Add initial message if data is loaded
    if (window.appState?.currentData) {
        addMessage('system', 'Data loaded successfully. How can I help you analyze it?');
    }
}

async function handleAIQuestion() {
    const questionInput = document.getElementById('aiQuestion');
    const chatMessages = document.getElementById('chatMessages');
    const loadingIndicator = document.querySelector('.loading-indicator');

    if (!questionInput || !chatMessages || !loadingIndicator) {
        console.error('Required AI assistant elements not found');
        return;
    }

    const question = questionInput.value.trim();
    if (!question) {
        console.log('Empty question, ignoring');
        return;
    }

    try {
        console.log('Processing question:', question);
        
        // Add user message
        addMessage('user', question);

        // Show loading indicator
        loadingIndicator.classList.remove('d-none');

        // Check if data is loaded
        if (!window.appState?.currentData) {
            throw new Error('Please upload some data first.');
        }

        console.log('Sending request to server');
        const response = await askAIQuestion(question);
        console.log('Received response:', response);

        if (response && response.response) {
            // Handle visualization in the response
            const answer = response.response.answer;
            addMessage('assistant', answer);

            // Check if response contains visualization
            if (answer.includes('```echarts') || answer.includes('visualization generated')) {
                // Trigger visualization update
                await updateVisualizations(window.appState.currentData);
            }
        } else {
            throw new Error('Invalid response format');
        }

        // Clear input after successful response
        questionInput.value = '';
    } catch (error) {
        console.error('AI Error:', error);
        addMessage('error', `Error: ${error.message}`);
    } finally {
        // Hide loading indicator
        if (loadingIndicator) {
            loadingIndicator.classList.add('d-none');
        }
        scrollToBottom();
    }
}

function addMessage(type, content) {
    console.log(`Adding ${type} message:`, content);
    
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        console.error('Chat messages container not found');
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    
    const renderedContent = type === 'user' ? content : marked.parse(content);
    
    messageDiv.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="me-2">
                <i class="bi ${type === 'user' ? 'bi-person-circle' : type === 'error' ? 'bi-exclamation-triangle' : 'bi-robot'} fs-4"></i>
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
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

async function askAIQuestion(question) {
    console.log('Sending AI request:', question);
    
    try {
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

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to get AI response');
        }
        
        const result = await response.json();
        console.log('AI response:', result);
        return result;
    } catch (error) {
        console.error('AI request failed:', error);
        throw new Error(`AI request failed: ${error.message}`);
    }
}
