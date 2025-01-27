from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats
from .robust_statistics import RobustStatistics

class DataInsights:
    """Generates statistical insights and key metrics from data."""
    
    def __init__(self):
        self.insight_generators = {
            'distribution': self._analyze_distribution,
            'variability': self._analyze_variability,
            'outliers': self._analyze_outliers,
            'bias': self._analyze_bias
        }
        self.robust_stats = RobustStatistics()

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
        """Analyze data quality metrics using robust methods."""
        completeness = (1 - data.isnull().sum() / len(data)) * 100
        uniqueness = (data.nunique() / len(data)) * 100
        
        # Calculate consistency and outlier scores for each column
        consistency_scores = []
        outlier_scores = []
        
        for col in data.columns:
            col_data = data[col].dropna()
            if len(col_data) > 0:
                consistency_scores.append(self.robust_stats.calculate_consistency_score(col_data))
                if col_data.dtype in [np.number]:
                    outlier_scores.append(self.robust_stats.calculate_outlier_score(col_data))
        
        # Calculate overall scores
        avg_consistency = np.mean(consistency_scores) if consistency_scores else 100
        avg_outlier = np.mean(outlier_scores) if outlier_scores else 100
        
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
                'score': f"{avg_consistency:.1f}%",
                'rating': 'Excellent' if avg_consistency > 90 else 'Good' if avg_consistency > 70 else 'Poor'
            },
            'outlier_score': {
                'score': f"{avg_outlier:.1f}%",
                'rating': 'Excellent' if avg_outlier > 95 else 'Good' if avg_outlier > 85 else 'Poor'
            }
        }

    def _analyze_column(self, series: pd.Series) -> Dict[str, Any]:
        """Generate comprehensive insights for a single column using robust statistics."""
        # Get robust statistics
        stats_dict = self.robust_stats.calculate_robust_stats(series)
        
        if stats_dict is None:
            return {
                'statistics': {
                    'mean': 'N/A',
                    'median': 'N/A',
                    'std': 'N/A',
                    'cv': 'N/A',
                    'kurtosis': 'N/A',
                    'skewness': 'N/A'
                },
                'key_insights': []
            }
        
        # Calculate CV only if mean is not zero
        cv = f"{(stats_dict['std'] / stats_dict['mean'] * 100):.1f}%" if stats_dict['mean'] != 0 else "N/A"
        
        insights = {
            'statistics': {
                'mean': float(stats_dict['mean']),
                'median': float(stats_dict['median']),
                'std': float(stats_dict['std']),
                'cv': cv,
                'kurtosis': float(stats_dict['kurtosis']),
                'skewness': float(stats_dict['skewness'])
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
        stats_dict = self.robust_stats.calculate_robust_stats(series)
        if stats_dict is None:
            return None
            
        skewness = stats_dict['skewness']
        kurtosis = stats_dict['kurtosis']
        
        insights = []
        if abs(skewness) > 1:
            insights.append(f"{'Positive' if skewness > 0 else 'Negative'} skew detected (skewness: {skewness:.2f})")
        if abs(kurtosis) > 2:
            insights.append(f"{'Heavy-tailed' if kurtosis > 0 else 'Light-tailed'} distribution (kurtosis: {kurtosis:.2f})")
            
        return '; '.join(insights) if insights else None

    def _analyze_variability(self, series: pd.Series) -> Optional[str]:
        """Analyze the variability of values using robust statistics."""
        stats_dict = self.robust_stats.calculate_robust_stats(series)
        if stats_dict is None:
            return None
            
        cv = stats_dict['std'] / stats_dict['mean'] if stats_dict['mean'] != 0 else float('inf')
        if cv < 0.1:
            return f"Low variability (CV: {cv:.1%}), indicating consistent values"
        elif cv > 0.5:
            return f"High variability (CV: {cv:.1%}), suggesting diverse values"
        return None

    def _analyze_outliers(self, series: pd.Series) -> Optional[str]:
        """Detect and analyze outliers using robust methods."""
        clean_series = series.replace([np.inf, -np.inf], np.nan).dropna()
        if len(clean_series) < 2:
            return None
            
        outlier_score = self.robust_stats.calculate_outlier_score(clean_series)
        if outlier_score < 95:  # If more than 5% are outliers
            outlier_count = int(len(clean_series) * (100 - outlier_score) / 100)
            return f"Found {outlier_count} potential outliers ({(100-outlier_score):.1f}% of values)"
        return None

    def _analyze_bias(self, series: pd.Series) -> Optional[str]:
        """Analyze potential bias in the data using robust statistics."""
        stats_dict = self.robust_stats.calculate_robust_stats(series)
        if stats_dict is None:
            return None
            
        median = stats_dict['median']
        mean = stats_dict['mean']
        std = stats_dict['std']
        
        if abs(mean - median) > std * 0.1:
            return "Data concentration above the midpoint, suggesting positive bias"
        return None 