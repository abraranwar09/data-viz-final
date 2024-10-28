import os
from openai import OpenAI
from functools import lru_cache
import json
import httpx
from typing import Dict, Any, Optional, List, Union

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def clean_data_context(data: Dict[str, Any]) -> Dict[str, Any]:
    """Clean and validate the data context."""
    try:
        # Handle CSV string data if present
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
        # Prepare data context
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
    try:
        # Format the data context
        data_context = format_data_context(context['data'])

        system_message = """You are a data analysis assistant with access to the uploaded document data. 
        You can analyze the data and provide insights. If you need additional information from the web, 
        you can use the search_web function. Format your responses using markdown with proper headings, 
        lists, and tables when appropriate."""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Context:\n{data_context}\n\nQuestion: {prompt}"}
        ]

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

        if message.function_call:
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments)
            
            if function_name == "search_web":
                search_results = perplexity_web_search(function_args.get("query"))
                
                second_response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": message.content, "function_call": message.function_call},
                        {
                            "role": "function",
                            "name": "search_web",
                            "content": search_results
                        }
                    ]
                )
                final_content = second_response.choices[0].message.content
        else:
            final_content = message.content

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

def perplexity_web_search(query: str) -> str:
    """Search the web using Perplexity API."""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
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
                            "content": f"Search and summarize relevant information for: {query}"
                        }
                    ]
                }
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"Error: Unable to perform web search (Status code: {response.status_code})"

    except Exception as e:
        return f"Error performing web search: {str(e)}"

def get_ai_insights(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Get AI insights with proper data context handling."""
    if not context or not context.get('data'):
        return {
            "answer": "Error: No data context provided",
            "confidence": 0,
            "sources": []
        }

    try:
        # Clean and validate the context data
        cleaned_data = clean_data_context(context['data'])
        # Convert context to a hashable string for caching
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
        # Clean and format the data context
        cleaned_data = clean_data_context(data)
        data_context = format_data_context(cleaned_data)

        prompt = f"""Analyze this dataset and identify 4 key data comparisons that provide valuable insights. 
        Create a 2x2 grid dashboard using appropriate chart types for each insight. 
        Generate a single, self-contained HTML file that includes all necessary HTML, CSS, and JavaScript code. 
        Include legends and supplementary information. The visualization should use ECharts library. 
        Only return the complete code that can be directly rendered.

        Dataset Information:
        {data_context}
        """

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a data visualization expert."},
                {"role": "user", "content": prompt}
            ]
        )

        visualization_code = response.choices[0].message.content
        return {
            "success": True,
            "visualization_code": visualization_code
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
