/**
 * Data Processing Module
 * 
 * This module implements SOLID principles in the following ways:
 * 
 * Single Responsibility Principle (SRP):
 * - The module is solely responsible for data processing and transformation
 * - Each processing function handles a specific type of data transformation
 * - Statistical calculations are isolated from data structure manipulation
 * 
 * Open/Closed Principle (OCP):
 * - New data processing functions can be added without modifying existing ones
 * - Data transformation pipelines are extensible
 * - Statistical calculations can be extended for new types of analysis
 * 
 * Liskov Substitution Principle (LSP):
 * - All data processing functions follow consistent input/output patterns
 * - Data transformation functions are interchangeable when they operate on the same data type
 * - Statistical calculations maintain consistent behavior across different data types
 * 
 * Interface Segregation Principle (ISP):
 * - Data processing functions are grouped by data type (categorical, numerical, etc.)
 * - Statistical calculations are separated based on their specific purposes
 * - Helper functions are organized by their specific responsibilities
 * 
 * Dependency Inversion Principle (DIP):
 * - The module depends on data abstractions rather than concrete implementations
 * - Processing functions are independent of specific data sources
 * - Statistical calculations are decoupled from specific data structures
 */

function processData(data) {
    try {
        console.log('Processing data input:', data);
        let processedData = {};

        // Ensure we have valid data
        if (!data || !data.preview || !Array.isArray(data.preview) || data.preview.length === 0) {
            console.warn('Invalid or empty data provided to processData');
            return null;
        }

        // Extract column information
        const columns = Object.keys(data.preview[0] || {});
        console.log('Found columns:', columns);

        if (columns.length === 0) {
            console.warn('No columns found in data');
            return null;
        }

        // Calculate frequencies and statistics for all columns
        const columnStats = {};
        columns.forEach(column => {
            console.log(`Processing column: ${column}`);
            const values = data.preview.map(row => row[column]);
            console.log(`Values for ${column}:`, values);
            
            const validValues = values.filter(v => v != null && v !== '');
            console.log(`Valid values for ${column}:`, validValues);
            
            if (validValues.length === 0) {
                console.log(`Skipping empty column: ${column}`);
                return;
            }

            // Determine column type
            const isNumeric = validValues.every(v => !isNaN(v) && typeof v !== 'boolean');
            const uniqueValues = new Set(validValues);
            const isCategorical = uniqueValues.size <= Math.min(20, validValues.length / 2);
            
            console.log(`Column ${column} type:`, isNumeric ? 'numeric' : 'categorical');
            console.log(`Column ${column} unique values:`, Array.from(uniqueValues));

            // Calculate frequencies
            const frequencies = {};
            validValues.forEach(value => {
                frequencies[value] = (frequencies[value] || 0) + 1;
            });
            
            console.log(`Frequencies for ${column}:`, frequencies);

            columnStats[column] = {
                type: isNumeric ? 'numeric' : 'categorical',
                frequencies,
                uniqueValues: Array.from(uniqueValues),
                count: validValues.length
            };

            // Add numeric statistics if applicable
            if (isNumeric) {
                const numericValues = validValues.map(v => Number(v));
                const sorted = [...numericValues].sort((a, b) => a - b);
                columnStats[column] = {
                    ...columnStats[column],
                    min: Math.min(...numericValues),
                    max: Math.max(...numericValues),
                    mean: numericValues.reduce((a, b) => a + b, 0) / numericValues.length,
                    median: sorted[Math.floor(sorted.length / 2)],
                    q1: sorted[Math.floor(sorted.length * 0.25)],
                    q3: sorted[Math.floor(sorted.length * 0.75)]
                };
            }
        });

        console.log('Column stats:', columnStats);

        // Process categorical data
        const categoricalColumns = Object.entries(columnStats)
            .filter(([_, stats]) => stats.type === 'categorical')
            .map(([col]) => col);
            
        console.log('Categorical columns:', categoricalColumns);

        if (categoricalColumns.length > 0) {
            processedData.categorical = {};
            categoricalColumns.forEach(col => {
                console.log(`Processing categorical column: ${col}`);
                const stats = columnStats[col];
                console.log(`Stats for ${col}:`, stats);
                
                if (stats && stats.frequencies) {
                    processedData.categorical[col] = {
                        frequencies: stats.frequencies,
                        total: stats.count,
                        unique_values: stats.uniqueValues
                    };
                    console.log(`Processed categorical data for ${col}:`, processedData.categorical[col]);
                } else {
                    console.warn(`Missing stats or frequencies for column: ${col}`);
                }
            });
        }

        // Process numeric data
        const numericColumns = Object.entries(columnStats)
            .filter(([_, stats]) => stats.type === 'numeric')
            .map(([col]) => col);

        if (numericColumns.length > 0) {
            const numericData = {};
            
            // Prepare histogram data
            if (numericColumns[0]) {
                const histogramData = prepareHistogramData(data, numericColumns[0], columnStats);
                if (histogramData) {
                    numericData.histogram = histogramData;
                }
            }
            
            // Prepare scatter data
            if (numericColumns.length >= 2) {
                const scatterData = prepareScatterData(data, numericColumns[0], numericColumns[1]);
                if (scatterData) {
                    numericData.scatter = scatterData;
                }
            }
            
            // Prepare boxplot data
            const boxplotData = prepareBoxplotData(data, numericColumns, columnStats);
            if (boxplotData) {
                numericData.boxplot = boxplotData;
            }
            
            // Prepare heatmap data
            if (numericColumns.length >= 2) {
                const heatmapData = prepareHeatmapData(data, numericColumns);
                if (heatmapData) {
                    numericData.heatmap = heatmapData;
                }
            }

            if (Object.keys(numericData).length > 0) {
                processedData = { ...processedData, ...numericData };
            }
        }

        // Add column statistics
        processedData.column_stats = columnStats;
        
        // Add preview data
        processedData.preview = data.preview;

        console.log('Final processed data:', processedData);
        return processedData;
    } catch (error) {
        console.error('Error in processData:', error);
        return null;
    }
}

