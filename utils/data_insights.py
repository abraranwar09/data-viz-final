from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats

class DataInsights:
    """Generates statistical insights and key metrics from data."""
    
    def __init__(self):
        self.insight_generators = {
            'distribution': self._analyze_distribution,
            'variability': self._analyze_variability,
            'outliers': self._analyze_outliers,
            'bias': self._analyze_bias
        }

    def generate_insights(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate comprehensive statistical insights from the data.
        
        Args:
            data: Pandas DataFrame to analyze
            
        Returns:
            Dictionary containing statistical insights and metrics
        """
        insights = {
            'columns': {},
            'dataset_overview': self._generate_dataset_overview(data),
            'data_quality': self._analyze_data_quality(data)
        }
        
        # Generate insights for each numeric column
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            col_data = data[col].dropna()
            if len(col_data) > 0:
                insights['columns'][col] = self._analyze_column(col_data)
        
        return insights

    def _generate_dataset_overview(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate dataset-level overview metrics."""
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        categorical_cols = data.select_dtypes(include=['object']).columns
        datetime_cols = data.select_dtypes(include=['datetime64']).columns
        
        return {
            'total_rows': len(data),
            'total_columns': len(data.columns),
            'column_types': {
                'numeric': {
                    'count': len(numeric_cols),
                    'percentage': f"{(len(numeric_cols) / len(data.columns)) * 100:.1f}%"
                },
                'categorical': {
                    'count': len(categorical_cols),
                    'percentage': f"{(len(categorical_cols) / len(data.columns)) * 100:.1f}%"
                },
                'datetime': {
                    'count': len(datetime_cols),
                    'percentage': f"{(len(datetime_cols) / len(data.columns)) * 100:.1f}%"
                },
                'other': {
                    'count': len(data.columns) - len(numeric_cols) - len(categorical_cols) - len(datetime_cols),
                    'percentage': f"{((len(data.columns) - len(numeric_cols) - len(categorical_cols) - len(datetime_cols)) / len(data.columns)) * 100:.1f}%"
                }
            }
        }

    def _analyze_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data quality metrics."""
        completeness = (1 - data.isnull().sum() / len(data)) * 100
        uniqueness = (data.nunique() / len(data)) * 100
        
        # Calculate consistency score based on value ranges and patterns
        consistency_scores = []
        for col in data.columns:
            if data[col].dtype in [np.number]:
                # For numeric columns, check for values within expected ranges
                z_scores = np.abs(stats.zscore(data[col].dropna()))
                consistency_scores.append((z_scores < 3).mean() * 100)
            else:
                # For categorical columns, check pattern consistency
                value_counts = data[col].value_counts(normalize=True)
                consistency_scores.append((value_counts < 0.95).mean() * 100)
        
        return {
            'completeness': {
                'score': f"{completeness.mean():.1f}%",
                'rating': 'Excellent' if completeness.mean() > 95 else 'Good' if completeness.mean() > 80 else 'Poor'
            },
            'uniqueness': {
                'score': f"{uniqueness.mean():.1f}%",
                'rating': 'Excellent' if uniqueness.mean() > 75 else 'Good' if uniqueness.mean() > 50 else 'Poor'
            },
            'consistency': {
                'score': f"{np.mean(consistency_scores):.1f}%",
                'rating': 'Excellent' if np.mean(consistency_scores) > 90 else 'Good' if np.mean(consistency_scores) > 70 else 'Poor'
            }
        }

    def _analyze_column(self, series: pd.Series) -> Dict[str, Any]:
        """Generate comprehensive insights for a single column."""
        insights = {
            'statistics': {
                'mean': series.mean(),
                'median': series.median(),
                'std': series.std(),
                'cv': f"{(series.std() / series.mean() * 100):.1f}%" if series.mean() != 0 else "N/A"
            },
            'key_insights': []
        }
        
        # Generate key insights using all insight generators
        for generator in self.insight_generators.values():
            insight = generator(series)
            if insight:
                insights['key_insights'].append(insight)
        
        return insights

    def _analyze_distribution(self, series: pd.Series) -> Optional[str]:
        """Analyze the distribution of values."""
        skewness = series.skew()
        if abs(skewness) > 1:
            return f"{'Positive' if skewness > 0 else 'Negative'} skew detected (skewness: {skewness:.2f})"
        return None

    def _analyze_variability(self, series: pd.Series) -> Optional[str]:
        """Analyze the variability of values."""
        cv = series.std() / series.mean() if series.mean() != 0 else float('inf')
        if cv < 0.1:
            return f"Low variability (CV: {cv:.1%}), indicating consistent values"
        elif cv > 0.5:
            return f"High variability (CV: {cv:.1%}), suggesting diverse values"
        return None

    def _analyze_outliers(self, series: pd.Series) -> Optional[str]:
        """Detect and analyze outliers."""
        z_scores = np.abs(stats.zscore(series))
        outlier_count = (z_scores > 3).sum()
        if outlier_count > 0:
            return f"Found {outlier_count} potential outliers ({(outlier_count/len(series)):.1%} of values)"
        return None

    def _analyze_bias(self, series: pd.Series) -> Optional[str]:
        """Analyze potential bias in the data."""
        median = series.median()
        mean = series.mean()
        if abs(mean - median) > series.std() * 0.1:
            return "Data concentration above the midpoint, suggesting positive bias"
        return None 