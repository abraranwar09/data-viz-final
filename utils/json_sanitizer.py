import math
import json

def sanitize_json(data):
    """
    Recursively sanitize JSON data, converting NaN values to None.
    """
    if isinstance(data, dict):
        return {k: sanitize_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_json(item) for item in data]
    elif isinstance(data, float) and math.isnan(data):
        return None
    else:
        return data 