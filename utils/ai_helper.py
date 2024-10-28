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
    """Get AI insights with proper data context handling."""
    if not openai_client:
        raise APIKeyError("OpenAI client is not properly initialized")

    try:
        # Format the data context
        data_context = format_data_context(context.get('data'))
        
        # Enhanced system prompt for better tool usage
        system_prompt = """You are a helpful data analysis assistant. You have access to:
        1. The uploaded data for analysis
        2. A web search tool to find relevant information
        3. A visualization tool to create charts

        When answering:
        - If you need external information, use the web_search tool
        - If the question involves data patterns or trends, use create_visualization
        - Always explain your insights clearly using markdown formatting
        - Use bullet points and headers for better readability
        - Include specific data points to support your analysis
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context:\n{data_context}\n\nQuestion: {question}" if data_context else question}
        ]

        # Make the API call with both tools
        chat_completion = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            functions=[
                {
                    "name": "web_search",
                    "description": "Search the web for additional information or context",
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
                                "enum": ["bar", "line", "scatter", "pie", "boxplot", "heatmap"],
                                "description": "Type of chart to create"
                            },
                            "title": {
                                "type": "string",
                                "description": "Chart title"
                            },
                            "x_axis": {
                                "type": "string",
                                "description": "Column name for x-axis"
                            },
                            "y_axis": {
                                "type": "string",
                                "description": "Column name for y-axis"
                            }
                        },
                        "required": ["chart_type", "title"]
                    }
                }
            ],
            function_call="auto"
        )

        message = chat_completion.choices[0].message
        final_content = message.content or ""

        # Handle function calls
        if message.function_call:
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments)
            
            function_response = None
            if function_name == "web_search":
                search_results = web_search(function_args.get("query"))
                function_response = search_results
                
                # Get a new response incorporating the search results
                messages.extend([
                    {"role": "assistant", "content": message.content, "function_call": message.function_call},
                    {"role": "function", "name": function_name, "content": function_response}
                ])
                
                final_response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=messages
                )
                final_content = final_response.choices[0].message.content

            elif function_name == "create_visualization":
                viz_config = generate_visualization_config(function_args, context.get('data', {}))
                final_content = f"{message.content}\n\n```echarts\n{json.dumps(viz_config, indent=2)}\n```"

        return {
            "answer": final_content,
            "confidence": 0.95 if data_context else 0.8,
            "sources": ["Data Analysis"] if data_context else ["General Assistant"]
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

    # Base configuration
    config = {
        'title': {'text': title},
        'tooltip': {'trigger': 'axis'},
        'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True}
    }

    # Add chart-specific configuration
    if chart_type == 'bar':
        config.update(generate_bar_chart_config(data, x_axis, y_axis))
    elif chart_type == 'line':
        config.update(generate_line_chart_config(data, x_axis, y_axis))
    elif chart_type == 'scatter':
        config.update(generate_scatter_chart_config(data, x_axis, y_axis))
    elif chart_type == 'pie':
        config.update(generate_pie_chart_config(data, x_axis, y_axis))
    elif chart_type == 'boxplot':
        config.update(generate_boxplot_config(data, x_axis))
    elif chart_type == 'heatmap':
        config.update(generate_heatmap_config(data))

    # Apply any additional options
    config.update(additional_options)

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
