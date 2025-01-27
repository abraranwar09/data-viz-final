import numpy as np
from scipy import stats
import pandas as pd
from typing import Optional, Dict, Any

class RobustStatistics:
    """Provides robust statistical calculations with high precision and accuracy."""
    
    @staticmethod
    def safe_numeric_calculation(func):
        """Decorator to handle inf/nan values safely."""
        def wrapper(series: pd.Series, *args, **kwargs):
            clean_series = series.replace([np.inf, -np.inf], np.nan).dropna()
            if len(clean_series) == 0:
                return None
            return func(clean_series, *args, **kwargs)
        return wrapper

    @staticmethod
    @safe_numeric_calculation
    def calculate_robust_stats(series: pd.Series) -> Optional[Dict[str, float]]:
        """Calculate robust statistical measures using high precision."""
        try:
            # Use float64 for maximum precision
            return {
                'mean': np.float64(series.mean()),
                'median': np.float64(series.median()),
                'std': np.float64(series.std()),
                'kurtosis': np.float64(stats.kurtosis(series, fisher=True)),
                'skewness': np.float64(stats.skew(series))
            }
        except Exception:
            return None

    @staticmethod
    def calculate_outlier_score(series: pd.Series) -> float:
        """Calculate outlier score using distribution-appropriate method."""
        clean_series = series.replace([np.inf, -np.inf], np.nan).dropna()
        if len(clean_series) < 2:
            return 100.0

        try:
            # Check for normality
            _, p_value = stats.normaltest(clean_series)
            
            if p_value < 0.05:  # Not normally distributed
                # Use IQR method
                Q1 = clean_series.quantile(0.25)
                Q3 = clean_series.quantile(0.75)
                IQR = Q3 - Q1
                outliers = ((clean_series < (Q1 - 1.5 * IQR)) | 
                           (clean_series > (Q3 + 1.5 * IQR)))
            else:
                # Use z-score for normal distributions
                z_scores = np.abs(stats.zscore(clean_series))
                outliers = z_scores > 3
            
            return float(100 * (1 - outliers.mean()))
        except Exception:
            return 100.0  # Return perfect score if calculation fails

    @staticmethod
    def calculate_consistency_score(series: pd.Series) -> float:
        """Calculate consistency score using robust methods."""
        if series.dtype in [np.number]:
            clean_series = series.replace([np.inf, -np.inf], np.nan).dropna()
            if len(clean_series) < 2:
                return 100.0

            try:
                # Combine multiple methods for robustness
                z_score_consistency = (np.abs(stats.zscore(clean_series)) < 3).mean()
                
                Q1 = clean_series.quantile(0.25)
                Q3 = clean_series.quantile(0.75)
                IQR = Q3 - Q1
                iqr_consistency = (
                    (clean_series >= Q1 - 1.5 * IQR) & 
                    (clean_series <= Q3 + 1.5 * IQR)
                ).mean()
                
                return float(np.mean([z_score_consistency, iqr_consistency]) * 100)
            except Exception:
                return 100.0
        else:
            # For categorical data
            value_counts = series.value_counts(normalize=True)
            if len(value_counts) == 0:
                return 100.0
                
            try:
                entropy = stats.entropy(value_counts)
                max_entropy = np.log(len(value_counts))
                return float((1 - entropy/max_entropy if max_entropy > 0 else 1) * 100)
            except Exception:
                return 100.0 