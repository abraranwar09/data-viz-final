// Main application initialization
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Initialize app state first
        await initializeAppState();
        
        // Initialize visualization system first
        await initializeCharts();
        
        // Then initialize other components
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
            retryAttempts: 0,
            visualizationSystem: null
        };

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

document.addEventListener('DOMContentLoaded', function() {
    const insights = new StatisticalInsights('statisticalInsights');
    
    // File upload handling
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const errorAlert = document.getElementById('errorAlert');
    const progressBar = document.querySelector('.progress-bar');
    const uploadProgress = document.getElementById('uploadProgress');
    
    function handleFileUpload(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        uploadProgress.classList.remove('d-none');
        progressBar.style.width = '0%';
        errorAlert.classList.add('d-none');
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
       // Process and visualize data
            try {
                processUploadedData(data);
            } catch (error) {
                console.error('Error processing uploaded data:', error);
                showError('Failed to process uploaded data. Please check the file format.');
            }

            // Display statistical insights
            insights.displayInsights(data);

            // Update data preview
            updatePreviewTable(data);

            // Enable share button
            document.getElementById('shareAnalysis').disabled = false;
        })
        .catch(error => {
            errorAlert.textContent = error.message;
            errorAlert.classList.remove('d-none');
        })
        .finally(() => {
            uploadProgress.classList.add('d-none');
        });
    }

    // File drag and drop handling
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        handleFileUpload(file);
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        handleFileUpload(file);
    });

    // View mode switching
    document.getElementById('gridViewBtn').addEventListener('click', () => {
        document.getElementById('visualizationContainer').className = 'visualization-grid';
    });

    document.getElementById('singleViewBtn').addEventListener('click', () => {
        document.getElementById('visualizationContainer').className = 'visualization-single';
    });
});

function processUploadedData(data) {
    try {
        // Validate the structure of the received data
        if (!data || typeof data !== 'object' || !data.preview || !Array.isArray(data.preview) ||
            !data.processed_data || typeof data.processed_data !== 'object' ||
            !data.processed_data.column_stats || typeof data.processed_data.column_stats !== 'object') {
            throw new Error('Invalid data format received from server');
        }

        // Clean up the data structure
        const cleanData = {
            ...data,
            preview: data.preview.map(row => {
                // Ensure each row is an object
                if (typeof row !== 'object' || row === null) {
                    console.warn('Invalid row format. Skipping row:', row);
                    return null;
                }
                // Remove the ```csv wrapper if it exists
                const cleanRow = {};
                Object.entries(row).forEach(([key, value]) => {
                    const cleanKey = key.replace('```csv', '').trim();
                    cleanRow[cleanKey] = value;
                });
                return cleanRow;
            }).filter(row => row !== null), // Filter out any null rows
            column_stats: Object.entries(data.processed_data.column_stats).reduce((acc, [key, value]) => {
                // Ensure the value is an object
                if (typeof value !== 'object' || value === null) {
                    console.warn(`Invalid column_stats format for key: ${key}. Skipping.`);
                    return acc;
                }
                const cleanKey = key.replace('```csv', '').trim();
                acc[cleanKey] = value;
                return acc;
            }, {})
        };

        // Store clean data in app state
        window.appState.currentData = cleanData;

        // Process the cleaned data
        const processedData = processData(cleanData);

        // Check if processedData is valid before proceeding
        if (processedData && typeof processedData === 'object') {
            // Generate visualizations with both processed data and insights
            generateVisualizations({
                processed_data: processedData,
                statistical_insights: data.statistical_insights
            });
        } else {
            throw new Error('Failed to process data into a valid format');
        }
    } catch (error) {
        console.error('Error processing uploaded data:', error);
        showError('Error processing data: ' + error.message);
    }
}
