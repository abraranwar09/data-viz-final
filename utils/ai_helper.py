import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from openai.types.chat import (ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
                               ChatCompletionFunctionMessageParam)
import json
import requests
import logging
import math
from utils.json_sanitizer import sanitize_json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('ai_helper')


class APIKeyError(Exception):
    """Exception raised for missing or invalid API keys."""
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


def get_ai_insights(question: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get insights from the AI model using the given question and context.
    Handles visualization requests and data analysis.
    """
    try:
        context = sanitize_json(context)

        # Detect if visualization is requested
        viz_keywords = ['chart', 'plot', 'graph', 'visualize', 'visualization', 'show']
        is_viz_request = any(keyword in question.lower() for keyword in viz_keywords)

        if is_viz_request:
            chart_configs = []

            # 1. First try GPT-4 function calling approach
            try:
                viz_configs = get_visualization_configs(context)
                if viz_configs.get("visualizations"):
                    for viz in viz_configs["visualizations"]:
                        config = generate_visualization_config(viz, context)
                        if config:
                            chart_configs.append(config)
            except Exception as e:
                logger.error(f"Primary visualization attempt failed: {str(e)}")

            # 2. If no charts yet, try basic suggestions
            if not chart_configs:
                try:
                    basic_suggestions = generate_basic_suggestions(context)
                    for suggestion in basic_suggestions:
                        config = generate_visualization_config(suggestion, context)
                        if config:
                            chart_configs.append(config)
                except Exception as e:
                    logger.error(f"Basic suggestions failed: {str(e)}")

            # 3. If still no charts, force a simple visualization
            if not chart_configs:
                try:
                    # Get any numeric column
                    numeric_cols = [
                        col for col, stats in context.get('column_stats', {}).items()
                        if stats.get('type') == 'numeric'
                    ]

                    if numeric_cols:
                        # Create a simple bar chart of the first numeric column
                        simple_config = {
                            'chart_type': 'bar',
                            'title': f'Distribution of {numeric_cols[0]}',
                            'x_axis': numeric_cols[0],
                            'y_axis': 'value',
                            'explanation': 'Basic distribution visualization'
                        }
                        config = generate_visualization_config(simple_config, context)
                        if config:
                            chart_configs.append(config)
                    else:
                        # If no numeric columns, use first categorical column as pie chart
                        categorical_cols = [
                            col for col, stats in context.get('column_stats', {}).items()
                            if stats.get('type') == 'categorical'
                        ]
                        if categorical_cols:
                            simple_config = {
                                'chart_type': 'pie',
                                'title': f'Distribution of {categorical_cols[0]}',
                                'x_axis': categorical_cols[0],
                                'explanation': 'Basic categorical distribution'
                            }
                            config = generate_visualization_config(simple_config, context)
                            if config:
                                chart_configs.append(config)
                except Exception as e:
                    logger.error(f"Forced visualization failed: {str(e)}")

            # 4. Absolute last resort - create an empty chart with message
            if not chart_configs:
                empty_chart = {
                    'title': {'text': 'Data Overview'},
                    'tooltip': {},
                    'series': [{
                        'type': 'bar',
                        'data': [1],
                        'itemStyle': {'color': '#37a2da'},
                        'label': {
                            'show': True,
                            'position': 'top',
                            'formatter': 'No visualizable data found'
                        }
                    }]
                }
                chart_configs.append(empty_chart)

            return {
                "answer": "Here are the visualizations based on your data:",
                "visualizations": chart_configs
            }

        else:
            # Handle non-visualization requests
            system_prompt = "You are a data analysis expert. Answer the specific question asked using the data provided."

            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "system",
                    "content": system_prompt
                }, {
                    "role": "user",
                    "content": question,
                }, {
                    "role": "system", 
                    "content": f"Data Context:\n{json.dumps(context)}"
                }],
                temperature=0.2
            )

            return {"answer": response.choices[0].message.content}

    except Exception as e:
        logger.error(f"Error in get_ai_insights: {str(e)}")
        # Even on complete failure, return an empty chart
        return {
            "answer": "Attempting to visualize your data:",
            "visualizations": [{
                'title': {'text': 'Data Overview'},
                'tooltip': {},
                'series': [{
                    'type': 'bar',
                    'data': [1],
                    'itemStyle': {'color': '#37a2da'},
                    'label': {
                        'show': True,
                        'position': 'top',
                        'formatter': 'Error processing data'
                    }
                }]
            }]
        }


def prepare_data_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare and validate data context for visualization with enhanced error handling."""
    logger.debug("Starting data context preparation")
    
    try:
        # Validate input context
        if not isinstance(context, dict):
            logger.error("Invalid context format provided")
            return {"success": False, "error": "Invalid data format"}

        # Extract and validate columns with proper logging
        column_stats = context.get('column_stats', {})
        preview_data = context.get('preview', [])
        
        if not column_stats:
            logger.error("No column statistics found in context")
            return {"success": False, "error": "Missing column statistics"}
            
        if not preview_data:
            logger.error("No preview data found in context")
            return {"success": False, "error": "Missing preview data"}

        # Extract column information with validation
        numeric_cols = []
        categorical_cols = []
        time_cols = []
        
        for col, stats in column_stats.items():
            if not isinstance(stats, dict):
                logger.warning(f"Invalid statistics format for column {col}")
                continue
                
            col_type = stats.get('type')
            if col_type == 'numeric':
                numeric_cols.append(col)
            elif col_type == 'categorical':
                categorical_cols.append(col)
                
            # Check for temporal columns
            if any(t in col.lower() for t in ['time', 'date', 'year', 'month', 'day']):
                time_cols.append(col)

        logger.debug(f"Found {len(numeric_cols)} numeric, {len(categorical_cols)} categorical, and {len(time_cols)} temporal columns")

        # Validate data availability for visualization
        if not numeric_cols and not categorical_cols:
            logger.error("No valid columns found for visualization")
            return {
                "success": False,
                "error": "No numeric or categorical data available for visualization"
            }

        # Prepare enhanced context with metadata
        data_context = {
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "time_columns": time_cols,
            "total_rows": len(preview_data),
            "column_stats": {
                col: stats for col, stats in column_stats.items()
                if isinstance(stats, dict)
            },
            "preview": preview_data[:10],  # Limit preview data
            "columns": list(column_stats.keys()),
            "metadata": {
                "numeric_count": len(numeric_cols),
                "categorical_count": len(categorical_cols),
                "temporal_count": len(time_cols),
                "total_columns": len(column_stats)
            },
            "available_chart_types": [
                "bar", "line", "scatter", "pie", "boxplot", "heatmap",
                "treemap", "sunburst", "gauge", "funnel", "candlestick",
                "graph", "themeRiver", "parallel"
            ]
        }

        logger.debug("Data context preparation completed successfully")
        return {
            "success": True,
            "data": data_context
        }

    except Exception as e:
        logger.exception("Critical error preparing data context")
        return {
            "success": False,
            "error": f"Failed to prepare data context: {str(e)}"
        }


def extract_visualization_suggestions(
        gpt_response: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract visualization suggestions using advanced analysis and GPT-4"""
    try:
        # First analyze data characteristics
        numeric_cols = [
            col for col, stats in data.get('column_stats', {}).items()
            if stats.get('type') == 'numeric'
        ]
        categorical_cols = [
            col for col, stats in data.get('column_stats', {}).items()
            if stats.get('type') == 'categorical'
        ]
        time_cols = [
            col for col in data.get('columns', [])
            if any(t in col.lower()
                   for t in ['time', 'date', 'year', 'month', 'day'])
        ]

        # Prepare data context for GPT
        data_context = {
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "time_columns": time_cols,
            "total_rows": data.get('summary', {}).get('rows', 0),
            "column_stats": data.get('column_stats', {}),
            "available_chart_types": ["bar", "line", "scatter", "pie", "boxplot", "heatmap", "treemap", "sunburst", "gauge", "funnel", "candlestick", "graph", "themeRiver", "parallel"]
        }

        # Ask GPT-4 for visualization suggestions
        system_prompt = """<system>
You are a data visualization expert with deep expertise in translating data characteristics into meaningful visual insights. Your role is to:

1. Analyze datasets by examining:
   - Data types (numeric, categorical, temporal)
   - Statistical distributions
   - Correlation patterns
   - Time-based trends
   - Category breakdowns

2. Recommend 3-4 of the most impactful visualizations, with each recommendation structured as:
{
    "chart_type": "[appropriate chart selection]",
    "title": "[clear, descriptive title]",
    "x_axis": "[x-axis variable]",
    "y_axis": "[y-axis variable]",
    "explanation": "[justification for this visualization choice]"
}

Focus on selecting visualizations that:
- Best represent the underlying data relationships
- Provide meaningful insights to stakeholders
- Follow data visualization best practices
- Tell a coherent story with the data

Ensure all recommendations are clear, actionable, and properly justified with analytical reasoning.
</system>"""

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system",
                "content": system_prompt
            }, {
                "role": "user",
                "content": f"Data context:\n{json.dumps(data_context, indent=2)}"
            }],
            temperature=0.2
        )

        # Parse GPT's suggestions
        content = response.choices[0].message.content
        suggestions = json.loads(
            content) if content.startswith('[') else json.loads(
                content.split('```')[1]) if '```' in content else []

        # Validate and filter suggestions
        valid_suggestions = []
        for suggestion in suggestions:
            if validate_visualization_suggestion(suggestion, data):
                valid_suggestions.append(suggestion)

        return valid_suggestions[:4]  # Limit to 4 visualizations

    except Exception as e:
        logger.error(f"Error in extract_visualization_suggestions: {str(e)}")
        return []


def validate_visualization_suggestion(suggestion: Dict[str, Any],
                                      data: Dict[str, Any]) -> bool:
    """
    Validate visualization suggestion against the provided data.
    """
    try:
        if not isinstance(suggestion, dict):
            return False

        # Check for required keys based on chart type
        base_required = ["chart_type", "title", "explanation"]
        if not all(key in suggestion for key in base_required):
            return False
            
        # Special handling for radar charts
        if suggestion["chart_type"] == "radar":
            x_axis = suggestion.get("x_axis", "")
            y_axis = suggestion.get("y_axis", "")
            if not x_axis or not y_axis:
                return False
            if x_axis not in data.get("column_stats", {}) or y_axis not in data.get("column_stats", {}):
                return False
            # Verify we have numeric data for radar
            return data["column_stats"][y_axis].get("type") == "numeric"
            
        # Regular charts need both axes
        if suggestion["chart_type"] not in ["pie", "gauge", "funnel"]:
            if not all(key in suggestion for key in ["x_axis", "y_axis"]):
                return False
            if not all(key in data["column_stats"] for key in [suggestion["x_axis"], suggestion["y_axis"]]):
                return False

        return True

    except Exception as e:
        logger.error(f"Error in validate_visualization_suggestion: {str(e)}")
        return False


def generate_basic_suggestions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate basic visualization suggestions as fallback"""
    suggestions = []

    # Use determine_best_chart_type for smarter selection
    numeric_cols = [
        col for col, stats in data.get('column_stats', {}).items()
        if stats.get('type') == 'numeric'
    ]
    categorical_cols = [
        col for col, stats in data.get('column_stats', {}).items()
        if stats.get('type') == 'categorical'
    ]

    if len(numeric_cols) >= 2:
        best_chart = determine_best_chart_type(data, numeric_cols[:2])
        suggestions.append({
            'chart_type':
            best_chart,
            'title':
            f'Relationship: {numeric_cols[0]} vs {numeric_cols[1]}',
            'x_axis':
            numeric_cols[0],
            'y_axis':
            numeric_cols[1],
            'explanation':
            'Exploring relationship between numeric variables'
        })

    if categorical_cols and numeric_cols:
        suggestions.append({
            'chart_type':
            'bar',
            'title':
            f'{numeric_cols[0]} by {categorical_cols[0]}',
            'x_axis':
            categorical_cols[0],
            'y_axis':
            numeric_cols[0],
            'explanation':
            'Analyzing numeric distribution across categories'
        })

    if len(numeric_cols) >= 1:
        suggestions.append({
            'chart_type':
            'boxplot',
            'title':
            f'Distribution of {numeric_cols[0]}',
            'x_axis':
            numeric_cols[0],
            'y_axis':
            'value',
            'explanation':
            'Understanding numeric distribution and outliers'
        })

    return suggestions


def validate_chart_data(chart_type: str, data: Dict[str, Any], x_axis: Optional[str] = None, y_axis: Optional[str] = None) -> bool:
    """Validate data requirements for specific chart types"""
    try:
        preview_data = data.get('preview', [])
        if not preview_data:
            return False

        if chart_type == 'candlestick':
            required_fields = ['open', 'close', 'high', 'low']
            return all(field in preview_data[0] for field in required_fields)

        elif chart_type == 'gauge':
            if not x_axis or x_axis not in preview_data[0]:
                return False
            try:
                float(preview_data[0][x_axis])
                return True
            except (ValueError, TypeError):
                return False

        elif chart_type == 'parallel':
            # Check if all dimensions have valid data
            dimensions = list(preview_data[0].keys())
            return all(
                any(isinstance(row.get(dim), (int, float, str)) 
                    for row in preview_data)
                for dim in dimensions
            )

        elif chart_type == 'funnel':
            if not x_axis:
                return False
            # Check if we can calculate meaningful stages
            value_counts = {}
            for row in preview_data:
                if x_axis not in row:
                    return False
                key = str(row.get(x_axis, ''))
                value_counts[key] = value_counts.get(key, 0) + 1
            return len(value_counts) >= 2

        elif chart_type in ['sunburst', 'treemap']:
            if not all([x_axis, y_axis]):
                return False
            # Check if we can create meaningful hierarchy
            return all(
                x_axis in row and y_axis in row and 
                row[x_axis] is not None and row[y_axis] is not None
                for row in preview_data
            )

        elif chart_type == 'radar':
            if not all([x_axis, y_axis]):
                return False
            # Check if we have categories and numeric values
            return all(
                x_axis in row and y_axis in row and
                row[x_axis] is not None and 
                isinstance(row.get(y_axis), (int, float))
                for row in preview_data
            )
            
        elif chart_type == 'graph':
            if not all([x_axis, y_axis]):
                return False
            # Check if we can create meaningful nodes and edges
            return all(
                x_axis in row and y_axis in row and
                row[x_axis] is not None and row[y_axis] is not None
                for row in preview_data
            )

        return True
    except Exception as e:
        logger.error(f"Error validating chart data: {str(e)}")
        return False


def generate_visualization_config(
        args: Dict[str, Any], data: Dict[str,
                                         Any]) -> Optional[Dict[str, Any]]:
    """Generate enhanced ECharts configuration with strict validation"""
    try:
        chart_type = args.get('chart_type')
        title = args.get('title')
        x_axis = args.get('x_axis')
        y_axis = args.get('y_axis')

        # Strict validation of required fields
        if not all([chart_type, title]):
            logger.error(f"Missing required fields in visualization config: {args}")
            return None

        # Chart types that don't need both axes
        AXISLESS_CHARTS = ['pie', 'treemap', 'sunburst', 'gauge', 'funnel']
        SPECIAL_CHARTS = ['radar']  # Charts with special handling
        if chart_type not in AXISLESS_CHARTS + SPECIAL_CHARTS and not all([x_axis, y_axis]):
            logger.error(f"Missing axis fields for {chart_type} chart: {args}")
            return None

        # Validate data requirements for chart type
        if not validate_chart_data(chart_type, data, x_axis, y_axis):
            logger.error(f"Data validation failed for {chart_type} chart")
            return None

        # Extract and validate data
        preview_data = data.get('preview', [])
        if not preview_data:
            logger.error("No data available for visualization")
            return None

        # Special handling for hierarchical charts
        if chart_type in ['treemap', 'sunburst']:
            value_map = {}
            for row in preview_data:
                parent = str(row.get(x_axis, ''))
                child = str(row.get(y_axis, ''))
                if parent not in value_map:
                    value_map[parent] = {}
                if child not in value_map[parent]:
                    value_map[parent][child] = 0
                value_map[parent][child] += 1

            tree_data = []
            for parent, children in value_map.items():
                parent_node = {
                    'name': parent,
                    'value': sum(children.values()),
                    'children': [{'name': child, 'value': value} 
                               for child, value in children.items()]
                }
                tree_data.append(parent_node)

            if chart_type == 'treemap':
                return {
                    'title': {'text': title},
                    'tooltip': {'formatter': '{b}: {c} records'},
                    'series': [{
                        'type': 'treemap',
                        'data': tree_data,
                        'leafDepth': 1,
                        'levels': [{
                            'itemStyle': {
                                'borderColor': '#fff',
                                'borderWidth': 2,
                                'gapWidth': 2
                            }
                        }],
                        'label': {'show': True, 'formatter': '{b}: {c}'}
                    }]
                }
            else:  # sunburst
                return {
                    'title': {'text': title},
                    'tooltip': {'trigger': 'item'},
                    'series': [{
                        'type': 'sunburst',
                        'data': tree_data,
                        'radius': ['20%', '90%'],
                        'label': {'rotate': 'radial'},
                        'levels': [{}, {
                            'r0': '20%',
                            'r': '55%',
                            'itemStyle': {'borderWidth': 2},
                            'label': {'rotate': 'tangential'}
                        }, {
                            'r0': '55%',
                            'r': '90%',
                            'label': {'position': 'outside', 'padding': 3}
                        }]
                    }]
                }

        # Enhanced parallel coordinates
        elif chart_type == 'parallel':
            dimensions = list(preview_data[0].keys())
            parallel_axis = []

            # Calculate value ranges for numeric dimensions
            ranges = {}
            for dim in dimensions:
                values = [row[dim] for row in preview_data if row[dim] is not None]
                if all(isinstance(v, (int, float)) for v in values):
                    ranges[dim] = (min(values), max(values))

            # Create parallel axes with proper configuration
            for dim in dimensions:
                axis = {'dim': dimensions.index(dim), 'name': dim}
                if dim in ranges:
                    axis.update({
                        'type': 'value',
                        'min': ranges[dim][0],
                        'max': ranges[dim][1],
                        'nameLocation': 'end'
                    })
                else:
                    axis.update({
                        'type': 'category',
                        'data': list(set(str(row[dim]) for row in preview_data if row[dim] is not None))
                    })
                parallel_axis.append(axis)

            # Normalize and prepare data
            normalized_data = []
            for row in preview_data:
                point = []
                for dim in dimensions:
                    value = row[dim]
                    if dim in ranges and value is not None:
                        # Normalize numeric values
                        min_val, max_val = ranges[dim]
                        if max_val != min_val:
                            normalized = (float(value) - min_val) / (max_val - min_val)
                            point.append(normalized)
                        else:
                            point.append(0)
                    else:
                        point.append(str(value) if value is not None else '')
                if all(p != '' for p in point):
                    normalized_data.append(point)

            return {
                'title': {'text': title},
                'parallelAxis': parallel_axis,
                'series': [{
                    'type': 'parallel',
                    'lineStyle': {'width': 2},
                    'data': normalized_data,
                    'smooth': True
                }]
            }

        # Enhanced funnel chart
        elif chart_type == 'funnel':
            value_counts = {}
            total = 0
            for row in preview_data:
                key = str(row.get(x_axis, ''))
                value_counts[key] = value_counts.get(key, 0) + 1
                total += 1

            # Calculate percentages and sort by value
            funnel_data = []
            for k, v in sorted(value_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (v / total) * 100
                funnel_data.append({
                    'value': v,
                    'name': f"{k} ({percentage:.1f}%)",
                    'percentage': percentage
                })

            return {
                'title': {'text': title},
                'tooltip': {
                    'trigger': 'item',
                    'formatter': '{b}: {c} ({d}%)'
                },
                'series': [{
                    'type': 'funnel',
                    'data': funnel_data,
                    'label': {
                        'show': True,
                        'position': 'inside',
                        'formatter': '{b}'
                    },
                    'emphasis': {
                        'label': {'fontSize': 20}
                    },
                    'sort': 'descending',
                    'gap': 2,
                    'minSize': '0%',
                    'maxSize': '100%'
                }]
            }

        # Enhanced gauge chart
        elif chart_type == 'gauge':
            try:
                values = [float(row[x_axis]) for row in preview_data 
                         if x_axis in row and row[x_axis] is not None]
                if not values:
                    return None

                value = values[0]  # Current value
                min_val = min(values)
                max_val = max(values)

                # Calculate ranges for color zones
                range_size = (max_val - min_val) / 3
                ranges = [
                    [min_val, min_val + range_size, '#67e0e3'],  # Good
                    [min_val + range_size, min_val + 2*range_size, '#37a2da'],  # Warning
                    [min_val + 2*range_size, max_val, '#fd666d']  # Critical
                ]

                return {
                    'title': {'text': title},
                    'tooltip': {'formatter': '{b}: {c}'},
                    'series': [{
                        'type': 'gauge',
                        'min': min_val,
                        'max': max_val,
                        'axisLine': {
                            'lineStyle': {
                                'width': 30,
                                'color': [
                                    [(r[1] - min_val) / (max_val - min_val), r[2]]
                                    for r in ranges
                                ]
                            }
                        },
                        'pointer': {'itemStyle': {'color': 'auto'}},
                        'axisTick': {'distance': -30, 'length': 8, 'lineStyle': {'color': '#fff'}},
                        'splitLine': {'distance': -30, 'length': 30, 'lineStyle': {'color': '#fff'}},
                        'axisLabel': {'color': '#fff', 'distance': -40, 'fontSize': 12},
                        'detail': {
                            'valueAnimation': True,
                            'formatter': '{value}',
                            'color': '#fff'
                        },
                        'data': [{'value': value, 'name': x_axis}]
                    }]
                }
            except Exception as e:
                logger.error(f"Error generating gauge chart: {str(e)}")
                return None

        # Enhanced candlestick chart
        elif chart_type == 'candlestick':
            try:
                data = []
                categories = []
                volumes = []  # For volume bars if available

                for row in preview_data:
                    if all(row.get(f) is not None for f in [x_axis, 'open', 'close', 'high', 'low']):
                        categories.append(row[x_axis])
                        point = [
                            float(row['open']),
                            float(row['close']),
                            float(row['low']),
                            float(row['high'])
                        ]
                        data.append(point)

                        # Add volume if available
                        if 'volume' in row and row['volume'] is not None:
                            volumes.append(float(row['volume']))

                if not data:
                    return None

                series = [{
                    'type': 'candlestick',
                    'data': data,
                    'itemStyle': {
                        'color': '#fd666d',
                        'color0': '#37a2da',
                        'borderColor': '#fd666d',
                        'borderColor0': '#37a2da'
                    }
                }]

                # Add volume bars if available
                if volumes:
                    series.append({
                        'type': 'bar',
                        'xAxisIndex': 1,
                        'yAxisIndex': 1,
                        'data': volumes,
                        'itemStyle': {'color': '#37a2da'}
                    })

                config = {
                    'title': {'text': title},
                    'tooltip': {
                        'trigger': 'axis',
                        'axisPointer': {'type': 'cross'}
                    },
                    'legend': {'data': ['Price', 'Volume']},
                    'grid': [
                        {'left': '10%', 'right': '8%', 'height': '50%'},
                        {'left': '10%', 'right': '8%', 'top': '65%', 'height': '25%'}
                    ],
                    'xAxis': [{
                        'data': categories,
                        'axisLine': {'lineStyle': {'color': '#fff'}},
                        'axisLabel': {'color': '#fff'}
                    }, {
                        'data': categories,
                        'gridIndex': 1,
                        'axisLine': {'lineStyle': {'color': '#fff'}},
                        'axisLabel': {'color': '#fff'}
                    }],
                    'yAxis': [{
                        'scale': True,
                        'splitLine': {'show': False},
                        'axisLine': {'lineStyle': {'color': '#fff'}},
                        'axisLabel': {'color': '#fff'}
                    }, {
                        'scale': True,
                        'gridIndex': 1,
                        'splitNumber': 2,
                        'axisLine': {'lineStyle': {'color': '#fff'}},
                        'axisLabel': {'color': '#fff'}
                    }],
                    'series': series
                }

                return config

            except Exception as e:
                logger.error(f"Error generating candlestick chart: {str(e)}")
                return None

        # Enhanced graph chart
        elif chart_type == 'radar':
            return generate_radar_config(data, x_axis, y_axis, title)
            
        elif chart_type == 'graph':
            try:
                nodes = []
                links = []
                node_map = {}

                # Calculate node weights (frequency of appearance)
                node_weights = {}
                for row in preview_data:
                    source = str(row.get(x_axis, ''))
                    target = str(row.get(y_axis, ''))
                    node_weights[source] = node_weights.get(source, 0) + 1
                    node_weights[target] = node_weights.get(target, 0) + 1

                # Create nodes with size based on weight
                for node, weight in node_weights.items():
                    node_map[node] = len(nodes)
                    nodes.append({
                        'name': node,
                        'symbolSize': min(50, 10 + weight * 5),  # Scale node size
                        'value': weight
                    })

                # Create edges with weights
                edge_weights = {}
                for row in preview_data:
                    source = str(row.get(x_axis, ''))
                    target = str(row.get(y_axis, ''))
                    edge_key = f"{source}-{target}"
                    edge_weights[edge_key] = edge_weights.get(edge_key, 0) + 1

                for edge_key, weight in edge_weights.items():
                    source, target = edge_key.split('-')
                    links.append({
                        'source': node_map[source],
                        'target': node_map[target],
                        'value': weight,
                        'lineStyle': {
                            'width': min(10, 1 + weight)  # Scale edge width
                        }
                    })

                return {
                    'title': {'text': title},
                    'tooltip': {
                        'trigger': 'item',
                        'formatter': '{b}: {c}'
                    },
                    'series': [{
                        'type': 'graph',
                        'layout': 'force',
                        'data': nodes,
                        'links': links,
                        'categories': [],
                        'roam': True,
                        'label': {
                            'show': True,
                            'position': 'right',
                            'color': '#fff'
                        },
                        'force': {
                            'repulsion': 100,
                            'gravity': 0.1,
                            'edgeLength': 50,
                            'layoutAnimation': True
                        },
                        'draggable': True,
                        'itemStyle': {
                            'normal': {
                                'color': '#37a2da',
                                'borderColor': '#fff',
                                'borderWidth': 2
                            }
                        },
                        'lineStyle': {
                            'color': 'source',
                            'curveness': 0.3
                        },
                        'emphasis': {
                            'focus': 'adjacency',
                            'lineStyle': {
                                'width': 4
                            }
                        }
                    }]
                }

            except Exception as e:
                logger.error(f"Error generating graph chart: {str(e)}")
                return None

        # Handle themeRiver chart
        elif chart_type == 'themeRiver':
            try:
                # Get the continuous axis values (e.g., income)
                x_values = [float(row[x_axis]) for row in preview_data if x_axis in row and row[x_axis] is not None]
                y_values = [float(row[y_axis]) for row in preview_data if y_axis in row and row[y_axis] is not None]

                if not x_values or not y_values:
                    logger.error("No valid data points for ThemeRiver")
                    return None

                # Create income brackets
                min_income = min(x_values)
                max_income = max(x_values)
                bracket_size = (max_income - min_income) / 5  # 5 brackets
                brackets = [
                    (min_income + i * bracket_size, min_income + (i + 1) * bracket_size)
                    for i in range(5)
                ]

                #Create debt ratio categories
                min_ratio = min(y_values)
                max_ratio = max(y_values)
                ratio_range = max_ratio - min_ratio
                ratio_categories = [
                    ('Low', min_ratio, min_ratio + ratio_range/3),
                    ('Medium', min_ratio + ratio_range/3, min_ratio + 2*ratio_range/3),
                    ('High', min_ratio + 2*ratio_range/3, max_ratio)
                ]

                # Transform data into ThemeRiver format
                theme_data = []
                for i, (bracket_start, bracket_end) in enumerate(brackets):
                    bracket_midpoint = (bracket_start + bracket_end) / 2
                    bracket_label = f"${int(bracket_start)}k-${int(bracket_end)}k"

                    # Count records in each category for this bracket
                    for category_name, cat_start, cat_end in ratio_categories:
                        count = sum(
                            1 for row in preview_data
                            if x_axis in row and y_axis in row
                            and bracket_start <= float(row[x_axis]) < bracket_end
                            and cat_start <= float(row[y_axis]) < cat_end
                        )
                        if count > 0:  # Only add non-zero data points
                            theme_data.append([bracket_label, count, category_name])

                if not theme_data:
                    logger.error("No valid theme data generated")
                    return None

                # Sort data by bracket label
                theme_data.sort(key=lambda x: float(x[0].split('-')[0].replace('$', '').replace('k', '')))

                return {
                    'title': {'text': title},
                    'tooltip': {
                        'trigger': 'axis',
                        'axisPointer': {'type': 'line', 'lineStyle': {'color': 'rgba(255,255,255,0.2)', 'width': 1, 'type': 'solid'}}
                    },
                    'legend': {
                        'data': [cat[0] for cat in ratio_categories],
                        'textStyle': {'color': '#fff'}
                    },
                    'singleAxis': {
                        'top': 50,
                        'bottom': 50,
                        'axisTick': {},
                        'axisLabel': {'color': '#fff'},
                        'type': 'category',
                        'data': sorted(set(x[0] for x in theme_data)),
                        'splitLine': {'show': True, 'lineStyle': {'color': 'rgba(255,255,255,0.2)'}}
                    },
                    'series': [{
                        'type': 'themeRiver',
                        'emphasis': {'itemStyle': {'shadowBlur': 20, 'shadowColor': 'rgba(0, 0, 0, 0.8)'}},
                        'data': theme_data,
                        'label': {'show': True},
                        'itemStyle': {
                            'color': {
                                'type': 'linear',
                                'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                                'colorStops': [
                                    {'offset': 0, 'color': '#37a2da'},  # Low
                                    {'offset': 0.5, 'color': '#67e0e3'},  # Medium
                                    {'offset': 1, 'color': '#fd666d'}  # High
                                ]
                            }
                        }
                    }]
                }
            except Exception as e:
                logger.error(f"Error generating ThemeRiver chart: {str(e)}")
            return None

        # Extract valid data points based on chart type
        valid_data = []
        if chart_type in ['bar', 'line']:
            valid_data = [
                (str(row[x_axis]), float(row[y_axis])) for row in preview_data
                if x_axis in row and y_axis in row and row[x_axis] is not None
                and row[y_axis] is not None and not (
                    isinstance(row[y_axis], float) and math.isnan(row[y_axis]))
            ]
        elif chart_type == 'scatter':
            valid_data = [
                [float(row[x_axis]), float(row[y_axis])]
                for row in preview_data
                if x_axis in row and y_axis in row and row[x_axis] is not None
                and row[y_axis] is not None and not (
                    isinstance(row[x_axis], float) and math.isnan(row[x_axis]))
                and not (
                    isinstance(row[y_axis], float) and math.isnan(row[y_axis]))
            ]
        elif chart_type == 'boxplot':
            # For boxplot, we need to calculate the statistical values
            valid_values = [
                float(row[y_axis]) for row in preview_data
                if y_axis in row and row[y_axis] is not None and not (
                    isinstance(row[y_axis], float) and math.isnan(row[y_axis]))
            ]
            if valid_values:
                sorted_values = sorted(valid_values)
                q1 = sorted_values[len(sorted_values) // 4]
                median = sorted_values[len(sorted_values) // 2]
                q3 = sorted_values[3 * len(sorted_values) // 4]
                iqr = q3 - q1
                lower = max(min(sorted_values), q1 - 1.5 * iqr)
                upper = min(max(sorted_values), q3 + 1.5 * iqr)
                valid_data = [[lower, q1, median, q3, upper]]
        elif chart_type == 'pie':
            # For pie charts, we need category and value pairs
            value_counts = {}
            for row in preview_data:
                if x_axis in row and row[x_axis] is not None:
                    key = str(row[x_axis])
                    value_counts[key] = value_counts.get(key, 0) + 1
            valid_data = [{
                'name': k,
                'value': v
            } for k, v in value_counts.items()]
        elif chart_type == 'heatmap':
            # For heatmap, create a correlation matrix or frequency matrix
            x_values = list(
                set(str(row[x_axis]) for row in preview_data if x_axis in row))
            y_values = list(
                set(str(row[y_axis]) for row in preview_data if y_axis in row))

            # Create frequency matrix
            matrix = []
            for i, y_val in enumerate(y_values):
                for j, x_val in enumerate(x_values):
                    count = sum(1 for row in preview_data
                                if str(row.get(x_axis)) == x_val
                                and str(row.get(y_axis)) == y_val)
                    matrix.append([j, i, count])
            valid_data = matrix

        # If no valid data points, return None
        if not valid_data:
            logger.error(f"No valid data points found for {chart_type} chart")
            return None

        # Create base config
        config = {
            'backgroundColor': 'transparent',
            'title': {
                'text': title,
                'textStyle': {
                    'color': '#fff',
                    'fontSize': 16
                },
                'left': 'center'
            },
            'tooltip': {
                'trigger': 'item' if chart_type in ['pie'] else 'axis',
                'axisPointer': {
                    'type': 'cross'
                } if chart_type not in ['pie', 'heatmap'] else None,
                'backgroundColor': 'rgba(50,50,50,0.9)',
                'borderColor': '#333',
                'textStyle': {
                    'color': '#fff'
                }
            },
            'grid': {
                'left': '3%',
                'right': '4%',
                'bottom': '15%',
                'containLabel': True
            }
        }

        # Configure axes and series based on chart type
        if chart_type in ['bar', 'line', 'scatter', 'boxplot']:
            config.update({
            'xAxis': {
                    'type':
                    'category'
                    if chart_type in ['bar', 'line', 'boxplot'] else 'value',
                    'axisLabel': {
                        'color': '#fff'
                    },
                    'axisLine': {
                        'lineStyle': {
                            'color': '#fff'
                        }
                    }
            },
            'yAxis': {
                'type': 'value',
                    'axisLabel': {
                        'color': '#fff'
                    },
                    'axisLine': {
                        'lineStyle': {
                            'color': '#fff'
                        }
                    }
                }
            })
        elif chart_type == 'heatmap':
            config.update({
                'xAxis': {
                    'type': 'category',
                    'data': x_values,
                    'axisLabel': {
                        'color': '#fff',
                        'rotate': 45
                    },
                    'axisLine': {
                        'lineStyle': {
                            'color': '#fff'
                        }
                    }
                },
                'yAxis': {
                    'type': 'category',
                    'data': y_values,
                    'axisLabel': {
                        'color': '#fff'
                    },
                    'axisLine': {
                        'lineStyle': {
                            'color': '#fff'
                        }
                    }
                },
                'visualMap': {
                    'min': 0,
                    'max': max(item[2] for item in valid_data),
                    'calculable': True,
                    'orient': 'horizontal',
                    'left': 'center',
                    'bottom': '0%',
                    'textStyle': {
                        'color': '#fff'
                    },
                    'inRange': {
                        'color': ['#37a2da', '#32c5e9', '#67e0e3']
                    }
                }
            })

        # Configure series based on chart type
        if chart_type in ['bar', 'line']:
            x_values, y_values = zip(*valid_data)
            config['xAxis']['data'] = list(x_values)
            series = {
                'type': chart_type,
                'data': list(y_values),
                'itemStyle': {
                    'color': new_gradient_color()
                }
            }
            if chart_type == 'line':
                series.update({
                    'smooth': True,
                    'symbol': 'circle',
                    'symbolSize': 8,
                    'lineStyle': {
                        'width': 3
                    }
                })
        elif chart_type == 'scatter':
            series = {
                'type': 'scatter',
                'data': valid_data,
                'symbolSize': 12,
                'itemStyle': {
                    'color': '#188df0'
                }
            }
        elif chart_type == 'boxplot':
            config['xAxis']['data'] = [x_axis]  # Use column name as category
            series = {
                'type': 'boxplot',
                'data': valid_data,
                'itemStyle': {
                    'color': '#37a2da',
                    'borderColor': '#fff'
                }
            }
        elif chart_type == 'pie':
            series = {
                'type': 'pie',
                'radius': ['40%', '70%'],
                'avoidLabelOverlap': True,
                'itemStyle': {
                    'borderRadius': 10,
                    'borderColor': '#fff',
                    'borderWidth': 2
                },
                'label': {
                    'show': True,
                    'color': '#fff',
                    'formatter': '{b}: {c} ({d}%)'
                },
                'emphasis': {
                    'label': {
                        'show': True,
                        'fontSize': '16',
                        'fontWeight': 'bold'
                    }
                },
                'data': valid_data
            }
        elif chart_type == 'heatmap':
            series = {
                'type': 'heatmap',
                'data': valid_data,
                'label': {
                    'show': True,
                    'color': '#fff'
                },
                'emphasis': {
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowColor': 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }

        config['series'] = [series]

        # Final validation of the complete config
        if not config['series'][0].get('data'):
            logger.error("Generated config has no data in series")
            return None

        return config

    except Exception as e:
        logger.exception(f"Error generating visualization config: {str(e)}")
        return None


def new_gradient_color():
    """Generate a new gradient color scheme"""
    return {
        'type':
        'linear',
        'x':
        0,
        'y':
        0,
        'x2':
        0,
        'y2':
        1,
        'colorStops': [{
            'offset': 0,
            'color': '#83bff6'
        }, {
            'offset': 0.5,
            'color': '#188df0'
        }, {
            'offset': 1,
            'color': '#188df0'
        }]
    }


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


def validate_data_quality(data: Dict[str, Any]) -> str:
    """Validate data quality and return issues description"""
    issues = []

    try:
        preview_data = data.get('preview', [])
        columns = data.get('columns', [])
        stats = data.get('column_stats', {})

        # Check for empty or minimal data
        if not preview_data:
            issues.append("No preview data available")
            return "Dataset appears to be empty or inaccessible."

        # Check for headers-only data
        if len(preview_data) == 0 and columns:
            issues.append("Dataset contains only headers")
            return "Dataset contains only headers without data. Consider adding sample data or explaining the expected format."

        # Check for missing values
        for col in columns:
            null_count = sum(1 for row in preview_data
                             if row.get(col) is None or row.get(col) == '')
            if null_count > 0:
                issues.append(
                    f"Column '{col}' has {null_count} missing values")

        # Check for NaN values in numeric columns
        for col, stat in stats.items():
            if stat.get('type') == 'numeric':
                nan_count = sum(1 for row in preview_data
                                if isinstance(row.get(col), float)
                                and math.isnan(row.get(col)))
                if nan_count > 0:
                    issues.append(f"Column '{col}' has {nan_count} NaN values")

        # Check for inconsistent data types
        for col in columns:
            types_found = set(
                type(row.get(col)) for row in preview_data
                if row.get(col) is not None)
            if len(types_found) > 1:
                issues.append(
                    f"Column '{col}' has mixed data types: {', '.join(str(t) for t in types_found)}"
                )

        if issues:
            return "Data Quality Issues Found:\n- " + "\n- ".join(
                issues
            ) + "\n\nRecommendations will be provided in the analysis."

        return ""

    except Exception as e:
        logger.error(f"Error validating data quality: {str(e)}")
        return "Unable to fully validate data quality. Analysis will be performed with available data."


def determine_best_chart_type(data: Dict[str, Any], columns: List[str]) -> str:
    """Determine the most appropriate chart type based on data characteristics"""
    try:
        # Get column types
        col_types = {col: data['column_stats'][col]['type'] for col in columns}

        # Time series detection
        time_cols = [
            col for col, stats in data['column_stats'].items()
            if any(t in col.lower() for t in ['time', 'date', 'year', 'month'])
        ]

        if time_cols and any(col_types[col] == 'numeric'
                             for col in columns if col not in time_cols):
            return 'line'  # Time series data

        # Count numeric and categorical columns
        numeric_cols = [
            col for col, type_ in col_types.items() if type_ == 'numeric'
        ]
        categorical_cols = [
            col for col, type_ in col_types.items() if type_ == 'categorical'
        ]

        if len(numeric_cols) >= 2:
            return 'scatter'  # Multiple numeric columns -> correlation
        elif len(categorical_cols) == 1 and len(numeric_cols) == 1:
            return 'bar'  # Category vs number -> bar chart
        elif len(categorical_cols) == 1:
            return 'pie'  # Single category -> distribution
        else:
            return 'bar'  # Default to bar

    except Exception:
        return 'bar'  # Safe default


def get_visualization_configs(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get visualization configurations using GPT-4 with structured output."""
    logger.debug("Starting visualization configuration generation")

    if not openai_client:
        logger.error("OpenAI client not initialized")
        raise APIKeyError("OpenAI client is not properly initialized")
        
    # Extract numeric and categorical columns with data validation
    numeric_cols = []
    categorical_cols = []
    
    for col, stats in data.get('column_stats', {}).items():
        if stats.get('type') == 'numeric' and stats.get('valid_count', 0) > 0:
            numeric_cols.append(col)
        elif stats.get('type') == 'categorical' and stats.get('unique_values', 0) > 0:
            categorical_cols.append(col)

    try:
        # Prepare enhanced data context with statistics
        data_context = {
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "total_rows": data.get('summary', {}).get('rows', 0),
            "column_stats": {
                col: stats for col, stats in data.get('column_stats', {}).items()
                if stats.get('valid_count', 0) > 0
            },
            "preview_data": data.get('preview', [])[:5],
            "available_chart_types": ["bar", "scatter", "line", "boxplot"]
        }
        time_cols = [
            col for col in data.get('columns', [])
            if any(t in col.lower()
                   for t in ['time', 'date', 'year', 'month', 'day'])
        ]

        data_context = {
            "numeric_columns":
            numeric_cols,
            "categorical_columns":
            categorical_cols,
            "time_columns":
            time_cols,
            "total_rows":
            data.get('summary', {}).get('rows', 0),
            "column_stats":
            data.get('column_stats', {}),
            "available_chart_types": ["bar", "line", "scatter", "pie", "boxplot", "heatmap", "treemap", "sunburst", "gauge", "funnel", "candlestick", "graph", "themeRiver", "parallel"]
        }

        system_message = {
            "role":
            "system",
            "content":
            """You are a data visualization expert specializing in ECharts.
            Create diverse and insightful visualizations using multiple chart types to best represent the data.

            Available chart types:
            - Basic: bar, line, scatter, pie
            - Statistical: boxplot, heatmap
            - Hierarchical: treemap, sunburst
            - Special: gauge, funnel, candlestick
            - Relational: graph
            - Advanced: themeRiver, parallel

            Consider:
            1. Use different chart types based on data characteristics
            2. Combine multiple visualization types for comprehensive insights
            3. Match chart types to data relationships:
               - Distributions: boxplot, histogram
               - Correlations: scatter, heatmap
               - Hierarchical: treemap, sunburst
               - Time series: line, candlestick
               - Categories: bar, pie, funnel
               - Multi-dimensional: parallel, radar

            For each visualization, provide:
            1. chart_type: Select from available types
            2. title: Clear, descriptive title
            3. x_axis: Column for x-axis (if applicable)
            4. y_axis: Column for y-axis (if applicable)
            5. explanation: Why this visualization and chart type is appropriate

            Return 3-4 different chart types that best represent the data patterns."""
        }

        user_message = {
            "role":
            "user",
            "content":
            f"Create visualizations for this data:\n{json.dumps(data_context, indent=2)}"
        }

        # Define function for structured output
        functions = [{
            "name": "create_visualizations",
            "description":
            "Create robust Echarts visualization configurations of ANY type  based on data analysis",
            "parameters": {
                "type": "object",
                "properties": {
                    "visualizations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "chart_type": {
                                    "type":
                                    "string",
                                    "enum": [
                                        "bar", "line", "scatter", "pie",
                                        "boxplot", "heatmap", "treemap", "sunburst",
                                        "gauge", "funnel", "candlestick", "graph",
                                        "themeRiver", "parallel"
                                    ]
                                },
                                "title": {
                                    "type": "string"
                                },
                                "x_axis": {
                                    "type": "string"
                                },
                                "y_axis": {
                                    "type": "string"
                                },
                                "explanation": {
                                    "type": "string"
                                }
                            },
                            "required": ["chart_type", "title", "explanation"]
                        }
                    }
                },
                "required": ["visualizations"]
            }
        }]

        logger.debug("Sending request to OpenAI")
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[system_message, user_message],
            functions=functions,
            function_call={"name": "create_visualizations"},
            temperature=0.2)
        logger.debug("Received response from OpenAI")

        # Extract and validate the function call result
        if not response.choices[0].message.function_call:
            raise ValueError("No function call in response")

        result = json.loads(
            response.choices[0].message.function_call.arguments)

        # Validate each visualization config
        valid_visualizations = []
        for viz in result.get('visualizations', []):
            if validate_visualization_suggestion(viz, data):
                valid_visualizations.append(viz)
            else:
                logger.warning(f"Skipping invalid visualization config: {viz}")

        if not valid_visualizations:
            logger.warning("No valid visualizations generated")
            return {
                "success": False,
                "error": "No valid visualizations could be generated"
            }

        logger.debug(
            f"Successfully generated {len(valid_visualizations)} visualizations"
        )
        return {"success": True, "visualizations": valid_visualizations}

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return {
            "success": False,
            "error": f"Invalid visualization format: {str(e)}"
        }
    except Exception as e:
        logger.exception("Error generating visualizations")
        return {"success": False, "error": str(e)}
def generate_radar_config(data: Dict[str, Any], x_axis: str, y_axis: str, title: str) -> Dict[str, Any]:
    """Generate radar chart configuration."""
    try:
        # Get unique categories from x_axis
        categories = list(set(str(row.get(x_axis, '')) 
                            for row in data.get('preview', [])
                            if row.get(x_axis) is not None))
        
        # Calculate average values for each category
        values = []
        for category in categories:
            category_values = [
                float(row.get(y_axis, 0))
                for row in data.get('preview', [])
                if str(row.get(x_axis)) == category 
                and row.get(y_axis) is not None
            ]
            if category_values:
                values.append(sum(category_values) / len(category_values))
            else:
                values.append(0)
        
        return {
            'title': {'text': title},
            'tooltip': {'trigger': 'item'},
            'legend': {'textStyle': {'color': '#fff'}},
            'radar': {
                'indicator': [{'name': cat, 'max': max(values) * 1.2} for cat in categories],
                'axisName': {'color': '#fff'},
                'axisLine': {'lineStyle': {'color': 'rgba(255,255,255,0.2)'}},
                'splitLine': {'lineStyle': {'color': 'rgba(255,255,255,0.2)'}},
                'splitArea': {'areaStyle': {'color': 'rgba(255,255,255,0.1)'}}
            },
            'series': [{
                'type': 'radar',
                'data': [{
                    'value': values,
                    'name': y_axis,
                    'itemStyle': {'color': '#37a2da'},
                    'areaStyle': {'color': 'rgba(55,162,218,0.6)'}
                }]
            }]
        }
    except Exception as e:
        logger.error(f"Error generating radar chart: {str(e)}")
        return None
