/**
 * Visualization System Core Module
 * 
 * This module implements SOLID principles in the following ways:
 * 
 * Single Responsibility Principle (SRP):
 * - Each function has a single, well-defined purpose
 * - Chart creation, updating, and management are separated into distinct functions
 * - Data processing and visualization logic are kept separate
 * 
 * Open/Closed Principle (OCP):
 * - The visualization system is extensible for new chart types without modifying existing code
 * - New chart configurations can be added by extending the config generation functions
 * - Chart styling and themes are separate from core functionality
 * 
 * Liskov Substitution Principle (LSP):
 * - All chart types follow the same interface pattern
 * - Any chart implementation can be substituted without affecting the rest of the system
 * - Chart containers are consistent and interchangeable
 * 
 * Interface Segregation Principle (ISP):
 * - Chart configurations are modular and specific to each chart type
 * - Event handlers are separated by responsibility
 * - UI components are isolated from data processing logic
 * 
 * Dependency Inversion Principle (DIP):
 * - The system depends on abstractions (chart configs) rather than concrete implementations
 * - Data processing is independent of visualization rendering
 * - Chart initialization is decoupled from specific chart types
 */

let chartInstances = [];
let pinnedCharts = [];
const MAX_PINNED_CHARTS = 2;
const MAX_CHARTS = 6; // Updated to 6 as requested
const DEBUG = true;
const LOG_PREFIX = '[Visualization]';
const ERROR_PREFIX = '[Visualization Error]';

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
        console.log(LOG_PREFIX, ...args);
    }
}

