from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import bcrypt
import json

db = SQLAlchemy()


# ============================================================
# USER MODEL
# ============================================================
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


# ============================================================
# INSPECTION SESSION MODEL
# ============================================================
class InspectionSession(db.Model):
    __tablename__ = 'inspection_sessions'

    # --------------------------------------------------------
    # Core session fields
    # --------------------------------------------------------
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(50), unique=True, nullable=False)
    operator_id = db.Column(db.String(80), db.ForeignKey('users.operator_id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    shirt_count = db.Column(db.Integer, default=1)
    image_path = db.Column(db.String(200))
    annotated_image_path = db.Column(db.String(200))
    result_summary = db.Column(db.String(20))
    has_defect = db.Column(db.Boolean, default=False)

    # --------------------------------------------------------
    # BUTTON DETECTION FIELDS
    # --------------------------------------------------------
    button_count = db.Column(db.Integer, default=0)
    expected_count = db.Column(db.Integer, default=7)
    alignment_score = db.Column(db.Float, default=0.0)
    spacing_score = db.Column(db.Float, default=0.0)

    # --------------------------------------------------------
    # COLOR IMBALANCE FIELDS
    # --------------------------------------------------------
    color_has_imbalance = db.Column(db.Boolean, default=False, nullable=True)
    color_confidence = db.Column(db.Float, default=0.0, nullable=True)
    color_prediction = db.Column(db.String(30), nullable=True)  # "Balanced" / "Imbalanced"
    color_balanced_probability = db.Column(db.Float, default=0.0, nullable=True)
    color_imbalanced_probability = db.Column(db.Float, default=0.0, nullable=True)
    color_imbalance_score = db.Column(db.Float, default=0.0, nullable=True)
    color_uniformity_score = db.Column(db.Float, default=100.0, nullable=True)
    color_dominant_colors = db.Column(db.Text, default='[]', nullable=True)
    color_analysis_json = db.Column(db.Text, default='{}', nullable=True)

    # --------------------------------------------------------
    # ⭐ 4-MODEL SUMMARY FLAGS
    # True = Defect Detected | False = No Defect
    # These give a quick checklist view of each detection model
    # --------------------------------------------------------
    has_broken_stitch = db.Column(db.Boolean, default=False, nullable=False)
    has_button_defect = db.Column(db.Boolean, default=False, nullable=False)
    has_label_defect  = db.Column(db.Boolean, default=False, nullable=False)
    # NOTE: `color_has_imbalance` is already declared above — reuse it

    # Extra label-specific info (e.g., "missing", "OK", "faded", "misprinted")
    size_label_status = db.Column(db.String(50), nullable=True)

    # Overall inspection verdict: 'PASS' or 'FAIL'
    overall_status = db.Column(db.String(10), default='PASS', nullable=False)

    # --------------------------------------------------------
    # DEFECT DETAILS — stored as JSON string
    # --------------------------------------------------------
    defect_details = db.Column(db.Text, default='[]')

    # --------------------------------------------------------
    # HELPER METHODS
    # --------------------------------------------------------
    def get_defect_details(self):
        """Safely parse defect_details JSON."""
        try:
            return json.loads(self.defect_details or '[]')
        except (ValueError, TypeError):
            return []

    def get_dominant_colors(self):
        """Safely parse dominant colors JSON."""
        try:
            return json.loads(self.color_dominant_colors or '[]')
        except (ValueError, TypeError):
            return []

    def to_dict(self):
        """Serialize for API/history views."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'operator_id': self.operator_id,
            'date': self.date.isoformat() if self.date else None,
            'image_path': self.image_path,
            'shirt_count': self.shirt_count,
            'result_summary': self.result_summary,
            'has_defect': self.has_defect,

            # Button model
            'button_count': self.button_count,
            'expected_count': self.expected_count,
            'alignment_score': self.alignment_score,
            'spacing_score': self.spacing_score,

            # Color model
            'color_has_imbalance': self.color_has_imbalance,
            'color_confidence': self.color_confidence,
            'color_prediction': self.color_prediction,
            'color_balanced_probability': self.color_balanced_probability,
            'color_imbalanced_probability': self.color_imbalanced_probability,
            'color_imbalance_score': self.color_imbalance_score,
            'color_uniformity_score': self.color_uniformity_score,
            'color_dominant_colors': self.get_dominant_colors(),

            # ⭐ 4-Model Summary Flags
            'has_broken_stitch': self.has_broken_stitch,
            'has_button_defect': self.has_button_defect,
            'has_label_defect': self.has_label_defect,
            'size_label_status': self.size_label_status,
            'overall_status': self.overall_status,

            # Defect details
            'defect_details': self.get_defect_details()
        }


# ============================================================
# DEFECT MODEL
# ============================================================
class Defect(db.Model):
    __tablename__ = 'defects'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('inspection_sessions.id'))
    defect_type = db.Column(db.String(50))
    defect_status = db.Column(db.String(20))
    description = db.Column(db.String(500))
    severity = db.Column(db.String(20), default='MEDIUM')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confidence = db.Column(db.Float, default=0.0, nullable=True)