function initializeFileHandlers() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const progressBar = document.querySelector('.progress-bar');
    const progressDiv = document.getElementById('uploadProgress');
    const errorAlert = document.getElementById('errorAlert');
    const shareButton = document.getElementById('shareAnalysis');

    // Drag and drop handlers
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
        handleFile(file);
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        handleFile(file);
    });
}

async function handleFile(file) {
    console.log('Handling file upload');

    const elements = {
        progressBar: document.querySelector('.progress-bar'),
        errorAlert: document.getElementById('uploadErrorAlert'),
        uploadProgress: document.getElementById('uploadProgress')
    };

    const formData = new FormData();
    formData.append('file', file);

    // Reset error alert and show progress bar
    elements.errorAlert.classList.add('d-none');
    elements.progressBar.style.width = '0%';
    elements.uploadProgress.classList.remove('d-none');

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error('Failed to upload file');
        }

        let data = await response.json();
        data = sanitizeJsonData(data);  // Ensure the data is sanitized

        const analysisResponse = await fetch('/ai/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question: "Perform an initial analysis of this dataset. Create multiple visualizations that best represent the key relationships and patterns in the data. Focus on the most important insights and provide a clear explanation of your findings.",
                context: {
                    data: data,
                    type: 'initial_analysis'
                }
            })
        });

        if (!analysisResponse.ok) {
            throw new Error('Failed to generate initial analysis');
        }

        let result = await analysisResponse.json();
        result = sanitizeJsonData(result);  // Sanitize result before using it

        if (result?.response?.answer) {
            addMessage('assistant', result.response.answer);
        }

    } catch (err) {
        console.error('Error:', err);
        elements.errorAlert.classList.remove('d-none');
        elements.errorAlert.textContent = err.message || 'Failed to process file';
    } finally {
        // Hide progress bar
        elements.uploadProgress.classList.add('d-none');
    }
}

function sanitizeJsonData(data) {
    if (typeof data === 'number') return isNaN(data) ? null : data;
    if (Array.isArray(data)) return data.map(sanitizeJsonData);
    if (typeof data === 'object' && data !== null) {
        return Object.fromEntries(Object.entries(data).map(([k, v]) => [k, sanitizeJsonData(v)]));
    }
    return data;
}

// Initialize file handler elements
const elements = {
    fileInput: document.getElementById('fileInput'),
    uploadButton: document.getElementById('uploadButton'),
    uploadProgress: document.getElementById('uploadProgress'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    uploadErrorAlert: document.getElementById('errorAlert'),
    visualizationContainer: document.getElementById('visualizationContainer')
};

// Function to show error message
function showError(message) {
    let errorAlert = document.getElementById('errorAlert');
    
    // Create error alert if it doesn't exist
    if (!errorAlert) {
        errorAlert = document.createElement('div');
        errorAlert.id = 'errorAlert';
        errorAlert.className = 'alert alert-danger';
        
        // Find a suitable container for the error alert
        const container = document.getElementById('visualizationContainer');
        if (container) {
            container.parentElement.insertBefore(errorAlert, container);
        } else {
            document.body.appendChild(errorAlert);
        }
    }

    errorAlert.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            <span>${message}</span>
        </div>
    `;
    errorAlert.classList.remove('d-none');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorAlert.classList.add('d-none');
    }, 5000);
}

// Function to hide error message
function hideError() {
    const errorAlert = document.getElementById('errorAlert');
    if (errorAlert) {
        errorAlert.classList.add('d-none');
    }
}

// Initialize file upload handler
function initializeFileHandler() {
    // ... rest of the initialization code ...
    
    // Handle file upload
    elements.uploadButton.addEventListener('click', async () => {
        try {
            hideError();
            const file = elements.fileInput.files[0];
            if (!file) {
                showError('Please select a file to upload');
                return;
            }

            // Show progress bar
            elements.uploadProgress.classList.remove('d-none');
            elements.progressBar.style.width = '0%';
            elements.progressText.textContent = '0%';

            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            // Process the uploaded data
            console.log('Handling file upload');
            window.appState.currentData = data;
            processUploadedData(data);

            // Hide progress
            elements.uploadProgress.classList.add('d-none');
            elements.fileInput.value = '';

        } catch (err) {
            console.error('Upload error:', err);
            showError(err.message || 'Failed to process file');
            elements.uploadProgress.classList.add('d-none');
        }
    });
}

// Export the initialization function
window.initializeFileHandler = initializeFileHandler;

function updateDataStats(data) {
    const statsDiv = document.getElementById('dataStats');
    const insights = data.statistical_insights;
    const overview = insights.dataset_overview;
    
    statsDiv.innerHTML = `
        <div class="row g-3">
            <div class="col-md-3">
                <div class="border rounded p-2">
                    <small class="text-muted">Total Rows</small>
                    <div class="h5 mb-0">${overview.total_rows.toLocaleString()}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="border rounded p-2">
                    <small class="text-muted">Total Columns</small>
                    <div class="h5 mb-0">${overview.total_columns}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="border rounded p-2">
                    <small class="text-muted">Numeric Columns</small>
                    <div class="h5 mb-0">${overview.column_types.numeric.count}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="border rounded p-2">
                    <small class="text-muted">Memory Usage</small>
                    <div class="h5 mb-0">${data.processed_data.summary.memory_usage}</div>
                </div>
            </div>
        </div>
    `;
}

function updatePreviewTable(preview) {
    const table = document.getElementById('previewTable');
    if (!preview || !preview.length) {
        table.innerHTML = '<thead><tr><th>No data available</th></tr></thead>';
        return;
    }

    const headers = Object.keys(preview[0]);
    const headerRow = headers.map(h => `<th>${h}</th>`).join('');
    
    const rows = preview.map(row => {
        return `<tr>${headers.map(h => `<td>${row[h] ?? ''}</td>`).join('')}</tr>`;
    }).join('');

    table.innerHTML = `
        <thead><tr>${headerRow}</tr></thead>
        <tbody>${rows}</tbody>
    `;
}