function logError(...args) {
    console.error(ERROR_PREFIX, ...args);
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
    log('Received visualization configs:', configs);
    
    if (!Array.isArray(configs)) {
        logError('Invalid configs format:', configs);
        showError('Invalid visualization configuration format');
        return;
    }

    // Enhanced validation and transformation with more flexible data handling
    configs = configs.filter(config => {
        log('Validating config:', config);
        
        // Validate basic structure
        if (!config || typeof config !== 'object') {
            logError('Invalid config structure:', config);
            return false;
        }
        
        // Handle different valid E-charts data formats
        if (config.dataset && config.dataset.source) {
            log('Valid dataset format found');
            return true;
        }
        
        if (config.series && Array.isArray(config.series)) {
            log('Processing series data');
            // Transform and validate each series
            config.series = config.series.map(series => {
                log('Processing series:', series);
                
                // Handle different data formats
                if (series.data === undefined && series.source) {
                    log('Converting source to data:', series.source);
                    series.data = series.source;
                }
                
                // Convert single value to array if needed
                if (series.data !== undefined && !Array.isArray(series.data)) {
                    log('Converting single value to array:', series.data);
                    series.data = [series.data];
                }
                
                // Initialize empty data array if none exists
                if (!series.data) {
                    log('Initializing empty data array');
                    series.data = [];
                }
                
                // Ensure type is set
                if (!series.type) {
                    log('Setting default chart type: bar');
                    series.type = 'bar'; // Default to bar chart
                }
                
                return series;
            });
            return true;
        }
        
        logError('Invalid config format:', config);
        return false;
    });

    log('Filtered configs:', configs);
    
    if (configs.length === 0) {
        logError('No valid visualization configs found');
        showError('No valid visualization configurations found');
        return;
    }
    
    // Limit number of visualizations
    configs = configs.slice(0, 3);
    log('Limited configs:', configs);
    
    const container = document.getElementById('visualizationContainer');
    if (!container) {
        logError('Visualization container not found');
        showError('Visualization container not found');
        return;
    }

    try {
        log('Starting visualization update');
        showLoadingState();

        // Clear existing charts if in single view mode
        const isSingleView = container.classList.contains('single-view');
        if (isSingleView) {
            log('Single view mode - cleaning up existing charts');
            cleanupCharts();
            container.innerHTML = '';
        }

        // Process each configuration
        for (const config of configs) {
            try {
                log('Creating chart with config:', config);
                
                // Create container for this chart
                const chartDiv = document.createElement('div');
                chartDiv.className = 'chart-container';
                chartDiv.style.width = '100%';
                chartDiv.style.height = '400px';
                container.appendChild(chartDiv);

                // Initialize chart with explicit size
                log('Initializing ECharts instance');
                const chart = echarts.init(chartDiv, null, {
                    renderer: 'canvas',
                    useDirtyRect: false
                });
                
                log('Setting chart configuration');
                chart.setOption(config);
                
                log('Chart created successfully');
                
                // Add resize observer
                const resizeObserver = new ResizeObserver(() => {
                    log('Container resized - updating chart');
                    chart.resize();
                });
                resizeObserver.observe(chartDiv);
                
                // Store chart instance
                chartInstances.push({ chart, container: chartDiv, resizeObserver });
                
            } catch (error) {
                logError('Error creating chart:', error);
                showError(`Failed to create chart: ${error.message}`);
                // Remove the failed chart's container
                chartDiv.remove();
            }
        }
        
        log('All charts created successfully');
        updateChartLayout();
        hideLoadingState();
        
    } catch (error) {
        logError('Error in visualization update:', error);
        showError(`Failed to update visualizations: ${error.message}`);
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
    console.log('Generating categorical charts with data:', data);
    const configs = [];
    
    if (!data.categorical) {
        console.warn('No categorical data found');
        return configs;
    }
    
    // For each categorical column
    Object.entries(data.categorical).forEach(([column, columnData]) => {
        console.log(`Processing column ${column} with data:`, columnData);
        
        if (!columnData || !columnData.frequencies) {
            console.warn(`Missing data or frequencies for column ${column}`);
            return;
        }

        const frequencies = columnData.frequencies;
        console.log(`Frequencies for ${column}:`, frequencies);
        
        const sortedData = Object.entries(frequencies)
            .sort(([, a], [, b]) => b - a) // Sort by frequency descending
            .map(([category, count], index) => ({
                name: category,
                value: count,
                itemStyle: {
                    color: THEME_COLORS[index % THEME_COLORS.length]
                }
            }));
            
        console.log(`Sorted data for ${column}:`, sortedData);

        // Bar Chart
        const barConfig = {
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
                data: sortedData.map(item => item.name),
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
                name: 'Count',
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
                data: sortedData,
                label: {
                    show: true,
                    position: 'top',
                    color: '#fff'
                }
            }]
        };
        
        console.log(`Bar chart config for ${column}:`, barConfig);
        configs.push(barConfig);

        // Pie Chart
        const pieConfig = {
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
                data: sortedData
            }]
        };
        
        console.log(`Pie chart config for ${column}:`, pieConfig);
        configs.push(pieConfig);
    });
    
    console.log('Generated chart configs:', configs);
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
        
        // Handle relationship analysis from AI assistant
        if (data.analysis_request) {
            const { variables, type, metrics } = data.analysis_request;
            
            // Get the actual data for the requested variables
            const variableData = variables.map(v => ({
                name: v,
                values: data.processed_data.preview.map(row => row[v]),
                type: data.processed_data.column_stats[v]?.type
            }));

            // Generate appropriate visualization based on variable types and analysis request
            const analysisConfig = generateAnalysisVisualization(variableData, type, metrics);
            if (analysisConfig) {
                configs.push(analysisConfig);
            }
        }
        
        // Add categorical visualizations if no specific analysis is requested
        if (!data.analysis_request && data.processed_data.categorical) {
            configs.push(...generateCategoricalCharts(data.processed_data));
        }
        
        // Update visualizations with the generated configs
        if (configs.length > 0) {
            await updateVisualizations(configs);
        } else {
            throw new Error('No visualization configurations could be generated');
        }
        
    } catch (error) {
        logError('Error generating visualizations:', error);
        showError('Failed to generate visualizations: ' + error.message);
    }
}

