from typing import Dict, Any, List, Optional
import json
import logging
from utils.ai_helper import get_ai_insights
from utils.data_processor import process_data

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('smart_vis')

class SmartVis:
    """
    A smart visualization class that uses AI to dynamically generate ECharts configurations
    based on data analysis and user requirements.
    """
    
    def __init__(self):
        logger.info("Initializing SmartVis")
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
        logger.debug(f"Applying common style to config: {json.dumps(config, default=str)}")
        styled_config = {**self.common_style, **config}
        
        # Ensure title styling is preserved
        if "title" in config:
            logger.debug("Preserving custom title styling")
            styled_config["title"] = {
                **self.common_style["title"],
                **config["title"]
            }
        
        # Add axis styling for charts that have axes
        if "xAxis" in config:
            logger.debug("Adding xAxis styling")
            styled_config["xAxis"] = {
                "axisLine": {"lineStyle": {"color": "#666"}},
                "axisLabel": {"color": "#fff"},
                "splitLine": {"lineStyle": {"color": "#333"}},
                **config["xAxis"]
            }
        
        if "yAxis" in config:
            logger.debug("Adding yAxis styling")
            styled_config["yAxis"] = {
                "axisLine": {"lineStyle": {"color": "#666"}},
                "axisLabel": {"color": "#fff"},
                "splitLine": {"lineStyle": {"color": "#333"}},
                **config["yAxis"]
            }
            
        logger.debug(f"Final styled config: {json.dumps(styled_config, default=str)}")
        return styled_config

    def generate_data_preview(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate diverse statistical preview visualizations from processed data.
        Ensures variety in visualization types based on data characteristics.
        """
        visualizations = []
        used_types = set()  # Track used visualization types to avoid redundancy
        
        # Dataset Overview - using gauge
        overview = {
            "title": {"text": "Dataset Overview"},
            "series": [{
                "type": "gauge",
                "min": 0,
                "max": max(data["summary"]["rows"], 100),
                "data": [{"value": data["summary"]["rows"], "name": "Total Rows"}]
            }]
        }
        visualizations.append(self._apply_common_style(overview))
        used_types.add("gauge")

        # Find correlations between numeric columns for scatter/heatmap
        numeric_cols = [col for col, stats in data["column_stats"].items() 
                       if stats["type"] == "numeric"]
        
        if len(numeric_cols) >= 2:
            # Correlation heatmap
            correlation_data = self._generate_correlation_heatmap(data, numeric_cols)
            if correlation_data:
                visualizations.append(correlation_data)
                used_types.add("heatmap")
            
            # Scatter plot for highest correlation pair
            scatter_data = self._generate_scatter_plot(data, numeric_cols)
            if scatter_data:
                visualizations.append(scatter_data)
                used_types.add("scatter")

        # Box plots for numeric distributions
        if numeric_cols and "boxplot" not in used_types:
            boxplot_data = self._generate_boxplot(data, numeric_cols[:3])  # Limit to 3 columns
            if boxplot_data:
                visualizations.append(boxplot_data)
                used_types.add("boxplot")

        # Time series analysis if time columns exist
        time_cols = [col for col in data.get("columns", [])
                    if any(t in col.lower() for t in ["time", "date", "year"])]
        if time_cols and numeric_cols:
            line_chart = self._generate_time_series(data, time_cols[0], numeric_cols[0])
            if line_chart:
                visualizations.append(line_chart)
                used_types.add("line")

        # Categorical analysis using different chart types
        categorical_cols = [col for col, stats in data["column_stats"].items() 
                           if stats["type"] == "categorical"]
        if categorical_cols:
            # Use sunburst for hierarchical categorical data
            if len(categorical_cols) >= 2 and "sunburst" not in used_types:
                sunburst = self._generate_sunburst(data, categorical_cols[:2])
                if sunburst:
                    visualizations.append(sunburst)
                    used_types.add("sunburst")
            
            # Use radar for categorical comparisons
            if "radar" not in used_types:
                radar = self._generate_radar(data, categorical_cols[0])
                if radar:
                    visualizations.append(radar)
                    used_types.add("radar")

        return visualizations[:6]  # Limit total visualizations

    def _generate_correlation_heatmap(self, data: Dict[str, Any], numeric_cols: List[str]) -> Dict[str, Any]:
        """Generate correlation heatmap for numeric columns."""
        try:
            # Calculate correlations
            correlations = [[0 for _ in numeric_cols] for _ in numeric_cols]
            # ... correlation calculation logic ...
            
            return {
                "title": {"text": "Correlation Heatmap"},
                "tooltip": {"position": "top"},
                "xAxis": {"data": numeric_cols, "axisLabel": {"rotate": 45}},
                "yAxis": {"data": numeric_cols},
                "visualMap": {
                    "min": -1,
                    "max": 1,
                    "calculable": True,
                    "orient": "horizontal",
                    "left": "center",
                    "bottom": "15%"
                },
                "series": [{
                    "type": "heatmap",
                    "data": correlations,
                    "label": {"show": True},
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowColor": "rgba(0, 0, 0, 0.5)"
                        }
                    }
                }]
            }
        except Exception as e:
            logger.error(f"Error generating heatmap: {str(e)}")
            return None

    def _generate_scatter_plot(self, data: Dict[str, Any], numeric_cols: List[str]) -> Dict[str, Any]:
        """Generate scatter plot for highest correlated numeric columns."""
        try:
            # Find highest correlated pair
            # ... correlation calculation logic ...
            
            return {
                "title": {"text": f"Correlation: {col1} vs {col2}"},
                "xAxis": {"type": "value", "name": col1},
                "yAxis": {"type": "value", "name": col2},
                "series": [{
                    "type": "scatter",
                    "data": scatter_data,
                    "symbolSize": 10,
                    "emphasis": {
                        "itemStyle": {
                            "shadowBlur": 10,
                            "shadowColor": "rgba(0, 0, 0, 0.5)"
                        }
                    }
                }]
            }
        except Exception as e:
            logger.error(f"Error generating scatter plot: {str(e)}")
            return None

    def generate_visualization(self, data: Dict[str, Any], query: str = None) -> Dict[str, Any]:
        """Generate visualization configuration based on data and query."""
        logger.info(f"Generating visualization for query: {query}")
        logger.debug(f"Input data summary: {json.dumps(self._get_data_summary(data), default=str)}")
        
        try:
            # First generate the statistical preview
            logger.info("Generating statistical preview")
            preview_visualizations = self.generate_data_preview(data)
            logger.debug(f"Generated {len(preview_visualizations)} preview visualizations")
            
            # If there's a specific query, generate additional visualizations
            if query:
                logger.info(f"Processing specific visualization query: {query}")
                context = {
                    "type": "visualization_request",
                    "data": data,
                    "schema": self.echarts_schema
                }
                
                logger.debug("Calling AI insights")
                response = get_ai_insights(query, context)
                logger.debug(f"AI insights response: {json.dumps(response, default=str)}")
                
                if "error" in response:
                    logger.error(f"Error in AI insights: {response['error']}")
                    return {
                        "error": response["error"],
                        "visualizations": preview_visualizations
                    }
                
                # Combine preview and query-specific visualizations
                all_visualizations = preview_visualizations + response.get("visualizations", [])
                logger.info(f"Generated total of {len(all_visualizations)} visualizations")
                
                return {
                    "visualizations": all_visualizations,
                    "explanation": response.get("explanation", "")
                }
            
            logger.info("No specific query provided, returning preview visualizations")
            return {
                "visualizations": preview_visualizations
            }
            
        except Exception as e:
            logger.error(f"Error generating visualization: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "visualizations": [{
                    "title": {"text": "Error Generating Visualization"},
                    "series": [{
                        "type": "bar",
                        "data": [0],
                        "itemStyle": {"color": "#ff0000"},
                        "label": {
                            "show": True,
                            "position": "top",
                            "formatter": f"Error: {str(e)}"
                        }
                    }]
                }]
            }

    def _get_data_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of the data for logging purposes."""
        return {
            "num_rows": len(data.get("preview", [])),
            "num_columns": len(data.get("column_stats", {})),
            "column_types": {
                col: stats.get("type")
                for col, stats in data.get("column_stats", {}).items()
            }
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
