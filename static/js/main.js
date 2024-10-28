// Main application initialization
document.addEventListener('DOMContentLoaded', () => {
    initializeFileHandlers();
    initializeAIAssistant();
    initializeCharts();
});

// Global state management
const appState = {
    currentData: null,
    charts: {},
    statistics: null
};

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
