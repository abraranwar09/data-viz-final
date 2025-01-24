import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionFunctionMessageParam
)
import json
import requests
import logging
import math

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('ai_helper')

class APIKeyError(Exception):
    """Exception raised for missing or invalid API keys."""
    pass

def validate_api_keys():
    """Validate required API keys are present."""
    openai_key = os.environ.get("OPENAI_API_KEY")
    perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
    
    if not openai_key:
        raise APIKeyError("OpenAI API key is missing")
    if not perplexity_key:
        raise APIKeyError("Perplexity API key is missing")
    
    return openai_key, perplexity_key

try:
    OPENAI_API_KEY, PERPLEXITY_API_KEY = validate_api_keys()
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except APIKeyError as e:
    print(f"API Key Error: {str(e)}")
    openai_client = None

def web_search(query: str) -> str:
    """Perform web search using Perplexity API"""
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-sonar-small-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides accurate and up-to-date information based on web searches."
                    },
                    {
                        "role": "user",
                        "content": query
                    }
                ]
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("choices") and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
        return f"Error: Unable to get search results (Status: {response.status_code})"
    except Exception as e:
        return f"Error performing web search: {str(e)}"

def get_ai_insights(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    logger.debug(f"Starting AI insights request for question: {question}")
    
    if not openai_client:
        logger.error("OpenAI client not initialized")
        return {
            "answer": "The AI service is not properly configured. Please check your API keys.",
            "confidence": 0,
            "sources": []
        }

    try:
        data = context.get('data', {})
        is_initial_analysis = context.get('type') == 'initial_analysis'

        # Enhanced system prompt for better data handling
        system_prompt = """You are an expert data analyst and visualization specialist with advanced data cleaning capabilities. You can answewr in natural language about the data and provide in depth analysis and insights.

        DATA HANDLING CAPABILITIES:
        1. Handle various data formats and quality issues:
           - Missing values or incomplete data
           - Inconsistent formatting
           - Headers-only data
           - Mixed data types
           - Non-standard formats

        2. Data Quality Assessment:
           - Identify data completeness
           - Detect formatting issues
           - Suggest data improvements
           - Handle NaN or null values
           - Validate data consistency

        3. Data Enhancement:
           - Suggest data completion strategies
           - Recommend data cleaning steps
           - Provide data quality feedback
           - Explain data limitations

        VISUALIZATION REQUIREMENTS:
        1. Always create visualizations when possible
        2. Adapt to data limitations
        3. Explain any data quality issues
        4. Suggest improvements

        COMMUNICATION:
        1. Clearly explain data quality issues
        2. Provide context for limitations
        3. Suggest data improvements
        4. Explain visualization choices

        <INST>
        Typography and bullets and titles and headers and tables when it helps provide a strong user experience be very helpful. Always follow user instructions when interacting with the data if they want to contacts or specific types of data comparisons or chart or specific aspects you always follow those instructions
        </INST>

        NEVER:
        - Refuse to analyze data
        - Ignore data quality issues
        - Skip explaining limitations
        - Leave users without actionable insights"""

        # Check for data quality issues
        data_quality_issues = validate_data_quality(data)
        if data_quality_issues:
            # Add data quality context to the question
            question = f"{question}\n\nData Quality Context: {data_quality_issues}"

        # Define available functions for structured output
        functions = [
            {
                "name": "create_visualization",
                "description": "Create a data visualization using the provided data",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis": {
                            "type": "string",
                            "description": "Detailed analysis of the data and explanation of visualization choices"
                        },
                        "visualizations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "chart_type": {
                                        "type": "string",
                                        "enum": ["bar", "line", "scatter", "pie", "boxplot", "heatmap", "sunburst", "treemap", "parallel"]
                                    },
                                    "title": {
                                        "type": "string"
                                    },
                                    "x_axis": {
                                        "type": "string"
                                    },
                                    "y_axis": {
                                        "type": "string"
                                    },
                                    "explanation": {
                                        "type": "string"
                                    }
                                },
                                "required": ["chart_type", "title", "explanation"]
                            },
                            "minItems": 1
                        }
                    },
                    "required": ["analysis", "visualizations"]
                }
            }
        ]

        # Make the API call with function calling
        chat_completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Data Context:\n{format_data_context(data)}\n\nTask: {question}"}
            ],
            functions=functions,
            function_call={"name": "create_visualization"}  # Force function call
        )

        # Extract the function call arguments
        function_args = json.loads(chat_completion.choices[0].message.function_call.arguments)
        
        # Generate visualizations from the structured output
        visualizations = []
        for viz_config in function_args['visualizations']:
            try:
                config = generate_visualization_config(viz_config, data)
                if config:  # Only add valid configurations
                    visualizations.append({
                        'config': config,
                        'explanation': viz_config['explanation']
                    })
                else:
                    logger.warning(f"Skipping invalid visualization: {viz_config}")
            except Exception as e:
                logger.error(f"Error generating visualization: {str(e)}")

        # Only include visualizations that have valid configs
        final_response = [
            "# Data Analysis Report\n\n",
            function_args['analysis'],
        ]

        if visualizations:
            final_response.append("\n\n## Visualizations\n")
            for i, viz in enumerate(visualizations, 1):
                final_response.extend([
                    f"\n### Visualization {i}\n",
                    viz['explanation'],
                    f"\n```echarts\n{json.dumps(viz['config'], indent=2)}\n```\n"
                ])
        else:
            final_response.append("\n\nNo valid visualizations could be generated for this data.")

        return {
            "answer": "".join(final_response),
            "confidence": 0.95,
            "sources": ["Data Analysis"]
        }

    except Exception as e:
        logger.exception("Error in get_ai_insights")
        return {
            "answer": f"An error occurred while processing your request: {str(e)}",
            "confidence": 0,
            "sources": []
        }

