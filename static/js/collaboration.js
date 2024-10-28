// Socket.IO connection and event handling
let socket;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

function initializeCollaboration() {
    connectSocket();
    initializeToasts();
}

function connectSocket() {
    socket = io();
    
    socket.on('connect', () => {
        console.log('Connected to Socket.IO');
        reconnectAttempts = 0;
        const analysisId = document.querySelector('meta[name="analysis-id"]')?.content;
        if (analysisId) {
            socket.emit('join_analysis', { analysis_id: analysisId });
        }
    });

    socket.on('connect_error', (error) => {
        console.error('Socket.IO connection error:', error);
        showErrorToast('Connection lost. Attempting to reconnect...');
        handleReconnection();
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from Socket.IO');
        handleReconnection();
    });

    socket.on('collaborator_joined', (data) => {
        updateCollaboratorsList();
        showCollaboratorJoinedToast(data.name);
    });

    socket.on('new_comment', (comment) => {
        addCommentToList(comment);
        showCommentNotification(comment);
    });
}

function handleReconnection() {
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        setTimeout(() => {
            console.log(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
            socket.connect();
        }, 1000 * reconnectAttempts);
    } else {
        showErrorToast('Connection lost. Please refresh the page.');
    }
}

function initializeToasts() {
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '1050';
    document.body.appendChild(toastContainer);
}

function showToast(message, type = 'info') {
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast show bg-${type}`;
    toast.innerHTML = `
        <div class="toast-header">
            <i class="bi bi-info-circle me-2"></i>
            <strong class="me-auto">Notification</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;

    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function showCollaboratorJoinedToast(name) {
    showToast(`${name} joined the analysis`, 'info');
}

function showCommentNotification(comment) {
    showToast(`New comment from ${comment.author_name}`, 'primary');
}

function showErrorToast(message) {
    showToast(message, 'danger');
}

function updateCollaboratorsList() {
    const shareId = document.querySelector('meta[name="share-id"]')?.content;
    if (!shareId) return;

    fetch(`/analysis/${shareId}/collaborators`)
        .then(response => response.json())
        .then(collaborators => {
            const collaboratorList = document.querySelector('.collaborator-list');
            if (!collaboratorList) return;

            collaboratorList.innerHTML = collaborators.map(collab => `
                <div class="collaborator-badge ${collab.role === 'owner' ? 'owner' : ''}" 
                     title="Last active: ${new Date(collab.last_active).toLocaleString()}">
                    <i class="bi bi-person-fill"></i>
                    ${collab.name}
                    <span class="badge bg-${collab.role === 'owner' ? 'warning' : 'info'}">${collab.role}</span>
                </div>
            `).join('');
        })
        .catch(error => {
            console.error('Error updating collaborators:', error);
            showErrorToast('Failed to update collaborators list');
        });
}

// Initialize collaboration features when document is ready
document.addEventListener('DOMContentLoaded', initializeCollaboration);
