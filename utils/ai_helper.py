import os
from openai import OpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionFunctionMessageParam
)
from functools import lru_cache
import json
import httpx
from typing import Dict, Any, Optional, List, Union

class APIKeyError(Exception):
    """Exception raised for missing or invalid API keys."""
    pass

class WebSearchError(Exception):
    """Exception raised for web search related errors."""
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

async def perplexity_web_search(query: str) -> str:
    """Search the web using Perplexity API with improved error handling."""
    if not PERPLEXITY_API_KEY:
        raise APIKeyError("Perplexity API key is not configured")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
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
                            "content": f"Search and summarize relevant information for: {query}"
                        }
                    ]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    return result["choices"][0]["message"]["content"]
                raise WebSearchError("Invalid response format from Perplexity API")
            elif response.status_code == 401:
                raise APIKeyError("Invalid Perplexity API key")
            elif response.status_code == 429:
                raise WebSearchError("Rate limit exceeded for Perplexity API")
            else:
                raise WebSearchError(f"Perplexity API error: {response.status_code}")

    except httpx.TimeoutException:
        raise WebSearchError("Request to Perplexity API timed out")
    except httpx.RequestError as e:
        raise WebSearchError(f"Network error during web search: {str(e)}")
    except Exception as e:
        raise WebSearchError(f"Unexpected error during web search: {str(e)}")

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

def format_data_context(data: Dict[str, Any]) -> str:
    """Format the data context for the AI prompt."""
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

def send_openai_request(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Send request to OpenAI with function calling capability."""
    if not openai_client:
        raise APIKeyError("OpenAI client is not properly initialized")

    try:
        data_context = format_data_context(context['data'])
        system_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": """You are a data analysis assistant with access to the uploaded document data. 
            You can analyze the data and provide insights. If you need additional information from the web, 
            you can use the search_web function. Format your responses using markdown with proper headings, 
            lists, and tables when appropriate."""
        }

        user_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": f"Context:\n{data_context}\n\nQuestion: {prompt}"
        }

        messages: List[ChatCompletionMessageParam] = [system_message, user_message]

        chat_completion = openai_client.chat.completions.create(
            model="gpt-4o",
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

        message = chat_completion.choices[0].message
        final_content = message.content or ""

        if message.function_call:
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments)
            
            if function_name == "search_web":
                try:
                    search_results = perplexity_web_search(function_args.get("query"))
                    
                    function_message: ChatCompletionFunctionMessageParam = {
                        "role": "function",
                        "name": "search_web",
                        "content": search_results
                    }

                    assistant_message: ChatCompletionAssistantMessageParam = {
                        "role": "assistant",
                        "content": message.content,
                        "function_call": message.function_call
                    }

                    second_messages: List[ChatCompletionMessageParam] = [
                        system_message,
                        user_message,
                        assistant_message,
                        function_message
                    ]

                    second_response = openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=second_messages
                    )
                    final_content = second_response.choices[0].message.content or "No response generated"
                except WebSearchError as e:
                    final_content = f"I encountered an error while searching for additional information: {str(e)}\n\n" + (message.content or "")

        return {
            "answer": final_content,
            "confidence": 0.95,
            "sources": ["Data Analysis"]
        }

    except Exception as e:
        print(f"Error in send_openai_request: {str(e)}")
        return {
            "answer": f"An error occurred while processing your request: {str(e)}",
            "confidence": 0,
            "sources": []
        }

def get_ai_insights(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Get AI insights with proper data context handling."""
    if not context or not context.get('data'):
        return {
            "answer": "Error: No data context provided",
            "confidence": 0,
            "sources": []
        }

    try:
        cleaned_data = clean_data_context(context['data'])
        context_hash = json.dumps({'data': cleaned_data}, sort_keys=True)
        return cached_openai_request(question, context_hash)
    except Exception as e:
        return {
            "answer": f"Error analyzing data: {str(e)}",
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
            "content": "You are a data visualization expert."
        }

        user_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": f"""Analyze this dataset and identify 4 key data comparisons that provide valuable insights. 
            Create a 2x2 grid dashboard using appropriate chart types for each insight. 
            Generate a single, self-contained HTML file that includes all necessary HTML, CSS, and JavaScript code. 
            Include legends and supplementary information. The visualization should use ECharts library. 
            Only return the complete code that can be directly rendered.

            Dataset Information:
            {data_context}
            """
        }

        messages: List[ChatCompletionMessageParam] = [system_message, user_message]

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )

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
