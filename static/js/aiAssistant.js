function initializeAIAssistant() {
    const askButton = document.getElementById('askAI');
    const questionInput = document.getElementById('aiQuestion');
    const responseDiv = document.getElementById('aiResponse');

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
    responseDiv.parentNode.insertBefore(loadingIndicator, responseDiv);
}

async function handleAIQuestion() {
    const questionInput = document.getElementById('aiQuestion');
    const responseDiv = document.getElementById('aiResponse');
    const loadingIndicator = document.querySelector('.loading-indicator');
    const question = questionInput.value.trim();
    
    if (!question) return;

    try {
        // Show loading indicator
        loadingIndicator.classList.remove('d-none');
        responseDiv.style.opacity = '0.5';

        const response = await askAIQuestion(question);
        displayAIResponse(response);
    } catch (error) {
        console.error('AI Error:', error);
        responseDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                Error: ${error.message}
            </div>
        `;
    } finally {
        // Hide loading indicator
        loadingIndicator.classList.add('d-none');
        responseDiv.style.opacity = '1';
    }
}

async function askAIQuestion(question) {
    const context = {
        data: appState.currentData,
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

function displayAIResponse(response) {
    const responseDiv = document.getElementById('aiResponse');
    const questionInput = document.getElementById('aiQuestion');
    
    responseDiv.innerHTML = `
        <div class="card border-0 bg-transparent">
            <div class="card-body p-0">
                <h6 class="card-subtitle mb-3 text-muted">
                    <i class="bi bi-robot me-2"></i>AI Response
                </h6>
                <p class="card-text">${response.response.answer}</p>
                <div class="text-muted small mt-3">
                    <i class="bi bi-info-circle me-1"></i>
                    Confidence: ${(response.response.confidence * 100).toFixed(1)}%
                </div>
            </div>
        </div>
    `;

    // Clear input after successful response
    questionInput.value = '';
}
