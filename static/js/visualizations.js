function initializeCharts() {
    appState.charts = {
        histogram: echarts.init(document.getElementById('chart1')),
        scatter: echarts.init(document.getElementById('chart2')),
        boxplot: echarts.init(document.getElementById('chart3')),
        heatmap: echarts.init(document.getElementById('chart4'))
    };

    // Handle window resize
    window.addEventListener('resize', () => {
        Object.values(appState.charts).forEach(chart => chart.resize());
    });
}

function updateVisualizations(data) {
    const visualizationData = processData(data);
    
    updateHistogram(visualizationData.histogram);
    updateScatterPlot(visualizationData.scatter);
    updateBoxplot(visualizationData.boxplot);
    updateHeatmap(visualizationData.heatmap);
}

function updateHistogram(data) {
    const option = {
        title: { text: 'Distribution' },
        tooltip: {},
        xAxis: { type: 'category' },
        yAxis: { type: 'value' },
        series: [{
            type: 'bar',
            data: data.values
        }]
    };
    
    appState.charts.histogram.setOption(option);
}

function updateScatterPlot(data) {
    const option = {
        title: { text: 'Correlation' },
        tooltip: {},
        xAxis: { type: 'value' },
        yAxis: { type: 'value' },
        series: [{
            type: 'scatter',
            data: data.x.map((x, i) => [x, data.y[i]])
        }]
    };
    
    appState.charts.scatter.setOption(option);
}

function updateBoxplot(data) {
    const option = {
        title: { text: 'Distribution Summary' },
        tooltip: {},
        xAxis: { type: 'category' },
        yAxis: { type: 'value' },
        series: [{
            type: 'boxplot',
            data: data
        }]
    };
    
    appState.charts.boxplot.setOption(option);
}

function updateHeatmap(data) {
    const option = {
        title: { text: 'Correlation Matrix' },
        tooltip: {},
        xAxis: { type: 'category' },
        yAxis: { type: 'category' },
        visualMap: {
            min: -1,
            max: 1,
            calculable: true
        },
        series: [{
            type: 'heatmap',
            data: data
        }]
    };
    
    appState.charts.heatmap.setOption(option);
}