/**
 * Data Validation Layer
 * 
 * SRP: Responsible only for validating input data
 * ISP: Validation rules are separated by data type
 * DIP: Validation is independent of data processing implementation
 */

function validateNumericValues(values) {
    return values.filter(v => 
        v !== null && 
        v !== undefined && 
        !isNaN(v) && 
        typeof v !== 'boolean'
    ).map(v => Number(v));
}

/**
 * Statistical Processing Layer
 * 
 * SRP: Handles only statistical calculations
 * OCP: New statistical methods can be added without changing existing ones
 * ISP: Statistical functions are grouped by type of analysis
 */

function prepareHistogramData(data, column, columnStats) {
    if (!column || !columnStats[column]) return null;

    try {
        const stats = columnStats[column];
        const values = data.preview
            .map(row => row[column])
            .filter(v => v != null && !isNaN(v))
            .map(Number);

        if (values.length === 0) return null;

        // Create histogram bins
        const binCount = Math.min(10, Math.ceil(Math.sqrt(values.length)));
        const min = stats.min;
        const max = stats.max;
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

function prepareBoxplotData(data, columns, columnStats) {
    if (!columns || !columns.length) {
        return null;
    }

    try {
        return columns
            .filter(col => columnStats[col] && columnStats[col].type === 'numeric')
            .map(col => ({
                name: col,
                stats: {
                    min: columnStats[col].min,
                    q1: columnStats[col].q1 || columnStats[col].min,
                    median: columnStats[col].median,
                    q3: columnStats[col].q3 || columnStats[col].max,
                    max: columnStats[col].max
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

// Add new function to handle education vs income relationship
function prepareEducationIncomeData(data, educationColumn, incomeColumn) {
    if (!data.preview || !data.preview.length) {
        return null;
    }

    try {
        // Group data by education level
        const educationGroups = {};
        
        data.preview.forEach(row => {
            const education = row[educationColumn];
            const income = parseFloat(row[incomeColumn]);
            
            if (education && !isNaN(income)) {
                if (!educationGroups[education]) {
                    educationGroups[education] = [];
                }
                educationGroups[education].push(income);
            }
        });

        // Calculate statistics for each education level
        const result = Object.entries(educationGroups).map(([education, incomes]) => {
            const avg = incomes.reduce((a, b) => a + b, 0) / incomes.length;
            const sorted = [...incomes].sort((a, b) => a - b);
            const median = sorted[Math.floor(sorted.length / 2)];
            
            return {
                education,
                averageIncome: avg,
                medianIncome: median,
                count: incomes.length,
                min: Math.min(...incomes),
                max: Math.max(...incomes)
            };
        });

        return {
            educationLevels: result.map(r => r.education),
            averageIncomes: result.map(r => r.averageIncome),
            medianIncomes: result.map(r => r.medianIncome),
            counts: result.map(r => r.count),
            ranges: result.map(r => ({ min: r.min, max: r.max }))
        };
    } catch (error) {
        console.error('Error preparing education vs income data:', error);
        return null;
    }
}

/**
 * Data Transformation Layer
 * 
 * SRP: Responsible only for data structure transformation
 * OCP: New transformation methods can be added without modification
 * LSP: All transformations maintain consistent data patterns
 */
