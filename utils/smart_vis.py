from typing import Dict, Any, List, Optional
import json
from utils.ai_helper import get_ai_insights
from utils.data_processor import process_data

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
        
        # Define common styling for all charts
        self.common_style = {
            "backgroundColor": "#1e1e1e",  # Dark background
            "textStyle": {
                "color": "#ffffff"  # White text
            },
            "title": {
                "textStyle": {
                    "color": "#ffffff",
                    "fontSize": 16,
                    "fontWeight": "normal"
                },
                "left": "center",
                "top": 10
            },
            "tooltip": {
                "trigger": "axis",
                "backgroundColor": "rgba(50,50,50,0.9)",
                "borderColor": "#333",
                "textStyle": {
                    "color": "#fff"
                }
            },
            "grid": {
                "left": "10%",
                "right": "10%",
                "top": "15%",
                "bottom": "15%",
                "containLabel": True
            }
        }

    def _apply_common_style(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply common styling to a visualization config."""
        styled_config = {**self.common_style, **config}
        
        # Ensure title styling is preserved
        if "title" in config:
            styled_config["title"] = {
                **self.common_style["title"],
                **config["title"]
            }
        
        # Add axis styling for charts that have axes
        if "xAxis" in config:
            styled_config["xAxis"] = {
                "axisLine": {"lineStyle": {"color": "#666"}},
                "axisLabel": {"color": "#fff"},
                "splitLine": {"lineStyle": {"color": "#333"}},
                **config["xAxis"]
            }
        
        if "yAxis" in config:
            styled_config["yAxis"] = {
                "axisLine": {"lineStyle": {"color": "#666"}},
                "axisLabel": {"color": "#fff"},
                "splitLine": {"lineStyle": {"color": "#333"}},
                **config["yAxis"]
            }
            
        return styled_config

    def generate_data_preview(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate statistical preview visualizations from processed data.
        
        Args:
            data: Processed data dictionary from data_processor
            
        Returns:
            List of visualization configurations
        """
        visualizations = []
        
        # Dataset Overview
        overview = {
            "title": {"text": "Dataset Overview"},
            "series": [{
                "type": "gauge",
                "min": 0,
                "max": max(data["summary"]["rows"], 100),  # Adjust max based on data
                "axisLine": {
                    "lineStyle": {
                        "color": [[0.3, "#67e0e3"], [0.7, "#37a2da"], [1, "#fd666d"]]
                    }
                },
                "pointer": {"itemStyle": {"color": "auto"}},
                "axisTick": {"distance": -30, "length": 8, "lineStyle": {"color": "#fff"}},
                "splitLine": {"distance": -30, "length": 30, "lineStyle": {"color": "#fff"}},
                "axisLabel": {"color": "#fff", "distance": -40, "fontSize": 12},
                "detail": {"valueAnimation": True, "color": "#fff"},
                "data": [
                    {"value": data["summary"]["rows"], "name": "Total Rows"},
                    {"value": data["summary"]["columns"], "name": "Total Columns"},
                    {"value": float(data["summary"]["memory_usage"].split()[0]), "name": "Memory (MB)"}
                ]
            }]
        }
        visualizations.append(self._apply_common_style(overview))
        
        # Data Quality Analysis
        for col, stats in data["column_stats"].items():
            if stats["type"] == "numeric":
                # Distribution plot for numeric columns
                vis_config = {
                    "title": {"text": f"Distribution: {col}"},
                    "xAxis": {"type": "category", "data": ["Mean", "Median", "Std Dev"]},
                    "yAxis": {"type": "value"},
                    "series": [{
                        "type": "bar",
                        "data": [
                            {"value": stats["mean"], "itemStyle": {"color": "#37a2da"}},
                            {"value": stats["median"], "itemStyle": {"color": "#67e0e3"}},
                            {"value": stats["std"], "itemStyle": {"color": "#fd666d"}}
                        ],
                        "label": {
                            "show": True,
                            "position": "top",
                            "color": "#fff",
                            "formatter": "{c:.2f}"
                        }
                    }]
                }
                visualizations.append(self._apply_common_style(vis_config))
            else:
                # Bar chart for categorical columns
                categories = list(stats["top_values"].keys())
                values = list(stats["top_values"].values())
                vis_config = {
                    "title": {"text": f"Top Categories: {col}"},
                    "xAxis": {"type": "category", "data": categories},
                    "yAxis": {"type": "value"},
                    "series": [{
                        "type": "bar",
                        "data": values,
                        "itemStyle": {
                            "color": new_color = {
                                "type": "linear",
                                "x": 0,
                                "y": 0,
                                "x2": 0,
                                "y2": 1,
                                "colorStops": [{
                                    "offset": 0,
                                    "color": "#37a2da"
                                }, {
                                    "offset": 1,
                                    "color": "#67e0e3"
                                }]
                            }
                        },
                        "label": {
                            "show": True,
                            "position": "top",
                            "color": "#fff"
                        }
                    }]
                }
                visualizations.append(self._apply_common_style(vis_config))
        
        return visualizations

    def generate_visualization(self, data: Dict[str, Any], query: str = None) -> Dict[str, Any]:
        """
        Generate a visualization configuration based on the input data and optional query.
        
        Args:
            data: The data to visualize
            query: Optional specific visualization request/question
            
        Returns:
            Dict containing visualization config and metadata
        """
        # First generate the statistical preview
        preview_visualizations = self.generate_data_preview(data)
        
        # If there's a specific query, generate additional visualizations
        if query:
            context = {
                "type": "visualization_request",
                "data": data,
                "schema": self.echarts_schema
            }
            
            response = get_ai_insights(query, context)
            custom_config = self._extract_config_from_response(response["answer"])
            
            if custom_config:
                preview_visualizations.append(self._apply_common_style(custom_config))
        
        return {
            "visualizations": preview_visualizations,
            "data_summary": data["summary"]
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
