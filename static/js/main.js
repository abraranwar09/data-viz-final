// Main application initialization
document.addEventListener('DOMContentLoaded', () => {
    initializeAppState();
    initializeFileHandlers();
    initializeAIAssistant();
    initializeSharing();
    // Initialize charts after DOM is loaded and state is initialized
    if (window.appState) {
        initializeCharts();
    } else {
        console.error('Failed to initialize app state');
    }
});

// Global state management with error handling
function initializeAppState() {
    if (typeof window.appState === 'undefined') {
        window.appState = {
            currentData: null,
            charts: {},
            statistics: null,
            initialized: false
        };
    }
}

// Event bus for component communication
const eventBus = {
    subscribers: {},
    subscribe(event, callback) {
        if (!this.subscribers[event]) {
            this.subscribers[event] = [];
        }
        this.subscribers[event].push(callback);
    },
    publish(event, data) {
        if (this.subscribers[event]) {
            this.subscribers[event].forEach(callback => callback(data));
        }
    }
};

function initializeSharing() {
    const shareButton = document.getElementById('shareAnalysis');
    if (!shareButton) return;

    shareButton.addEventListener('click', async () => {
        if (!window.appState || !window.appState.currentData) {
            showError('Please upload and analyze data before sharing.');
            return;
        }

        const title = prompt('Enter a title for this analysis:', 'My Data Analysis');
        if (!title) return;

        const description = prompt('Enter a description (optional):', '');

        try {
            const response = await fetch('/share', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title,
                    description,
                    data: window.appState.currentData
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to share analysis');
            }

            const result = await response.json();
            showShareSuccess(result.url);
        } catch (error) {
            showError(error.message);
        }
    });
}

function showShareSuccess(url) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
    alertDiv.style.zIndex = '1050';
    alertDiv.innerHTML = `
        <strong>Analysis shared successfully!</strong><br>
        Share this link: <input type="text" value="${url}" class="form-control mt-2" readonly>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);

    // Add click-to-copy functionality
    const input = alertDiv.querySelector('input');
    input.addEventListener('click', () => {
        input.select();
        navigator.clipboard.writeText(input.value);
        input.setSelectionRange(0, 99999);
    });

    // Auto-remove after 10 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 10000);
}

// Error handling utility
function showError(message) {
    const errorAlert = document.getElementById('errorAlert');
    if (errorAlert) {
        errorAlert.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <span>${message}</span>
            </div>
        `;
        errorAlert.classList.remove('d-none');
    } else {
        console.error('Error:', message);
    }
}
