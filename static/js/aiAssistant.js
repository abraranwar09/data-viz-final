// Initialize marked library for markdown rendering
marked.setOptions({
    breaks: true,
    gfm: true,
    tables: true,
    smartLists: true,
    smartypants: true
});

function initializeAIAssistant() {
    return new Promise((resolve) => {
        // Wait for DOM to be fully loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => setupAIAssistant().then(resolve));
        } else {
            setupAIAssistant().then(resolve);
        }
    });
}

async function setupAIAssistant() {
    console.log('Setting up AI assistant');
    
    // Find the sidebar first
    const sidebar = document.querySelector('.ai-sidebar');
    if (!sidebar) {
        console.error('AI sidebar not found');
        return;
    }

    // Simplified chat container structure with a guaranteed working loading indicator
    sidebar.innerHTML = `
        <div class="ai-sidebar-header d-flex justify-content-between align-items-center">
            <h5 class="mb-0">
                <i class="bi bi-robot me-2"></i>AI Assistant
                <span class="thinking-dots d-none">
                    <span>.</span><span>.</span><span>.</span>
                </span>
            </h5>
            <button class="btn btn-link d-lg-none" id="closeAiSidebar">
                <i class="bi bi-x-lg"></i>
            </button>
        </div>
        <div class="ai-container">
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
        </div>
    `;

    // Update element references
    const elements = {
        askButton: document.getElementById('askAI'),
        questionInput: document.getElementById('aiQuestion'),
        chatMessages: document.getElementById('chatMessages'),
        thinkingDots: document.querySelector('.thinking-dots')
    };

    // Check if all required elements exist
    const missingElements = Object.entries(elements)
        .filter(([_, element]) => !element)
        .map(([name]) => name);

    if (missingElements.length > 0) {
        console.error('Failed to initialize AI assistant elements:', missingElements);
        return;
    }

    // Add keyboard event listener for Enter key
    elements.questionInput.addEventListener('keydown', async (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            console.log('Enter key pressed');
            await handleAIQuestion();
        }
    });

    // Add click event listener for ask button
    elements.askButton.addEventListener('click', async () => {
        console.log('Ask button clicked');
        await handleAIQuestion();
    });

    // Add initial message if data is loaded
    if (window.appState?.currentData) {
        addMessage('system', 'Data loaded successfully. How can I help you analyze it?');
    }

    console.log('AI assistant initialization complete');
}

