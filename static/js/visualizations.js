let chartInstances = [];
let pinnedCharts = [];
const MAX_PINNED_CHARTS = 2;
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
        // Initialize containers
        const container = document.getElementById('visualizationContainer');
        const pinnedContainer = document.createElement('div');
        pinnedContainer.className = 'pinned-graphs';
        container.parentElement.insertBefore(pinnedContainer, container);
        
        if (!container) {
            throw new Error('Visualization container not found');
        }

        // Set up scroll handler for infinite scroll
        window.addEventListener('scroll', () => {
            const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
            if (scrollTop + clientHeight >= scrollHeight - 5) {
                // User has scrolled to bottom, load more charts if needed
                loadMoreCharts();
            }
        });

        // Set up resize handler
        window.addEventListener('resize', () => {
            chartInstances.forEach(({chart}) => chart.resize());
            pinnedCharts.forEach(({chart}) => chart.resize());
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

// Function to generate tree chart configuration
function generateTreeChart(data, title) {
    // Transform data into hierarchical structure
    function transformData(data, parentField, childField) {
        const result = [];
        const valueMap = {};
        
        // First pass: Count values
        data.forEach(row => {
            const parentVal = row[parentField];
            const childVal = row[childField];
            
            if (!valueMap[parentVal]) {
                valueMap[parentVal] = {};
            }
            if (!valueMap[parentVal][childVal]) {
                valueMap[parentVal][childVal] = 0;
            }
            valueMap[parentVal][childVal]++;
        });
        
        // Second pass: Create hierarchical structure
        Object.entries(valueMap).forEach(([parent, children]) => {
            const parentNode = {
                name: parent,
                value: Object.values(children).reduce((a, b) => a + b, 0),
                children: Object.entries(children).map(([child, value]) => ({
                    name: child,
                    value: value
                }))
            };
            result.push(parentNode);
        });
        
        return result;
    }

    const treeData = transformData(data.preview, 'Education Level', 'Previous Default');
    
    return {
        title: {
            text: title,
            textStyle: { color: '#fff' }
        },
        tooltip: {
            formatter: function(info) {
                const value = info.value;
                const name = info.name;
                return `${name}: ${value} records`;
            }
        },
        series: [{
            type: 'treemap',
            data: treeData,
            leafDepth: 1,
            levels: [{
                itemStyle: {
                    borderColor: '#fff',
                    borderWidth: 2,
                    gapWidth: 2
                }
            }, {
                colorSaturation: [0.3, 0.6],
                itemStyle: {
                    borderColor: '#fff',
                    borderWidth: 1,
                    gapWidth: 1
                }
            }],
            label: {
                show: true,
                formatter: '{b}: {c}',
                color: '#fff'
            }
        }]
    };
}

// Function to generate categorical charts
function generateCategoricalCharts(data) {
    const configs = [];
    
    if (!data.categorical) return configs;
    
    // For each categorical column
    Object.entries(data.categorical).forEach(([column, stats]) => {
        // Pie Chart
        configs.push({
            title: {
                text: `Distribution of ${column}`,
                textStyle: { color: '#fff' }
            },
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} ({d}%)'
            },
            series: [{
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    formatter: '{b}: {c} ({d}%)',
                    color: '#fff'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: '16',
                        fontWeight: 'bold'
                    }
                },
                data: Object.entries(stats.frequencies).map(([name, value]) => ({
                    name,
                    value,
                    itemStyle: {
                        color: getColorForCategory(name)
                    }
                }))
            }]
        });

        // Bar Chart
        configs.push({
            title: {
                text: `Frequency of ${column}`,
                textStyle: { color: '#fff' }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'shadow'
                }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: Object.keys(stats.frequencies),
                axisLabel: {
                    color: '#fff',
                    rotate: 45,
                    interval: 0
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: { color: '#fff' }
            },
            series: [{
                type: 'bar',
                data: Object.entries(stats.frequencies).map(([name, value]) => ({
                    value,
                    itemStyle: {
                        color: getColorForCategory(name)
                    }
                })),
                label: {
                    show: true,
                    position: 'top',
                    color: '#fff'
                }
            }]
        });
    });
    
    return configs;
}

// Helper function to get consistent colors for categories
function getColorForCategory(category) {
    const colors = {
        'Healthy': '#28a745',
        'Excellent growth': '#20c997',
        'Minor blight': '#ffc107',
        'Needs more sunlight': '#17a2b8',
        'default': '#6c757d'
    };
    
    return colors[category] || colors.default;
}

// Update the generateVisualizations function
async function generateVisualizations(data) {
    try {
        log('Generating visualizations for data:', data);
        
        if (!data || !data.processed_data) {
            throw new Error('Invalid data format');
        }

        const configs = [];
        
        // Add categorical visualizations
        if (data.processed_data.categorical) {
            configs.push(...generateCategoricalCharts(data.processed_data));
        }
        
        // Add existing numeric visualizations
        // ... existing numeric visualization code ...
        
        // Update visualizations with the generated configs
        await updateVisualizations(configs);
        
    } catch (error) {
        logError('Error generating visualizations:', error);
        showError('Failed to generate visualizations: ' + error.message);
    }
}

