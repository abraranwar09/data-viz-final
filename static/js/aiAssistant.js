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
    // First find or create the AI container
    let aiContainer = document.querySelector('.ai-container');
    if (!aiContainer) {
        console.log('Creating new AI container');
        aiContainer = document.createElement('div');
        aiContainer.className = 'ai-container';
        // Append to a known parent element - adjust this selector as needed
        const mainContent = document.querySelector('#mainContent') || document.body;
        mainContent.appendChild(aiContainer);
    }

    console.log('Setting up AI assistant interface');

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

    // Verify elements exist after creation
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
        console.error('Failed to initialize AI assistant elements:', missingElements);
        return;
    }

    console.log('Setting up event listeners');

    // Add keyboard event listener for Enter key
    elements.questionInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            console.log('Enter key pressed');
            if (!elements.questionInput.disabled) {
                setTimeout(async () => {
                    await handleAIQuestion();
                }, 0);
            }
        }
    });

    // Add click event listener for ask button
    elements.askButton.addEventListener('click', async () => {
        console.log('Ask button clicked');
        if (!elements.askButton.disabled) {
            setTimeout(async () => {
                await handleAIQuestion();
            }, 0);
        }
    });

    // Add initial message if data is loaded
    if (window.appState?.currentData) {
        addMessage('system', 'Data loaded successfully. How can I help you analyze it?');
    }

    console.log('AI assistant initialization complete');
}

async function handleAIQuestion() {
    console.log('Handling AI question');
    
    // Get elements
    const questionInput = document.getElementById('aiQuestion');
    const chatMessages = document.getElementById('chatMessages');
    const loadingIndicator = document.querySelector('.loading-indicator');
    const askButton = document.getElementById('askAI');

    // Verify all elements exist
    if (!questionInput || !chatMessages || !loadingIndicator || !askButton) {
        console.error('Missing required elements:', {
            questionInput: !!questionInput,
            chatMessages: !!chatMessages,
            loadingIndicator: !!loadingIndicator,
            askButton: !!askButton
        });
        return;
    }

    const question = questionInput.value.trim();
    if (!question) {
        console.log('Empty question, ignoring');
        return;
    }

    try {
        // Disable input and button while processing
        questionInput.disabled = true;
        askButton.disabled = true;

        // Show loading indicator
        loadingIndicator.classList.remove('d-none');

        // Add user message
        addMessage('user', question);

        // Check if data is loaded
        if (!window.appState?.currentData) {
            throw new Error('Please upload some data first.');
        }

        console.log('Sending request to server');
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
        console.log('Received response:', result);

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
            questionInput.value = '';
        } else {
            throw new Error('Invalid response format');
        }
        
    } catch (error) {
        console.error('AI Error:', error);
        addMessage('error', `Error: ${error.message}`);
    } finally {
        // Re-enable input and button
        questionInput.disabled = false;
        askButton.disabled = false;
        
        // Hide loading indicator
        loadingIndicator.classList.add('d-none');
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

// Add helper function to extract visualization config
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
