import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import pandas as pd
import json
from utils.data_processor import process_data, chunk_process_data
from utils.ai_helper import get_ai_insights
from utils.db_models import db, SharedAnalysis
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
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            extension = filename.rsplit('.', 1)[1].lower()
            
            file_content = file.read()
            file_buffer = io.BytesIO(file_content)
            
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
            
            if df.empty:
                return jsonify({'error': 'The file contains no data'}), 400
                
            if len(df) > CHUNK_SIZE:
                result = chunk_process_data(df, chunk_size=CHUNK_SIZE)
            else:
                result = process_data(df)
                
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

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

@app.route('/analysis/<share_id>')
def view_analysis(share_id):
    shared = SharedAnalysis.query.filter_by(share_id=share_id).first_or_404()
    shared.views += 1
    db.session.commit()
    return render_template('shared_analysis.html', analysis=shared)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
