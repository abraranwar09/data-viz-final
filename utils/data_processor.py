import pandas as pd
import numpy as np
from typing import Dict, Any
import io
import logging

logger = logging.getLogger(__name__)

def process_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Process uploaded data and generate statistics."""
    
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
            stats['column_stats'][col] = {
                'type': 'numeric',
                'mean': float(df[col].mean()),
                'median': float(df[col].median()),
                'std': float(df[col].std()),
                'min': float(df[col].min()),
                'max': float(df[col].max())
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
        raise ValueError(f"Error processing data: {str(e)}")

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
    categorical_columns = df.select_dtypes(include=['object']).columns
    
    for col in numeric_columns:
        combined_stats['column_stats'][col] = {
            'mean': float(df[col].mean()),
            'median': float(df[col].median()),
            'std': float(df[col].std()),
            'min': float(df[col].min()),
            'max': float(df[col].max()),
            'type': 'numeric'
        }
    
    for col in categorical_columns:
        value_counts = df[col].value_counts()
        combined_stats['column_stats'][col] = {
            'unique_values': len(value_counts),
            'top_values': value_counts.head(5).to_dict(),
            'type': 'categorical'
        }
    
    return combined_stats
