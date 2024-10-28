let initializationAttempts = 0;
const MAX_INITIALIZATION_ATTEMPTS = 3;
let chartInstances = [];

function initializeCharts() {
    try {
        if (!window.appState) {
            throw new Error('Application state not initialized');
        }

        // Validate chart containers
        const containers = ['chart1', 'chart2', 'chart3', 'chart4'];
        const missingContainers = containers.filter(id => !document.getElementById(id));
        
        if (missingContainers.length > 0) {
            throw new Error(`Missing chart containers: ${missingContainers.join(', ')}`);
        }

        // Clean up existing chart instances
        cleanupCharts();
        window.appState.initialized = true;

    } catch (error) {
        console.error('Failed to initialize charts:', error);
        handleChartInitializationError(error);
    }
}

function cleanupCharts() {
    // Dispose of any existing chart instances
    chartInstances.forEach(chart => {
        if (chart && typeof chart.dispose === 'function') {
            chart.dispose();
        }
    });
    chartInstances = [];
}

function handleChartInitializationError(error) {
    initializationAttempts++;
    
    if (initializationAttempts < MAX_INITIALIZATION_ATTEMPTS) {
        console.warn(`Chart initialization attempt ${initializationAttempts} failed, retrying...`);
        setTimeout(initializeCharts, 1000);
    } else {
        console.error('Failed to initialize charts after multiple attempts:', error);
        showError('Failed to initialize visualization components. Please refresh the page.');
    }
}

async function updateVisualizations(data) {
    if (!window.appState || !window.appState.initialized) {
        console.error('Charts not initialized');
        return;
    }

    try {
        // Request AI-generated visualizations
        const response = await fetch('/visualize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error('Failed to generate visualizations');
        }

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.error || 'Failed to generate visualizations');
        }

        // Clear existing charts
        cleanupCharts();

        // Create a temporary container to parse the HTML
        const tempContainer = document.createElement('div');
        tempContainer.innerHTML = result.visualization_code;

        // Extract and execute any scripts
        const scripts = tempContainer.getElementsByTagName('script');
        for (let script of scripts) {
            if (script.textContent) {
                eval(script.textContent);
            }
        }

        // Add generated styles
        const styles = tempContainer.getElementsByTagName('style');
        for (let style of styles) {
            document.head.appendChild(style.cloneNode(true));
        }

        // Initialize new charts
        const chartElements = document.querySelectorAll('[id^="chart"]');
        chartElements.forEach(element => {
            const chart = echarts.init(element);
            chartInstances.push(chart);
        });

    } catch (error) {
        console.error('Error updating visualizations:', error);
        showError('Failed to update visualizations: ' + error.message);
    }
}

// Utility function to debounce resize events
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Handle window resize
window.addEventListener('resize', debounce(() => {
    chartInstances.forEach(chart => {
        if (chart && typeof chart.resize === 'function') {
            try {
                chart.resize();
            } catch (error) {
                console.warn('Error resizing chart:', error);
            }
        }
    });
}, 250));

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
    }
}