// Update generateAnalysisVisualization function
function generateAnalysisVisualization(variables, type, metrics = []) {
    try {
        // Enhanced data validation and cleaning
        const cleanVariables = variables.map(v => {
            // Get the raw data and stats for this variable
            const rawData = v.values;
            const stats = window.appState.currentData.column_stats[v.name];
            
            // Clean and validate the data
            const cleanValues = v.type === 'numeric' 
                ? rawData.map(val => Number(val)).filter(val => !isNaN(val))
                : rawData.filter(val => val != null && val !== '');
            
            return {
                name: v.name,
                type: v.type,
                values: cleanValues,
                stats: stats || {},
                raw_values: rawData
            };
        });

        // Log the cleaned data for debugging
        console.log('Clean variables for visualization:', cleanVariables);

        // Get variable types
        const types = cleanVariables.map(v => v.type);

        // Generate appropriate chart configuration based on variable types
        if (types.includes('categorical') && types.includes('numeric')) {
            return generateCategoricalNumericChart(cleanVariables, metrics);
        } else if (types.every(t => t === 'numeric')) {
            return generateNumericChart(cleanVariables, metrics);
        } else if (types.every(t => t === 'categorical')) {
            return generateCategoricalChart(cleanVariables, metrics);
        }

        return null;
    } catch (error) {
        logError('Error generating analysis visualization:', error);
        return null;
    }
}

function generateCategoricalNumericChart(variables, metrics = []) {
    // Find categorical and numeric variables
    const categoricalVar = variables.find(v => v.type === 'categorical');
    const numericVar = variables.find(v => v.type === 'numeric');
    
    if (!categoricalVar || !numericVar) {
        throw new Error('Required variables not found');
    }
    
    // Group numeric values by categories
    const groupedData = {};
    for (let i = 0; i < categoricalVar.values.length; i++) {
        const category = categoricalVar.values[i];
        const value = numericVar.values[i];
        
        if (category != null && !isNaN(value)) {
            if (!groupedData[category]) {
                groupedData[category] = [];
            }
            groupedData[category].push(value);
        }
    }
    
    // Calculate statistics for each group
    const stats = Object.entries(groupedData).map(([category, values]) => {
        const sorted = [...values].sort((a, b) => a - b);
        return {
            category,
            count: values.length,
            mean: values.reduce((a, b) => a + b, 0) / values.length,
            median: sorted[Math.floor(sorted.length / 2)],
            min: Math.min(...values),
            max: Math.max(...values),
            q1: sorted[Math.floor(sorted.length * 0.25)],
            q3: sorted[Math.floor(sorted.length * 0.75)],
            values
        };
    });
    
    // Create chart configuration
    return {
        title: {
            text: `${numericVar.name} by ${categoricalVar.name}`,
            left: 'center'
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            },
            formatter: function(params) {
                const stat = stats.find(s => s.category === params[0].name);
                if (!stat) return '';
                
                return `
                    <strong>${params[0].name}</strong><br/>
                    Count: ${stat.count}<br/>
                    Mean: ${stat.mean.toFixed(2)}<br/>
                    Median: ${stat.median.toFixed(2)}<br/>
                    Min: ${stat.min.toFixed(2)}<br/>
                    Max: ${stat.max.toFixed(2)}<br/>
                    Q1: ${stat.q1.toFixed(2)}<br/>
                    Q3: ${stat.q3.toFixed(2)}
                `;
            }
        },
        legend: {
            data: ['Mean', 'Box Plot'],
            top: 30
        },
        grid: {
            top: 80,
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: stats.map(s => s.category),
            name: categoricalVar.name,
            axisLabel: {
                rotate: 45
            }
        },
        yAxis: {
            type: 'value',
            name: numericVar.name
        },
        series: [
            {
                name: 'Mean',
                type: 'bar',
                data: stats.map(s => s.mean),
                itemStyle: {
                    color: '#91cc75'
                }
            },
            {
                name: 'Box Plot',
                type: 'boxplot',
                data: stats.map(s => [s.min, s.q1, s.median, s.q3, s.max]),
                itemStyle: {
                    color: '#5470c6'
                }
            }
        ]
    };
}

