from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import os

db = SQLAlchemy()

def get_database_url():
    """Get database URL based on environment"""
    if os.environ.get('USE_SQLITE', 'true').lower() == 'true':
        return 'sqlite:///app.db'
    return os.environ.get('DATABASE_URL', 'sqlite:///app.db')

def generate_share_id():
    return str(uuid.uuid4())[:8]

class SharedAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    share_id = db.Column(db.String(8), unique=True, default=generate_share_id)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    comments = db.relationship('Comment', backref='analysis', lazy=True)
    collaborators = db.relationship('Collaborator', backref='analysis', lazy=True)
    is_public = db.Column(db.Boolean, default=True)
    password = db.Column(db.String(100))  # For password-protected shares

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_name = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    analysis_id = db.Column(db.Integer, db.ForeignKey('shared_analysis.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]))

class Collaborator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('shared_analysis.id'), nullable=False)
    session_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='viewer')  # viewer, editor, owner
