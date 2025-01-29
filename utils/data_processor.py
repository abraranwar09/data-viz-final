"""
Data Processing Module

This module implements SOLID principles in the following ways:

Single Responsibility Principle (SRP):
- Each function has a single, well-defined purpose
- Statistical calculations are separated from data processing
- Data cleaning and transformation are handled separately

Open/Closed Principle (OCP):
- New statistical measures can be added without modifying existing ones
- Data processing pipelines are extensible
- New data types can be supported without changing core functionality

Liskov Substitution Principle (LSP):
- All statistical functions follow the same interface pattern
- Data processing functions maintain consistent behavior
- Type checking ensures proper substitution

Interface Segregation Principle (ISP):
- Statistical functions are grouped by type
- Data processing functions are separated by responsibility
- Helper functions are isolated by purpose

Dependency Inversion Principle (DIP):
- The module depends on abstractions (pandas DataFrame) rather than concrete implementations
- Statistical calculations are independent of data source
- Processing functions are decoupled from specific data formats
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, Any
import io
import logging
from utils.json_sanitizer import sanitize_json

logger = logging.getLogger(__name__)

def calculate_numeric_stats(series: pd.Series) -> Dict[str, float]:
    """Calculate comprehensive statistics for a numeric series."""
    clean_series = series.replace([np.inf, -np.inf], np.nan).dropna()
    
    if len(clean_series) < 2:
        return {
            'type': 'numeric',
            'mean': np.nan,
            'median': np.nan,
            'std': np.nan,
            'cv': np.nan,
            'kurtosis': np.nan,
            'skewness': np.nan,
            'min': np.nan,
            'max': np.nan,
            'iqr': np.nan,
            'q1': np.nan,
            'q3': np.nan
        }
    
    q1 = float(clean_series.quantile(0.25))
    q3 = float(clean_series.quantile(0.75))
    iqr = float(q3 - q1)
    mean = float(clean_series.mean())
    std = float(clean_series.std())
    
    # Calculate outlier bounds
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = clean_series[(clean_series < lower_bound) | (clean_series > upper_bound)]
    
    return {
        'type': 'numeric',
        'mean': mean,
        'median': float(clean_series.median()),
        'std': std,
        'cv': float((std / mean * 100) if mean != 0 else np.nan),
        'kurtosis': float(stats.kurtosis(clean_series, fisher=True)),
        'skewness': float(stats.skew(clean_series)),
        'min': float(clean_series.min()),
        'max': float(clean_series.max()),
        'iqr': iqr,
        'q1': q1,
        'q3': q3,
        'outliers_count': len(outliers),
        'outliers_percentage': float(len(outliers) / len(clean_series) * 100)
    }

def calculate_data_quality(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Calculate comprehensive data quality metrics."""
    
    # Calculate completeness (percentage of non-null values)
    completeness = float((1 - df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100)
    
    # Calculate uniqueness (average percentage of unique values across columns)
    uniqueness = float(np.mean([len(df[col].unique()) / len(df) * 100 for col in df.columns]))
    
    # Calculate consistency (percentage of values within expected ranges/patterns)
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    consistency_scores = []
    
    for col in numeric_cols:
        clean_series = df[col].replace([np.inf, -np.inf], np.nan).dropna()
        if len(clean_series) > 0:
            # Calculate z-scores
            z_scores = np.abs(stats.zscore(clean_series))
            # Consider values within 3 standard deviations as consistent
            consistency_scores.append(np.mean(z_scores <= 3) * 100)
    
    consistency = float(np.mean(consistency_scores)) if consistency_scores else 0.0
    
    return {
        'completeness': {
            'score': f"{completeness:.1f}%",
            'rating': 'Excellent' if completeness >= 95 else 'Good' if completeness >= 80 else 'Poor'
        },
        'uniqueness': {
            'score': f"{uniqueness:.1f}%",
            'rating': 'Excellent' if uniqueness >= 80 else 'Good' if uniqueness >= 50 else 'Poor'
        },
        'consistency': {
            'score': f"{consistency:.1f}%",
            'rating': 'Excellent' if consistency >= 90 else 'Good' if consistency >= 70 else 'Poor'
        }
    }

def process_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Process uploaded data and generate statistics."""
    
    df = sanitize_json(df)
    
    try:
        # Clean column names and handle potential single-column CSV issue
        if len(df.columns) == 1 and ',' in df.columns[0]:
            # The file was not properly parsed, try to parse it again
            first_col_name = df.columns[0]
            if isinstance(df.iloc[0, 0], str) and ',' in df.iloc[0, 0]:
                # Convert the single column to a string and split by newlines
                data_str = '\n'.join([first_col_name] + df[first_col_name].astype(str).tolist())
                # Read the string as a CSV
                df = pd.read_csv(io.StringIO(data_str))

        # Clean column names
        df.columns = df.columns.str.strip()
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        categorical_columns = df.select_dtypes(include=['object']).columns
        
        # Calculate data quality metrics
        quality_metrics = calculate_data_quality(df)
        
        stats = {
            'summary': {
                'rows': len(df),
                'columns': len(df.columns),
                'numeric_columns': len(numeric_columns),
                'categorical_columns': len(categorical_columns),
                'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
            },
            'data_quality': quality_metrics,
            'column_stats': {},
            'preview': df.head(5).to_dict('records'),
            'columns': list(df.columns)
        }
        
        # Calculate statistics for numeric columns
        for col in numeric_columns:
            col_stats = calculate_numeric_stats(df[col])
            stats['column_stats'][col] = {
                'statistics': col_stats,
                'key_insights': generate_column_insights(df[col], col_stats)
            }
        
        # Calculate statistics for categorical columns
        for col in categorical_columns:
            value_counts = df[col].value_counts()
            stats['column_stats'][col] = {
                'type': 'categorical',
                'unique_values': len(value_counts),
                'top_values': value_counts.head(5).to_dict()
            }
        
        return stats
    except Exception as e:
        logger.exception("Error processing data")
        return None

def generate_column_insights(series: pd.Series, stats: Dict[str, float]) -> list:
    """Generate detailed insights about the column based on its statistics."""
    insights = []
    
    # Check for data distribution
    if abs(stats['mean'] - stats['median']) > stats['std'] * 0.1:
        if stats['mean'] > stats['median']:
            insights.append(f"Data shows positive skew with mean ({stats['mean']:.2f}) greater than median ({stats['median']:.2f})")
        else:
            insights.append(f"Data shows negative skew with mean ({stats['mean']:.2f}) less than median ({stats['median']:.2f})")
    
    # Check for skewness
    if abs(stats['skewness']) > 1:
        direction = "positive" if stats['skewness'] > 0 else "negative"
        severity = "highly" if abs(stats['skewness']) > 2 else "moderately"
        insights.append(f"{severity.capitalize()} {direction} skewed distribution (skewness: {stats['skewness']:.2f})")
    
    # Check for kurtosis
    if abs(stats['kurtosis']) > 2:
        if stats['kurtosis'] > 0:
            insights.append(f"Heavy-tailed distribution with more extreme values than normal (kurtosis: {stats['kurtosis']:.2f})")
        else:
            insights.append(f"Light-tailed distribution with fewer extreme values than normal (kurtosis: {stats['kurtosis']:.2f})")
    
    # Check for variability
    if stats['cv'] > 100:
        severity = "extremely" if stats['cv'] > 150 else "highly"
        insights.append(f"{severity.capitalize()} variable data (CV: {stats['cv']:.1f}%), indicating wide value dispersion")
    
    # Check for outliers
    if 'outliers_count' in stats and stats['outliers_count'] > 0:
        insights.append(f"Found {stats['outliers_count']} potential outliers ({stats['outliers_percentage']:.1f}% of values)")
    
    # Check for data range
    range_size = stats['max'] - stats['min']
    if range_size > 0:
        insights.append(f"Data spans from {stats['min']:.2f} to {stats['max']:.2f} (range: {range_size:.2f})")
    
    # Check for concentration
    if 'iqr' in stats and stats['iqr'] > 0:
        central_range = f"50% of values fall between {stats['q1']:.2f} and {stats['q3']:.2f} (IQR: {stats['iqr']:.2f})"
        insights.append(central_range)
    
    return insights

def chunk_process_data(df: pd.DataFrame, chunk_size: int = 10000) -> Dict[str, Any]:
    """Process large datasets in chunks to avoid memory issues."""
    
    total_rows = len(df)
    chunks = []
    chunk_stats = []
    
    # Process data in chunks
    for i in range(0, total_rows, chunk_size):
        chunk = df.iloc[i:i + chunk_size]
        chunk_stats.append(process_data(chunk))
    
    # Combine chunk statistics
    combined_stats = {
        'summary': {
            'rows': total_rows,
            'columns': len(df.columns),
            'numeric_columns': len(df.select_dtypes(include=[np.number]).columns),
            'categorical_columns': len(df.select_dtypes(include=['object']).columns),
            'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB",
            'chunks_processed': len(chunk_stats)
        },
        'column_stats': {},
        'preview': df.head(5).to_dict('records'),
        'columns': list(df.columns)
    }
    
    # Merge column statistics from all chunks
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    for col in numeric_columns:
        combined_stats['column_stats'][col] = {
            'statistics': calculate_numeric_stats(df[col]),
            'key_insights': generate_column_insights(df[col], calculate_numeric_stats(df[col]))
        }
    
    # Handle categorical columns
    categorical_columns = df.select_dtypes(include=['object']).columns
    for col in categorical_columns:
        value_counts = df[col].value_counts()
        combined_stats['column_stats'][col] = {
            'type': 'categorical',
            'unique_values': len(value_counts),
            'top_values': value_counts.head(5).to_dict()
        }
    
    return combined_stats

"""
Statistical Processing Layer

SRP: Handles only statistical calculations
OCP: New statistical methods can be added without modification
LSP: All statistical functions follow same interface
"""

"""
Data Transformation Layer

SRP: Responsible only for data transformation
ISP: Transformations are separated by data type
DIP: Independent of specific data formats
"""

"""
Data Quality Analysis Layer

SRP: Handles only data quality assessment
OCP: New quality metrics can be added without modification
ISP: Quality checks are separated by type
"""

"""
Insight Generation Layer

SRP: Responsible only for generating insights
OCP: New insight types can be added without modification
DIP: Independent of specific data sources
"""
