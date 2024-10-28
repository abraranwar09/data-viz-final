let chartInstances = [];
let initializationAttempts = 0;
const MAX_RETRY_ATTEMPTS = 3;
const RETRY_DELAY = 1000;

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

        // Initialize Mermaid with error handling
        if (window.mermaid) {
            try {
                await mermaid.initialize({
                    startOnLoad: true,
                    theme: 'dark',
                    securityLevel: 'loose',
                    themeVariables: {
                        fontFamily: 'var(--bs-body-font-family)',
                        primaryColor: 'var(--bs-primary)',
                        primaryTextColor: 'var(--bs-primary-text)',
                        primaryBorderColor: 'var(--bs-border-color)',
                        lineColor: 'var(--bs-border-color)',
                        secondaryColor: 'var(--bs-secondary)',
                        tertiaryColor: 'var(--bs-tertiary)'
                    }
                });
            } catch (error) {
                console.error('Mermaid initialization error:', error);
            }
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
    if (!window.appState || !window.appState.initialized) {
        console.error('Application state not initialized');
        return;
    }

    try {
        showLoadingState();

        // Validate containers
        const containers = document.querySelectorAll('.chart-container');
        if (!containers || containers.length === 0) {
            throw new Error('Chart containers not found');
        }

        // Request AI-generated visualizations with timeout
        const response = await Promise.race([
            fetch('/visualize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            }),
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Visualization request timeout')), 30000)
            )
        ]);

        if (!response.ok) {
            throw new Error(`Failed to generate visualizations: ${response.statusText}`);
        }

        const result = await response.json();
        if (!result.success) {
            throw new Error(result.error || 'Failed to generate visualizations');
        }

        // Clean up existing charts
        cleanupCharts();

        // Process visualization containers
        const tempContainer = document.createElement('div');
        tempContainer.innerHTML = result.visualization_code;

        // Add generated styles
        const styles = tempContainer.getElementsByTagName('style');
        Array.from(styles).forEach(style => {
            document.head.appendChild(style.cloneNode(true));
        });

        // Process each visualization
        const visualizationElements = tempContainer.querySelectorAll('[id^="chart"]');
        await Promise.all(Array.from(visualizationElements).map(async (element, index) => {
            const container = containers[index];
            if (!container) return;

            try {
                const content = element.innerHTML.trim();
                
                if (content.startsWith('graph') || 
                    content.startsWith('sequenceDiagram') || 
                    content.startsWith('classDiagram')) {
                    await renderMermaidDiagram(container, content);
                } else {
                    // Initialize ECharts with error boundaries
                    const chart = echarts.init(container, null, {
                        renderer: 'canvas',
                        useDirtyRect: true
                    });
                    
                    const options = JSON.parse(content);
                    await new Promise((resolve, reject) => {
                        try {
                            chart.setOption(options);
                            resolve();
                        } catch (error) {
                            reject(error);
                        }
                    });

                    chartInstances.push({
                        chart,
                        container: container.id,
                        resizeObserver: new ResizeObserver(() => chart.resize())
                    });
                }
            } catch (error) {
                console.error(`Error initializing visualization ${index + 1}:`, error);
                container.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="bi bi-exclamation-triangle me-2"></i>
                        Failed to load visualization
                        <button class="btn btn-sm btn-outline-primary ms-2" onclick="updateVisualizations(window.appState.currentData)">
                            <i class="bi bi-arrow-clockwise me-1"></i>Retry
                        </button>
                    </div>`;
            }
        }));

        hideLoadingState();

    } catch (error) {
        console.error('Error updating visualizations:', error);
        // Show error state in all containers
        document.querySelectorAll('.chart-container').forEach(container => {
            container.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Failed to load visualization
                    <button class="btn btn-sm btn-outline-primary ms-2" onclick="updateVisualizations(window.appState.currentData)">
                        <i class="bi bi-arrow-clockwise me-1"></i>Retry
                    </button>
                </div>`;
        });
        hideLoadingState();
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

async function renderMermaidDiagram(container, code) {
    if (!window.mermaid) {
        console.warn('Mermaid.js not loaded');
        container.innerHTML = `
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Mermaid.js not available
            </div>`;
        return false;
    }

    try {
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        container.innerHTML = `<div class="mermaid" id="${id}">${code}</div>`;
        await mermaid.run();
        return true;
    } catch (error) {
        console.error('Error rendering Mermaid diagram:', error);
        container.innerHTML = `
            <div class="alert alert-warning">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Failed to render diagram
                <button class="btn btn-sm btn-outline-primary ms-2" onclick="renderMermaidDiagram(this.closest('.chart-container'), '${code.replace(/'/g, "\\'")}')">
                    <i class="bi bi-arrow-clockwise me-1"></i>Retry
                </button>
            </div>`;
        return false;
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
