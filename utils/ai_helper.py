import os
from typing import Dict, Any, List, Optional, Union
from openai import OpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionFunctionMessageParam,
    ChatCompletionAssistantMessageParam
)
from functools import lru_cache
import json
import requests

class APIKeyError(Exception):
    """Exception raised for missing or invalid API keys."""
    pass

class WebSearchError(Exception):
    """Exception raised for web search related errors."""
    pass

class AIModelError(Exception):
    """Exception raised for AI model related errors."""
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

def perplexity_web_search(query: str) -> str:
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "sonar-small-online",
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

def send_openai_request(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Send request to OpenAI with function calling capability."""
    if not openai_client:
        raise APIKeyError("OpenAI client is not properly initialized")

    try:
        data_context = format_data_context(context.get('data'))
        
        system_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": (
                "You are a helpful assistant. No data is currently loaded, but you can still help with "
                "general questions or guide users on data analysis concepts."
            ) if not data_context else (
                "You are a data analysis assistant with access to the uploaded document data. "
                "You can analyze the data and provide insights. If you need additional information "
                "from the web, you can use the search_web function. Format your responses using "
                "markdown with proper headings, lists, and tables when appropriate."
            )
        }

        user_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": f"Context:\n{data_context}\n\nQuestion: {prompt}" if data_context else prompt
        }

        messages: List[ChatCompletionMessageParam] = [system_message, user_message]

        try:
            chat_completion = openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                functions=[{
                    "name": "search_web",
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
                }],
                function_call="auto"
            )
        except Exception as e:
            raise AIModelError(f"Error calling OpenAI API: {str(e)}")

        message = chat_completion.choices[0].message
        final_content = message.content or ""

        # Handle function calls for web search
        if message.function_call:
            try:
                function_name = message.function_call.name
                function_args = json.loads(message.function_call.arguments)
                
                if function_name == "search_web":
                    search_results = perplexity_web_search(function_args.get("query"))
                    
                    # Create a new message list including the search results
                    search_messages = messages + [
                        ChatCompletionMessageParam(
                            role="assistant",
                            content=message.content,
                            function_call=message.function_call
                        ),
                        ChatCompletionMessageParam(
                            role="function",
                            name="search_web",
                            content=search_results
                        )
                    ]

                    # Get final response incorporating search results
                    final_response = openai_client.chat.completions.create(
                        model="gpt-4",
                        messages=search_messages
                    )
                    final_content = final_response.choices[0].message.content or "No response generated"

            except Exception as e:
                final_content = f"Error during web search: {str(e)}\n\n{message.content or ''}"

        return {
            "answer": final_content,
            "confidence": 0.95 if data_context else 0.8,
            "sources": ["Data Analysis"] if data_context else ["General Assistant"]
        }

    except Exception as e:
        print(f"Error in send_openai_request: {str(e)}")
        return {
            "answer": f"An error occurred while processing your request: {str(e)}",
            "confidence": 0,
            "sources": []
        }

# Helper functions (unchanged)
def get_ai_insights(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Get AI insights with proper data context handling."""
    try:
        if not context or not context.get('data'):
            return send_openai_request(question, {'data': None})
        
        cleaned_data = clean_data_context(context['data'])
        context_hash = json.dumps({'data': cleaned_data}, sort_keys=True)
        return cached_openai_request(question, context_hash)
    except Exception as e:
        return {
            "answer": f"Error analyzing data: {str(e)}",
            "confidence": 0,
            "sources": []
        }

def clean_data_context(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and validate the data context."""
    try:
        if isinstance(data.get('column_stats'), dict) and any('```csv' in key for key in data['column_stats']):
            return {
                'column_stats': {k.replace('```csv', ''): v for k, v in data['column_stats'].items()},
                'columns': [col.replace('```csv', '') for col in data.get('columns', [])],
                'preview': [
                    {k.replace('```csv', ''): v for k, v in row.items()}
                    for row in data.get('preview', [])
                ],
                'summary': data.get('summary', {})
            }
        return data
    except Exception as e:
        print(f"Error cleaning data context: {str(e)}")
        return data

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

@lru_cache(maxsize=100)
def cached_openai_request(prompt: str, context_hash: str) -> Dict[str, Any]:
    """Cache OpenAI requests to avoid duplicate processing."""
    try:
        context = json.loads(context_hash)
        return send_openai_request(prompt, context)
    except Exception as e:
        print(f"Error in cached_openai_request: {str(e)}")
        return {
            "answer": "I encountered an error while processing your request. Please try again later.",
            "confidence": 0,
            "sources": []
        }

def generate_visualizations(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate dynamic visualizations using GPT-4."""
    try:
        cleaned_data = clean_data_context(data)
        data_context = format_data_context(cleaned_data)

        system_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": """You are a data visualization expert. You can create visualizations using ECharts and Mermaid.js.
            Analyze the data and choose the most appropriate visualization types including charts, graphs, and diagrams."""
        }

        user_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": f"""Analyze this dataset and identify 4 key insights that would benefit from visualization. 
            Create a mixed dashboard using appropriate visualization types (ECharts and Mermaid.js) for each insight. 
            Consider using:
            - ECharts for statistical visualizations (charts, plots)
            - Mermaid.js for relationship diagrams, flows, and sequences
            Generate a single, self-contained HTML file that includes all necessary visualization code.
            Include proper titles, legends, and explanatory text.

            Dataset Information:
            {data_context}
            """
        }

        messages: List[ChatCompletionMessageParam] = [system_message, user_message]

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages
            )
        except Exception as e:
            raise AIModelError(f"Error generating visualizations: {str(e)}")

        visualization_code = response.choices[0].message.content
        return {
            "success": True,
            "visualization_code": visualization_code or "Error: No visualization code generated"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
