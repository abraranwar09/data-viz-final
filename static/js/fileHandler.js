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
    const progressBar = document.querySelector('.progress-bar');
    const progressDiv = document.getElementById('uploadProgress');
    const errorAlert = document.getElementById('errorAlert');
    const shareButton = document.getElementById('shareAnalysis');

    // Reset UI state
    progressDiv.classList.add('d-none');
    errorAlert.classList.add('d-none');
    shareButton.disabled = true;

    // Client-side validation
    if (!file) {
        showError('Please select a file to upload');
        return;
    }

    // Check file size
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
        showError(`File size exceeds maximum limit of 50MB. Your file is ${(file.size / 1024 / 1024).toFixed(2)}MB`);
        return;
    }

    // Check if file is empty
    if (file.size === 0) {
        showError('The selected file is empty');
        return;
    }

    // Check file extension
    const allowedExtensions = ['csv', 'xlsx', 'xls', 'json', 'tsv', 'txt'];
    const extension = file.name.split('.').pop().toLowerCase();
    if (!allowedExtensions.includes(extension)) {
        showError(`Invalid file type. Allowed types are: ${allowedExtensions.join(', ')}`);
        return;
    }

    // Show progress bar
    progressDiv.classList.remove('d-none');
    progressBar.style.width = '0%';
    progressBar.setAttribute('aria-valuenow', 0);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/upload', true);
        
        // Track upload progress
        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressBar.style.width = percentComplete + '%';
                progressBar.setAttribute('aria-valuenow', percentComplete);
            }
        };

        // Handle response
        xhr.onload = async function() {
            try {
                const response = JSON.parse(xhr.responseText);
                
                if (xhr.status !== 200) {
                    throw new Error(response.error || 'Upload failed');
                }

                // Update application state
                appState.currentData = response;
                eventBus.publish('dataLoaded', response);
                
                // Update UI
                updateDataStats(response);
                updatePreviewTable(response.preview);
                updateVisualizations(response);
                shareButton.disabled = false;
                progressDiv.classList.add('d-none');
                
            } catch (error) {
                console.error('Error:', error);
                showError(error.message);
                shareButton.disabled = true;
            }
            progressDiv.classList.add('d-none');
        };

        // Handle network errors
        xhr.onerror = function() {
            showError('Network error occurred while uploading the file');
            progressDiv.classList.add('d-none');
            shareButton.disabled = true;
        };

        xhr.send(formData);
    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
        progressDiv.classList.add('d-none');
        shareButton.disabled = true;
    }
}

function showError(message) {
    const errorAlert = document.getElementById('errorAlert');
    errorAlert.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            <span>${message}</span>
        </div>
    `;
    errorAlert.classList.remove('d-none');
}

function updateDataStats(data) {
    const statsDiv = document.getElementById('dataStats');
    const summary = data.summary;
    
    statsDiv.innerHTML = `
        <div class="row g-3">
            <div class="col-md-3">
                <div class="border rounded p-2">
                    <small class="text-muted">Total Rows</small>
                    <div class="h5 mb-0">${summary.rows.toLocaleString()}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="border rounded p-2">
                    <small class="text-muted">Total Columns</small>
                    <div class="h5 mb-0">${summary.columns}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="border rounded p-2">
                    <small class="text-muted">Numeric Columns</small>
                    <div class="h5 mb-0">${summary.numeric_columns}</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="border rounded p-2">
                    <small class="text-muted">Memory Usage</small>
                    <div class="h5 mb-0">${summary.memory_usage}</div>
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
