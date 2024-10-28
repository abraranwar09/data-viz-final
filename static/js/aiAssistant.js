// Initialize marked library for markdown rendering
marked.setOptions({
    breaks: true,
    gfm: true,
    tables: true,
    smartLists: true,
    smartypants: true
});

function initializeAIAssistant() {
    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupAIAssistant);
    } else {
        setupAIAssistant();
    }
}

function setupAIAssistant() {
    let aiContainer = document.querySelector('.ai-container');
    if (!aiContainer) {
        console.error('AI container not found');
        return;
    }

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
                        </div>
                    </div>
                </div>
            </div>
            <div class="loading-indicator d-none">
                <div class="loading-bar"></div>
                <div class="loading-bar"></div>
                <div class="loading-bar"></div>
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

    // Verify all required elements exist
    const elements = {
        askButton: document.getElementById('askAI'),
        questionInput: document.getElementById('aiQuestion'),
        chatMessages: document.getElementById('chatMessages'),
        loadingIndicator: document.querySelector('.loading-indicator')
    };

    // Check if all required elements exist
    const missingElements = Object.entries(elements)
        .filter(([_, element]) => !element)
        .map(([name]) => name);

    if (missingElements.length > 0) {
        console.error('Missing required elements:', missingElements);
        return;
    }

    // Add keyboard event listener for Enter key
    elements.questionInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            console.log('Enter key pressed');
            if (!elements.questionInput.disabled) {
                await handleAIQuestion();
            }
        }
    });

    // Add click event listener for ask button
    elements.askButton.addEventListener('click', async () => {
        console.log('Ask button clicked');
        if (!elements.askButton.disabled) {
            await handleAIQuestion();
        }
    });

    // Add initial message if data is loaded
    if (window.appState?.currentData) {
        addMessage('system', 'Data loaded successfully. How can I help you analyze it?');
    }
}

async function handleAIQuestion() {
    const elements = {
        askButton: document.getElementById('askAI'),
        questionInput: document.getElementById('aiQuestion'),
        chatMessages: document.getElementById('chatMessages'),
        loadingIndicator: document.querySelector('.loading-indicator')
    };

    if (!elements.loadingIndicator) {
        console.error('Loading indicator not found');
        return;
    }

    const question = elements.questionInput.value.trim();
    if (!question) return;

    try {
        // Disable input and button while processing
        elements.questionInput.disabled = true;
        elements.askButton.disabled = true;

        // Show loading indicator
        elements.loadingIndicator.classList.remove('d-none');

        // Add user message
        addMessage('user', question);

        // Check if data is loaded
        if (!window.appState?.currentData) {
            throw new Error('Please upload some data first.');
        }

        const response = await fetch('/ai/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: question,
                context: {
                    data: window.appState.currentData
                }
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to get AI response');
        }

        const result = await response.json();

        if (result?.response?.answer) {
            const answer = result.response.answer;
            
            // Handle visualization in the response
            if (answer.includes('```echarts')) {
                const vizConfig = extractVisualizationConfig(answer);
                if (vizConfig) {
                    await updateVisualizations([vizConfig]);
                }
                
                // Remove the raw echarts config from the display
                const cleanAnswer = answer.replace(/```echarts[\s\S]*?```/g, 
                    '*Visualization generated based on your request*');
                addMessage('assistant', cleanAnswer);
            } else {
                addMessage('assistant', answer);
            }

            // Clear input after successful response
            elements.questionInput.value = '';
        } else {
            throw new Error('Invalid response format');
        }
    } catch (error) {
        console.error('AI Error:', error);
        addMessage('error', `Error: ${error.message}`);
    } finally {
        // Re-enable input and button
        elements.questionInput.disabled = false;
        elements.askButton.disabled = false;
        
        // Hide loading indicator
        elements.loadingIndicator.classList.add('d-none');
        scrollToBottom();
    }
}

function addMessage(type, content) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        console.error('Chat messages container not found');
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${type}`;
    
    let icon = type === 'user' ? 'bi-person-circle' : 
               type === 'error' ? 'bi-exclamation-triangle' : 
               'bi-robot';
    
    let renderedContent = type === 'user' ? content : marked.parse(content);
    
    messageDiv.innerHTML = `
        <div class="d-flex align-items-start">
            <div class="me-2">
                <i class="bi ${icon} fs-4"></i>
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

function extractVisualizationConfig(message) {
    const matches = message.match(/```echarts\n([\s\S]*?)\n```/);
    if (matches && matches[1]) {
        try {
            return JSON.parse(matches[1]);
        } catch (e) {
            console.error('Failed to parse visualization config:', e);
            return null;
        }
    }
    return null;
}
