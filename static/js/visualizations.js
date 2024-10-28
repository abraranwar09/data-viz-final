let initializationAttempts = 0;
const MAX_INITIALIZATION_ATTEMPTS = 3;

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

        // Initialize chart containers with retry logic
        initializeChartContainers();

    } catch (error) {
        console.error('Failed to initialize charts:', error);
        handleChartInitializationError(error);
    }
}

function initializeChartContainers() {
    try {
        // Initialize chart containers
        window.appState.charts = {
            histogram: echarts.init(document.getElementById('chart1')),
            scatter: echarts.init(document.getElementById('chart2')),
            boxplot: echarts.init(document.getElementById('chart3')),
            heatmap: echarts.init(document.getElementById('chart4'))
        };

        // Handle window resize
        window.addEventListener('resize', debounce(() => {
            Object.values(window.appState.charts).forEach(chart => {
                if (chart && typeof chart.resize === 'function') {
                    try {
                        chart.resize();
                    } catch (error) {
                        console.warn('Error resizing chart:', error);
                    }
                }
            });
        }, 250));

        window.appState.initialized = true;
        initializationAttempts = 0;

    } catch (error) {
        handleChartInitializationError(error);
    }
}

function handleChartInitializationError(error) {
    initializationAttempts++;
    
    if (initializationAttempts < MAX_INITIALIZATION_ATTEMPTS) {
        console.warn(`Chart initialization attempt ${initializationAttempts} failed, retrying...`);
        setTimeout(initializeCharts, 1000); // Retry after 1 second
    } else {
        console.error('Failed to initialize charts after multiple attempts:', error);
        showError('Failed to initialize visualization components. Please refresh the page.');
    }
}

function updateVisualizations(data) {
    if (!window.appState || !window.appState.initialized) {
        console.error('Charts not initialized');
        return;
    }

    try {
        const visualizationData = processData(data);
        if (visualizationData) {
            updateHistogram(visualizationData.histogram);
            updateScatterPlot(visualizationData.scatter);
            updateBoxplot(visualizationData.boxplot);
            updateHeatmap(visualizationData.heatmap);
        }
    } catch (error) {
        console.error('Error updating visualizations:', error);
        showError('Failed to update visualizations');
    }
}

function updateHistogram(data) {
    if (!data || !data.values) {
        console.warn('Invalid histogram data');
        return;
    }

    const option = {
        title: { text: `Distribution of ${data.column}` },
        tooltip: { trigger: 'axis' },
        xAxis: { 
            type: 'category',
            data: data.bins || data.values.map((v, i) => i)
        },
        yAxis: { type: 'value' },
        series: [{
            type: 'bar',
            data: data.values,
            barWidth: '99%'
        }]
    };
    
    try {
        window.appState.charts.histogram.setOption(option);
    } catch (error) {
        console.error('Error updating histogram:', error);
    }
}

function updateScatterPlot(data) {
    if (!data || !data.x || !data.y) {
        console.warn('Invalid scatter plot data');
        return;
    }

    const option = {
        title: { text: `${data.xLabel} vs ${data.yLabel}` },
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                return `${data.xLabel}: ${params.value[0]}<br/>${data.yLabel}: ${params.value[1]}`;
            }
        },
        xAxis: { type: 'value', name: data.xLabel },
        yAxis: { type: 'value', name: data.yLabel },
        series: [{
            type: 'scatter',
            data: data.x.map((x, i) => [x, data.y[i]]),
            symbolSize: 8
        }]
    };
    
    try {
        window.appState.charts.scatter.setOption(option);
    } catch (error) {
        console.error('Error updating scatter plot:', error);
    }
}

function updateBoxplot(data) {
    if (!data || !Array.isArray(data)) {
        console.warn('Invalid boxplot data');
        return;
    }

    const option = {
        title: { text: 'Distribution Summary' },
        tooltip: { trigger: 'item' },
        xAxis: {
            type: 'category',
            data: data.map(d => d.name)
        },
        yAxis: { type: 'value' },
        series: [{
            type: 'boxplot',
            data: data.map(d => [
                d.stats.min,
                d.stats.q1 || d.stats.min,
                d.stats.median,
                d.stats.q3 || d.stats.max,
                d.stats.max
            ])
        }]
    };
    
    try {
        window.appState.charts.boxplot.setOption(option);
    } catch (error) {
        console.error('Error updating boxplot:', error);
    }
}

function updateHeatmap(data) {
    if (!data || !data.columns || !data.values) {
        console.warn('Invalid heatmap data');
        return;
    }

    const option = {
        title: { text: 'Correlation Matrix' },
        tooltip: {
            position: 'top',
            formatter: function(params) {
                return `Correlation: ${params.value[2].toFixed(2)}`;
            }
        },
        animation: false,
        grid: {
            height: '70%',
            top: '10%'
        },
        xAxis: {
            type: 'category',
            data: data.columns,
            splitArea: { show: true }
        },
        yAxis: {
            type: 'category',
            data: data.columns,
            splitArea: { show: true }
        },
        visualMap: {
            min: -1,
            max: 1,
            calculable: true,
            orient: 'horizontal',
            left: 'center',
            bottom: '15%'
        },
        series: [{
            type: 'heatmap',
            data: data.values,
            label: {
                show: true,
                formatter: function(params) {
                    return params.value[2].toFixed(2);
                }
            },
            emphasis: {
                itemStyle: {
                    shadowBlur: 10,
                    shadowColor: 'rgba(0, 0, 0, 0.5)'
                }
            }
        }]
    };
    
    try {
        window.appState.charts.heatmap.setOption(option);
    } catch (error) {
        console.error('Error updating heatmap:', error);
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
