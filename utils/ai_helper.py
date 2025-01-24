import os
from typing import Dict, Any, List, Optional
import json
import requests
import logging
import math
import re

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('ai_helper')

def clean_numeric_values(obj):
    """Recursively clean numeric values in a data structure"""
    if isinstance(obj, dict):
        return {k: clean_numeric_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_numeric_values(x) for x in obj]
    elif isinstance(obj, (int, float)):
        if isinstance(obj, float) and (math.isinf(obj) or math.isnan(obj)):
            return 0
        return obj
    elif isinstance(obj, str):
        # Handle string representations of special numeric values
        if obj in ['Infinity', '-Infinity', 'NaN', 'inf', '-inf']:
            return '0'
    return obj

def prepare_json_data(data):
    """Prepare data for JSON serialization"""
    if isinstance(data, dict):
        return {k: prepare_json_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [prepare_json_data(x) for x in data]
    elif isinstance(data, (int, float)):
        if isinstance(data, float) and (math.isinf(data) or math.isnan(data)):
            return 0
        return data
    elif isinstance(data, str):
        # Clean string values
        if data in ['Infinity', '-Infinity', 'NaN', 'inf', '-inf']:
            return '0'
        return data
    return str(data)

def get_data_insights(question: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Make API call for data analysis and single-file HTML visualization generation"""
    logger.debug(f"Requesting insights for question: {question}")
    
    try:
        # Clean and prepare the data
        cleaned_data = clean_numeric_values(data)
        json_safe_data = prepare_json_data(cleaned_data)
        
        # Verify the data is JSON-safe before sending
        try:
            data_str = json.dumps(json_safe_data)
            logger.debug(f"Data String for API: {data_str}")
        except Exception as e:
            logger.error(f"JSON serialization error: {str(e)}")
            raise ValueError("Failed to serialize data for API request")
        
        response = requests.post(
            "http://localhost:8000/v1/chat/completions",  # Update with your LM Studio server URL
            headers={"Content-Type": "application/json"},
            json={
                "model": "internlm2_5-20b-chat-q5_k_m",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a data analysis expert. Analyze the data and create visualizations using ECharts. Use only finite numbers in your response."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze this data and create visualizations:\n{data_str}\n\nQuestion: {question}"
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
                "stream": False
            }
        )
        
        if response.status_code != 200:
            logger.error(f"API Response: {response.text}")
            raise Exception(f"API request failed with status {response.status_code}")
            
        result = response.json()
        logger.debug(f"Raw API Response: {json.dumps(result)}")
        
        # Extract and clean the content
        content = result['choices'][0]['message']['content']
        logger.debug(f"Raw Content from API: {content}")

        # Extract visualization code using regex
        viz_codes = []
        viz_matches = re.finditer(r'```html\n(.*?)\n```', content, re.DOTALL)
        for match in viz_matches:
            viz_codes.append(match.group(1))

        # Remove the visualization code blocks from the content
        analysis = re.sub(r'```html\n.*?\n```', '', content, flags=re.DOTALL).strip()

        # Process each visualization code block
        visualizations = []
        for i, viz_code in enumerate(viz_codes):
            logger.debug(f"Processing visualization code block {i+1}")
            
            # Clean up the code
            cleaned_code = viz_code.replace("< /", "</")  # Fix potential spacing issues

            # Create a visualization object
            visualizations.append({
                "type": "html",
                "code": cleaned_code
            })

        return {
            "success": True,
            "answer": analysis,
            "visualizations": visualizations
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting insights: {str(e)}")
        return {
            "success": False,
            "answer": "Failed to get insights due to connection error",
            "visualizations": []
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "success": False,
            "answer": f"Failed to get insights: {str(e)}",
            "visualizations": []
        }

def get_ai_insights(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Main function that handles the complete analysis process"""
    logger.debug(f"Processing AI request for question: {question}")
    
    try:
        data = context.get('data', {})
        # Clean the data before processing
        data = clean_numeric_values(data)
        response = get_data_insights(question, data)
        
        return {
            "response": {
                "answer": response.get("answer", "Failed to get insights"),
                "confidence": 0.95 if response.get("success") else 0,
                "sources": ["Data Analysis"]
            },
            "visualizations": response.get("visualizations", [])
        }

    except Exception as e:
        logger.error(f"Error in AI insights request: {str(e)}")
        return {
            "response": {
                "answer": f"Error processing request: {str(e)}",
                "confidence": 0,
                "sources": []
            }
        }

