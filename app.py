import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import pandas as pd
import json
from utils.data_processor import process_data, chunk_process_data
from utils.ai_helper import get_ai_insights, get_visualization_configs
from utils.data_insights import DataInsights
from utils.db_models import db, SharedAnalysis, Comment, Collaborator
from datetime import datetime, timedelta
import io
import secrets
from sqlalchemy import text
import sys
import logging
from dotenv import load_dotenv
from utils.json_sanitizer import sanitize_json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('app')

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Database configuration with debug logging
use_sqlite = os.environ.get('USE_SQLITE', 'false').lower() == 'true'
database_url = os.environ.get('DATABASE_URL')

logger.debug(f"USE_SQLITE: {use_sqlite}")
logger.debug(f"DATABASE_URL: {database_url if database_url else 'Not set'}")

if use_sqlite or not database_url:
    logger.info("Using SQLite database")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
else:
    logger.info("Using PostgreSQL database")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

def init_database():
    """Initialize database with schema version tracking."""
    try:
        with app.app_context():
            logger.info("Starting database initialization")
            
            # Create schema_version table if it doesn't exist
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Check current schema version
            result = db.session.execute(text("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"))
            current_version = result.scalar()
            target_version = 1  # Increment this when making schema changes
            
            logger.debug(f"Current schema version: {current_version}, Target version: {target_version}")
            
            if not current_version or current_version < target_version:
                logger.info(f"Upgrading database schema from version {current_version} to {target_version}")
                # Apply migrations
                try:
                    db.create_all()
                    logger.info("Created all database tables")
                    
                    # Add missing columns if needed
                    for column in ['last_modified', 'is_public', 'password']:
                        try:
                            db.session.execute(text(f"""
                                ALTER TABLE shared_analysis
                                ADD COLUMN IF NOT EXISTS {column} {get_column_type(column)}
                            """))
                            logger.debug(f"Added or verified column: {column}")
                        except Exception as e:
                            logger.error(f"Error adding column {column}: {str(e)}")
                            if not use_sqlite:  # Re-raise for PostgreSQL, continue for SQLite
                                raise
                    
                    # Update schema version
                    db.session.execute(
                        text("INSERT INTO schema_version (version) VALUES (:version)"),
                        {"version": target_version}
                    )
                    db.session.commit()
                    
                    logger.info(f"Database schema updated to version {target_version}")
                except Exception as e:
                    logger.error(f"Error updating database schema: {str(e)}")
                    db.session.rollback()
                    raise
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        if not use_sqlite:  # Only exit if using PostgreSQL
            sys.exit(1)
        else:
            logger.warning("Continuing with SQLite despite initialization error")

def get_column_type(column_name):
    """Get SQL type for a column."""
    column_types = {
        'last_modified': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
        'is_public': 'BOOLEAN DEFAULT TRUE',
        'password': 'VARCHAR(100)'
    }
    return column_types.get(column_name, 'VARCHAR(100)')

# Initialize database with schema version tracking
init_database()

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json', 'tsv', 'txt'}
CHUNK_SIZE = 10000  # Number of rows to process at a time

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def check_session():
    if not session.get('user_id'):
        session['user_id'] = secrets.token_urlsafe(32)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shared')
def list_shared_analyses():
    analyses = SharedAnalysis.query.filter_by(is_public=True)\
                                 .order_by(SharedAnalysis.created_at.desc())\
                                 .all()
    return render_template('shared_list.html', analyses=analyses)

@app.route('/analysis/<share_id>', methods=['GET'])
def view_analysis(share_id):
    shared = SharedAnalysis.query.filter_by(share_id=share_id).first_or_404()
    
    if not shared.is_public:
        if 'password' not in session.get(f'access_{share_id}', {}):
            return redirect(url_for('analysis_auth', share_id=share_id))
    
    shared.views += 1
    
    collaborator = Collaborator.query.filter_by(
        analysis_id=shared.id,
        session_id=session['user_id']
    ).first()
    
    if not collaborator:
        collaborator = Collaborator(
            analysis_id=shared.id,
            session_id=session['user_id'],
            name=f'Viewer_{secrets.token_hex(4)}',
            role='viewer'
        )
        db.session.add(collaborator)
    
    collaborator.last_active = datetime.utcnow()
    db.session.commit()
    
    return render_template('shared_analysis.html', 
                         analysis=shared,
                         collaborator=collaborator)

