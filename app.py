import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import pandas as pd
import json
from utils.data_processor import process_data, chunk_process_data
from utils.ai_helper import get_ai_insights
from utils.db_models import db, SharedAnalysis, Comment
import io

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    db.create_all()

ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls', 'json', 'tsv', 'txt'}
CHUNK_SIZE = 10000  # Number of rows to process at a time

def allowed_file(filename):
    if not filename:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/shared')
def list_shared_analyses():
    analyses = SharedAnalysis.query.order_by(SharedAnalysis.created_at.desc()).all()
    return render_template('shared_list.html', analyses=analyses)

@app.route('/analysis/<share_id>')
def view_analysis(share_id):
    shared = SharedAnalysis.query.filter_by(share_id=share_id).first_or_404()
    shared.views += 1
    db.session.commit()
    return render_template('shared_analysis.html', analysis=shared)

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
            analysis_id=analysis.id
        )
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            'id': comment.id,
            'content': comment.content,
            'author_name': comment.author_name,
            'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M UTC')
        })
    
    comments = Comment.query.filter_by(analysis_id=analysis.id)\
                           .order_by(Comment.created_at.desc())\
                           .all()
    return jsonify([{
        'id': c.id,
        'content': c.content,
        'author_name': c.author_name,
        'created_at': c.created_at.strftime('%Y-%m-%d %H:%M UTC')
    } for c in comments])

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if file was included in request
    if 'file' not in request.files:
        return jsonify({'error': 'No file was uploaded'}), 400
    
    file = request.files['file']
    
    # Check if file was selected
    if not file or not file.filename:
        return jsonify({'error': 'No file was selected'}), 400
    
    # Validate file extension
    if not allowed_file(file.filename):
        return jsonify({
            'error': f'Invalid file type. Allowed types are: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    try:
        # Read file content
        file_content = file.read()
        if not file_content:
            return jsonify({'error': 'The uploaded file is empty'}), 400
        
        file_buffer = io.BytesIO(file_content)
        filename = secure_filename(file.filename)
        extension = filename.rsplit('.', 1)[1].lower()
        
        # Attempt to read the file based on its extension
        try:
            if extension == 'csv':
                df = pd.read_csv(file_buffer)
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
            
            # Validate DataFrame
            if df.empty:
                return jsonify({'error': 'The file contains no data rows'}), 400
            
            if len(df.columns) == 0:
                return jsonify({'error': 'The file contains no columns'}), 400
            
            # Process the data
            if len(df) > CHUNK_SIZE:
                result = chunk_process_data(df, chunk_size=CHUNK_SIZE)
            else:
                result = process_data(df)
                
            return jsonify(result)
            
        except pd.errors.EmptyDataError:
            return jsonify({'error': 'The file contains no data'}), 400
        except pd.errors.ParserError as e:
            return jsonify({
                'error': f'Unable to parse the file. Please check if the format matches the file extension. Details: {str(e)}'
            }), 400
        except ValueError as e:
            return jsonify({'error': f'Invalid file format: {str(e)}'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

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
            data=data['data']
        )
        db.session.add(shared)
        db.session.commit()

        return jsonify({
            'share_id': shared.share_id,
            'url': url_for('view_analysis', share_id=shared.share_id, _external=True)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error sharing analysis: {str(e)}'}), 500

@app.route('/ai/analyze', methods=['POST'])
def analyze_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
            
        question = data.get('question')
        context = data.get('context')
        
        if not question or not context:
            return jsonify({'error': 'Missing required parameters'}), 400
        
        response = get_ai_insights(question, context)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': f'Error processing request: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
