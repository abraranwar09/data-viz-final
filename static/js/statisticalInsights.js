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
            <div class="card overview-card">
                <div class="card-header">
                    <span class="header-icon">📊</span>
                    <h6 class="mb-0">Dataset Overview</h6>
                    <span class="health-indicator">94% Health</span>
                </div>
                <div class="card-body">
                    <div class="metrics-grid">
                        <div class="metric-item">
                            <div class="metric-icon">📝</div>
                            <div class="metric-label">Total Rows</div>
                            <div class="metric-value">${overview.total_rows}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-icon">📊</div>
                            <div class="metric-label">Total Columns</div>
                            <div class="metric-value">${overview.total_columns}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-icon">💾</div>
                            <div class="metric-label">Memory Usage</div>
                            <div class="metric-value">${overview.memory_usage}</div>
                        </div>
                        <div class="metric-item">
                            <div class="metric-icon">🕒</div>
                            <div class="metric-label">Last Updated</div>
                            <div class="metric-value">${new Date().toLocaleTimeString()}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderDataQuality(quality) {
        if (!quality) return '';
        
        return `
            <div class="card quality-card">
                <div class="card-header">
                    <span class="header-icon">✨</span>
                    <h6 class="mb-0">Data Quality Analysis</h6>
                </div>
                <div class="card-body">
                    <div class="quality-grid">
                        ${this._renderQualityMetric('Completeness', quality.completeness)}
                        ${this._renderQualityMetric('Uniqueness', quality.uniqueness)}
                        ${this._renderQualityMetric('Consistency', quality.consistency)}
                        ${this._renderQualityMetric('Outlier Score', quality.outlier_score)}
                    </div>
                </div>
            </div>
        `;
    }

    _renderQualityMetric(label, metric) {
        if (!metric) return '';
        
        return `
            <div class="quality-metric">
                <div class="metric-icon ${metric.rating.toLowerCase()}">
                    ${this._getQualityIcon(metric.rating)}
                </div>
                <div class="metric-details">
                    <div class="metric-label">${label}</div>
                    <div class="metric-value ${metric.rating.toLowerCase()}">${metric.score}</div>
                    <div class="metric-rating">${metric.rating}</div>
                </div>
            </div>
        `;
    }

    _getQualityIcon(rating) {
        switch(rating.toLowerCase()) {
            case 'excellent': return '✅';
            case 'good': return '👍';
            case 'poor': return '⚠️';
            default: return '❓';
        }
    }

    _renderColumnInsights(columns) {
        if (!columns) return '';
        
        return `
            <div class="card distribution-card">
                <div class="card-header">
                    <span class="header-icon">📊</span>
                    <h6 class="mb-0">Column Analysis</h6>
                </div>
                <div class="card-body">
                    ${Object.entries(columns).map(([column, stats]) => this._renderColumnStats(column, stats)).join('')}
                </div>
            </div>
        `;
    }

    _renderColumnStats(column, stats) {
        if (!stats || !stats.statistics) return '';
        
        const insights = stats.key_insights || [];
        
        return `
            <div class="column-stats">
                <div class="stats-header">
                    <span class="column-icon">📊</span>
                    <span class="column-name">${column}</span>
                </div>
                <div class="stats-content">
                    <div class="stats-grid">
                        <div class="stats-row">
                            <div class="stat-group">
                                <div class="stat-item">
                                    <span class="stat-label">Mean</span>
                                    <span class="stat-value">${this._formatValue(stats.statistics.mean)}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Median</span>
                                    <span class="stat-value">${this._formatValue(stats.statistics.median)}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Std Dev</span>
                                    <span class="stat-value">${this._formatValue(stats.statistics.std)}</span>
                                </div>
                            </div>
                            <div class="stat-group">
                                <div class="stat-item">
                                    <span class="stat-label">CV</span>
                                    <span class="stat-value">${this._formatValue(stats.statistics.cv, '%')}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Kurtosis</span>
                                    <span class="stat-value">${this._formatValue(stats.statistics.kurtosis)}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">Skewness</span>
                                    <span class="stat-value">${this._formatValue(stats.statistics.skewness)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    ${insights.length > 0 ? `
                        <div class="insights-list">
                            ${insights.map(insight => `
                                <div class="insight-item">
                                    <span class="insight-icon">💡</span>
                                    ${insight}
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    _formatValue(value, suffix = '') {
        if (value === undefined || value === null) return 'N/A';
        if (typeof value === 'number') {
            // Handle percentage values
            if (suffix === '%') {
                return `${value.toFixed(1)}${suffix}`;
            }
            // Handle regular numbers
            return Math.abs(value) < 0.01 ? value.toExponential(2) : value.toFixed(2);
        }
        return value;
    }
} 