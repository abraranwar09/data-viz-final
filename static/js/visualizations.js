function initializeCharts() {
    try {
        if (!window.appState) {
            throw new Error('Application state not initialized');
        }

        // Initialize chart containers
        window.appState.charts = {
            histogram: echarts.init(document.getElementById('chart1')),
            scatter: echarts.init(document.getElementById('chart2')),
            boxplot: echarts.init(document.getElementById('chart3')),
            heatmap: echarts.init(document.getElementById('chart4'))
        };

        // Handle window resize
        window.addEventListener('resize', () => {
            Object.values(window.appState.charts).forEach(chart => {
                if (chart && typeof chart.resize === 'function') {
                    chart.resize();
                }
            });
        });

        window.appState.initialized = true;
    } catch (error) {
        console.error('Failed to initialize charts:', error);
        showError('Failed to initialize visualization components');
    }
}

function updateVisualizations(data) {
    if (!window.appState || !window.appState.initialized) {
        console.error('Charts not initialized');
        return;
    }

    if (!data || !data.column_stats) {
        console.error('Invalid data format for visualizations');
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
    if (!data || !data.values || !data.values.length) {
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
    if (!data || !data.x || !data.y || !data.x.length || !data.y.length) {
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
    if (!data || !Array.isArray(data) || !data.length) {
        console.warn('Invalid heatmap data');
        return;
    }

    const option = {
        title: { text: 'Correlation Matrix' },
        tooltip: {
            position: 'top',
            formatter: function(params) {
                return `${params.value[2]}`;
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
