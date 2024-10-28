function initializeFileHandlers() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const progressBar = document.querySelector('.progress-bar');
    const progressDiv = document.getElementById('uploadProgress');
    const errorAlert = document.getElementById('errorAlert');

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
    if (!file) return;

    // Check file size
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
        showError(`File size exceeds maximum limit of 50MB. Your file is ${(file.size / 1024 / 1024).toFixed(2)}MB`);
        return;
    }

    const progressBar = document.querySelector('.progress-bar');
    const progressDiv = document.getElementById('uploadProgress');
    const errorAlert = document.getElementById('errorAlert');

    // Show progress bar
    progressDiv.classList.remove('d-none');
    progressBar.style.width = '0%';
    errorAlert.classList.add('d-none');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData,
            onUploadProgress: (progressEvent) => {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                progressBar.style.width = percentCompleted + '%';
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Upload failed');
        }

        const data = await response.json();
        appState.currentData = data;
        eventBus.publish('dataLoaded', data);
        
        updateDataStats(data);
        updatePreviewTable(data.preview);
        updateVisualizations(data);

        // Hide progress bar
        progressDiv.classList.add('d-none');
    } catch (error) {
        console.error('Error:', error);
        showError(error.message);
        progressDiv.classList.add('d-none');
    }
}

function showError(message) {
    const errorAlert = document.getElementById('errorAlert');
    errorAlert.textContent = message;
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
    if (!preview || !preview.length) return;

    const headers = Object.keys(preview[0]);
    const headerRow = headers.map(h => `<th>${h}</th>`).join('');
    
    const rows = preview.map(row => {
        return `<tr>${headers.map(h => `<td>${row[h]}</td>`).join('')}</tr>`;
    }).join('');

    table.innerHTML = `
        <thead><tr>${headerRow}</tr></thead>
        <tbody>${rows}</tbody>
    `;
}
