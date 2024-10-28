let chartInstances = [];

function initializeCharts() {
    try {
        // Check if DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => initializeCharts());
            return;
        }

        // Validate app state
        if (!window.appState) {
            throw new Error('Application state not initialized');
        }

        // Clean up existing chart instances
        cleanupCharts();

        // Initialize chart instances
        const containers = document.querySelectorAll('.chart-container');
        if (!containers || containers.length === 0) {
            throw new Error('No chart containers found');
        }

        containers.forEach(container => {
            if (!container || !container.id) {
                console.warn('Invalid chart container found');
                return;
            }

            try {
                const chart = echarts.init(container);
                chartInstances.push(chart);
            } catch (error) {
                console.error(`Failed to initialize chart for ${container.id}:`, error);
            }
        });

        // Initialize Mermaid
        if (window.mermaid) {
            mermaid.initialize({
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
        }

        window.appState.initialized = true;

        // Add resize handler
        window.removeEventListener('resize', handleResize);
        window.addEventListener('resize', handleResize);

    } catch (error) {
        console.error('Failed to initialize charts:', error);
        showError('Failed to initialize visualization components. Please refresh the page.');
    }
}

function cleanupCharts() {
    chartInstances.forEach(chart => {
        if (chart && typeof chart.dispose === 'function') {
            try {
                chart.dispose();
            } catch (error) {
                console.warn('Error disposing chart:', error);
            }
        }
    });
    chartInstances = [];
}

function handleResize() {
    chartInstances.forEach(chart => {
        if (chart && typeof chart.resize === 'function') {
            try {
                chart.resize();
            } catch (error) {
                console.warn('Error resizing chart:', error);
            }
        }
    });
}

function showLoadingState() {
    const loadingDiv = document.querySelector('.visualization-loading');
    if (loadingDiv) {
        loadingDiv.classList.remove('d-none');
    }
}

function hideLoadingState() {
    const loadingDiv = document.querySelector('.visualization-loading');
    if (loadingDiv) {
        loadingDiv.classList.add('d-none');
    }
}

async function renderMermaidDiagram(container, code) {
    if (!window.mermaid) {
        console.warn('Mermaid.js not loaded');
        return false;
    }

    try {
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;
        container.innerHTML = `<div class="mermaid" id="${id}">${code}</div>`;
        await mermaid.run();
        return true;
    } catch (error) {
        console.error('Error rendering Mermaid diagram:', error);
        return false;
    }
}

async function updateVisualizations(data) {
    if (!window.appState) {
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

        // Clean up existing charts
        cleanupCharts();

        // Create a temporary container to parse the HTML
        const tempContainer = document.createElement('div');
        tempContainer.innerHTML = result.visualization_code;

        // Add generated styles
        const styles = tempContainer.getElementsByTagName('style');
        Array.from(styles).forEach(style => {
            document.head.appendChild(style.cloneNode(true));
        });

        // Process visualization containers
        const visualizationElements = tempContainer.querySelectorAll('[id^="chart"]');
        await Promise.all(Array.from(visualizationElements).map(async (element, index) => {
            const container = containers[index];
            if (!container) return;

            const content = element.innerHTML;
            
            // Check if content is a Mermaid diagram
            if (content.trim().startsWith('graph') || 
                content.trim().startsWith('sequenceDiagram') || 
                content.trim().startsWith('classDiagram')) {
                await renderMermaidDiagram(container, content);
            } else {
                // Assume ECharts
                try {
                    const chart = echarts.init(container);
                    chartInstances.push(chart);
                    const options = JSON.parse(content);
                    chart.setOption(options);
                } catch (error) {
                    console.error('Error initializing chart:', error);
                }
            }
        }));

        // Execute any additional scripts
        const scripts = tempContainer.getElementsByTagName('script');
        Array.from(scripts).forEach(script => {
            if (script.textContent) {
                try {
                    eval(script.textContent);
                } catch (error) {
                    console.error('Error executing visualization script:', error);
                }
            }
        });

        window.appState.initialized = true;
        hideLoadingState();

    } catch (error) {
        console.error('Error updating visualizations:', error);
        showError('Failed to update visualizations: ' + error.message);
        hideLoadingState();
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
