import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import pandas as pd
from utils.data_processor import process_data
from utils.ai_helper import get_ai_insights

app = Flask(__name__)
app.secret_key = "your-secret-key-here"  # In production, use environment variable
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

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
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Read file content
        if filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:  # xlsx
            df = pd.read_excel(file)
            
        # Process data
        result = process_data(df)
        return jsonify(result)
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/ai/analyze', methods=['POST'])
def analyze_data():
    data = request.json
    question = data.get('question')
    context = data.get('context')
    
    if not question or not context:
        return jsonify({'error': 'Missing required parameters'}), 400
    
    response = get_ai_insights(question, context)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
