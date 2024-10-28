from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

def generate_share_id():
    return str(uuid.uuid4())[:8]

class SharedAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    share_id = db.Column(db.String(8), unique=True, default=generate_share_id)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
