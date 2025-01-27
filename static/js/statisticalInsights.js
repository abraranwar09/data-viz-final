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
        
        // Initialize mini visualizations
        this._initializeMiniVisualizations();
    }

    _initializeMiniVisualizations() {
        // Initialize mini-gauges
        document.querySelectorAll('.mini-gauge').forEach(gauge => {
            const value = parseFloat(gauge.dataset.value);
            const min = parseFloat(gauge.dataset.min);
            const max = parseFloat(gauge.dataset.max);
            const percentage = ((value - min) / (max - min)) * 100;
            gauge.style.setProperty('--gauge-value', `${Math.min(Math.max(percentage, 0), 100)}%`);
            gauge.style.setProperty('--gauge-color', this._getColorForValue(percentage));
        });

        // Initialize sparklines
        document.querySelectorAll('.sparkline').forEach(sparkline => {
            const values = JSON.parse(sparkline.dataset.values);
            const max = Math.max(...values);
            const points = values.map((v, i) => {
                const x = (i / (values.length - 1)) * 40;
                const y = 20 - ((v / max) * 20);
                return `${x},${y}`;
            }).join(' ');
            
            sparkline.innerHTML = `
                <svg width="40" height="20" class="sparkline-svg">
                    <polyline
                        fill="none"
                        stroke="var(--bs-primary)"
                        stroke-width="1"
                        points="${points}"
                    />
                </svg>
            `;
        });

        // Initialize mini-bars
        document.querySelectorAll('.mini-bar').forEach(bar => {
            const width = parseFloat(bar.style.width);
            bar.style.setProperty('--bar-color', this._getColorForValue(width));
        });

        // Initialize mini histograms
        document.querySelectorAll('.mini-histogram').forEach(histogram => {
            const values = histogram.dataset.values.split(',').map(Number);
            histogram.innerHTML = values.map(value => `
                <div class="histogram-bar" style="height: ${value}%"></div>
            `).join('');
        });
    }

    _getColorForValue(percentage) {
        if (percentage <= 33) return 'var(--bs-danger)';
        if (percentage <= 66) return 'var(--bs-warning)';
        return 'var(--bs-success)';
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
        const quartiles = this._calculateQuartiles(stats.statistics);
        const healthScore = this._calculateHealthScore(stats.statistics);
        const availableMetrics = this._getAvailableMetrics(stats.statistics);
        
        return `
            <div class="column-stats">
                <div class="stats-header">
                    <div class="header-main">
                        <span class="column-icon">📊</span>
                        <span class="column-name">${column}</span>
                    </div>
                    <div class="header-stats">
                        <div class="data-health" style="--health-score: ${healthScore}%">
                            <div class="health-bar">
                                <div class="health-fill"></div>
                            </div>
                            <div class="health-label">Data Health: ${healthScore}%</div>
                        </div>
                        <div class="data-preview">
                            <div class="preview-bar">
                                ${this._generatePreviewBars(stats.statistics)}
                            </div>
                            <div class="preview-markers">
                                <div class="preview-marker mean" style="left: ${this._getPercentagePosition(stats.statistics.mean, stats.statistics.min, stats.statistics.max)}%"></div>
                                <div class="preview-marker median" style="left: ${this._getPercentagePosition(stats.statistics.median, stats.statistics.min, stats.statistics.max)}%"></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="stats-grid" data-metrics-count="${availableMetrics.length}">
                    ${this._renderDistributionOverview(stats, quartiles)}
                    <div class="stats-details" style="--columns: ${this._calculateGridColumns(availableMetrics)}">
                        ${this._renderMetricGroups(stats, availableMetrics)}
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
        `;
    }

    _getAvailableMetrics(stats) {
        const metrics = [];
        
        // Check Central Tendency metrics
        if (this._hasValidValues([stats.mean, stats.median, stats.mode])) {
            metrics.push({
                type: 'central',
                label: 'Central Tendency',
                values: {
                    mean: stats.mean,
                    median: stats.median,
                    mode: stats.mode
                }
            });
        }
        
        // Check Dispersion metrics
        if (this._hasValidValues([stats.std, stats.cv]) || 
            this._hasValidValues([stats.q1, stats.q3])) {
            metrics.push({
                type: 'dispersion',
                label: 'Dispersion',
                values: {
                    std: stats.std,
                    cv: stats.cv,
                    iqr: stats.q3 - stats.q1
                }
            });
        }
        
        // Check Shape metrics
        if (this._hasValidValues([stats.skewness, stats.kurtosis])) {
            metrics.push({
                type: 'shape',
                label: 'Shape',
                values: {
                    skewness: stats.skewness,
                    kurtosis: stats.kurtosis
                }
            });
        }
        
        return metrics;
    }

    _hasValidValues(values) {
        return values.some(v => v !== undefined && v !== null && !isNaN(v));
    }

    _calculateGridColumns(metrics) {
        const count = metrics.length;
        if (count <= 1) return 1;
        if (count === 2) return 2;
        return 3;
    }

    _renderDistributionOverview(stats, quartiles) {
        return `
            <div class="stat-row">
                <div class="stat-item stat-item-large">
                    <div class="distribution-container">
                        <div class="distribution-header">
                            <span class="stat-label">Distribution Overview</span>
                            <div class="distribution-legend">
                                <span class="legend-item"><span class="legend-color mean"></span>Mean (${this._formatValue(stats.statistics.mean)})</span>
                                <span class="legend-item"><span class="legend-color median"></span>Median (${this._formatValue(stats.statistics.median)})</span>
                                <span class="legend-item"><span class="legend-color quartile"></span>IQR (${this._formatValue(stats.statistics.q3 - stats.statistics.q1)})</span>
                            </div>
                        </div>
                        <div class="distribution-preview">
                            <div class="quartile-box" style="left: ${quartiles.q1}%; width: ${quartiles.iqr}%"></div>
                            <div class="dist-marker mean" style="left: ${this._getPercentagePosition(stats.statistics.mean, stats.statistics.min, stats.statistics.max)}%" title="Mean: ${this._formatValue(stats.statistics.mean)}">
                                <span class="marker-label">μ</span>
                            </div>
                            <div class="dist-marker median" style="left: ${this._getPercentagePosition(stats.statistics.median, stats.statistics.min, stats.statistics.max)}%" title="Median: ${this._formatValue(stats.statistics.median)}">
                                <span class="marker-label">M</span>
                            </div>
                            <div class="dist-range">
                                <span class="range-min">${this._formatValue(stats.statistics.min)}</span>
                                <span class="range-q1">${this._formatValue(stats.statistics.q1)}</span>
                                <span class="range-q3">${this._formatValue(stats.statistics.q3)}</span>
                                <span class="range-max">${this._formatValue(stats.statistics.max)}</span>
                            </div>
                        </div>
                        <div class="mini-histogram" data-values="${this._generateHistogramData(stats.statistics)}"></div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderMetricGroups(stats, metrics) {
        return metrics.map(metric => {
            switch (metric.type) {
                case 'central':
                    return this._renderCentralTendencyMetrics(metric.values);
                case 'dispersion':
                    return this._renderDispersionMetrics(metric.values, stats.statistics);
                case 'shape':
                    return this._renderShapeMetrics(metric.values);
                default:
                    return '';
            }
        }).join('');
    }

    _renderCentralTendencyMetrics(values) {
        return `
            <div class="stat-column">
                <div class="stat-item">
                    <span class="stat-label">Central Tendency</span>
                    <div class="stat-value-container">
                        <div class="tendency-metrics">
                            ${values.mean !== undefined ? `
                                <div class="tendency-metric">
                                    <span class="metric-name">Mean</span>
                                    <span class="metric-value">${this._formatValue(values.mean)}</span>
                                    <div class="mini-gauge" data-value="${values.mean}" data-min="${values.min}" data-max="${values.max}"></div>
                                </div>
                            ` : ''}
                            ${values.median !== undefined ? `
                                <div class="tendency-metric">
                                    <span class="metric-name">Median</span>
                                    <span class="metric-value">${this._formatValue(values.median)}</span>
                                    <div class="mini-gauge" data-value="${values.median}" data-min="${values.min}" data-max="${values.max}"></div>
                                </div>
                            ` : ''}
                            ${values.mode !== undefined ? `
                                <div class="tendency-metric">
                                    <span class="metric-name">Mode</span>
                                    <span class="metric-value">${this._formatValue(values.mode)}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderDispersionMetrics(values, stats) {
        return `
            <div class="stat-column">
                <div class="stat-item">
                    <span class="stat-label">Dispersion</span>
                    <div class="stat-value-container">
                        <div class="dispersion-metrics">
                            ${values.std !== undefined ? `
                                <div class="dispersion-metric">
                                    <span class="metric-name">Std Dev</span>
                                    <span class="metric-value">${this._formatValue(values.std)}</span>
                                    <div class="sparkline" data-values="[${values.std}, ${stats.mean}]"></div>
                                </div>
                            ` : ''}
                            ${values.cv !== undefined ? `
                                <div class="dispersion-metric">
                                    <span class="metric-name">CV</span>
                                    <span class="metric-value">${this._formatValue(values.cv, '%')}</span>
                                    <div class="mini-bar" style="width: ${Math.min(values.cv * 100, 100)}%"></div>
                                </div>
                            ` : ''}
                            ${values.iqr !== undefined ? `
                                <div class="dispersion-metric">
                                    <span class="metric-name">IQR</span>
                                    <span class="metric-value">${this._formatValue(values.iqr)}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _renderShapeMetrics(values) {
        return `
            <div class="stat-column">
                <div class="stat-item">
                    <span class="stat-label">Shape</span>
                    <div class="stat-value-container">
                        <div class="shape-metrics">
                            ${values.kurtosis !== undefined ? `
                                <div class="shape-metric">
                                    <span class="metric-name">Kurtosis</span>
                                    <div class="shape-value">
                                        <span class="metric-value">${this._formatValue(values.kurtosis)}</span>
                                        <div class="distribution-shape" data-kurtosis="${values.kurtosis}"></div>
                                        <span class="distribution-label">${this._getKurtosisLabel(values.kurtosis)}</span>
                                    </div>
                                </div>
                            ` : ''}
                            ${values.skewness !== undefined ? `
                                <div class="shape-metric">
                                    <span class="metric-name">Skewness</span>
                                    <div class="shape-value">
                                        <span class="metric-value">${this._formatValue(values.skewness)}</span>
                                        <div class="distribution-shape" data-skewness="${values.skewness}"></div>
                                        <span class="distribution-label">${this._getSkewnessLabel(values.skewness)}</span>
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    _calculateQuartiles(stats) {
        const q1Pos = this._getPercentagePosition(stats.q1, stats.min, stats.max);
        const q3Pos = this._getPercentagePosition(stats.q3, stats.min, stats.max);
        return {
            q1: q1Pos,
            q3: q3Pos,
            iqr: q3Pos - q1Pos
        };
    }

    _calculateHealthScore(stats) {
        // Calculate a health score based on multiple factors
        const factors = [];
        
        // Data completeness (missing values)
        const completeness = ((stats.count - (stats.missing || 0)) / stats.count) * 100;
        factors.push(completeness);
        
        // Distribution normality (based on skewness and kurtosis)
        const skewnessScore = Math.max(0, 100 - Math.abs(stats.skewness) * 20);
        const kurtosisScore = Math.max(0, 100 - Math.abs(stats.kurtosis - 3) * 10);
        factors.push(skewnessScore, kurtosisScore);
        
        // Outlier presence
        const outlierScore = 100 - (stats.outliers_percentage || 0);
        factors.push(outlierScore);
        
        // Calculate weighted average
        return Math.round(factors.reduce((a, b) => a + b, 0) / factors.length);
    }

    _generatePreviewBars(stats) {
        // Generate a series of bars representing the data distribution
        const bins = 20;
        const values = this._generateHistogramData(stats).split(',').map(Number);
        
        return values.map(value => `
            <div class="preview-bar-segment" style="height: ${value}%">
                <div class="bar-highlight" style="opacity: ${value / 100}"></div>
            </div>
        `).join('');
    }

    _generateHistogramData(stats) {
        // Generate histogram data based on actual statistics
        const bins = 20;
        const range = stats.max - stats.min;
        const binWidth = range / bins;
        
        // Create a normal distribution approximation using mean and std
        const values = Array(bins).fill(0).map((_, i) => {
            const x = stats.min + (i + 0.5) * binWidth;
            const z = (x - stats.mean) / stats.std;
            return Math.exp(-0.5 * z * z) / (stats.std * Math.sqrt(2 * Math.PI));
        });
        
        // Normalize to percentages
        const max = Math.max(...values);
        return values.map(v => (v / max) * 100).join(',');
    }

    _getPercentagePosition(value, min, max) {
        return ((value - min) / (max - min)) * 100;
    }

    _getKurtosisLabel(kurtosis) {
        if (kurtosis > 3) return 'Heavy-tailed';
        if (kurtosis < 3) return 'Light-tailed';
        return 'Normal';
    }

    _getSkewnessLabel(skewness) {
        if (skewness > 0.5) return 'Right-skewed';
        if (skewness < -0.5) return 'Left-skewed';
        return 'Symmetric';
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