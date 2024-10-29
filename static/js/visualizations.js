let chartInstances = [];
const MAX_CHARTS = 4; // Maximum number of charts to show at once
const DEBUG = true;

// Add missing logging functions
function log(...args) {
    if (DEBUG) {
        console.log('[Visualization]', ...args);
    }
}

function logError(...args) {
    console.error('[Visualization Error]', ...args);
}

// Add initialization function
async function initializeCharts() {
    log('Initializing charts system');
    
    try {
        // Initialize visualization container
        const container = document.getElementById('visualizationContainer');
        if (!container) {
            throw new Error('Visualization container not found');
        }

        // Set up view toggle buttons
        const gridViewBtn = document.getElementById('gridViewBtn');
        const singleViewBtn = document.getElementById('singleViewBtn');

        if (gridViewBtn && singleViewBtn) {
            gridViewBtn.addEventListener('click', () => {
                container.classList.remove('single-view');
                gridViewBtn.classList.add('active');
                singleViewBtn.classList.remove('active');
                chartInstances.forEach(({chart}) => chart.resize());
            });

            singleViewBtn.addEventListener('click', () => {
                container.classList.add('single-view');
                singleViewBtn.classList.add('active');
                gridViewBtn.classList.remove('active');
                chartInstances.forEach(({chart}) => chart.resize());
            });
        }

        // Set up resize handler
        window.addEventListener('resize', () => {
            chartInstances.forEach(({chart}) => chart.resize());
        });

        log('Charts system initialized successfully');
        return true;
    } catch (error) {
        logError('Error initializing charts:', error);
        throw error;
    }
}

function cleanupCharts() {
    chartInstances.forEach(({chart, resizeObserver}) => {
        try {
            if (resizeObserver) {
                resizeObserver.disconnect();
            }
            if (chart) {
                chart.dispose();
            }
        } catch (error) {
            logError('Error cleaning up chart:', error);
        }
    });
    chartInstances = [];
}

async function updateVisualizations(configs) {
    log('Starting visualization update with configs:', configs);
    
    const container = document.getElementById('visualizationContainer');
    if (!container) {
        logError('Visualization container not found');
        return;
    }

    try {
        showLoadingState();

        // Clear existing charts if in single view mode
        const isSingleView = container.classList.contains('single-view');
        if (isSingleView) {
            cleanupCharts();
            container.innerHTML = '';
        }

        // Limit the number of charts in grid view
        if (!isSingleView && chartInstances.length >= MAX_CHARTS) {
            // Remove oldest charts
            const numToRemove = configs.length;
            const chartsToRemove = chartInstances.slice(0, numToRemove);
            chartsToRemove.forEach(({chart, container, resizeObserver}) => {
                resizeObserver.disconnect();
                chart.dispose();
                container.remove();
            });
            chartInstances = chartInstances.slice(numToRemove);
        }

        // Create new chart containers
        for (const config of configs) {
            log('Creating chart with config:', config);
            
            const chartDiv = document.createElement('div');
            chartDiv.className = 'chart-container';
            chartDiv.id = `chart_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            container.appendChild(chartDiv);

            try {
                const chart = echarts.init(chartDiv, null, {
                    renderer: 'canvas',
                    useDirtyRect: true
                });

                const resizeObserver = new ResizeObserver(() => {
                    chart.resize();
                });
                resizeObserver.observe(chartDiv);

                chart.setOption(config);
                chartInstances.push({ chart, container: chartDiv, resizeObserver });
                log('Chart created successfully');
            } catch (error) {
                logError('Error creating chart:', error);
                chartDiv.innerHTML = `
                    <div class="alert alert-danger">
                        Failed to create visualization: ${error.message}
                    </div>
                `;
            }
        }

    } catch (error) {
        logError('Error updating visualizations:', error);
        showError('Failed to update visualizations');
    } finally {
        hideLoadingState();
    }
}

function showLoadingState() {
    const container = document.getElementById('visualizationContainer');
    if (!container) return;

    const loadingOverlay = document.createElement('div');
    loadingOverlay.id = 'vizLoadingOverlay';
    loadingOverlay.className = 'viz-loading-overlay';
    loadingOverlay.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    
    container.appendChild(loadingOverlay);
}

function hideLoadingState() {
    const overlay = document.getElementById('vizLoadingOverlay');
    if (overlay) {
        overlay.remove();
    }
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
