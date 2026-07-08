from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    operator_id = db.Column(db.String(80), unique=True, nullable=False)
    operator_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    pin_hash = db.Column(db.String(128), nullable=False)
    nic = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_pin(self, pin):
        salt = bcrypt.gensalt()
        self.pin_hash = bcrypt.hashpw(pin.encode('utf-8'), salt).decode('utf-8')
    
    def check_pin(self, pin):
        return bcrypt.checkpw(pin.encode('utf-8'), self.pin_hash.encode('utf-8'))
    
    def get_reset_token(self):
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps(self.operator_id, salt='password-reset-salt')
    
    @staticmethod
    def verify_reset_token(token):
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            operator_id = s.loads(token, salt='password-reset-salt', max_age=3600)
            return operator_id
        except:
            return None


class InspectionSession(db.Model):
    __tablename__ = 'inspection_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), unique=True, nullable=False)
    operator_id = db.Column(db.String(80), db.ForeignKey('users.operator_id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    shirt_count = db.Column(db.Integer, default=1)
    image_path = db.Column(db.String(200))
    annotated_image_path = db.Column(db.String(200))
    result_summary = db.Column(db.String(20))
    has_defect = db.Column(db.Boolean, default=False)
    button_count = db.Column(db.Integer, default=0)
    expected_count = db.Column(db.Integer, default=7)
    alignment_score = db.Column(db.Float, default=0.0)
    spacing_score = db.Column(db.Float, default=0.0)
    defect_details = db.Column(db.Text, default='[]')


class Defect(db.Model):
    __tablename__ = 'defects'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('inspection_sessions.id'))
    defect_type = db.Column(db.String(50))
    defect_status = db.Column(db.String(20))
    description = db.Column(db.String(500))
    severity = db.Column(db.String(20), default='MEDIUM')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)