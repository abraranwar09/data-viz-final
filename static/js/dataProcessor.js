function processData(data) {
    if (!data || !data.column_stats) {
        console.error('Invalid data format');
        return null;
    }

    try {
        // Get column types from cleaned data
        const categoricalColumns = Object.entries(data.column_stats)
            .filter(([_, stats]) => stats.type === 'categorical')
            .map(([col, _]) => col);

        const numericColumns = Object.entries(data.column_stats)
            .filter(([_, stats]) => stats.type === 'numeric')
            .map(([col, _]) => col);

        let processedData = {};

        // Handle categorical data
        if (categoricalColumns.length > 0) {
            const catData = prepareCategoricalData(data, categoricalColumns);
            if (catData) {
                processedData.categorical = catData;
            }
        }

        // Handle numeric data
        if (numericColumns.length > 0) {
            const numericData = {
                histogram: prepareHistogramData(data, numericColumns[0]),
                scatter: prepareScatterData(data, numericColumns[0], numericColumns[1]),
                boxplot: prepareBoxplotData(data, numericColumns),
                heatmap: prepareHeatmapData(data, numericColumns)
            };

            // Only add numeric data if at least one visualization was created
            if (Object.values(numericData).some(v => v !== null)) {
                processedData = { ...processedData, ...numericData };
            }
        }

        return processedData;
    } catch (error) {
        console.error('Error processing data:', error);
        return null;
    }
}

function validateNumericValues(values) {
    return values.filter(v => 
        v !== null && 
        v !== undefined && 
        !isNaN(v) && 
        typeof v !== 'boolean'
    ).map(v => Number(v));
}

function prepareHistogramData(data, column) {
    if (!column || !data.preview || !data.preview.length) {
        return null;
    }

    try {
        const values = validateNumericValues(data.preview.map(row => row[column]));
        if (!values.length) return null;

        // Create histogram bins
        const binCount = Math.min(10, Math.ceil(Math.sqrt(values.length)));
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

        return {
            column,
            values: bins,
            bins: Array(binCount).fill(0).map((_, i) => 
                `${(min + i * binWidth).toFixed(2)} - ${(min + (i + 1) * binWidth).toFixed(2)}`
            )
        };
    } catch (error) {
        console.error('Error preparing histogram data:', error);
        return null;
    }
}

function prepareScatterData(data, columnX, columnY) {
    if (!columnX || !columnY || !data.preview || !data.preview.length) {
        return null;
    }

    try {
        const pairedData = data.preview
            .map(row => [row[columnX], row[columnY]])
            .filter(([x, y]) => 
                x !== null && y !== null && 
                !isNaN(x) && !isNaN(y)
            );

        if (!pairedData.length) return null;

        return {
            x: pairedData.map(d => d[0]),
            y: pairedData.map(d => d[1]),
            xLabel: columnX,
            yLabel: columnY
        };
    } catch (error) {
        console.error('Error preparing scatter data:', error);
        return null;
    }
}

function prepareBoxplotData(data, columns) {
    if (!columns || !columns.length) {
        return null;
    }

    try {
        return columns
            .filter(col => data.column_stats[col] && data.column_stats[col].type === 'numeric')
            .map(col => ({
                name: col,
                stats: {
                    min: data.column_stats[col].min,
                    q1: data.column_stats[col].q1 || data.column_stats[col].min,
                    median: data.column_stats[col].median,
                    q3: data.column_stats[col].q3 || data.column_stats[col].max,
                    max: data.column_stats[col].max
                }
            }));
    } catch (error) {
        console.error('Error preparing boxplot data:', error);
        return null;
    }
}

function prepareHeatmapData(data, columns) {
    if (!columns || columns.length < 2) {
        return null;
    }

    try {
        const correlationMatrix = {
            columns: columns,
            values: []
        };

        // Calculate correlations between numeric columns
        for (let i = 0; i < columns.length; i++) {
            for (let j = 0; j < columns.length; j++) {
                const correlation = i === j ? 1 : calculateCorrelation(
                    data.preview.map(row => row[columns[i]]),
                    data.preview.map(row => row[columns[j]])
                );
                correlationMatrix.values.push([i, j, correlation || 0]);
            }
        }

        return correlationMatrix;
    } catch (error) {
        console.error('Error preparing heatmap data:', error);
        return null;
    }
}

function calculateCorrelation(x, y) {
    try {
        const validPairs = x.map((val, i) => [val, y[i]])
            .filter(([a, b]) => 
                a !== null && b !== null && 
                !isNaN(a) && !isNaN(b)
            );

        if (validPairs.length < 2) return null;

        const n = validPairs.length;
        const [xs, ys] = validPairs.reduce(
            ([accX, accY], [currX, currY]) => [
                [...accX, Number(currX)],
                [...accY, Number(currY)]
            ],
            [[], []]
        );

        const sumX = xs.reduce((a, b) => a + b, 0);
        const sumY = ys.reduce((a, b) => a + b, 0);
        const sumXY = xs.reduce((sum, x, i) => sum + x * ys[i], 0);
        const sumX2 = xs.reduce((sum, x) => sum + x * x, 0);
        const sumY2 = ys.reduce((sum, y) => sum + y * y, 0);

        const numerator = n * sumXY - sumX * sumY;
        const denominator = Math.sqrt(
            (n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY)
        );

        return denominator === 0 ? 0 : numerator / denominator;
    } catch (error) {
        console.error('Error calculating correlation:', error);
        return null;
    }
}

function prepareCategoricalData(data, columns) {
    if (!columns || !columns.length || !data.preview || !data.preview.length) {
        return null;
    }

    try {
        const result = {};
        
        for (const column of columns) {
            // Count frequency of each category
            const frequencies = {};
            data.preview.forEach(row => {
                const value = row[column];
                if (value !== null && value !== undefined) {
                    frequencies[value] = (frequencies[value] || 0) + 1;
                }
            });

            // Only include if we have valid frequencies
            if (Object.keys(frequencies).length > 0) {
                // Sort categories by frequency
                const sortedCategories = Object.entries(frequencies)
                    .sort(([,a], [,b]) => b - a)
                    .reduce((obj, [key, value]) => {
                        obj[key] = value;
                        return obj;
                    }, {});

                result[column] = {
                    frequencies: sortedCategories,
                    total: Object.values(frequencies).reduce((a, b) => a + b, 0)
                };
            }
        }

        return Object.keys(result).length > 0 ? result : null;
    } catch (error) {
        console.error('Error preparing categorical data:', error);
        return null;
    }
}