// Create a new chart container with actions
function createChartContainer() {
    const container = document.createElement('div');
    container.className = 'chart-container';
    
    const actions = document.createElement('div');
    actions.className = 'chart-actions';
    
    // Download button
    const downloadBtn = document.createElement('button');
    downloadBtn.className = 'chart-action-btn';
    downloadBtn.innerHTML = '<i class="bi bi-download"></i>';
    downloadBtn.title = 'Download Chart';
    
    // Pin button
    const pinBtn = document.createElement('button');
    pinBtn.className = 'chart-action-btn';
    pinBtn.innerHTML = '<i class="bi bi-pin"></i>';
    pinBtn.title = 'Pin Chart';
    
    actions.appendChild(downloadBtn);
    actions.appendChild(pinBtn);
    container.appendChild(actions);
    
    return { container, downloadBtn, pinBtn };
}

// Update pinned graphs container height and main container margin
function updatePinnedGraphsLayout() {
    const pinnedContainer = document.querySelector('.pinned-graphs');
    const mainContainer = document.querySelector('.visualization-grid');
    
    if (pinnedContainer && mainContainer) {
        const height = pinnedCharts.length > 0 ? pinnedContainer.offsetHeight : 0;
        document.documentElement.style.setProperty('--pinned-height', `${height}px`);
    }
}

// Enhanced chart initialization with better responsive handling
function initializeChart(container, config) {
    const chart = echarts.init(container, null, {
        renderer: 'canvas',
        useDirtyRect: true
    });
    
    // Set responsive options
    const responsiveConfig = {
        ...config,
        grid: {
            ...config.grid,
            containLabel: true,
            left: '5%',
            right: '5%',
            top: '15%',
            bottom: '10%'
        },
        title: {
            ...config.title,
            textStyle: {
                ...config.title?.textStyle,
                fontSize: window.innerWidth < 768 ? 14 : 16
            }
        }
    };
    
    // Adjust font sizes for mobile
    if (window.innerWidth < 768) {
        if (responsiveConfig.xAxis) {
            responsiveConfig.xAxis.axisLabel = {
                ...responsiveConfig.xAxis.axisLabel,
                fontSize: 10,
                interval: 0,
                rotate: 45
            };
        }
        if (responsiveConfig.yAxis) {
            responsiveConfig.yAxis.axisLabel = {
                ...responsiveConfig.yAxis.axisLabel,
                fontSize: 10
            };
        }
    }
    
    chart.setOption(responsiveConfig);
    return chart;
}

// Enhanced addChart function with responsive support
function addChart(chartConfig) {
    const { container, downloadBtn, pinBtn } = createChartContainer();
    document.getElementById('visualizationContainer').appendChild(container);
    
    const chart = initializeChart(container, chartConfig);
    const chartInstance = { chart, container, config: chartConfig };
    chartInstances.push(chartInstance);
    
    // Set up download handler with error handling
    downloadBtn.addEventListener('click', async () => {
        try {
            const dataURL = chart.getDataURL({
                type: 'png',
                pixelRatio: window.devicePixelRatio || 2
            });
            const link = document.createElement('a');
            link.download = `chart_${Date.now()}.png`;
            link.href = dataURL;
            link.click();
        } catch (error) {
            logError('Error downloading chart:', error);
            showError('Failed to download chart');
        }
    });
    
    // Enhanced pin handler with layout updates
    pinBtn.addEventListener('click', () => {
        if (pinBtn.classList.contains('pinned')) {
            unpinChart(chartInstance);
            pinBtn.classList.remove('pinned');
        } else {
            pinChart(chartInstance);
            pinBtn.classList.add('pinned');
        }
        updatePinnedGraphsLayout();
    });
    
    return chartInstance;
}

// Enhanced pin/unpin functions
function pinChart(chartInstance) {
    if (pinnedCharts.length >= MAX_PINNED_CHARTS) {
        const oldestChart = pinnedCharts.shift();
        const oldestPinBtn = oldestChart.container.querySelector('.chart-action-btn:nth-child(2)');
        oldestPinBtn.classList.remove('pinned');
        document.getElementById('visualizationContainer').appendChild(oldestChart.container);
        oldestChart.chart.resize();
    }
    
    pinnedCharts.push(chartInstance);
    document.querySelector('.pinned-graphs').appendChild(chartInstance.container);
    chartInstance.chart.resize();
    updatePinnedGraphsLayout();
}

function unpinChart(chartInstance) {
    const index = pinnedCharts.indexOf(chartInstance);
    if (index !== -1) {
        pinnedCharts.splice(index, 1);
        document.getElementById('visualizationContainer').appendChild(chartInstance.container);
        chartInstance.chart.resize();
        updatePinnedGraphsLayout();
    }
}

// Enhanced resize handling
window.addEventListener('resize', debounce(() => {
    chartInstances.forEach(({chart, config, container}) => {
        chart.dispose();
        const newChart = initializeChart(container, config);
        chart = newChart;
    });
    
    pinnedCharts.forEach(({chart, config, container}) => {
        chart.dispose();
        const newChart = initializeChart(container, config);
        chart = newChart;
    });
    
    updatePinnedGraphsLayout();
}, 250));

// Utility function for debouncing
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

// Load more charts if needed
function loadMoreCharts() {
    // This function would be called when user scrolls to bottom
    // You would implement your logic here to load more charts if needed
    log('Loading more charts...');
}
