import os
from openai import OpenAI
from functools import lru_cache
import json
import httpx
from typing import Dict, Any, Optional

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

@lru_cache(maxsize=100)
def cached_openai_request(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Cache OpenAI requests to avoid duplicate processing."""
    try:
        return send_openai_request(prompt, context)
    except Exception as e:
        print(f"Error in cached_openai_request: {str(e)}")
        return {
            "answer": "I encountered an error while processing your request. Please try again later.",
            "confidence": 0,
            "sources": []
        }

def send_openai_request(prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Send request to OpenAI with function calling capability."""
    try:
        # Prepare data context
        data_summary = f"Data summary: {context['data']['summary']}\n"
        column_info = "Columns: " + ", ".join(context['data']['columns']) + "\n"
        stats_info = "Statistics available for: " + ", ".join(
            context['data']['column_stats'].keys())

        system_message = """You are a data analysis assistant with access to the uploaded document data. 
        You can analyze the data and provide insights. If you need additional information from the web, 
        you can use the search_web function. Format your responses using markdown with proper headings, 
        lists, and tables when appropriate."""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"""
            Context:
            {data_summary}
            {column_info}
            {stats_info}
            
            Question: {prompt}
            """}
        ]

        response = openai_client.chat.completions.create(
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

        message = response.choices[0].message

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
                        message,
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
    """Get AI insights with caching and error handling."""
    if not context or not context.get('data'):
        return {
            "answer": "Error: No data context provided",
            "confidence": 0,
            "sources": []
        }

    try:
        return cached_openai_request(question, context)
    except Exception as e:
        return {
            "answer": f"Error analyzing data: {str(e)}",
            "confidence": 0,
            "sources": []
        }

def generate_visualizations(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate dynamic visualizations using GPT-4."""
    try:
        # Prepare data context
        data_summary = f"Data summary: {data['summary']}\n"
        column_info = "Columns: " + ", ".join(data['columns']) + "\n"
        stats_info = "Column statistics:\n"
        
        for col, stats in data['column_stats'].items():
            if stats['type'] == 'numeric':
                stats_info += f"{col}: mean={stats['mean']}, min={stats['min']}, max={stats['max']}\n"
            else:
                stats_info += f"{col}: categorical with {stats['unique_values']} unique values\n"
        
        preview_data = "Sample data (first 5 rows):\n" + str(data['preview'])

        prompt = f"""Analyze this dataset and identify 4 key data comparisons that provide valuable insights. 
        Create a 2x2 grid dashboard using appropriate chart types for each insight. 
        Generate a single, self-contained HTML file that includes all necessary HTML, CSS, and JavaScript code. 
        Include legends and supplementary information. The visualization should use ECharts library. 
        Only return the complete code that can be directly rendered.

        Dataset Information:
        {data_summary}
        {column_info}
        {stats_info}
        {preview_data}
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
