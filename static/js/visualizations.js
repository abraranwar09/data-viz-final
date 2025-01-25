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

// Function to generate visualizations from data
async function generateVisualizations(data) {
    try {
        log('Generating visualizations for data:', data);
        
        if (!data || !data.processed_data || !data.statistical_insights) {
            throw new Error('Invalid data format');
        }

        const insights = data.statistical_insights;
        const processedData = data.processed_data;
        const configs = [];

        // Add overview visualization
        configs.push({
            title: { text: 'Dataset Overview' },
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
                    formatter: '{b}: {c} ({d}%)'
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

        // Add visualizations for numeric columns
        for (const [column, stats] of Object.entries(insights.columns)) {
            // Distribution visualization
            configs.push({
                title: { text: `Distribution of ${column}` },
                tooltip: { trigger: 'axis' },
                grid: { containLabel: true },
                xAxis: {
                    type: 'category',
                    data: ['Mean', 'Median', 'Std Dev'],
                    axisLabel: { rotate: 30 }
                },
                yAxis: { type: 'value' },
                series: [{
                    type: 'bar',
                    data: [
                        {
                            value: stats.statistics.mean,
                            itemStyle: { color: '#37a2da' }
                        },
                        {
                            value: stats.statistics.median,
                            itemStyle: { color: '#67e0e3' }
                        },
                        {
                            value: stats.statistics.std,
                            itemStyle: { color: '#fd666d' }
                        }
                    ],
                    label: {
                        show: true,
                        position: 'top',
                        formatter: '{c:.2f}'
                    }
                }]
            });
        }

        // Add data quality visualization
        const quality = insights.data_quality;
        configs.push({
            title: { text: 'Data Quality Metrics' },
            tooltip: { trigger: 'axis' },
            grid: { containLabel: true },
            xAxis: {
                type: 'category',
                data: ['Completeness', 'Uniqueness', 'Consistency'],
                axisLabel: { rotate: 30 }
            },
            yAxis: {
                type: 'value',
                max: 100,
                axisLabel: { formatter: '{value}%' }
            },
            series: [{
                type: 'bar',
                data: [
                    {
                        value: parseFloat(quality.completeness.score),
                        itemStyle: { color: quality.completeness.rating === 'Excellent' ? '#28a745' : '#ffc107' }
                    },
                    {
                        value: parseFloat(quality.uniqueness.score),
                        itemStyle: { color: quality.uniqueness.rating === 'Excellent' ? '#28a745' : '#ffc107' }
                    },
                    {
                        value: parseFloat(quality.consistency.score),
                        itemStyle: { color: quality.consistency.rating === 'Excellent' ? '#28a745' : '#ffc107' }
                    }
                ],
                label: {
                    show: true,
                    position: 'top',
                    formatter: '{c}%'
                }
            }]
        });

        // Update visualizations with the generated configs
        await updateVisualizations(configs);
        
    } catch (error) {
        logError('Error generating visualizations:', error);
        showError('Failed to generate visualizations: ' + error.message);
    }
}