@app.route('/analysis/<share_id>/auth', methods=['GET', 'POST'])
def analysis_auth(share_id):
    shared = SharedAnalysis.query.filter_by(share_id=share_id).first_or_404()
    
    if request.method == 'POST':
        if shared.password == request.form.get('password'):
            session[f'access_{share_id}'] = {'password': True}
            return redirect(url_for('view_analysis', share_id=share_id))
        return render_template('analysis_auth.html', 
                            share_id=share_id,
                            error="Invalid password")
    
    return render_template('analysis_auth.html', share_id=share_id)

@app.route('/analysis/<share_id>/collaborators')
def get_collaborators(share_id):
    shared = SharedAnalysis.query.filter_by(share_id=share_id).first_or_404()
    
    timeout = datetime.utcnow() - timedelta(minutes=5)
    Collaborator.query.filter(
        Collaborator.analysis_id == shared.id,
        Collaborator.last_active < timeout
    ).delete()
    db.session.commit()
    
    collaborators = Collaborator.query.filter_by(analysis_id=shared.id).all()
    return jsonify([{
        'name': c.name,
        'role': c.role,
        'joined_at': c.joined_at.isoformat(),
        'last_active': c.last_active.isoformat()
    } for c in collaborators])

@app.route('/analysis/<share_id>/comments', methods=['GET', 'POST'])
def handle_comments(share_id):
    analysis = SharedAnalysis.query.filter_by(share_id=share_id).first_or_404()
    
    if request.method == 'POST':
        data = request.get_json()
        if not data or not data.get('content') or not data.get('author_name'):
            return jsonify({'error': 'Missing required fields'}), 400
            
        comment = Comment(
            content=data['content'],
            author_name=data['author_name'],
            analysis_id=analysis.id,
            parent_id=data.get('parent_id')
        )
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'id': comment.id,
            'content': comment.content,
            'author_name': comment.author_name,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M UTC'),
            'parent_id': comment.parent_id
        })
    
    comments = Comment.query.filter_by(analysis_id=analysis.id)\
                           .order_by(Comment.created_at.desc())\
                           .all()
    return jsonify([{
        'id': c.id,
        'content': c.content,
        'author_name': c.author_name,
        'created_at': c.created_at.strftime('%Y-%m-%d %H:%M UTC'),
        'parent_id': c.parent_id,
        'replies': [{
            'id': r.id,
            'content': r.content,
            'author_name': r.author_name,
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M UTC')
        } for r in c.replies]
    } for c in comments if not c.parent_id])

