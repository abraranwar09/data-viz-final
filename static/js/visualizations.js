let chartInstances = [];
let pinnedCharts = [];
const MAX_PINNED_CHARTS = 2;
const MAX_CHARTS = 6; // Updated to 6 as requested
const DEBUG = true;

// ECharts theme colors
const THEME_COLORS = [
    '#7ec2f3',  // Blue
    '#91cc75',  // Green
    '#fac858',  // Yellow
    '#ee6666',  // Red
    '#73c0de',  // Light Blue
    '#3ba272',  // Teal
    '#fc8452',  // Orange
    '#9a60b4'   // Purple
];

// Add missing logging functions
function log(...args) {
    if (DEBUG) {
        console.log('[Visualization]', ...args);
    }
}

function logError(...args) {
    console.error('[Visualization Error]', ...args);
}

// Update chart layout based on count
function updateChartLayout() {
    const container = document.getElementById('visualizationContainer');
    const totalCharts = chartInstances.length;
    
    // Update data-charts attribute to trigger CSS grid changes
    container.setAttribute('data-charts', totalCharts.toString());
    
    // Resize all charts to fit their containers
    chartInstances.forEach(({chart}) => {
        if (chart) {
            setTimeout(() => chart.resize(), 100); // Delay resize to ensure container has updated
        }
    });
    
    // Update pinned charts layout
    const pinnedContainer = document.querySelector('.pinned-graphs');
    if (pinnedContainer) {
        const pinnedHeight = pinnedCharts.length > 0 ? pinnedContainer.offsetHeight : 0;
        document.documentElement.style.setProperty('--pinned-height', `${pinnedHeight}px`);
        pinnedCharts.forEach(({chart}) => {
            if (chart) {
                setTimeout(() => chart.resize(), 100);
            }
        });
    }
}

