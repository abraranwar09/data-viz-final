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

        # Enhanced system prompt for better visualization guidance
        system_prompt = """You are an expert data analyst and visualization specialist. Your primary goal is to create insightful visualizations from data.

        REQUIREMENTS:
        1. For initial analysis:
           - Create at least 3 different visualizations
           - Show different aspects of the data
           - Provide clear explanations for each visualization
           - Summarize key findings

        2. For user questions:
           - Always create at least one visualization
           - Choose the most appropriate chart type
           - Explain your visualization choices

        VISUALIZATION GUIDELINES:
        - Numerical relationships: Use scatter plots or line charts
        - Distributions: Use histograms or box plots
        - Categories: Use bar charts or pie charts
        - Time series: Use line charts with time on x-axis
        - Correlations: Use heatmaps or scatter matrices
        - Complex relationships: Use sunburst or treemap charts

        ALWAYS:
        - Analyze the full data structure
        - Create multiple visualizations for comprehensive analysis
        - Explain patterns and insights clearly
        - Choose appropriate chart types based on data characteristics
        - Provide context for each visualization

        NEVER:
        - Refuse to create a visualization
        - Return analysis without visualizations
        - Ignore any part of the data structure"""

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
                visualizations.append({
                    'config': config,
                    'explanation': viz_config['explanation']
                })
            except Exception as e:
                logger.error(f"Error generating visualization: {str(e)}")

        # Construct the final response with markdown formatting
        final_response = [
            "# Data Analysis Report\n\n",
            function_args['analysis'],
            "\n\n## Visualizations\n"
        ]

        for i, viz in enumerate(visualizations, 1):
            final_response.extend([
                f"\n### Visualization {i}\n",
                viz['explanation'],
                f"\n```echarts\n{json.dumps(viz['config'], indent=2)}\n```\n"
            ])

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

def generate_visualization_config(args: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate enhanced ECharts configuration with advanced features"""
    try:
        chart_type = args.get('chart_type')
        title = args.get('title')
        x_axis = args.get('x_axis')
        y_axis = args.get('y_axis')
        
        # Extract data for visualization
        preview_data = data.get('preview', [])
        
        # Base theme configuration
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
                'type': 'category',
                'data': [],
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

        # Process data based on chart type
        if chart_type == 'bar':
            # Extract unique x values and corresponding y values
            x_values = []
            y_values = []
            for row in preview_data:
                if x_axis in row and y_axis in row:
                    x_values.append(str(row[x_axis]))
                    y_values.append(float(row[y_axis]) if row[y_axis] is not None else 0)

            config['xAxis']['data'] = x_values
            config['series'].append({
                'type': 'bar',
                'data': y_values,
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
                },
                'emphasis': {
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowColor': 'rgba(0,0,0,0.5)'
                    }
                }
            })

        elif chart_type == 'line':
            x_values = []
            y_values = []
            for row in preview_data:
                if x_axis in row and y_axis in row:
                    x_values.append(str(row[x_axis]))
                    y_values.append(float(row[y_axis]) if row[y_axis] is not None else 0)

            config['xAxis']['data'] = x_values
            config['series'].append({
                'type': 'line',
                'data': y_values,
                'smooth': True,
                'symbol': 'circle',
                'symbolSize': 8,
                'lineStyle': {'width': 3},
                'itemStyle': {'color': '#188df0'},
                'areaStyle': {
                    'color': {
                        'type': 'linear',
                        'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                        'colorStops': [
                            {'offset': 0, 'color': 'rgba(24,141,240,0.5)'},
                            {'offset': 1, 'color': 'rgba(24,141,240,0)'}
                        ]
                    }
                }
            })

        elif chart_type == 'scatter':
            data_points = []
            for row in preview_data:
                if x_axis in row and y_axis in row:
                    x_val = row[x_axis]
                    y_val = row[y_axis]
                    if x_val is not None and y_val is not None:
                        data_points.append([float(x_val), float(y_val)])

            config['xAxis']['type'] = 'value'
            config['series'].append({
                'type': 'scatter',
                'data': data_points,
                'symbolSize': 12,
                'itemStyle': {'color': '#188df0'},
                'emphasis': {
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowColor': 'rgba(0,0,0,0.5)'
                    }
                }
            })

        return config

    except Exception as e:
        logger.exception("Error generating visualization config")
        return {
            'title': {'text': 'Error Creating Visualization'},
            'xAxis': {'type': 'category', 'data': []},
            'yAxis': {'type': 'value'},
            'series': [{'type': 'bar', 'data': []}]
        }

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
