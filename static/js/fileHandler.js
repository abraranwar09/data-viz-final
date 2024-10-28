function initializeFileHandlers() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

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

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Upload failed');

        const data = await response.json();
        appState.currentData = data;
        eventBus.publish('dataLoaded', data);
        
        updatePreviewTable(data.preview);
        updateStatistics(data.column_stats);
        updateVisualizations(data);
    } catch (error) {
        console.error('Error:', error);
        alert('Error uploading file');
    }
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
