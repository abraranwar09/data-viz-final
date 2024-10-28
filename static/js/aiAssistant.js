function initializeAIAssistant() {
    const askButton = document.getElementById('askAI');
    const questionInput = document.getElementById('aiQuestion');
    const responseDiv = document.getElementById('aiResponse');

    askButton.addEventListener('click', async () => {
        const question = questionInput.value.trim();
        if (!question) return;

        try {
            const response = await askAIQuestion(question);
            displayAIResponse(response);
        } catch (error) {
            console.error('AI Error:', error);
            responseDiv.innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
        }
    });
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
    responseDiv.innerHTML = `
        <div class="card">
            <div class="card-body">
                <h6 class="card-subtitle mb-2 text-muted">AI Response</h6>
                <p class="card-text">${response.response.answer}</p>
                <div class="text-muted small">
                    Confidence: ${response.response.confidence * 100}%
                </div>
            </div>
        </div>
    `;
}