def extract_visualization_suggestions(gpt_response: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract visualization suggestions from GPT's response"""
    suggestions = []
    
    # Analyze the data types
    numeric_cols = [col for col, stats in data.get('column_stats', {}).items() 
                   if stats.get('type') == 'numeric']
    categorical_cols = [col for col, stats in data.get('column_stats', {}).items() 
                       if stats.get('type') == 'categorical']
    
    # Create appropriate visualization configs based on data types
    if len(numeric_cols) >= 2:
        suggestions.append({
            'chart_type': 'scatter',
            'title': f'Correlation: {numeric_cols[0]} vs {numeric_cols[1]}',
            'x_axis': numeric_cols[0],
            'y_axis': numeric_cols[1]
        })
    
    if categorical_cols:
        suggestions.append({
            'chart_type': 'bar',
            'title': f'Distribution of {categorical_cols[0]}',
            'x_axis': categorical_cols[0],
            'y_axis': 'count'
        })
    
    if len(numeric_cols) >= 1:
        suggestions.append({
            'chart_type': 'boxplot',
            'title': f'Distribution of {numeric_cols[0]}',
            'x_axis': numeric_cols[0],
            'y_axis': 'value'
        })
    
    return suggestions

def generate_visualization_config(args: Dict[str, Any], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate enhanced ECharts configuration with strict validation"""
    try:
        chart_type = args.get('chart_type')
        title = args.get('title')
        x_axis = args.get('x_axis')
        y_axis = args.get('y_axis')
        
        # Strict validation of required fields
        if not all([chart_type, title, x_axis, y_axis]):
            logger.error(f"Missing required fields in visualization config: {args}")
            return None
        
        # Extract and validate data
        preview_data = data.get('preview', [])
        if not preview_data:
            logger.error("No data available for visualization")
            return None

        # Extract valid data points based on chart type
        valid_data = []
        if chart_type in ['bar', 'line']:
            valid_data = [
                (str(row[x_axis]), float(row[y_axis]))
                for row in preview_data
                if x_axis in row and y_axis in row
                and row[x_axis] is not None 
                and row[y_axis] is not None
                and not (isinstance(row[y_axis], float) and math.isnan(row[y_axis]))
            ]
        elif chart_type == 'scatter':
            valid_data = [
                [float(row[x_axis]), float(row[y_axis])]
                for row in preview_data
                if x_axis in row and y_axis in row
                and row[x_axis] is not None 
                and row[y_axis] is not None
                and not (isinstance(row[x_axis], float) and math.isnan(row[x_axis]))
                and not (isinstance(row[y_axis], float) and math.isnan(row[y_axis]))
            ]

        # If no valid data points, return None
        if not valid_data:
            logger.error(f"No valid data points found for {chart_type} chart with {x_axis} vs {y_axis}")
            return None

        # Create base config
        config = {
            'backgroundColor': 'transparent',
            'title': {
                'text': title,
                'textStyle': {'color': '#fff', 'fontSize': 16},
                'left': 'center'
            },
            'tooltip': {
                'trigger': 'axis',
                'axisPointer': {'type': 'cross'},
                'backgroundColor': 'rgba(50,50,50,0.9)',
                'borderColor': '#333',
                'textStyle': {'color': '#fff'}
            },
            'grid': {
                'left': '3%',
                'right': '4%',
                'bottom': '15%',
                'containLabel': True
            },
            'xAxis': {
                'type': 'category' if chart_type in ['bar', 'line'] else 'value',
                'axisLabel': {'color': '#fff'},
                'axisLine': {'lineStyle': {'color': '#fff'}}
            },
            'yAxis': {
                'type': 'value',
                'axisLabel': {'color': '#fff'},
                'axisLine': {'lineStyle': {'color': '#fff'}}
            },
            'series': []
        }

        # Configure series based on chart type
        if chart_type in ['bar', 'line']:
            x_values, y_values = zip(*valid_data)
            config['xAxis']['data'] = list(x_values)
            series = {
                'type': chart_type,
                'data': list(y_values),
                'itemStyle': {
                    'color': {
                        'type': 'linear',
                        'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                        'colorStops': [
                            {'offset': 0, 'color': '#83bff6'},
                            {'offset': 0.5, 'color': '#188df0'},
                            {'offset': 1, 'color': '#188df0'}
                        ]
                    }
                }
            }
            if chart_type == 'line':
                series.update({
                    'smooth': True,
                    'symbol': 'circle',
                    'symbolSize': 8,
                    'lineStyle': {'width': 3}
                })
        elif chart_type == 'scatter':
            series = {
                'type': 'scatter',
                'data': valid_data,
                'symbolSize': 12,
                'itemStyle': {'color': '#188df0'}
            }

        config['series'].append(series)

        # Final validation of the complete config
        if not config['series'][0]['data']:
            logger.error("Generated config has no data in series")
            return None

        return config

    except Exception as e:
        logger.exception(f"Error generating visualization config: {str(e)}")
        return None

def new_gradient_color():
    """Generate a new gradient color scheme"""
    return {
        'type': 'linear',
        'x': 0,
        'y': 0,
        'x2': 0,
        'y2': 1,
        'colorStops': [{
            'offset': 0,
            'color': '#83bff6'
        }, {
            'offset': 0.5,
            'color': '#188df0'
        }, {
            'offset': 1,
            'color': '#188df0'
        }]
    }

def new_area_gradient():
    """Generate a new area gradient"""
    return {
        'type': 'linear',
        'x': 0,
        'y': 0,
        'x2': 0,
        'y2': 1,
        'colorStops': [{
            'offset': 0,
            'color': 'rgba(88,160,253,0.5)'
        }, {
            'offset': 1,
            'color': 'rgba(88,160,253,0)'
        }]
    }

# Add helper functions for each chart type...

def format_data_context(data: Optional[Dict[str, Any]]) -> Optional[str]:
    """Format the data context for the AI prompt."""
    if not data:
        return None
        
    try:
        data_summary = f"Data summary: {json.dumps(data['summary'])}\n"
        column_info = "Columns: " + ", ".join(data['columns']) + "\n"
        
        stats_info = "Column statistics:\n"
        for col, stats in data['column_stats'].items():
            if isinstance(stats, dict):
                if stats.get('type') == 'numeric':
                    stats_info += f"{col}: numeric (mean={stats.get('mean')}, min={stats.get('min')}, max={stats.get('max')})\n"
                else:
                    stats_info += f"{col}: categorical ({stats.get('unique_values', 0)} unique values)\n"

        preview = "Sample data (first 5 rows):\n"
        if data.get('preview'):
            preview += json.dumps(data['preview'][:5], indent=2)

        return f"{data_summary}\n{column_info}\n{stats_info}\n{preview}"
    except Exception as e:
        print(f"Error formatting data context: {str(e)}")
        return str(data)

def get_visualization_configs(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get visualization configurations using GPT-4 with structured output."""
    logger.debug("Starting visualization configuration generation")
    
    if not openai_client:
        logger.error("OpenAI client not initialized")
        raise APIKeyError("OpenAI client is not properly initialized")

    try:
        logger.debug("Formatting data context")
        data_context = format_data_context(data)
        logger.debug(f"Data context formatted: {data_context[:200]}...")
        
        system_message = {
            "role": "system",
            "content": """You are a data visualization expert specializing in ECharts.
            Analyze the provided data and create optimal visualizations that best represent the patterns and insights.
            Use dark theme colors and ensure visualizations are clear and informative.
            
            IMPORTANT: Return ONLY a raw JSON object with a 'visualizations' key containing an array of ECharts configurations.
            DO NOT include markdown code blocks or any other formatting.
            DO NOT include explanations or any text outside the JSON object."""
        }

        user_message = {
            "role": "user",
            "content": f"Create visualizations for this data:\n{data_context}"
        }

        logger.debug("Sending request to OpenAI")
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[system_message, user_message]
        )
        logger.debug("Received response from OpenAI")

        try:
            content = response.choices[0].message.content
            # Remove any markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            content = content.strip()
            
            logger.debug(f"Cleaned content for parsing: {content[:200]}...")
            result = json.loads(content)
            
            if not isinstance(result.get('visualizations'), list):
                logger.error("Invalid visualization format - not a list")
                raise ValueError("Invalid visualization format")
            
            logger.debug(f"Successfully parsed {len(result['visualizations'])} visualizations")
            return {
                "success": True,
                "visualizations": result['visualizations']
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            logger.error(f"Raw content: {content}")
            return {
                "success": False,
                "error": f"Invalid visualization format: {str(e)}"
            }

    except Exception as e:
        logger.exception("Error generating visualizations")
        return {
            "success": False,
            "error": str(e)
        }

def determine_best_chart_type(data: Dict[str, Any], columns: List[str]) -> str:
    """Determine the most appropriate chart type based on data characteristics"""
    try:
        # Get column types
        col_types = {col: data['column_stats'][col]['type'] for col in columns}
        
        # Time series detection
        time_cols = [col for col, stats in data['column_stats'].items() 
                    if any(t in col.lower() for t in ['time', 'date', 'year', 'month'])]
        
        if time_cols and any(col_types[col] == 'numeric' for col in columns if col not in time_cols):
            return 'line'  # Time series data
            
        # Count numeric and categorical columns
        numeric_cols = [col for col, type_ in col_types.items() if type_ == 'numeric']
        categorical_cols = [col for col, type_ in col_types.items() if type_ == 'categorical']
        
        if len(numeric_cols) >= 2:
            return 'scatter'  # Multiple numeric columns -> correlation
        elif len(categorical_cols) == 1 and len(numeric_cols) == 1:
            return 'bar'  # Category vs number -> bar chart
        elif len(categorical_cols) == 1:
            return 'pie'  # Single category -> distribution
        else:
            return 'bar'  # Default to bar
            
    except Exception:
        return 'bar'  # Safe default

def validate_data_quality(data: Dict[str, Any]) -> str:
    """Validate data quality and return issues description"""
    issues = []
    
    try:
        preview_data = data.get('preview', [])
        columns = data.get('columns', [])
        stats = data.get('column_stats', {})

        # Check for empty or minimal data
        if not preview_data:
            issues.append("No preview data available")
            return "Dataset appears to be empty or inaccessible."

        # Check for headers-only data
        if len(preview_data) == 0 and columns:
            issues.append("Dataset contains only headers")
            return "Dataset contains only headers without data. Consider adding sample data or explaining the expected format."

        # Check for missing values
        for col in columns:
            null_count = sum(1 for row in preview_data if row.get(col) is None or row.get(col) == '')
            if null_count > 0:
                issues.append(f"Column '{col}' has {null_count} missing values")

        # Check for NaN values in numeric columns
        for col, stat in stats.items():
            if stat.get('type') == 'numeric':
                nan_count = sum(1 for row in preview_data if isinstance(row.get(col), float) and math.isnan(row.get(col)))
                if nan_count > 0:
                    issues.append(f"Column '{col}' has {nan_count} NaN values")

        # Check for inconsistent data types
        for col in columns:
            types_found = set(type(row.get(col)) for row in preview_data if row.get(col) is not None)
            if len(types_found) > 1:
                issues.append(f"Column '{col}' has mixed data types: {', '.join(str(t) for t in types_found)}")

        if issues:
            return "Data Quality Issues Found:\n- " + "\n- ".join(issues) + "\n\nRecommendations will be provided in the analysis."
        
        return ""

    except Exception as e:
        logger.error(f"Error validating data quality: {str(e)}")
        return "Unable to fully validate data quality. Analysis will be performed with available data."
