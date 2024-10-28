import pandas as pd
import numpy as np

def process_data(df):
    """Process uploaded data and generate statistics."""
    
    numeric_columns = df.select_dtypes(include=[np.number]).columns
    
    stats = {
        'summary': {
            'rows': len(df),
            'columns': len(df.columns),
            'numeric_columns': len(numeric_columns)
        },
        'column_stats': {},
        'preview': df.head(5).to_dict('records'),
        'columns': list(df.columns)
    }
    
    # Calculate statistics for numeric columns
    for col in numeric_columns:
        stats['column_stats'][col] = {
            'mean': float(df[col].mean()),
            'median': float(df[col].median()),
            'std': float(df[col].std()),
            'min': float(df[col].min()),
            'max': float(df[col].max())
        }
    
    return stats
