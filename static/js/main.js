// Main application initialization
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Initialize app state first
        await initializeAppState();
        
        // Initialize components in order
        await initializeAIAssistant();
        initializeFileHandlers();
        initializeSharing();
        
        console.log('Application initialized successfully');
    } catch (error) {
        console.error('Error during application initialization:', error);
        showError('Failed to initialize application. Please refresh the page.');
    }
});

// Global state management with error handling and retry logic
async function initializeAppState(retryCount = 0) {
    try {
        window.appState = {
            currentData: null,
            charts: {},
            statistics: null,
            initialized: false,
            retryAttempts: 0
        };

        // Initialize charts after state is ready
        await initializeCharts();
        window.appState.initialized = true;

    } catch (error) {
        console.error('Failed to initialize app state:', error);
        if (retryCount < 3) {
            console.log(`Retrying initialization (attempt ${retryCount + 1})...`);
            await new Promise(resolve => setTimeout(resolve, 1000));
            return initializeAppState(retryCount + 1);
        }
        throw error;
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
            this.subscribers[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event subscriber for ${event}:`, error);
                }
            });
        }
    }
};

function initializeSharing() {
    const shareButton = document.getElementById('shareAnalysis');
    if (!shareButton) return;

    shareButton.addEventListener('click', async () => {
        try {
            if (!window.appState || !window.appState.currentData) {
                showError('Please upload and analyze data before sharing.');
                return;
            }

            const title = prompt('Enter a title for this analysis:', 'My Data Analysis');
            if (!title) return;

            const description = prompt('Enter a description (optional):', '');
            const isPublic = confirm('Make this analysis public? Click Cancel for private sharing.');
            const password = !isPublic ? prompt('Enter a password for private sharing (optional):') : null;

            const response = await fetch('/share', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title,
                    description,
                    data: window.appState.currentData,
                    is_public: isPublic,
                    password: password
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to share analysis');
            }

            const result = await response.json();
            showShareSuccess(result.url);
        } catch (error) {
            console.error('Error sharing analysis:', error);
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
    input.addEventListener('click', async () => {
        try {
            input.select();
            await navigator.clipboard.writeText(input.value);
            input.setSelectionRange(0, 99999);
            
            const copyConfirm = document.createElement('div');
            copyConfirm.className = 'alert alert-info position-fixed bottom-0 start-50 translate-middle-x mb-3';
            copyConfirm.style.zIndex = '1051';
            copyConfirm.textContent = 'Link copied to clipboard!';
            document.body.appendChild(copyConfirm);
            
            setTimeout(() => copyConfirm.remove(), 2000);
        } catch (error) {
            console.error('Error copying to clipboard:', error);
            showError('Failed to copy link to clipboard');
        }
    });

    // Auto-remove after 10 seconds
    setTimeout(() => {
        alertDiv.remove();
    }, 10000);
}

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