@app.route('/share', methods=['POST'])
def share_analysis():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data received'}), 400

        required_fields = ['title', 'data']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        shared = SharedAnalysis(
            title=data['title'],
            description=data.get('description', ''),
            data=data['data'],
            is_public=data.get('is_public', True),
            password=data.get('password')
        )
        db.session.add(shared)
        
        owner = Collaborator(
            analysis_id=shared.id,
            session_id=session['user_id'],
            name=data.get('author_name', f'Owner_{secrets.token_hex(4)}'),
            role='owner'
        )
        db.session.add(owner)
        db.session.commit()

        return jsonify({
            'share_id': shared.share_id,
            'url': url_for('view_analysis', share_id=shared.share_id, _external=True)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error sharing analysis: {str(e)}'}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
            
        # Read the file based on its type
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            elif file.filename.endswith('.json'):
                df = pd.read_json(file)
            elif file.filename.endswith('.tsv'):
                df = pd.read_csv(file, sep='\t')
            else:
                df = pd.read_csv(file, sep=None, engine='python')
        except Exception as e:
            return jsonify({'error': f'Error reading file: {str(e)}'}), 400
            
        # Process data in chunks if it's large
        if len(df) > CHUNK_SIZE:
            processed_data = chunk_process_data(df, CHUNK_SIZE)
        else:
            processed_data = process_data(df)
            
        # Generate statistical insights
        insights_generator = DataInsights()
        statistical_insights = insights_generator.generate_insights(df)
        
        # Combine processed data with insights
        response_data = {
            'processed_data': processed_data,
            'statistical_insights': statistical_insights,
            'preview': df.head(5).to_dict('records'),
            'filename': secure_filename(file.filename)
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.exception("Error in upload_file")
        return jsonify({'error': str(e)}), 500

@app.route('/visualize', methods=['POST'])
def visualize():
    logger.debug("Received visualization request")
    try:
        data = request.json
        if not data:
            logger.error("No data provided in request")
            return jsonify({
                'success': False,
                'error': "No data provided"
            }), 400

        logger.debug("Getting visualization configurations")
        result = get_visualization_configs(data)
        logger.debug(f"Got visualization result: success={result['success']}")
        
        if result["success"]:
            logger.debug(f"Returning {len(result['configs'])} visualizations")
            return jsonify({
                'success': True,
                'visualizations': result["configs"]
            })
        else:
            logger.warning(f"Visualization generation failed: {result.get('error', 'Unknown error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to generate visualizations')
            }), 400

    except Exception as e:
        logger.exception("Visualization error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def generate_default_visualizations(processed_data):
    """Generate default visualizations based on processed data"""
    visualizations = []
    
    # Multiline chart
    if processed_data.get('multiline'):
        multiline_config = {
            'title': {'text': 'Time Series Analysis'},
            'tooltip': processed_data['multiline']['tooltip'],
            'legend': processed_data['multiline']['legend'],
            'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True},
            'xAxis': processed_data['multiline']['xAxis'],
            'yAxis': processed_data['multiline']['yAxis'],
            'series': processed_data['multiline']['series']
        }
        visualizations.append(multiline_config)
    
    # Histogram
    if processed_data.get('histogram'):
        visualizations.append({
            'title': {'text': 'Distribution'},
            'tooltip': {'trigger': 'axis'},
            'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True},
            'xAxis': {
                'type': 'category',
                'data': processed_data['histogram']['bins'],
                'axisLabel': {'rotate': 45}
            },
            'yAxis': {'type': 'value'},
            'series': [{
                'name': processed_data['histogram']['column'],
                'data': processed_data['histogram']['values'],
                'type': 'bar',
                'showBackground': True,
                'backgroundStyle': {
                    'color': 'rgba(180, 180, 180, 0.2)'
                }
            }]
        })
    
    # Scatter plot
    if processed_data.get('scatter'):
        visualizations.append({
            'title': {'text': 'Correlation'},
            'tooltip': {'trigger': 'axis'},
            'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True},
            'xAxis': {
                'type': 'value',
                'name': processed_data['scatter']['xLabel'],
                'nameLocation': 'middle',
                'nameGap': 30
            },
            'yAxis': {
                'type': 'value',
                'name': processed_data['scatter']['yLabel'],
                'nameLocation': 'middle',
                'nameGap': 30
            },
            'series': [{
                'symbolSize': 10,
                'data': list(zip(processed_data['scatter']['x'], processed_data['scatter']['y'])),
                'type': 'scatter',
                'emphasis': {
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowColor': 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        })
    
    # Box plot
    if processed_data.get('boxplot'):
        visualizations.append({
            'title': {'text': 'Distribution Summary'},
            'tooltip': {'trigger': 'item'},
            'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True},
            'xAxis': {
                'type': 'category',
                'data': [d['name'] for d in processed_data['boxplot']],
                'axisLabel': {'rotate': 45}
            },
            'yAxis': {'type': 'value'},
            'series': [{
                'type': 'boxplot',
                'data': [[d['stats']['min'], d['stats']['q1'], d['stats']['median'], 
                         d['stats']['q3'], d['stats']['max']] for d in processed_data['boxplot']]
            }]
        })
    
    # Heatmap
    if processed_data.get('heatmap'):
        visualizations.append({
            'title': {'text': 'Correlation Matrix'},
            'tooltip': {'position': 'top'},
            'grid': {'height': '50%', 'top': '10%'},
            'xAxis': {'type': 'category', 'data': processed_data['heatmap']['columns'], 'splitArea': {'show': True}},
            'yAxis': {'type': 'category', 'data': processed_data['heatmap']['columns'], 'splitArea': {'show': True}},
            'visualMap': {
                'min': -1,
                'max': 1,
                'calculable': True,
                'orient': 'horizontal',
                'left': 'center',
                'bottom': '15%'
            },
            'series': [{
                'name': 'Correlation',
                'type': 'heatmap',
                'data': processed_data['heatmap']['values'],
                'label': {'show': True},
                'emphasis': {
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowColor': 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        })
    
    return visualizations

def processData(data):
    """Process data for visualizations using dataProcessor.js logic"""
    logger.debug("Processing data for visualizations")
    
    # Initialize results
    results = {}
    
    # Get multiline chart data
    multiline = prepareMultilineData(data)
    if multiline:
        logger.debug("Generated multiline chart data")
        results['multiline'] = multiline
    else:
        logger.debug("Failed to generate multiline chart")
    
    # Get histogram data
    histogram = prepareHistogramData(data)
    if histogram:
        logger.debug("Generated histogram data")
        results['histogram'] = histogram
    else:
        logger.debug("Failed to generate histogram")
    
    # Get scatter plot data
    scatter = prepareScatterData(data)
    if scatter:
        logger.debug("Generated scatter plot data")
        results['scatter'] = scatter
    else:
        logger.debug("Failed to generate scatter plot")
    
    # Get box plot data
    boxplot = prepareBoxplotData(data)
    if boxplot:
        logger.debug("Generated box plot data")
        results['boxplot'] = boxplot
    else:
        logger.debug("Failed to generate box plot")
    
    # Get heatmap data
    heatmap = prepareHeatmapData(data)
    if heatmap:
        logger.debug("Generated heatmap data")
        results['heatmap'] = heatmap
    else:
        logger.debug("Failed to generate heatmap")
    
    logger.debug(f"Generated {len(results)} visualizations")
    return results

def prepareMultilineData(data):
    """Prepare multiline chart data from the uploaded dataset"""
    try:
        if not data or 'column_stats' not in data:
            return None
            
        # Find numeric columns for y-axis values
        numeric_cols = [
            col for col, stats in data['column_stats'].items() 
            if stats.get('type') == 'numeric'
        ]
        
        if len(numeric_cols) < 1:
            return None
            
        # Find a suitable x-axis column (datetime or numeric)
        x_col = next(
            (col for col, stats in data['column_stats'].items()
             if stats.get('type') in ['datetime', 'numeric']),
            None
        )
        
        if not x_col:
            return None
            
        # Prepare series data
        series = []
        for y_col in numeric_cols[:5]:  # Limit to 5 lines for readability
            values = [
                [row[x_col], row[y_col]]
                for row in data['preview']
                if row[x_col] is not None and row[y_col] is not None
            ]
            if values:
                series.append({
                    'name': y_col,
                    'type': 'line',
                    'data': values,
                    'smooth': True,
                    'emphasis': {
                        'focus': 'series'
                    }
                })
        
        if not series:
            return None
            
        return {
            'xAxis': {
                'type': 'value' if data['column_stats'][x_col]['type'] == 'numeric' else 'time',
                'name': x_col
            },
            'yAxis': {
                'type': 'value'
            },
            'series': series,
            'tooltip': {
                'trigger': 'axis',
                'axisPointer': {
                    'type': 'cross',
                    'label': {
                        'backgroundColor': '#6a7985'
                    }
                }
            },
            'legend': {
                'data': [s['name'] for s in series]
            }
        }
    except Exception as e:
        logger.error(f"Error preparing multiline data: {str(e)}")
        return None

def prepareHistogramData(data):
    """Prepare histogram data from the uploaded dataset"""
    try:
        if not data or 'column_stats' not in data:
            return None
            
        # Find first numeric column
        numeric_col = next(
            (col for col, stats in data['column_stats'].items() 
             if stats.get('type') == 'numeric'),
            None
        )
        
        if not numeric_col:
            return None
            
        # Get column data
        values = [row[numeric_col] for row in data['preview'] if row[numeric_col] is not None]
        if not values:
            return None
            
        # Create histogram bins
        min_val = data['column_stats'][numeric_col]['min']
        max_val = data['column_stats'][numeric_col]['max']
        bin_count = 10
        bin_width = (max_val - min_val) / bin_count
        
        bins = []
        values_count = [0] * bin_count
        
        for i in range(bin_count):
            bin_start = min_val + (i * bin_width)
            bin_end = bin_start + bin_width
            bins.append(f"{bin_start:.2f} - {bin_end:.2f}")
            
            # Count values in this bin
            values_count[i] = sum(1 for v in values 
                                if bin_start <= v < bin_end or 
                                (i == bin_count - 1 and v == max_val))
        
        return {
            'column': numeric_col,
            'bins': bins,
            'values': values_count
        }
    except Exception as e:
        print(f"Error preparing histogram data: {str(e)}")
        return None

def prepareScatterData(data):
    """Prepare scatter plot data from the uploaded dataset"""
    try:
        if not data or 'column_stats' not in data:
            return None
            
        # Find first two numeric columns
        numeric_cols = [
            col for col, stats in data['column_stats'].items() 
            if stats.get('type') == 'numeric'
        ][:2]
        
        if len(numeric_cols) < 2:
            return None
            
        x_col, y_col = numeric_cols[:2]
        
        # Get paired values
        paired_data = [
            (row[x_col], row[y_col]) 
            for row in data['preview']
            if row[x_col] is not None and row[y_col] is not None
        ]
        
        if not paired_data:
            return None
            
        return {
            'x': [pair[0] for pair in paired_data],
            'y': [pair[1] for pair in paired_data],
            'xLabel': x_col,
            'yLabel': y_col
        }
    except Exception as e:
        print(f"Error preparing scatter data: {str(e)}")
        return None

def prepareBoxplotData(data):
    """Prepare box plot data from the uploaded dataset"""
    try:
        if not data or 'column_stats' not in data:
            return None
            
        numeric_cols = [
            col for col, stats in data['column_stats'].items() 
            if stats.get('type') == 'numeric'
        ]
        
        if not numeric_cols:
            return None
            
        boxplot_data = []
        for col in numeric_cols:
            stats = data['column_stats'][col]
            if all(key in stats for key in ['min', 'max', 'median']):
                # Calculate Q1 and Q3 if not present
                values = [row[col] for row in data['preview'] if row[col] is not None]
                values.sort()
                q1_idx = len(values) // 4
                q3_idx = (len(values) * 3) // 4
                
                boxplot_data.append({
                    'name': col,
                    'stats': {
                        'min': stats['min'],
                        'q1': stats.get('q1', values[q1_idx] if values else stats['min']),
                        'median': stats['median'],
                        'q3': stats.get('q3', values[q3_idx] if values else stats['max']),
                        'max': stats['max']
                    }
                })
        
        return boxplot_data
    except Exception as e:
        print(f"Error preparing boxplot data: {str(e)}")
        return None

def prepareHeatmapData(data):
    """Prepare heatmap data from the uploaded dataset"""
    try:
        if not data or 'column_stats' not in data:
            return None
            
        numeric_cols = [
            col for col, stats in data['column_stats'].items() 
            if stats.get('type') == 'numeric'
        ]
        
        if len(numeric_cols) < 2:
            return None
            
        # Calculate correlation matrix
        correlations = []
        for i, col1 in enumerate(numeric_cols):
            for j, col2 in enumerate(numeric_cols):
                # Get paired values
                pairs = [
                    (row[col1], row[col2])
                    for row in data['preview']
                    if row[col1] is not None and row[col2] is not None
                ]
                
                if not pairs:
                    correlations.append([i, j, 0])
                    continue
                
                # Calculate correlation
                x_vals, y_vals = zip(*pairs)
                x_mean = sum(x_vals) / len(x_vals)
                y_mean = sum(y_vals) / len(y_vals)
                
                numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
                x_variance = sum((x - x_mean) ** 2 for x in x_vals)
                y_variance = sum((y - y_mean) ** 2 for y in y_vals)
                
                if x_variance == 0 or y_variance == 0:
                    correlation = 0
                else:
                    correlation = numerator / (x_variance ** 0.5 * y_variance ** 0.5)
                
                correlations.append([i, j, correlation])
        
        return {
            'columns': numeric_cols,
            'values': correlations
        }
    except Exception as e:
        print(f"Error preparing heatmap data: {str(e)}")
        return None

@app.route('/ai/analyze', methods=['POST'])
def analyze_data():
    logger.debug("Received AI analysis request")
    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No JSON data received'}), 400
        
        data = sanitize_json(data)  # Sanitize received data
        
        question = data.get('question')
        context = data.get('context')
        
        logger.debug(f"Question: {question}")
        logger.debug(f"Context: {json.dumps(context)[:200]}...")
        
        if not question or not context:
            logger.error("Missing required parameters")
            return jsonify({'error': 'Missing required parameters'}), 400

        response = get_ai_insights(question, context)
        sanitized_response = sanitize_json(response)  # Sanitize response before sending
        logger.debug(f"AI Response: {json.dumps(sanitized_response)[:200]}...")
        
        return jsonify({'response': sanitized_response})
    except Exception as e:
        logger.exception("Error in AI analysis")
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)