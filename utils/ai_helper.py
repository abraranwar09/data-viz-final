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
    """Get AI insights with enhanced tool usage and dynamic responses."""
    logger.debug(f"Starting AI insights request for question: {question}")
    
    if not openai_client:
        logger.error("OpenAI client not initialized")
        return {
            "answer": "The AI service is not properly configured. Please check your API keys.",
            "confidence": 0,
            "sources": []
        }

    try:
        data_context = format_data_context(context.get('data'))
        logger.debug(f"Formatted data context: {data_context[:200]}...")
        
        # Enhanced system prompt for better tool usage
        system_prompt = """You are an advanced data analysis assistant with expertise in data visualization.

        Available Tools:
        1. Web Search (via Perplexity AI) - Use for current information or additional context
        2. Visualization Generator - Create dynamic charts using ECharts
        
        Visualization Capabilities:
        - Basic: line, bar, scatter, pie charts
        - Statistical: boxplot, heatmap
        - Advanced: sunburst, treemap, graph networks
        - Multi-dimensional: parallel, sankey diagrams
        - 3D: scatter3D, surface plots
        
        When responding:
        1. For data questions:
           - Analyze the context carefully
           - Choose the most appropriate visualization type
           - Explain your choice and insights
        
        2. For visualization requests:
           - Consider data characteristics
           - Suggest the best chart type if not specified
           - Use advanced visualizations when appropriate
        
        3. For general questions:
           - Use web search for current information
           - Combine data insights with web context
           - Provide clear, structured responses

        Always explain your reasoning and provide context for your choices."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{data_context}\n\nQuestion: {question}" if data_context else question}
        ]

        # Enhanced function definitions
        functions = [
            {
                "name": "web_search",
                "description": "Search the web for current information or additional context",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_visualization",
                "description": "Create a data visualization using ECharts",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_type": {
                            "type": "string",
                            "enum": [
                                "line", "bar", "scatter", "pie", 
                                "boxplot", "heatmap", "sunburst", 
                                "treemap", "graph", "parallel", 
                                "sankey", "scatter3D"
                            ],
                            "description": "Type of chart to create"
                        },
                        "title": {
                            "type": "string",
                            "description": "Chart title"
                        },
                        "x_axis": {
                            "type": "string",
                            "description": "Column name for x-axis or primary dimension"
                        },
                        "y_axis": {
                            "type": "string",
                            "description": "Column name for y-axis or secondary dimension"
                        },
                        "additional_options": {
                            "type": "object",
                            "description": "Additional chart configuration options"
                        }
                    },
                    "required": ["chart_type", "title"]
                }
            }
        ]

        # Make the API call with enhanced function calling
        chat_completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            functions=functions,
            function_call="auto"
        )

        message = chat_completion.choices[0].message
        final_content = message.content or ""

        # Handle function calls with better context management
        if message.function_call:
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments)
            
            if function_name == "web_search":
                search_results = web_search(function_args.get("query"))
                
                # Get a new response incorporating the search results
                messages.extend([
                    {"role": "assistant", "content": message.content, "function_call": message.function_call},
                    {"role": "function", "name": function_name, "content": search_results}
                ])
                
                final_response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=messages
                )
                final_content = final_response.choices[0].message.content

            elif function_name == "create_visualization":
                viz_config = generate_visualization_config(function_args, context.get('data', {}))
                
                # Add visualization context to the response
                viz_context = f"\n\nI've created a visualization based on your request. Here's what it shows:\n\n"
                final_content = f"{message.content}{viz_context}```echarts\n{json.dumps(viz_config, indent=2)}\n```"

        return {
            "answer": final_content,
            "confidence": 0.95 if data_context else 0.8,
            "sources": ["Data Analysis", "Web Search"] if "web_search" in final_content else ["Data Analysis"]
        }

    except Exception as e:
        logger.exception("Error in get_ai_insights")
        return {
            "answer": f"An error occurred while processing your request: {str(e)}",
            "confidence": 0,
            "sources": []
        }

def generate_visualization_config(args: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate ECharts configuration based on requested visualization"""
    chart_type = args.get('chart_type')
    title = args.get('title')
    x_axis = args.get('x_axis')
    y_axis = args.get('y_axis')
    additional_options = args.get('additional_options', {})

    # Enhanced base configuration with better styling
    config = {
        'title': {
            'text': title,
            'textStyle': {
                'color': '#fff',
                'fontSize': 16
            }
        },
        'tooltip': {
            'trigger': 'axis',
            'axisPointer': {
                'type': 'cross',
                'label': {
                    'backgroundColor': '#6a7985'
                }
            }
        },
        'grid': {
            'left': '3%',
            'right': '4%',
            'bottom': '3%',
            'containLabel': True
        },
        'toolbox': {
            'feature': {
                'saveAsImage': {},
                'dataZoom': {},
                'dataView': {},
                'restore': {}
            }
        }
    }

    # Add chart-specific configuration
    if chart_type == 'sunburst':
        config.update(generate_sunburst_config(data))
    elif chart_type == 'treemap':
        config.update(generate_treemap_config(data))
    elif chart_type == 'graph':
        config.update(generate_graph_config(data))
    elif chart_type == 'parallel':
        config.update(generate_parallel_config(data))
    elif chart_type == 'sankey':
        config.update(generate_sankey_config(data))
    elif chart_type == 'heatmap':
        config.update(generate_heatmap_config(data))
    elif chart_type == 'scatter3D':
        config.update(generate_scatter3d_config(data))
    else:
        # Default to basic chart types with enhanced styling
        config.update(generate_basic_chart_config(chart_type, data, x_axis, y_axis))

    # Apply any additional options
    config.update(additional_options)

    return config

def generate_basic_chart_config(chart_type: str, data: Dict[str, Any], x_axis: str, y_axis: str) -> Dict[str, Any]:
    """Generate configuration for basic chart types with enhanced styling"""
    config = {
        'xAxis': {
            'type': 'category',
            'boundaryGap': True,
            'axisLine': {'lineStyle': {'color': '#fff'}},
            'axisLabel': {'color': '#fff'}
        },
        'yAxis': {
            'type': 'value',
            'axisLine': {'lineStyle': {'color': '#fff'}},
            'axisLabel': {'color': '#fff'}
        },
        'series': [{
            'type': chart_type,
            'smooth': True,
            'symbolSize': 8,
            'itemStyle': {
                'color': '#91cc75',
                'borderWidth': 2
            },
            'emphasis': {
                'focus': 'series',
                'itemStyle': {
                    'shadowBlur': 10,
                    'shadowColor': 'rgba(0,0,0,0.5)'
                }
            }
        }]
    }

    if chart_type in ['line', 'bar']:
        config['series'][0].update({
            'areaStyle': {
                'opacity': 0.3,
                'color': {
                    'type': 'linear',
                    'x': 0,
                    'y': 0,
                    'x2': 0,
                    'y2': 1,
                    'colorStops': [{
                        'offset': 0,
                        'color': '#91cc75'
                    }, {
                        'offset': 1,
                        'color': 'rgba(145,204,117,0.1)'
                    }]
                }
            }
        })

    return config

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
