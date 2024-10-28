import os
import httpx

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
    stats_info = "Statistics available for: " + ", ".join(context['data']['column_stats'].keys())
    
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
                    'model': 'mixtral-8x7b-instruct',
                    'messages': [
                        {'role': 'system', 'content': 'You are a data analysis assistant.'},
                        {'role': 'user', 'content': prompt}
                    ]
                }
            )
            
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
        return {
            'answer': f"Error: {str(e)}",
            'confidence': 0,
            'sources': []
        }
