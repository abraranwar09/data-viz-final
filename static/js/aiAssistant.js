async function initializeAIAssistant() {
    console.log('Initializing AI Assistant');
    // Add your initialization logic here
}

function addMessage(sender, message) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) {
        console.error('Chat messages container not found');
        return;
    }

    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    messageElement.textContent = message;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to the bottom
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
        console.log('Received response:', result);

        // Handle the combined response
        if (result?.response?.answer) {
            addMessage('assistant', result.response.answer);
            elements.questionInput.value = '';
        }

        // Update visualizations if present
        if (result?.visualizations) {
            updateVisualizations(result.visualizations);
        }

    } catch (error) {
        console.error('AI Error:', error);
        addMessage('error', `Error: ${error.message}`);
    } finally {
        // Hide thinking animation
        elements.questionInput.disabled = false;
        elements.askButton.disabled = false;
        elements.thinkingDots.classList.add('d-none');
        scrollToBottom();
    }
}
