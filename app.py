import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
import json
from utils.data_processor import process_data, chunk_process_data
from utils.ai_helper import get_ai_insights
import io

app = Flask(__name__)
app.secret_key = "your-secret-key-here"  # In production, use environment variable
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

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
            
            # Read file content into memory buffer
            file_content = file.read()
            file_buffer = io.BytesIO(file_content)
            
            # Read file content based on format
            if extension == 'csv':
                df = pd.read_csv(file_buffer)
            elif extension in ['tsv', 'txt']:
                df = pd.read_csv(file_buffer, sep='\t')
            elif extension in ['xlsx', 'xls']:
                df = pd.read_excel(file_buffer)
            elif extension == 'json':
                # Handle both JSON Lines and regular JSON formats
                try:
                    df = pd.read_json(file_buffer)
                except ValueError:
                    # Try reading as JSON Lines
                    file_buffer.seek(0)
                    df = pd.read_json(file_buffer, lines=True)
            
            # Validate DataFrame
            if df.empty:
                return jsonify({'error': 'The file contains no data'}), 400
                
            # Check if the dataset is large
            if len(df) > CHUNK_SIZE:
                result = chunk_process_data(df, chunk_size=CHUNK_SIZE)
            else:
                result = process_data(df)
                
            return jsonify(result)
            
        except pd.errors.EmptyDataError:
            return jsonify({'error': 'The file is empty'}), 400
        except pd.errors.ParserError as e:
            return jsonify({'error': f'Unable to parse the file. Please check the format. Details: {str(e)}'}), 400
        except ValueError as e:
            return jsonify({'error': f'Invalid file format: {str(e)}'}), 400
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
