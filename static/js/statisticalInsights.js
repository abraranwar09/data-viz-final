class StatisticalInsights {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
    }

    displayInsights(data) {
        if (!data || !data.statistical_insights) return;
        
        const insights = data.statistical_insights;
        this.container.innerHTML = `
            <div class="insights-container">
                ${this._renderDatasetOverview(insights.dataset_overview)}
                ${this._renderDataQuality(insights.data_quality)}
                ${this._renderColumnInsights(insights.columns)}
            </div>
        `;
    }

    _renderDatasetOverview(overview) {
        if (!overview) return '';
        
        return `
            <div class="card mb-4">
                <div class="card-header d-flex align-items-center">
                    <i class="bi bi-table me-2"></i>
                    <h6 class="mb-0">Dataset Overview</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3 mb-3">
                            <div class="stat-box">
                                <div class="stat-label">Total Rows</div>
                                <div class="stat-value">${overview.total_rows}</div>
                            </div>
                        </div>
                        <div class="col-md-3 mb-3">
                            <div class="stat-box">
                                <div class="stat-label">Total Columns</div>
                                <div class="stat-value">${overview.total_columns}</div>
                            </div>
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-12">
                            <h6 class="text-muted mb-3">Column Distribution</h6>
                            <div class="d-flex justify-content-between">
                                ${this._renderColumnType('Numeric', overview.column_types.numeric)}
                                ${this._renderColumnType('Categorical', overview.column_types.categorical)}
                                ${this._renderColumnType('DateTime', overview.column_types.datetime)}
                                ${this._renderColumnType('Text/Other', overview.column_types.other)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderColumnType(label, data) {
        return `
            <div class="column-type-box">
                <div class="type-label">${label}</div>
                <div class="type-count">${data.count}</div>
                <div class="type-percentage">${data.percentage}</div>
            </div>
        `;
    }

    _renderDataQuality(quality) {
        if (!quality) return '';
        
        return `
            <div class="card mb-4">
                <div class="card-header d-flex align-items-center">
                    <i class="bi bi-check-circle me-2"></i>
                    <h6 class="mb-0">Data Quality Analysis</h6>
                </div>
                <div class="card-body">
                    <div class="row">
                        ${this._renderQualityMetric('Completeness', quality.completeness)}
                        ${this._renderQualityMetric('Uniqueness', quality.uniqueness)}
                        ${this._renderQualityMetric('Consistency', quality.consistency)}
                    </div>
                </div>
            </div>
        `;
    }

    _renderQualityMetric(label, metric) {
        return `
            <div class="col-md-4 mb-3">
                <div class="quality-metric">
                    <div class="metric-label">${label}</div>
                    <div class="metric-value ${metric.rating.toLowerCase()}">${metric.score}</div>
                    <div class="metric-rating">${metric.rating}</div>
                </div>
            </div>
        `;
    }

    _renderColumnInsights(columns) {
        if (!columns) return '';
        
        return `
            <div class="card">
                <div class="card-header d-flex align-items-center">
                    <i class="bi bi-graph-up me-2"></i>
                    <h6 class="mb-0">Statistical Insights</h6>
                </div>
                <div class="card-body">
                    ${Object.entries(columns).map(([column, stats]) => this._renderColumnStats(column, stats)).join('')}
                </div>
            </div>
        `;
    }

    _renderColumnStats(column, stats) {
        return `
            <div class="column-stats mb-4">
                <h6 class="stats-header">
                    <i class="bi bi-bar-chart me-2"></i>${column}
                </h6>
                <div class="row">
                    <div class="col-md-6">
                        <div class="stats-grid">
                            <div class="stat-item">
                                <span class="stat-label">Mean</span>
                                <span class="stat-value">${stats.statistics.mean.toFixed(2)}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Median</span>
                                <span class="stat-value">${stats.statistics.median.toFixed(2)}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">Std Dev</span>
                                <span class="stat-value">${stats.statistics.std.toFixed(2)}</span>
                            </div>
                            <div class="stat-item">
                                <span class="stat-label">CV</span>
                                <span class="stat-value">${stats.statistics.cv}</span>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="key-insights">
                            ${stats.key_insights.map(insight => `
                                <div class="insight-item">
                                    <i class="bi bi-lightbulb me-2"></i>
                                    ${insight}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
} 