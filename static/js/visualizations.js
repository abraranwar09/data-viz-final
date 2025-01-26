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

// Add tree chart support to generateVisualizations
async function generateVisualizations(data) {
    try {
        log('Generating visualizations for data:', data);
        
        if (!data || !data.processed_data || !data.statistical_insights) {
            throw new Error('Invalid data format');
        }

        const insights = data.statistical_insights;
        const processedData = data.processed_data;
        const configs = [];

        // Add tree chart for Education Level vs Previous Default
        configs.push(generateTreeChart(data, 'Education Level and Default Distribution'));

        // Dataset Overview - Gauge Chart
        configs.push({
            title: { 
                text: 'Dataset Overview',
                textStyle: { color: '#fff' }
            },
            tooltip: { trigger: 'item' },
            series: [{
                type: 'gauge',
                min: 0,
                max: Math.max(insights.dataset_overview.total_rows, 100),
                axisLine: {
                    lineStyle: {
                        color: [[0.3, '#67e0e3'], [0.7, '#37a2da'], [1, '#fd666d']]
                    }
                },
                pointer: { itemStyle: { color: 'auto' } },
                axisTick: { distance: -30, length: 8, lineStyle: { color: '#fff' } },
                splitLine: { distance: -30, length: 30, lineStyle: { color: '#fff' } },
                axisLabel: { color: '#fff', distance: -40, fontSize: 12 },
                detail: { valueAnimation: true, color: '#fff' },
                data: [
                    { value: insights.dataset_overview.total_rows, name: 'Total Rows' },
                    { value: insights.dataset_overview.total_columns, name: 'Total Columns' },
                    { value: insights.dataset_overview.memory_usage, name: 'Memory (MB)' }
                ]
            }]
        });

        // Column Types Distribution - Pie Chart
        configs.push({
            title: { 
                text: 'Column Types Distribution',
                textStyle: { color: '#fff' }
            },
            tooltip: { trigger: 'item' },
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
                data: [
                    {
                        value: insights.dataset_overview.column_types.numeric.count,
                        name: 'Numeric',
                        itemStyle: { color: '#37a2da' }
                    },
                    {
                        value: insights.dataset_overview.column_types.categorical.count,
                        name: 'Categorical',
                        itemStyle: { color: '#67e0e3' }
                    },
                    {
                        value: insights.dataset_overview.column_types.datetime.count,
                        name: 'DateTime',
                        itemStyle: { color: '#fd666d' }
                    },
                    {
                        value: insights.dataset_overview.column_types.other.count,
                        name: 'Other',
                        itemStyle: { color: '#ffdb5c' }
                    }
                ]
            }]
        });

        // For each numeric column
        for (const [column, stats] of Object.entries(insights.columns)) {
            if (stats.type === 'numeric') {
                // Distribution - Box Plot
                if (stats.distribution) {
                    configs.push({
                        title: { 
                            text: `Distribution: ${column}`,
                            textStyle: { color: '#fff' }
                        },
                        tooltip: { trigger: 'item' },
                        grid: { containLabel: true },
                        xAxis: {
                            type: 'category',
                            data: [column],
                            axisLabel: { color: '#fff' }
                        },
                        yAxis: {
                            type: 'value',
                            axisLabel: { color: '#fff' }
                        },
                        series: [{
                            type: 'boxplot',
                            data: [[
                                stats.distribution.min,
                                stats.distribution.q1,
                                stats.distribution.median,
                                stats.distribution.q3,
                                stats.distribution.max
                            ]],
                            itemStyle: {
                                color: '#37a2da',
                                borderColor: '#fff'
                            }
                        }]
                    });
                }

                // Histogram
                if (stats.histogram) {
                    configs.push({
                        title: { 
                            text: `Histogram: ${column}`,
                            textStyle: { color: '#fff' }
                        },
                        tooltip: { trigger: 'axis' },
                        grid: { containLabel: true },
                        xAxis: {
                            type: 'category',
                            data: stats.histogram.bins,
                            axisLabel: { 
                                color: '#fff',
                                rotate: 45
                            }
                        },
                        yAxis: {
                            type: 'value',
                            axisLabel: { color: '#fff' }
                        },
                        series: [{
                            type: 'bar',
                            data: stats.histogram.frequencies,
                            itemStyle: {
                                color: {
                                    type: 'linear',
                                    x: 0, y: 0, x2: 0, y2: 1,
                                    colorStops: [
                                        { offset: 0, color: '#83bff6' },
                                        { offset: 0.5, color: '#188df0' },
                                        { offset: 1, color: '#188df0' }
                                    ]
                                }
                            }
                        }]
                    });
                }
            } else if (stats.type === 'categorical') {
                // Bar Chart for Categorical Columns
                if (stats.value_counts) {
                    configs.push({
                        title: { 
                            text: `Value Distribution: ${column}`,
                            textStyle: { color: '#fff' }
                        },
                        tooltip: { trigger: 'axis' },
                        grid: { containLabel: true },
                        xAxis: {
                            type: 'category',
                            data: Object.keys(stats.value_counts),
                            axisLabel: { 
                                color: '#fff',
                                rotate: 45
                            }
                        },
                        yAxis: {
                            type: 'value',
                            axisLabel: { color: '#fff' }
                        },
                        series: [{
                            type: 'bar',
                            data: Object.values(stats.value_counts),
                            itemStyle: {
                                color: {
                                    type: 'linear',
                                    x: 0, y: 0, x2: 0, y2: 1,
                                    colorStops: [
                                        { offset: 0, color: '#67e0e3' },
                                        { offset: 1, color: '#37a2da' }
                                    ]
                                }
                            },
                            label: {
                                show: true,
                                position: 'top',
                                color: '#fff'
                            }
                        }]
                    });
                }
            }
        }

        // Correlation Heatmap
        if (insights.correlations) {
            configs.push({
                title: { 
                    text: 'Correlation Matrix',
                    textStyle: { color: '#fff' }
                },
                tooltip: { position: 'top' },
                grid: { 
                    height: '50%',
                    top: '10%'
                },
                xAxis: {
                    type: 'category',
                    data: insights.correlations.columns,
                    splitArea: { show: true },
                    axisLabel: { 
                        color: '#fff',
                        rotate: 45
                    }
                },
                yAxis: {
                    type: 'category',
                    data: insights.correlations.columns,
                    splitArea: { show: true },
                    axisLabel: { color: '#fff' }
                },
                visualMap: {
                    min: -1,
                    max: 1,
                    calculable: true,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: '15%',
                    textStyle: { color: '#fff' },
                    inRange: {
                        color: ['#fd666d', '#ffffff', '#37a2da']
                    }
                },
                series: [{
                    name: 'Correlation',
                    type: 'heatmap',
                    data: insights.correlations.values,
                    label: {
                        show: true,
                        color: '#fff',
                        formatter: (params) => params.value[2].toFixed(2)
                    },
                    emphasis: {
                        itemStyle: {
                            shadowBlur: 10,
                            shadowColor: 'rgba(0, 0, 0, 0.5)'
                        }
                    }
                }]
            });
        }

        // Data Quality Metrics - Radar Chart
        const quality = insights.data_quality;
        configs.push({
            title: { 
                text: 'Data Quality Metrics',
                textStyle: { color: '#fff' }
            },
            tooltip: { trigger: 'item' },
            radar: {
                indicator: [
                    { name: 'Completeness', max: 100 },
                    { name: 'Uniqueness', max: 100 },
                    { name: 'Consistency', max: 100 },
                    { name: 'Validity', max: 100 }
                ],
                axisName: {
                    color: '#fff'
                },
                splitArea: {
                    areaStyle: {
                        color: ['rgba(255,255,255,0.1)']
                    }
                },
                axisLine: {
                    lineStyle: {
                        color: 'rgba(255,255,255,0.2)'
                    }
                },
                splitLine: {
                    lineStyle: {
                        color: 'rgba(255,255,255,0.2)'
                    }
                }
            },
            series: [{
                type: 'radar',
                data: [{
                    value: [
                        parseFloat(quality.completeness.score),
                        parseFloat(quality.uniqueness.score),
                        parseFloat(quality.consistency.score),
                        parseFloat(quality.validity?.score || 0)
                    ],
                    name: 'Quality Scores',
                    areaStyle: {
                        color: 'rgba(55,162,218,0.6)'
                    },
                    lineStyle: {
                        color: '#37a2da'
                    },
                    itemStyle: {
                        color: '#37a2da'
                    }
                }]
            }]
        });

        // Update visualizations with the generated configs
        await updateVisualizations(configs);
        
    } catch (error) {
        logError('Error generating visualizations:', error);
        showError('Failed to generate visualizations: ' + error.message);
    }
}
