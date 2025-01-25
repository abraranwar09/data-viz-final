from typing import Dict, Any, List, Optional
import json
from utils.ai_helper import get_ai_insights
from utils.data_processor import process_data  # Assuming this exists for data preprocessing

class SmartVis:
    """
    A smart visualization class that uses AI to dynamically generate ECharts configurations
    based on data analysis and user requirements.
    """
    
    def __init__(self):
        # Define the base schema for ECharts configurations
        self.echarts_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "object"},
                "tooltip": {"type": "object"},
                "legend": {"type": "object"},
                "xAxis": {"type": "object"},
                "yAxis": {"type": "object"},
                "series": {"type": "array"},
                "grid": {"type": "object"},
                "toolbox": {"type": "object"},
                "dataZoom": {"type": "array"},
                "visualMap": {"type": "object"},
            }
        }

    def generate_visualization(self, data: Dict[str, Any], query: str = None) -> Dict[str, Any]:
        """
        Generate a visualization configuration based on the input data and optional query.
        
        Args:
            data: The data to visualize
            query: Optional specific visualization request/question
            
        Returns:
            Dict containing visualization config and metadata
        """
        # Prepare context for AI analysis
        context = {
            "type": "visualization_request",
            "data": data,
            "schema": self.echarts_schema
        }
        
        # If no specific query provided, generate a general analysis request
        if not query:
            query = "Analyze this data and create the most appropriate visualization"
            
        # Get AI insights with visualization configuration
        response = get_ai_insights(query, context)
        
        # Extract the visualization configuration from the markdown response
        config = self._extract_config_from_response(response["answer"])
        
        return {
            "config": config,
            "explanation": response["answer"],
            "confidence": response["confidence"]
        }
    
    def _extract_config_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract the ECharts configuration from the markdown response.
        
        Args:
            response: The markdown response containing the configuration
            
        Returns:
            The extracted ECharts configuration or None if not found
        """
        try:
            # Look for the echarts code block
            start_marker = "```echarts"
            end_marker = "```"
            
            start_idx = response.find(start_marker)
            if start_idx == -1:
                return None
                
            start_idx += len(start_marker)
            end_idx = response.find(end_marker, start_idx)
            
            if end_idx == -1:
                return None
                
            # Extract and parse the JSON configuration
            config_str = response[start_idx:end_idx].strip()
            return json.loads(config_str)
            
        except json.JSONDecodeError:
            return None
            
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate that a configuration matches the ECharts schema.
        
        Args:
            config: The configuration to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Basic validation of required properties
        required_props = ["title", "series"]
        return all(prop in config for prop in required_props)
