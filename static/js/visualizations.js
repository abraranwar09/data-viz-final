let chartInstances = [];
let initializationAttempts = 0;
const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY = 1000;
const DEBUG = true;

function log(...args) {
    if (DEBUG) {
        console.log('[Visualization]', new Date().toISOString(), ...args);
    }
}

function logError(...args) {
    console.error('[Visualization Error]', new Date().toISOString(), ...args);
}

function initializeCharts() {
    // Check if DOM is loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initializeChartsWithRetry());
        return;
    }
    initializeChartsWithRetry();
}

async function initializeChartsWithRetry(attempt = 0) {
    try {
        showLoadingState();
        
        // Validate app state
        if (!window.appState) {
            throw new Error('Application state not initialized');
        }

        // Clean up existing chart instances
        cleanupCharts();

        // Initialize chart instances with validation
        const containers = document.querySelectorAll('.chart-container');
        if (!containers || containers.length === 0) {
            throw new Error('No chart containers found');
        }

        let initializationErrors = [];
        await Promise.all(Array.from(containers).map(async (container) => {
            if (!container || !container.id) {
                console.warn('Invalid chart container found');
                return;
            }

            try {
                // Show loading state for each container
                container.innerHTML = `
                    <div class="loading-indicator">
                        <div class="loading-bar"></div>
                        <div class="loading-bar"></div>
                        <div class="loading-bar"></div>
                    </div>`;

                // Check if container is visible and has dimensions
                if (container.offsetWidth === 0 || container.offsetHeight === 0) {
                    throw new Error(`Container ${container.id} has no dimensions`);
                }

                const chart = echarts.init(container, null, {
                    renderer: 'canvas',
                    useDirtyRect: true
                });

                // Add resize observer
                const resizeObserver = new ResizeObserver(() => {
                    if (chart && typeof chart.resize === 'function') {
                        chart.resize();
                    }
                });
                resizeObserver.observe(container);

                chartInstances.push({
                    chart,
                    container: container.id,
                    resizeObserver
                });

            } catch (error) {
                initializationErrors.push(`Failed to initialize chart for ${container.id}: ${error.message}`);
                // Add fallback content
                container.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load visualization
                        <button class="btn btn-sm btn-outline-primary ms-2" onclick="initializeChartsWithRetry()">
                            <i class="bi bi-arrow-clockwise me-1"></i>Retry
                        </button>
                    </div>`;
            }
        }));

        if (initializationErrors.length > 0) {
            throw new Error(`Chart initialization errors: ${initializationErrors.join('; ')}`);
        }

        hideLoadingState();
        window.appState.initialized = true;
        initializationAttempts = 0; // Reset counter after successful initialization

    } catch (error) {
        console.error('Failed to initialize charts:', error);
        showError('Failed to initialize visualization components');
        
        // Show retry button in all containers
        document.querySelectorAll('.chart-container').forEach(container => {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Failed to load visualization
                    <button class="btn btn-sm btn-outline-primary ms-2" onclick="initializeChartsWithRetry()">
                        <i class="bi bi-arrow-clockwise me-1"></i>Retry
                    </button>
                </div>`;
        });
        
        // Attempt recovery
        if (attempt < MAX_RETRY_ATTEMPTS) {
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
            return initializeChartsWithRetry(attempt + 1);
        }
        hideLoadingState();
    }
}

function cleanupCharts() {
    chartInstances.forEach(({chart, resizeObserver}) => {
        try {
            if (resizeObserver) {
                resizeObserver.disconnect();
            }
            if (chart && typeof chart.dispose === 'function') {
                chart.dispose();
            }
        } catch (error) {
            console.warn('Error disposing chart:', error);
        }
    });
    chartInstances = [];
}

async function updateVisualizations(data) {
    log('Starting visualization update with data:', data);
    
    if (!window.appState || !window.appState.initialized) {
        logError('Application state not initialized');
        return;
    }

    try {
        const containers = document.querySelectorAll('.chart-container');
        log('Found chart containers:', containers.length);
        
        if (!containers || containers.length === 0) {
            throw new Error('Chart containers not found');
        }

        log('Sending visualization request to server');
        const response = await fetch('/visualize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        log('Server response status:', response.status);
        if (!response.ok) {
            const errorText = await response.text();
            logError('Server response not OK:', response.status, errorText);
            throw new Error(`Failed to generate visualizations: ${response.statusText}. Details: ${errorText}`);
        }

        const result = await response.json();
        log('Received visualization data:', result);

        if (!result.success || !result.visualizations) {
            logError('Invalid visualization data:', result);
            throw new Error(result.error || 'Invalid visualization data received');
        }

        // Render visualizations one at a time
        for (let i = 0; i < containers.length; i++) {
            const container = containers[i];
            const vizConfig = result.visualizations[i];
            
            if (!vizConfig) continue;

            log(`Rendering visualization ${i + 1} in container ${container.id}`);
            
            // Show loading state for current container
            container.innerHTML = `
                <div class="loading-indicator">
                    <div class="loading-bar"></div>
                    <div class="loading-bar"></div>
                    <div class="loading-bar"></div>
                </div>`;

            try {
                // Clean up existing chart
                const existingInstance = chartInstances.find(ci => ci.container === container.id);
                if (existingInstance) {
                    existingInstance.resizeObserver.disconnect();
                    existingInstance.chart.dispose();
                    chartInstances = chartInstances.filter(ci => ci.container !== container.id);
                }

                // Initialize new chart
                const chart = echarts.init(container, null, {
                    renderer: 'canvas',
                    useDirtyRect: true
                });
                
                // Add small delay between renders
                await new Promise(resolve => setTimeout(resolve, 100));
                
                log(`Setting options for chart ${i + 1}:`, vizConfig);
                chart.setOption(vizConfig);
                
                const resizeObserver = new ResizeObserver(() => {
                    log(`Resizing chart ${i + 1}`);
                    chart.resize();
                });
                resizeObserver.observe(container);
                
                chartInstances.push({
                    chart,
                    container: container.id,
                    resizeObserver
                });
                log(`Successfully rendered chart ${i + 1}`);
            } catch (error) {
                logError(`Error rendering visualization ${i + 1}:`, error);
                container.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load visualization: ${error.message}
                        <button class="btn btn-sm btn-outline-primary ms-2" onclick="updateVisualizations(window.appState.currentData)">
                            <i class="bi bi-arrow-clockwise me-1"></i>Retry
                        </button>
                    </div>`;
            }
        }

    } catch (error) {
        logError('Error updating visualizations:', error);
        document.querySelectorAll('.chart-container').forEach(container => {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Failed to load visualization: ${error.message}
                    <button class="btn btn-sm btn-outline-primary ms-2" onclick="updateVisualizations(window.appState.currentData)">
                        <i class="bi bi-arrow-clockwise me-1"></i>Retry
                    </button>
                </div>`;
        });
    }
}

function showLoadingState() {
    document.querySelectorAll('.chart-container').forEach(container => {
        container.innerHTML = `
            <div class="loading-indicator">
                <div class="loading-bar"></div>
                <div class="loading-bar"></div>
                <div class="loading-bar"></div>
            </div>`;
    });
}

function hideLoadingState() {
    document.querySelectorAll('.loading-indicator').forEach(indicator => {
        indicator.remove();
    });
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
    }
}