// Add initialization function
async function initializeCharts() {
    log('Initializing charts system');
    
    try {
        // Initialize containers
        const container = document.getElementById('visualizationContainer');
        const pinnedContainer = document.querySelector('.pinned-graphs') || document.createElement('div');
        pinnedContainer.className = 'pinned-graphs';
        if (!pinnedContainer.parentElement) {
            container.parentElement.insertBefore(pinnedContainer, container);
        }
        
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

        // Set up resize handler with debounce
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                updateChartLayout();
            }, 250);
        });

        // Initial layout update
        updateChartLayout();
        
        log('Charts system initialized successfully');
        return true;
    } catch (error) {
        logError('Failed to initialize charts system:', error);
        return false;
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
    if (!Array.isArray(configs)) {
        logError('Invalid configs format:', configs);
        showError('Invalid visualization configuration format');
        return;
    }

    // Filter out invalid/empty configurations
    configs = configs.filter(config => {
        if (!config.series || !Array.isArray(config.series)) return false;
        return config.series.some(series => 
            series.data && Array.isArray(series.data) && series.data.length > 0
        );
    });

    // Limit number of visualizations
    configs = configs.slice(0, 3);
    
    log('Processing visualization configs:', configs);
    
    const container = document.getElementById('visualizationContainer');
    if (!container) {
        logError('Visualization container not found');
        showError('Visualization container not found');
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

        // Process each configuration
        for (const config of configs) {
            try {
                // Deep validation of config structure
                if (!config || typeof config !== 'object') {
                    throw new Error('Invalid chart configuration format');
                }
                
                if (!config.series || !Array.isArray(config.series)) {
                    throw new Error('Missing or invalid series configuration');
                }

                // Validate each series has required properties
                config.series.forEach((series, idx) => {
                    if (!series.type) {
                        throw new Error(`Series ${idx} missing required 'type' property`);
                    }
                    if (!series.data && !series.source) {
                        throw new Error(`Series ${idx} missing required 'data' or 'source' property`);
                    }
                    // Ensure data is in correct format
                    if (series.data && !Array.isArray(series.data)) {
                        series.data = [series.data];
                    }
                });

                log('Creating chart with config:', config);

                // Create container for this chart
                const chartDiv = document.createElement('div');
                chartDiv.className = 'chart-container';
                chartDiv.style.width = '100%';
                chartDiv.style.height = '400px';
                container.appendChild(chartDiv);

                // Initialize chart with explicit size
                const chart = echarts.init(chartDiv, null, {
                    renderer: 'canvas',
                    useDirtyRect: false
                });
                
                log('Chart initialized:', chart);

                // Apply configuration with comprehensive defaults
                const enhancedConfig = {
                    animation: false,
                    backgroundColor: 'rgba(43, 51, 59, 1)', // Darker, consistent background
                    grid: {
                        left: '3%',
                        right: '4%',
                        bottom: '15%',
                        containLabel: true
                    },
                    tooltip: {
                        trigger: 'item',
                        axisPointer: { type: 'shadow' },
                        backgroundColor: 'rgba(0, 0, 0, 0.7)', // A darker tooltip background
                        textStyle: { color: '#fff' }
                    },
                    // Add a simple legend to many chart types by default (if not already present)
                    legend: {
                        show: true,
                        top: 'bottom',
                        textStyle: { color: '#fff' }
                    },
                    // Center-align title with better readability
                    title: {
                        ...(config.title || {}),
                        left: 'center',
                        top: 20,
                        textStyle: {
                            color: '#fff',
                            fontSize: 16,
                            fontWeight: 'bold',
                            ...(config.title?.textStyle || {})
                        }
                    },
                    xAxis: config.xAxis || {
                        type: 'category',
                        data: [],
                        axisLabel: { color: '#fff' },
                        axisLine: { lineStyle: { color: '#666' } }
                    },
                    yAxis: config.yAxis || {
                        type: 'value',
                        axisLabel: { color: '#fff' },
                        axisLine: { lineStyle: { color: '#666' } }
                    },
                    ...config,
                    series: config.series.map(series => ({
                        animation: false,
                        emphasis: {
                            focus: 'series'
                        },
                        label: {
                            show: true,
                            position: 'top',
                            color: '#fff'
                        },
                        ...series,
                        // Ensure data exists
                        data: series.data || []
                    }))
                };

                log('Applying chart configuration:', enhancedConfig);
                
                // Set the configuration with error catching
                try {
                    chart.setOption(enhancedConfig, true);
                } catch (chartError) {
                    throw new Error(`Failed to apply chart configuration: ${chartError.message}`);
                }
                
                // Force a resize after setup
                setTimeout(() => {
                    try {
                        chart.resize();
                    } catch (resizeError) {
                        logError('Error resizing chart:', resizeError);
                    }
                }, 100);

                // Add to instances with error recovery
                chartInstances.push({ 
                    chart,
                    container: chartDiv,
                    config: enhancedConfig
                });
                
                log('Chart created successfully');
            } catch (error) {
                logError('Error creating individual chart:', error);
                const errorDiv = document.createElement('div');
                errorDiv.className = 'alert alert-danger';
                errorDiv.innerHTML = `
                    <div class="d-flex align-items-center">
                        <i class="bi bi-exclamation-triangle-fill me-2"></i>
                        <span>Failed to create visualization: ${error.message}</span>
                    </div>
                `;
                container.appendChild(errorDiv);
            }
        }

        // Update layout with error handling
        try {
            updateChartLayout();
        } catch (layoutError) {
            logError('Error updating chart layout:', layoutError);
        }

    } catch (error) {
        logError('Error in updateVisualizations:', error);
        showError('Failed to update visualizations: ' + error.message);
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
    let errorAlert = document.getElementById('errorAlert');
    
    // Create error alert if it doesn't exist
    if (!errorAlert) {
        errorAlert = document.createElement('div');
        errorAlert.id = 'errorAlert';
        errorAlert.className = 'alert alert-danger d-none';
        
        // Find a suitable container for the error alert
        const container = document.getElementById('visualizationContainer');
        if (container) {
            container.parentElement.insertBefore(errorAlert, container);
        } else {
            document.body.appendChild(errorAlert);
        }
    }

    errorAlert.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-exclamation-triangle-fill me-2"></i>
            <span>${message}</span>
        </div>
    `;
    errorAlert.classList.remove('d-none');
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorAlert.classList.add('d-none');
    }, 5000);
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
        Object.entries(valueMap).forEach(([parent, children], parentIndex) => {
            const parentNode = {
                name: parent,
                value: Object.values(children).reduce((a, b) => a + b, 0),
                itemStyle: {
                    color: THEME_COLORS[parentIndex % THEME_COLORS.length]
                },
                children: Object.entries(children).map(([child, value], childIndex) => ({
                    name: child,
                    value: value,
                    itemStyle: {
                        color: THEME_COLORS[(parentIndex + childIndex + 1) % THEME_COLORS.length]
                    }
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
                    borderColor: 'rgba(40, 44, 52, 0.9)',
                    borderWidth: 2,
                    gapWidth: 2
                }
            }, {
                colorSaturation: [0.7, 1],
                itemStyle: {
                    borderColor: 'rgba(40, 44, 52, 0.9)',
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
                },
                axisLine: {
                    lineStyle: {
                        color: '#666'
                    }
                }
            },
            yAxis: {
                type: 'value',
                axisLabel: { color: '#fff' },
                axisLine: {
                    lineStyle: {
                        color: '#666'
                    }
                },
                splitLine: {
                    lineStyle: {
                        color: 'rgba(84, 91, 102, 0.2)'
                    }
                }
            },
            series: [{
                type: 'bar',
                data: Object.entries(stats.frequencies).map(([name, value], index) => ({
                    value,
                    itemStyle: {
                        color: THEME_COLORS[index % THEME_COLORS.length]
                    }
                })),
                label: {
                    show: true,
                    position: 'top',
                    color: '#fff'
                }
            }]
        });

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
                    borderColor: 'rgba(40, 44, 52, 0.9)',
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
                data: Object.entries(stats.frequencies).map(([name, value], index) => ({
                    name,
                    value,
                    itemStyle: {
                        color: THEME_COLORS[index % THEME_COLORS.length]
                    }
                }))
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
    actions.style.zIndex = '100'; // Ensure actions are above the chart
    
    // Download button
    const downloadBtn = document.createElement('button');
    downloadBtn.className = 'chart-action-btn';
    downloadBtn.type = 'button'; // Explicitly set button type
    downloadBtn.innerHTML = '<i class="bi bi-download"></i>';
    downloadBtn.title = 'Download Chart';
    
    // Pin button
    const pinBtn = document.createElement('button');
    pinBtn.className = 'chart-action-btn';
    pinBtn.type = 'button'; // Explicitly set button type
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
    
    // Enhanced download handler with high quality export
    downloadBtn.addEventListener('click', async () => {
        try {
            // Show loading state on button
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<i class="bi bi-hourglass-split"></i>';
            
            // Get high quality PNG with 2x pixel ratio
            const dataURL = chart.getDataURL({
                type: 'png',
                pixelRatio: 2, // Force 2x pixel ratio for high quality
                backgroundColor: '#ffffff', // Ensure white background
                excludeComponents: ['toolbox'] // Exclude UI components from export
            });
            
            // Create filename based on chart title
            const title = chartConfig.title?.text || 'chart';
            const sanitizedTitle = title.toLowerCase().replace(/[^a-z0-9]/g, '_');
            const filename = `${sanitizedTitle}_${Date.now()}.png`;
            
            // Trigger download
            const link = document.createElement('a');
            link.download = filename;
            link.href = dataURL;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            // Show success state briefly
            downloadBtn.innerHTML = '<i class="bi bi-check-lg"></i>';
            setTimeout(() => {
                downloadBtn.innerHTML = '<i class="bi bi-download"></i>';
                downloadBtn.disabled = false;
            }, 1000);
        } catch (error) {
            logError('Error downloading chart:', error);
            showError('Failed to download chart');
            // Reset button state
            downloadBtn.innerHTML = '<i class="bi bi-download"></i>';
            downloadBtn.disabled = false;
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