function generateNumericChart(variables, metrics = []) {
    if (variables.length === 1) {
        // Single numeric variable - create histogram
        const variable = variables[0];
        const values = variable.values;
        
        // Calculate histogram bins
        const binCount = Math.min(20, Math.ceil(Math.sqrt(values.length)));
        const min = Math.min(...values);
        const max = Math.max(...values);
        const binWidth = (max - min) / binCount;
        
        const bins = Array(binCount).fill(0);
        values.forEach(value => {
            const binIndex = Math.min(
                Math.floor((value - min) / binWidth),
                binCount - 1
            );
            bins[binIndex]++;
        });
        
        const binLabels = Array(binCount).fill(0).map((_, i) => {
            const start = min + (i * binWidth);
            const end = start + binWidth;
            return `${start.toFixed(2)} - ${end.toFixed(2)}`;
        });
        
        return {
            title: {
                text: `Distribution of ${variable.name}`,
                left: 'center'
            },
            tooltip: {
                trigger: 'axis',
                formatter: function(params) {
                    return `
                        <strong>${params[0].name}</strong><br/>
                        Count: ${params[0].value}
                    `;
                }
            },
            xAxis: {
                type: 'category',
                data: binLabels,
                name: variable.name,
                axisLabel: {
                    rotate: 45
                }
            },
            yAxis: {
                type: 'value',
                name: 'Count'
            },
            series: [{
                type: 'bar',
                data: bins,
                itemStyle: {
                    color: '#5470c6'
                }
            }]
        };
    } else {
        // Multiple numeric variables - create scatter plot
        const xVar = variables[0];
        const yVar = variables[1];
        
        // Pair the values
        const data = xVar.values.map((x, i) => [x, yVar.values[i]])
            .filter(([x, y]) => !isNaN(x) && !isNaN(y));
        
        return {
            title: {
                text: `${xVar.name} vs ${yVar.name}`,
                left: 'center'
            },
            tooltip: {
                trigger: 'item',
                formatter: function(params) {
                    return `
                        <strong>Point</strong><br/>
                        ${xVar.name}: ${params.value[0].toFixed(2)}<br/>
                        ${yVar.name}: ${params.value[1].toFixed(2)}
                    `;
                }
            },
            xAxis: {
                type: 'value',
                name: xVar.name
            },
            yAxis: {
                type: 'value',
                name: yVar.name
            },
            series: [{
                type: 'scatter',
                data: data,
                itemStyle: {
                    color: '#5470c6'
                }
            }]
        };
    }
}

//comment for commit

function generateCategoricalChart(variables, metrics = []) {
    const variable = variables[0];
    const frequencies = {};
    
    // Calculate frequencies
    variable.values.forEach(value => {
        if (value != null) {
            frequencies[value] = (frequencies[value] || 0) + 1;
        }
    });
    
    // Convert to array of objects
    const data = Object.entries(frequencies)
        .map(([name, value]) => ({ name, value }))
        .sort((a, b) => b.value - a.value);
    
    return {
        title: {
            text: `Distribution of ${variable.name}`,
            left: 'center'
        },
        tooltip: {
            trigger: 'item',
            formatter: function(params) {
                const percentage = ((params.value / variable.values.length) * 100).toFixed(1);
                return `
                    <strong>${params.name}</strong><br/>
                    Count: ${params.value}<br/>
                    Percentage: ${percentage}%
                `;
            }
        },
        series: [
            {
                type: 'pie',
                radius: '50%',
                data: data,
                emphasis: {
                    itemStyle: {
                        shadowBlur: 10,
                        shadowOffsetX: 0,
                        shadowColor: 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }
        ]
    };
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