async function handleAIQuestion() {
    console.log('Handling AI question');
    
    // Get elements with error checking
    const elements = {
        questionInput: document.getElementById('aiQuestion'),
        chatMessages: document.getElementById('chatMessages'),
        askButton: document.getElementById('askAI'),
        thinkingDots: document.querySelector('.thinking-dots')
    };

    // Verify all elements exist
    for (const [name, element] of Object.entries(elements)) {
        if (!element) {
            console.error(`Required element not found: ${name}`);
            addMessage('error', 'Chat interface error. Please refresh the page.');
            return;
        }
    }

    const question = elements.questionInput.value.trim();
    if (!question) {
        console.log('Empty question, ignoring');
        return;
    }

    try {
        // Show thinking animation
        elements.questionInput.disabled = true;
        elements.askButton.disabled = true;
        elements.thinkingDots.classList.remove('d-none');

        // Add user message
        addMessage('user', question);

        // Check if data is loaded
        if (!window.appState?.currentData) {
            addMessage('system', 'Please upload some data first before asking questions.');
            return;
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
            throw new Error(`Server error: ${response.status}`);
        }

        const result = await response.json();
        console.log('Raw AI Response:', result);

        // Extract answer and visualizations, with detailed logging
        const answer = result?.response?.response?.answer || result?.response?.answer;
        const visualizations = result?.response?.response?.visualizations || result?.response?.visualizations;
        
        console.log('Extracted Answer:', answer);
        console.log('Extracted Visualizations:', visualizations);

        if (answer) {
            addMessage('assistant', answer);
            
            // Handle visualizations with explicit type checking
            if (visualizations) {
                console.log('Visualization Type:', typeof visualizations);
                console.log('Visualization Structure:', JSON.stringify(visualizations, null, 2));
                
                // Ensure visualizations is an array
                const vizArray = Array.isArray(visualizations) ? visualizations : [visualizations];
                
                // Validate each visualization config
                const validConfigs = vizArray.filter(config => {
                    if (!config || typeof config !== 'object') {
                        console.error('Invalid config format:', config);
                        return false;
                    }
                    if (!config.series || !Array.isArray(config.series)) {
                        console.error('Missing or invalid series:', config);
                        return false;
                    }
                    return true;
                });

                if (validConfigs.length > 0) {
                    console.log('Valid visualization configs:', validConfigs);
                    await updateVisualizations(validConfigs);
                } else {
                    console.error('No valid visualization configs found');
                }
            }
            
            elements.questionInput.value = '';
        } else {
            throw new Error('Invalid response format');
        }

    } catch (error) {
        console.error('AI Error:', error);
        addMessage('error', `Error: ${error.message}`);
    } finally {
        elements.questionInput.disabled = false;
        elements.askButton.disabled = false;
        elements.thinkingDots.classList.add('d-none');
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
    
    // Check for visualization configs in the message
    if (type === 'assistant' && (content.includes('```echarts') || content.includes('```json'))) {
        // Extract all visualization configs
        const vizConfigs = [];
        const regex = /```echarts\n([\s\S]*?)\n```/g;
        let match;
        
        // Find all visualization configs in the message
        while ((match = regex.exec(content)) !== null) {
            try {
                const config = JSON.parse(match[1]);
                
                // Validate the config has necessary data
                if (isValidVisualizationConfig(config)) {
                    vizConfigs.push(config);
                } else {
                    console.warn('Invalid visualization config:', config);
                }
            } catch (e) {
                console.error('Failed to parse visualization config:', e);
            }
        }

        // Remove the raw configs from the message
        content = content.replace(/```echarts[\s\S]*?```/g, '');

        // Update visualizations if we found any valid configs
        if (vizConfigs.length > 0) {
            console.log(`Found ${vizConfigs.length} valid visualizations`);
            updateVisualizations(vizConfigs);
        }
    }
    
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

function isValidVisualizationConfig(config) {
    // Basic structure validation
    if (!config || typeof config !== 'object') return false;
    
    // Allow any valid ECharts configuration
    // Must have at least one series
    if (!config.series || !Array.isArray(config.series) || config.series.length === 0) return false;
    
    // Each series must have a type
    for (const series of config.series) {
        if (!series.type) return false;
    }
    
    return true;
}

function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Add helper function to extract visualization config
function extractVisualizationConfig(message) {
    const configs = [];
    const regex = /```(?:echarts|json)\n([\s\S]*?)\n```/g;
    let match;
    
    while ((match = regex.exec(message)) !== null) {
        try {
            const config = JSON.parse(match[1]);
            if (isValidVisualizationConfig(config)) {
                configs.push(config);
            }
        } catch (e) {
            console.error('Failed to parse visualization config:', e);
        }
    }
    return configs;
}

async function handleVisualizationResponse(response) {
    console.log('Processing visualization response:', response);
    
    try {
        let configs = [];
        
        // Handle both direct visualization configs and markdown-embedded configs
        if (Array.isArray(response)) {
            configs = response;
        } else if (typeof response === 'string' && (response.includes('```echarts') || response.includes('```json'))) {
            configs = extractVisualizationConfig(response);
        }
        
        // Validate and clean up configs
        configs = configs.filter(config => {
            try {
                return isValidVisualizationConfig(config);
            } catch (e) {
                console.error('Invalid visualization config:', e);
                return false;
            }
        });
        
        if (configs.length > 0) {
            console.log('Rendering visualizations:', configs);
            await updateVisualizations(configs);
            return true;
        }
        
        return false;
    } catch (error) {
        console.error('Error processing visualization response:', error);
        return false;
    }
}
