
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
        self.pin_hash = bcrypt.hashpw(
            pin.encode('utf-8'), salt
        ).decode('utf-8')

    def check_pin(self, pin):
        return bcrypt.checkpw(
            pin.encode('utf-8'),
            self.pin_hash.encode('utf-8')
        )

    def get_reset_token(self):
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app

        serializer = URLSafeTimedSerializer(
            current_app.config['SECRET_KEY']
        )
        return serializer.dumps(
            self.operator_id,
            salt='password-reset-salt'
        )

    @staticmethod
    def verify_reset_token(token):
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app

        serializer = URLSafeTimedSerializer(
            current_app.config['SECRET_KEY']
        )

        try:
            return serializer.loads(
                token,
                salt='password-reset-salt',
                max_age=3600
            )
        except Exception:
            return None


class InspectionSession(db.Model):
    __tablename__ = 'inspection_sessions'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    session_id = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    operator_id = db.Column(
        db.String(80),
        db.ForeignKey('users.operator_id'),
        nullable=False
    )

    date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    shirt_count = db.Column(
        db.Integer,
        default=1
    )

    # Garment defect inspection results
    color_balanced = db.Column(
        db.Boolean,
        nullable=False
    )

    buttons_missing = db.Column(
        db.Boolean,
        nullable=False
    )

    broken_stitches = db.Column(
        db.Boolean,
        nullable=False
    )

    size_label_missing = db.Column(
        db.Boolean,
        nullable=False
    )

    product_label_missing = db.Column(
        db.Boolean,
        nullable=False
    )

    # Final inspection result: PASS or FAIL
    overall_status = db.Column(
        db.String(10),
        nullable=False
    )

    # Store defect descriptions only
    defect_details = db.Column(
        db.Text,
        default='[]'
    )


    def get_defect_details(self):
        try:
            return json.loads(self.defect_details or '[]')
        except (ValueError, TypeError):
            return []

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'operator_id': self.operator_id,
            'date': self.date.isoformat() if self.date else None,
            'shirt_count': self.shirt_count,
            'color_balanced': self.color_balanced,
            'buttons_missing': self.buttons_missing,
            'broken_stitches': self.broken_stitches,
            'size_label_missing': self.size_label_missing,
            'product_label_missing': self.product_label_missing,
            'overall_status': self.overall_status,
            'defect_details': self.get_defect_details(),
        }


class Defect(db.Model):
    __tablename__ = 'defects'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    session_id = db.Column(
        db.Integer,
        db.ForeignKey('inspection_sessions.id')
    )

    defect_type = db.Column(
        db.String(50)
    )

    defect_status = db.Column(
        db.String(20)
    )

    description = db.Column(
        db.String(500)
    )

    severity = db.Column(
        db.String(20),
        default='MEDIUM'
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

