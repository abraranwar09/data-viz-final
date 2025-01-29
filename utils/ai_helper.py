import os
import logging
from openai import OpenAI
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ai_helper')

# Initialize OpenAI client here
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def get_ai_insights(question, data):
    """
    Generate any type of ECharts visualization based on user request or data analysis.
    If no specific question is asked, analyzes the data to create the most insightful visualization.
    
    Args:
        question: User's visualization request or None for automatic analysis
        data: The data to visualize
    """
    try:
        # Format data for GPT-4
        context = {
            'question':
            question or
            "Analyze this data and create the most insightful visualization",
            'data':
            data.get('preview', [])[:5],  # First 5 rows for context
            'columns':
            list(data.get('preview', [{}])[0].keys())
            if data.get('preview') else [],
            'column_stats':
            data.get('column_stats', {})  # Add statistics if available
        }

        # Get visualization from GPT-4 with structured output
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[{
                "role":
                "system",
                "content":
                """You are an expert in data visualization using ECharts. Give an answer and also  Create a visualization that best answers the user's request or reveals key insights in the data. Your response must be a valid ECharts configuration matching this schema:

{
    "title": {
        "text": string,  // Clear title describing the visualization
        "textStyle": { "color": "#fff" }
    },
    "tooltip": {
        "trigger": "axis" | "item",
        "formatter": string  // Optional tooltip format
    },
    "xAxis": {  // Optional, not needed for pie charts etc
        "type": "value" | "category" | "time",
        "name": string,  // Axis label
        "data"?: array,  // Required for category type
        "axisLabel": { "color": "#fff" }
    },
    "yAxis": {  // Optional, not needed for pie charts etc
        "type": "value" | "category",
        "name": string,  // Axis label
        "axisLabel": { "color": "#fff" }
    },
    "series": [{
        "type": string,  // Any valid ECharts chart type
        "data": array,   // The actual data points
        "itemStyle"?: {
            "color": string | gradient
        },
        // Include any other valid ECharts series options
    }],
    "backgroundColor": "transparent",
    "textStyle": { "color": "#fff" }
}

You can use ANY ECharts chart type (bar, line, scatter, pie, radar, funnel, gauge, boxplot, candlestick, heatmap, tree, treemap, sunburst, parallel, sankey, etc).
Choose the chart type that best represents the data and answers the user's question.
Return ONLY the ECharts configuration JSON with no additional text."""
            }, {
                "role": "user",
                "content": f"Data context: {json.dumps(context)}"
            }],
            temperature=0.2)

        # The response is guaranteed to be valid JSON
        config = response.choices[0].message.content

        return {
            'message': 'Visualization generated',
            'visualization': json.loads(config)
        }

    except Exception as e:
        logger.error(f"Error generating visualization: {str(e)}")
        return {'error': str(e)}


def get_visualization_configs(data, user_request=None):
    """
    Generate visualizations based on user request or data structure.
    
    Args:
        data: The data to visualize
        user_request: Optional string containing user's visualization request
    """
    try:
        # If user has a specific request, use that
        if user_request:
            return get_ai_insights(user_request, data)

        # Otherwise, let GPT-4 analyze the data and suggest appropriate visualizations
        return get_ai_insights(
            "Analyze this data and create the most insightful visualization that best represents the patterns and relationships in the data. Consider all available chart types in ECharts.",
            data)

    except Exception as e:
        logger.error(f"Error in get_visualization_configs: {str(e)}")
        return {'error': str(e)}


def get_chat_response(question, data):
    """
    Generate a chat response using GPT-4 with function calling capabilities.
    Can both answer questions and generate visualizations as needed.
    
    Args:
        question: User's question
        data: The data context
    """
    try:
        # Format data context
        context = {
            'data': data.get('preview', [])[:5],  # First 5 rows for context
            'columns': list(data.get('preview', [{}])[0].keys()) if data.get('preview') else [],
            'column_stats': data.get('column_stats', {})
        }

        # Get response from GPT-4 with function calling
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": """You are a helpful data analysis assistant. You can:
                1. Answer questions about the data
                2. Generate visualizations when needed
                3. Perform statistical analysis
                4. Explain patterns and trends
                
                When a visualization would be helpful, call the create_visualization function.
                Otherwise, provide a clear, concise response."""
            }, {
                "role": "user",
                "content": f"Question: {question}\n\nData context: {json.dumps(context)}"
            }],
            functions=[{
                "name": "create_visualization",
                "description": "Create a visualization to answer the question or show insights",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_type": {
                            "type": "string",
                            "description": "The type of chart to create (bar, line, scatter, pie, etc.)"
                        },
                        "title": {
                            "type": "string",
                            "description": "Clear title describing the visualization"
                        },
                        "config": {
                            "type": "object",
                            "description": "The ECharts configuration for the visualization"
                        }
                    },
                    "required": ["chart_type", "title", "config"]
                }
            }],
            function_call="auto"
        )

        message = response.choices[0].message
        
        # Handle function calling response
        if message.function_call:
            # If the model called create_visualization, generate a visualization
            if message.function_call.name == "create_visualization":
                function_args = json.loads(message.function_call.arguments)
                return {
                    'message': message.content or 'Here is a visualization to help answer your question.',
                    'visualization': function_args['config']
                }
        
        # For regular responses, just return the message
        return {
            'message': message.content,
            'visualization': None
        }

    except Exception as e:
        logger.error(f"Error generating chat response: {str(e)}")
        return {'error': str(e)}
