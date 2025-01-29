/**
 * AI Assistant Module
 * 
 * This module implements SOLID principles in the following ways:
 * 
 * Single Responsibility Principle (SRP):
 * - The module handles only AI-related interactions and processing
 * - Each component (chat, visualization, data processing) has a single responsibility
 * - Message handling and UI updates are separated
 * 
 * Open/Closed Principle (OCP):
 * - New AI capabilities can be added without modifying existing functionality
 * - Message handling can be extended for new types of interactions
 * - Visualization generation is extensible for new chart types
 * 
 * Liskov Substitution Principle (LSP):
 * - All AI response handlers follow the same interface
 * - Message processors are interchangeable
 * - Visualization generators maintain consistent behavior
 * 
 * Interface Segregation Principle (ISP):
 * - AI capabilities are separated into specific interfaces
 * - Message handling is divided by message type
 * - UI components are isolated from AI processing logic
 * 
 * Dependency Inversion Principle (DIP):
 * - The module depends on abstractions for AI processing
 * - Message handling is independent of specific AI implementations
 * - Visualization generation is decoupled from specific chart libraries
 */

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
        const context = {
            question,
            data: window.appState.currentData,
            column_stats: window.appState.currentData.column_stats || {},
            processed_data: {
                preview: window.appState.currentData.preview || [],
                column_stats: window.appState.currentData.column_stats || {},
                categorical: {},
                numeric: {},
                raw_data: window.appState.currentData.preview || []
            }
        };

        // Send request to server
        const response = await fetch('/ai/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(context)
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const result = await response.json();
        
        // Add AI response message
        if (result.message) {
            addMessage('assistant', result.message);
        }
        
        // Handle visualizations from SmartVis
        if (result.visualizations && result.visualizations.length > 0) {
            console.log('Received SmartVis visualizations:', result.visualizations);
            // Update visualizations using the existing visualization system
            await updateVisualizations(result.visualizations);
        }

        // Clear input and restore UI
        elements.questionInput.value = '';
        
    } catch (error) {
        console.error('Error:', error);
        addMessage('error', `Error: ${error.message}`);
    } finally {
        // Reset UI state
        elements.questionInput.disabled = false;
        elements.askButton.disabled = false;
        elements.thinkingDots.classList.add('d-none');
        elements.questionInput.focus();
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
    const regex = /```(?:echarts|json)\n([\s\S]*?)```/g;
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
        
        // Handle both direct visualization configs and analysis requests
        if (Array.isArray(response)) {
            configs = response;
        } else if (typeof response === 'object') {
            if (response.success === false) {
                throw new Error(response.error || 'Visualization generation failed');
            }
            if (response.visualizations) {
                configs = response.visualizations;
            }
        }
        
        if (!configs || configs.length === 0) {
            console.warn('No valid visualization configs found in response');
            return false;
        }
        
        // Enhanced data population and validation
        const currentData = window.appState.currentData;  // Get the current data
        const dataPopulatedConfigs = configs.map(config => {
            try {
                // Deep clone to avoid modifying original
                config = JSON.parse(JSON.stringify(config));
                
                // Handle dataset source population
                if (config.dataset && config.dataset.variable) {
                    const values = currentData.preview.map(row => row[config.dataset.variable]);
                    config.dataset.source = values.filter(v => v != null);
                }
                
                // Handle series data population
                if (config.series) {
                    config.series = config.series.map(series => {
                        // Handle direct variable reference
                        if (series.variable) {
                            const values = currentData.preview.map(row => row[series.variable]);
                            series.data = values.filter(v => v != null);
                        }
                        
                        // Handle mapping data from variables
                        if (series.mapping) {
                            const { x, y, category } = series.mapping;
                            const mappedData = currentData.preview.map(row => {
                                const point = {};
                                if (x) point.value = [row[x], row[y]];
                                if (category) point.category = row[category];
                                return point;
                            }).filter(point => {
                                return point.value ? !point.value.some(v => v == null) : true;
                            });
                            series.data = mappedData;
                        }
                        
                        return series;
                    });
                }
                
                return config;
            } catch (error) {
                console.error('Error populating data for config:', error);
                return null;
            }
        }).filter(config => config !== null);  // Remove any failed configs
        
        if (dataPopulatedConfigs.length > 0) {
            console.log('Rendering data-populated configs:', dataPopulatedConfigs);
            await updateVisualizations(dataPopulatedConfigs);
            return true;
        }
        
        return false;
    } catch (error) {
        console.error('Error handling visualization response:', error);
        showError(error.message);
        return false;
    }
}

// Add function to extract visualization config from markdown
function extractVisualizationConfig(markdown) {
    try {
        const configs = [];
        const configBlocks = markdown.match(/```(?:echarts|json)\n([\s\S]*?)```/g) || [];
        
        for (const block of configBlocks) {
            const content = block.replace(/```(?:echarts|json)\n([\s\S]*?)```/, '$1');
            try {
                const config = JSON.parse(content);
                configs.push(config);
            } catch (e) {
                console.error('Error parsing config block:', e);
            }
        }
        
        return configs;
    } catch (error) {
        console.error('Error extracting visualization config:', error);
        return [];
    }
}

// Add function to validate visualization config
function isValidVisualizationConfig(config) {
    if (!config || typeof config !== 'object') return false;
    
    // Must have either series or dataset
    if (!config.series && !config.dataset) return false;
    
    // If has series, must be array
    if (config.series && !Array.isArray(config.series)) return false;
    
    // Each series must have type and data/source
    if (config.series) {
        return config.series.every(series => 
            series.type && (series.data || series.source)
        );
    }
    
    return true;
}

/**
 * Message Processing System
 * 
 * SRP: Handles only message processing and routing
 * ISP: Message handlers are separated by type
 * DIP: Processing is independent of message source
 */

/**
 * AI Response Handler
 * 
 * SRP: Responsible only for processing AI responses
 * OCP: Can be extended for new response types
 * LSP: All response handlers follow the same pattern
 */

/**
 * Visualization Request Handler
 * 
 * SRP: Handles only visualization-related requests
 * ISP: Separated from other AI capabilities
 * DIP: Independent of specific visualization implementations
 */

/**
 * UI Management System
 * 
 * SRP: Handles only UI updates and interactions
 * ISP: UI components are separated by function
 * DIP: UI logic is independent of backend processing
 */

/**
 * Data Context Management
 * 
 * SRP: Manages only data context for AI processing
 * OCP: Extensible for new types of context
 * LSP: All context handlers follow the same pattern
 */
