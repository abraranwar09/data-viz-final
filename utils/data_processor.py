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
            'max': np.nan
        }
    
    mean = float(clean_series.mean())
    std = float(clean_series.std())
    
    return {
        'type': 'numeric',
        'mean': mean,
        'median': float(clean_series.median()),
        'std': std,
        'cv': float((std / mean * 100) if mean != 0 else np.nan),
        'kurtosis': float(stats.kurtosis(clean_series, fisher=True)),
        'skewness': float(stats.skew(clean_series)),
        'min': float(clean_series.min()),
        'max': float(clean_series.max())
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
        
        stats = {
            'summary': {
                'rows': len(df),
                'columns': len(df.columns),
                'numeric_columns': len(numeric_columns),
                'categorical_columns': len(categorical_columns),
                'memory_usage': f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
            },
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
    """Generate insights about the column based on its statistics."""
    insights = []
    
    # Check for bias
    if abs(stats['mean'] - stats['median']) > stats['std'] * 0.1:
        insights.append("Data concentration above the midpoint, suggesting positive bias")
    
    # Check for skewness
    if abs(stats['skewness']) > 1:
        direction = "positive" if stats['skewness'] > 0 else "negative"
        insights.append(f"{direction.capitalize()} skew detected (skewness: {stats['skewness']:.2f})")
    
    # Check for heavy/light tails
    if abs(stats['kurtosis']) > 2:
        tail_type = "Heavy-tailed" if stats['kurtosis'] > 0 else "Light-tailed"
        insights.append(f"{tail_type} distribution (kurtosis: {stats['kurtosis']:.2f})")
    
    # Check for high variability
    if stats['cv'] > 100:
        insights.append(f"High variability (CV: {stats['cv']:.1f}%), suggesting diverse values")
    
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
