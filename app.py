import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
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
import eventlet

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('app')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize database
db.init_app(app)

@socketio.on('connect')
def handle_connect():
    logger.debug(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.debug(f"Client disconnected: {request.sid}")
    if 'current_analysis' in session:
        leave_analysis_room(session['current_analysis'])

@socketio.on('join_analysis')
def handle_join_analysis(data):
    analysis_id = data.get('analysis_id')
    if not analysis_id:
        return
    
    join_analysis_room(analysis_id)
    emit('collaborator_joined', {
        'user': session.get('user_id'),
        'timestamp': datetime.utcnow().isoformat()
    }, room=f"analysis_{analysis_id}")

def join_analysis_room(analysis_id):
    room = f"analysis_{analysis_id}"
    join_room(room)
    session['current_analysis'] = analysis_id
    
    # Update collaborator status
    collaborator = Collaborator.query.filter_by(
        analysis_id=analysis_id,
        session_id=session['user_id']
    ).first()
    
    if collaborator:
        collaborator.last_active = datetime.utcnow()
        db.session.commit()

def leave_analysis_room(analysis_id):
    room = f"analysis_{analysis_id}"
    leave_room(room)
    if 'current_analysis' in session:
        del session['current_analysis']

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
    
    socketio.emit('collaborator_joined', {
        'name': collaborator.name,
        'role': collaborator.role
    }, room=f"analysis_{shared.id}")
    
    return render_template('shared_analysis.html', 
                         analysis=shared,
                         collaborator=collaborator)

@app.route('/analysis/<share_id>/collaborators')
def get_collaborators(share_id):
    shared = SharedAnalysis.query.filter_by(share_id=share_id).first_or_404()
    
    # Clean up inactive collaborators
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

@app.route('/analysis/<share_id>/comments', methods=['POST'])
def add_comment(share_id):
    analysis = SharedAnalysis.query.filter_by(share_id=share_id).first_or_404()
    
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
    
    comment_data = {
        'id': comment.id,
        'content': comment.content,
        'author_name': comment.author_name,
        'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M UTC'),
        'parent_id': comment.parent_id
    }
    socketio.emit('new_comment', comment_data, room=f"analysis_{analysis.id}")
    
    return jsonify(comment_data)

@app.route('/analysis/<share_id>/comments', methods=['GET'])
def get_comments(share_id):
    analysis = SharedAnalysis.query.filter_by(share_id=share_id).first_or_404()
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

if __name__ == '__main__':
    # Use a different port to avoid conflicts
    port = int(os.environ.get('PORT', 5001))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
