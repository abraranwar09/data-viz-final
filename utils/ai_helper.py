import os
import httpx
from openai import OpenAI

openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

def get_ai_insights(question, context):
    """
    Get insights from Perplexity AI API
    """
    api_key = os.environ.get('PERPLEXITY_API_KEY')
    if not api_key:
        return {
            'answer': "Error: Perplexity API key not configured",
            'confidence': 0,
            'sources': []
        }

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    # Prepare data context
    data_summary = f"Data summary: {context['data']['summary']}\n"
    column_info = "Columns: " + ", ".join(context['data']['columns']) + "\n"
    stats_info = "Statistics available for: " + ", ".join(
        context['data']['column_stats'].keys())

    prompt = f"""Analyze this dataset:
    {data_summary}
    {column_info}
    {stats_info}
    
    Question: {question}
    """

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                'https://api.perplexity.ai/chat/completions',
                headers=headers,
                json={
                    'model': 'llama-3.1-sonar-small-128k-online',
                    'messages': [{
                        'role': 'system',
                        'content': 'You are a data analysis assistant.'
                    }, {
                        'role': 'user',
                        'content': prompt
                    }]
                })

            if response.status_code == 200:
                result = response.json()
                return {
                    'answer': result['choices'][0]['message']['content'],
                    'confidence': 0.95,
                    'sources': ['Data Analysis']
                }
            else:
                return {
                    'answer': f"API Error: {response.status_code}",
                    'confidence': 0,
                    'sources': []
                }

    except Exception as e:
        return {'answer': f"Error: {str(e)}", 'confidence': 0, 'sources': []}

def generate_visualizations(data):
    """
    Generate dynamic visualizations using GPT-4
    """
    try:
        # Prepare data context for GPT-4
        data_summary = f"Data summary: {data['summary']}\n"
        column_info = "Columns: " + ", ".join(data['columns']) + "\n"
        stats_info = "Column statistics:\n"
        for col, stats in data['column_stats'].items():
            if stats['type'] == 'numeric':
                stats_info += f"{col}: mean={stats['mean']}, min={stats['min']}, max={stats['max']}\n"
            else:
                stats_info += f"{col}: categorical with {stats['unique_values']} unique values\n"
        
        preview_data = "Sample data (first 5 rows):\n" + str(data['preview'])

        prompt = f"""Analyze this dataset and identify 4 key data comparisons that provide valuable insights. Create a 2x2 grid dashboard using appropriate chart types for each insight. Generate a single, self-contained HTML file that includes all necessary HTML, CSS, and JavaScript code. Include legends and supplementary information. The visualization should use ECharts library. Only return the complete code that can be directly rendered.

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
            'success': True,
            'visualization_code': visualization_code
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
