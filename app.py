import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import pandas as pd
import json
from utils.data_processor import process_data, chunk_process_data
from utils.ai_helper import get_ai_insights, get_visualization_configs
from utils.db_models import db, SharedAnalysis, Comment, Collaborator
from datetime import datetime, timedelta
import io
import secrets
from sqlalchemy import text
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('app')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

def init_database():
    """Initialize database with schema version tracking."""
    try:
        with app.app_context():
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
            
            if not current_version or current_version < target_version:
                # Apply migrations
                try:
                    db.create_all()
                    
                    # Add missing columns if needed
                    for column in ['last_modified', 'is_public', 'password']:
                        try:
                            db.session.execute(text(f"""
                                ALTER TABLE shared_analysis
                                ADD COLUMN IF NOT EXISTS {column} {get_column_type(column)}
                            """))
                        except Exception as e:
                            print(f"Error adding column {column}: {str(e)}")
                    
                    # Update schema version
                    db.session.execute(
                        text("INSERT INTO schema_version (version) VALUES (:version)"),
                        {"version": target_version}
                    )
                    db.session.commit()
                    
                    print(f"Database schema updated to version {target_version}")
                except Exception as e:
                    print(f"Error updating database schema: {str(e)}")
                    db.session.rollback()
                    raise
    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        sys.exit(1)

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
    logger.debug("Received file upload request")
    if 'file' not in request.files:
        return jsonify({'error': 'No file was uploaded'}), 400
    
    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'error': 'No file was selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'error': f'Invalid file type. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    try:
        file_content = file.read()
        if not file_content:
            return jsonify({'error': 'The uploaded file is empty'}), 400
        
        file_buffer = io.BytesIO(file_content)
        filename = secure_filename(file.filename)
        extension = filename.rsplit('.', 1)[1].lower()
        
        try:
            logger.debug(f"Processing file with extension: {extension}")
            if extension == 'csv':
                # Try different encodings and delimiters
                try:
                    df = pd.read_csv(file_buffer, encoding='utf-8')
                except:
                    file_buffer.seek(0)
                    df = pd.read_csv(file_buffer, encoding='latin1')
                
                # If we got only one column, try different delimiter
                if len(df.columns) == 1:
                    file_buffer.seek(0)
                    df = pd.read_csv(file_buffer, sep=',', engine='python')
                
                logger.debug(f"CSV columns detected: {df.columns.tolist()}")
                
            elif extension in ['tsv', 'txt']:
                df = pd.read_csv(file_buffer, sep='\t')
            elif extension in ['xlsx', 'xls']:
                df = pd.read_excel(file_buffer)
            elif extension == 'json':
                try:
                    df = pd.read_json(file_buffer)
                except ValueError:
                    file_buffer.seek(0)
                    df = pd.read_json(file_buffer, lines=True)
            
            if df.empty:
                return jsonify({'error': 'The file contains no data rows'}), 400
            
            if len(df.columns) == 0:
                return jsonify({'error': 'The file contains no columns'}), 400
            
            logger.debug(f"DataFrame shape: {df.shape}")
            logger.debug(f"Columns: {df.columns.tolist()}")
            logger.debug(f"First row: {df.iloc[0].to_dict()}")
            
            if len(df) > CHUNK_SIZE:
                result = chunk_process_data(df, chunk_size=CHUNK_SIZE)
            else:
                result = process_data(df)
            
            logger.debug("Data processing completed successfully")
            return jsonify(result)
            
        except pd.errors.EmptyDataError:
            return jsonify({'error': 'The file contains no data'}), 400
        except pd.errors.ParserError as e:
            logger.error(f"Parser error: {str(e)}")
            return jsonify({
                'error': f'Unable to parse the file. Please check if the format matches the file extension. Details: {str(e)}'
            }), 400
        except ValueError as e:
            logger.error(f"Value error: {str(e)}")
            return jsonify({'error': f'Invalid file format: {str(e)}'}), 400
            
    except Exception as e:
        logger.exception("Error processing file")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/visualize', methods=['POST'])
def visualize():
    logger.debug("Received visualization request")
    try:
        data = request.json
        if not data:
            logger.error("No data provided in request")
            raise ValueError("No data provided")

        logger.debug("Getting visualization configurations")
        result = get_visualization_configs(data)
        logger.debug(f"Got visualization result: success={result['success']}")
        
        if result["success"]:
            logger.debug(f"Returning {len(result['visualizations'])} visualizations")
            return jsonify({
                'success': True,
                'visualizations': result["visualizations"]
            })
        else:
            logger.warning("GPT-4 visualization failed, falling back to default")
            processed_data = processData(data)
            visualizations = generate_default_visualizations(processed_data)
            
            if not visualizations:
                logger.error("No visualizations could be generated")
                raise ValueError("No visualizations could be generated")
            
            logger.debug(f"Returning {len(visualizations)} default visualizations")
            return jsonify({
                'success': True,
                'visualizations': visualizations
            })

    except Exception as e:
        logger.exception("Visualization error")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

def generate_default_visualizations(processed_data):
    """Generate default visualizations based on processed data"""
    visualizations = []
    
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

# Add these functions after the processData function and before the /ai/analyze route

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
            
        question = data.get('question')
        context = data.get('context')
        
        logger.debug(f"Question: {question}")
        logger.debug(f"Context: {json.dumps(context)[:200]}...")
        
        if not question or not context:
            logger.error("Missing required parameters")
            return jsonify({'error': 'Missing required parameters'}), 400
        
        # Add visualization system prompt if needed
        if 'visualize' in question.lower() or 'chart' in question.lower() or 'graph' in question.lower():
            context['system_prompt'] = """You are a data visualization expert. Analyze the data and create 
            visualizations that best represent the insights requested. Use the create_visualization function 
            to generate charts. Explain your visualization choices and insights clearly."""
        
        logger.debug("Calling get_ai_insights")
        response = get_ai_insights(question, context)
        logger.debug(f"AI Response: {json.dumps(response)[:200]}...")
        
        return jsonify({'response': response})
    except Exception as e:
        logger.exception("Error in AI analysis")
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)