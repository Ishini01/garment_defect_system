from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file

from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from flask_mail import Mail, Message

from dotenv import load_dotenv

import traceback

from datetime import datetime, timedelta

import os

import uuid

import json

import sys

import gc

import tempfile

from backend.models import db, User, InspectionSession, Defect

from backend.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm

from backend.utils.button_detector import ButtonDetector

from backend.utils.label_detector import LabelDetector
from backend.utils.stitch_detector import StitchDetector

from backend.utils.color_detector import predict_color_imbalance

from backend.utils.alarm import AlarmManager

from backend.utils.report_generator import ReportGenerator

load_dotenv()

# Create Flask app

app = Flask(__name__, template_folder='templates', static_folder='static')

# ============================================

# CONFIGURATION - MYSQL

# ============================================

app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/garment_defect_db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOAD_FOLDER'] = 'static/uploads'

app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')

app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))

app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'

app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')

app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# ============================================

# IPHONE CAMERA CONFIGURATION

# ============================================

CAMERA_TYPE = 'camo'           # 'webcam', 'camo', or 'url'

CAMERA_INDEX = 1               # iPhone via Camo (index 1)

PHONE_URL = 'http://localhost:8080/shot.jpg'  # For IP Webcam

# ============================================

# INITIALIZE EXTENSIONS

# ============================================

db.init_app(app)

mail = Mail(app)

login_manager = LoginManager()

login_manager.init_app(app)

login_manager.login_view = 'login'

login_manager.login_message = 'Please login to access this page.'

login_manager.login_message_category = 'warning'

@login_manager.user_loader

def load_user(user_id):

    return User.query.get(int(user_id))

# ============================================

# CONTEXT PROCESSOR

# ============================================

@app.context_processor

def inject_now():

    return {'now': datetime.now()}

# ============================================

# CREATE DATABASE TABLES

# ============================================

with app.app_context():

    db.create_all()

    print("Γ£à MySQL Database tables created successfully!")

# ============================================

# ROUTES

# ============================================

@app.route('/')

def home():

    """Homepage - Always shows first"""

    return render_template('home.html')

def get_saved_label_status(details):

    """Read a stored label decision without treating uncertainty as a defect.

    Legacy label detections were review-only. Only use PASS/FAIL when

    explicitly saved; never infer FAIL from an undetected YOLO class.

    """

    label = details.get('label_detection') if isinstance(details, dict) else None

    if not isinstance(label, dict) or label.get('evaluated') is not True:

        return 'Not Tested'

    status = str(label.get('status', 'REVIEW')).upper()

    return status if status in ('PASS', 'FAIL', 'REVIEW') else 'REVIEW'

def get_operator_defect_summary(operator_id):

    """Count affected inspections per defect type, including older saved sessions.

    Unimplemented checks are not counted as defect-free or defective.

    """

    inspections = InspectionSession.query.filter_by(operator_id=operator_id).all()

    counts = {

        'broken_stitch': 0,

        'button_defect': 0,

        'label_defect': 0,

        'color_imbalance': 0,

    }

    if not inspections:

        return counts

    ids = [item.id for item in inspections]

    defects = Defect.query.filter(Defect.session_id.in_(ids)).all()

    by_session = {}

    for defect in defects:

        by_session.setdefault(defect.session_id, set()).add(

            str(defect.defect_type or '').lower()

        )

    for item in inspections:

        try:

            details = json.loads(item.defect_details or '{}')

            if not isinstance(details, dict):

                details = {}

        except (ValueError, TypeError):

            details = {}

        types = by_session.get(item.id, set())

        button_details = details.get('button_detection') or {}

        button_defects = details.get('button_defects') or []

        color_details = details.get('color_imbalance') or {}

        if ('button_defect' in types or bool(item.buttons_missing)

                or bool(button_defects)

                or (isinstance(button_details, dict)

                    and button_details.get('status') == 'FAIL')):

            counts['button_defect'] += 1

        color_evaluated = (isinstance(color_details, dict)

                           and color_details.get('evaluated') is True)

        if ('color_imbalance' in types or

                (color_evaluated and

                 (color_details.get('status') == 'FAIL' or

                  (color_details.get('status') is None and

                   item.color_balanced is False)))):

            counts['color_imbalance'] += 1

        if 'broken_stitch' in types or 'broken_stitches' in types or (

            details.get('broken_stitches_evaluated') is True

            and bool(item.broken_stitches)

        ):

            counts['broken_stitch'] += 1

        if (get_saved_label_status(details) == 'FAIL' or

                'label_defect' in types or 'size_label_missing' in types

                or 'product_label_missing' in types or

                (details.get('size_label_evaluated') is True and

                 bool(item.size_label_missing)) or

                (details.get('product_label_evaluated') is True and

                 bool(item.product_label_missing))):

            counts['label_defect'] += 1

    return counts

@app.route('/dashboard')

@login_required

def dashboard():

    total = InspectionSession.query.filter_by(operator_id=current_user.operator_id).count()

    pass_count = InspectionSession.query.filter_by(

        operator_id=current_user.operator_id, overall_status='PASS'

    ).count()

    fail_count = InspectionSession.query.filter_by(

        operator_id=current_user.operator_id, overall_status='FAIL'

    ).count()

    pass_rate = (pass_count / total * 100) if total else 0

    defect_counts = get_operator_defect_summary(current_user.operator_id)

    recent_inspections = InspectionSession.query.filter_by(

        operator_id=current_user.operator_id

    ).order_by(InspectionSession.date.desc()).limit(5).all()

    from datetime import timezone

    sri_lanka_tz = timezone(timedelta(hours=5, minutes=30))

    for insp in recent_inspections:

        insp.local_date = (insp.date.replace(tzinfo=timezone.utc).astimezone(sri_lanka_tz)

                           if insp.date else None)

        try:

            details = json.loads(insp.defect_details or '{}')

            if not isinstance(details, dict):

                details = {}

        except (ValueError, TypeError):

            details = {}

        button = details.get('button_detection') or {}

        color = details.get('color_imbalance') or {}

        label = details.get('label_detection') or {}

        label_status = get_saved_label_status(details)

        if not isinstance(button, dict):

            button = {}

        if not isinstance(color, dict):

            color = {}

        button_status = 'Not Tested'

        if button.get('evaluated') is True:

            button_status = ('FAIL' if button.get('status') == 'FAIL' or

                             bool(details.get('button_defects')) else 'PASS')

        color_status = 'Not Tested'

        if color.get('evaluated') is True:

            if color.get('status') in ('PASS', 'FAIL'):

                color_status = color['status']

            elif color.get('label') in ('Balanced', 'Imbalanced'):

                color_status = 'FAIL' if color['label'] == 'Imbalanced' else 'PASS'

            elif color.get('raw_score') is not None:

                try:

                    color_status = 'FAIL' if float(color['raw_score']) > 0.5 else 'PASS'

                except (ValueError, TypeError):

                    pass

        insp.dashboard_checks = [

            ('Stitch', 'fa-cut', (details.get('stitch_detection') or {}).get('status', 'Not Tested') if (details.get('stitch_detection') or {}).get('evaluated') is True else 'Not Tested'),

            ('Button', 'fa-circle', button_status),

            ('Label', 'fa-tag', label_status),

            ('Color', 'fa-palette', color_status),

        ]

    return render_template(

        'dashboard.html',

        total=total,

        pass_count=pass_count,

        fail_count=fail_count,

        pass_rate=pass_rate,

        defect_counts=defect_counts,

        recent_inspections=recent_inspections,

        now=datetime.now(sri_lanka_tz),

        broken_stitch_count=defect_counts['broken_stitch'],

        button_defect_count=defect_counts['button_defect'],

        label_defect_count=defect_counts['label_defect'],

        color_imbalance_count=defect_counts['color_imbalance'],

    )

@app.route('/register', methods=['GET', 'POST'])

def register():

    if current_user.is_authenticated:

        return redirect(url_for('dashboard'))

    form = RegistrationForm()

    if form.validate_on_submit():

        user = User(

            operator_id=form.operator_id.data,

            operator_name=form.operator_name.data,

            email=form.email.data,

            nic=form.nic.data

        )

        user.set_pin(form.pin.data)

        db.session.add(user)

        db.session.commit()

        flash('Γ£à Registration successful! Please login.', 'success')

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])

def login():

    if current_user.is_authenticated:

        return redirect(url_for('dashboard'))

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(operator_id=form.operator_id.data).first()

        if user and user.check_pin(form.pin.data):

            login_user(user, remember=form.remember.data)

            flash(f'≡ƒæï Welcome back, {user.operator_name}!', 'success')

            next_page = request.args.get('next')

            return redirect(next_page) if next_page else redirect(url_for('dashboard'))

        flash('Γ¥î Invalid Operator ID or PIN.', 'danger')

    return render_template('login.html', form=form)

@app.route('/logout')

@login_required

def logout():

    logout_user()

    flash('≡ƒæï You have been logged out.', 'info')

    return redirect(url_for('login'))

def send_reset_email(user, reset_url):

    """Email a one-hour PIN reset link."""

    msg = Message(

        subject='Garment Detect - PIN Reset Request',

        recipients=[user.email],

        body=(f'Hello {user.operator_name},\n\n'

              f'Reset your PIN using this link (expires in one hour):\n{reset_url}\n\n'

              'If you did not request this, ignore this email.')

    )

    mail.send(msg)

@app.route('/forgot-password', methods=['GET', 'POST'])

def forgot_password():

    if current_user.is_authenticated:

        return redirect(url_for('dashboard'))

    form = ForgotPasswordForm()

    if form.validate_on_submit():

        user = User.query.filter_by(

            operator_id=form.operator_id.data, nic=form.nic.data

        ).first()

        if user and user.email:

            try:

                reset_url = url_for('reset_password', token=user.get_reset_token(), _external=True)

                send_reset_email(user, reset_url)

            except Exception:

                traceback.print_exc()

                flash('Unable to send reset email. Check SMTP configuration.', 'danger')

                return render_template('forgot_password.html', form=form)

        flash('If the account has a registered email, a reset link has been sent.', 'info')

        return redirect(url_for('login'))

    return render_template('forgot_password.html', form=form)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])

def reset_password(token):

    if current_user.is_authenticated:

        return redirect(url_for('dashboard'))

    operator_id = User.verify_reset_token(token)

    if not operator_id:

        flash('Γ¥î Invalid or expired reset link.', 'danger')

        return redirect(url_for('forgot_password'))

    user = User.query.filter_by(operator_id=operator_id).first()

    if not user:

        flash('Γ¥î User not found.', 'danger')

        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()

    if form.validate_on_submit():

        user.set_pin(form.pin.data)

        db.session.commit()

        flash('Γ£à PIN reset successful! Please login.', 'success')

        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form, token=token)

@app.route('/inspect')

@login_required

def inspect():

    return render_template('inspect.html')

@app.route('/history')

@login_required

def history():

    """Show inspection history with actual evaluated module statuses."""

    inspections = InspectionSession.query.filter_by(

        operator_id=current_user.operator_id

    ).order_by(InspectionSession.date.desc()).all()

    # Stored inspection timestamps are UTC; display them in Sri Lanka time.

    # Fixed UTC+05:30 avoids Windows ZoneInfo/tzdata dependency.

    from datetime import timezone

    sri_lanka_tz = timezone(timedelta(hours=5, minutes=30))

    for insp in inspections:

        if insp.date is not None:

            utc_date = insp.date.replace(tzinfo=timezone.utc)

            insp.local_date = utc_date.astimezone(sri_lanka_tz)

        else:

            insp.local_date = None

        try:

            details = json.loads(insp.defect_details or '{}')

            if not isinstance(details, dict):

                details = {}

        except (TypeError, ValueError):

            details = {}

        button = details.get('button_detection') or {}

        color = details.get('color_imbalance') or {}

        label = details.get('label_detection') or {}

        label_status = get_saved_label_status(details)

        if not isinstance(button, dict):

            button = {}

        if not isinstance(color, dict):

            color = {}

        insp.history_button_count = button.get('count')

        insp.history_expected_count = button.get('expected')

        # Only mark a model PASS when the saved details prove it was evaluated.

        button_status = 'Not Tested'

        if button.get('evaluated') is True:

            defects = details.get('button_defects') or []

            button_status = 'FAIL' if defects or button.get('status') == 'FAIL' else 'PASS'

        color_status = 'Not Tested'

        color_confidence = None

        if color.get('evaluated') is True:

            if color.get('status') in ('PASS', 'FAIL'):

                color_status = color['status']

            elif color.get('label') in ('Balanced', 'Imbalanced'):

                color_status = 'FAIL' if color['label'] == 'Imbalanced' else 'PASS'

            elif color.get('raw_score') is not None:

                try:

                    color_status = 'FAIL' if float(color['raw_score']) > 0.5 else 'PASS'

                except (TypeError, ValueError):

                    pass

            if color.get('confidence') is not None:

                try:

                    color_confidence = float(color['confidence'])

                except (TypeError, ValueError):

                    pass

        insp.history_color_status = color_status

        insp.history_color_confidence = color_confidence

        insp.history_checklist = [

            {'name': 'Stitch', 'icon': 'fa-cut', 'status': (details.get('stitch_detection') or {}).get('status', 'Not Tested') if (details.get('stitch_detection') or {}).get('evaluated') is True else 'Not Tested'},

            {'name': 'Button', 'icon': 'fa-circle', 'status': button_status},

            {'name': 'Label', 'icon': 'fa-tag', 'status': label_status},

            {'name': 'Color', 'icon': 'fa-palette', 'status': color_status},

        ]

    return render_template('history.html', inspections=inspections)

@app.route('/reports')

@login_required

def reports():

    return render_template('reports.html')

@app.route('/profile')

@login_required

def profile():

    total = InspectionSession.query.filter_by(operator_id=current_user.operator_id).count()

    pass_count = InspectionSession.query.filter_by(operator_id=current_user.operator_id, overall_status='PASS').count()

    fail_count = total - pass_count

    pass_rate = (pass_count / total * 100) if total > 0 else 0

    return render_template('profile.html', 

                          user=current_user,

                          total_inspections=total,

                          pass_count=pass_count,

                          fail_count=fail_count,

                          pass_rate=pass_rate)

# ============================================

# SETTINGS ROUTES

# ============================================

@app.route('/settings')

@login_required

def settings():

    """Settings page"""

    return render_template('settings.html')

@app.route('/api/update-profile', methods=['POST'])

@login_required

def update_profile():

    """Update user profile"""

    try:

        user = User.query.get(current_user.id)

        user.operator_name = request.form.get('operator_name')

        user.nic = request.form.get('nic')

        user.email = request.form.get('email')

        db.session.commit()

        return jsonify({'success': True, 'message': 'Profile updated successfully!'})

    except Exception as e:

        return jsonify({'error': str(e)}), 500

@app.route('/api/change-pin', methods=['POST'])

@login_required

def change_pin():

    """Change user PIN"""

    try:

        current_pin = request.form.get('current_pin')

        new_pin = request.form.get('new_pin')

        user = User.query.get(current_user.id)

        if not user.check_pin(current_pin):

            return jsonify({'error': 'Current PIN is incorrect'}), 400

        if len(new_pin) < 4 or len(new_pin) > 10:

            return jsonify({'error': 'PIN must be between 4 and 10 characters'}), 400

        user.set_pin(new_pin)

        db.session.commit()

        return jsonify({'success': True, 'message': 'PIN changed successfully!'})

    except Exception as e:

        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-data', methods=['POST'])

@login_required

def clear_data():

    """Clear all inspection data"""

    try:

        inspections = InspectionSession.query.filter_by(operator_id=current_user.operator_id).all()

        for inspection in inspections:

            Defect.query.filter_by(session_id=inspection.id).delete()

            db.session.delete(inspection)

        db.session.commit()

        return jsonify({'success': True, 'message': 'All data cleared successfully!'})

    except Exception as e:

        return jsonify({'error': str(e)}), 500

@app.route('/api/delete-account', methods=['POST'])

@login_required

def delete_account():

    """Delete user account"""

    try:

        inspections = InspectionSession.query.filter_by(operator_id=current_user.operator_id).all()

        for inspection in inspections:

            Defect.query.filter_by(session_id=inspection.id).delete()

            db.session.delete(inspection)

        user = User.query.get(current_user.id)

        db.session.delete(user)

        db.session.commit()

        logout_user()

        return jsonify({'success': True, 'message': 'Account deleted successfully!'})

    except Exception as e:

        return jsonify({'error': str(e)}), 500

# ============================================

# PRIVACY POLICY ROUTE

# ============================================

@app.route('/privacy-policy')

def privacy_policy():

    """Privacy and Policy page"""

    return render_template('privacy_policy.html')

# ============================================

# IPHONE CAMERA API ROUTES

# ============================================

@app.route('/api/iphone-status', methods=['GET'])

@login_required

def iphone_status():

    """Check if iPhone camera is connected"""

    try:

        detector = ButtonDetector(camera_type='camo', camera_index=1)

        is_connected = detector.test_camera()

        # Clean up memory

        gc.collect()

        return jsonify({

            'connected': is_connected,

            'camera_type': 'camo',

            'camera_index': 1,

            'message': 'iPhone camera connected!' if is_connected else 'iPhone camera not connected. Please connect via USB and open Camo.'

        })

    except Exception as e:

        gc.collect()

        return jsonify({'error': str(e)}), 500

@app.route('/api/capture-phone', methods=['POST'])
@login_required
def capture_phone():
    # Legacy endpoint previously wrote images into static/uploads.
    # Use the browser camera and POST its image to /api/detect instead.
    return jsonify({'error': 'Legacy camera capture disabled to prevent image storage. Use /api/detect.'}), 410

@app.route('/api/find-camera', methods=['GET'])

@login_required

def find_camera():

    """Find available camera indices"""

    try:

        detector = ButtonDetector()

        available = detector.find_camera_index(max_index=5)

        gc.collect()

        return jsonify({

            'available_indices': available,

            'message': f'Found {len(available)} camera(s)'

        })

    except Exception as e:

        gc.collect()

        return jsonify({'error': str(e)}), 500

# ============================================

# MAIN DETECTION API ROUTE

# ============================================

def interpret_color_prediction(result):

    """Map the trained sigmoid output: 0=Balanced, 1=Imbalanced."""

    score = float(result['raw_score'])

    if not 0.0 <= score <= 1.0:

        raise ValueError(f'Unexpected color model score: {score}')

    is_imbalanced = score > 0.5

    return {

        'model': 'ResNet50',

        'raw_score': score,

        'label': 'Imbalanced' if is_imbalanced else 'Balanced',

        'status': 'FAIL' if is_imbalanced else 'PASS',

        'color_balanced': not is_imbalanced,

        'confidence': score if is_imbalanced else 1.0 - score,

        'classification_verified': True,

    }

@app.route('/api/detect-color', methods=['POST'])

@login_required

def detect_color_only():

    """Test the color model without saving the uploaded image."""

    file = request.files.get('image')

    if file is None or not file.filename:

        return jsonify({'error': 'No image provided'}), 400

    data = file.read(10 * 1024 * 1024 + 1)

    if len(data) > 10 * 1024 * 1024:

        return jsonify({'error': 'Image too large'}), 400

    try:

        result = predict_color_imbalance(data)

        return jsonify({'success': True, **interpret_color_prediction(result)})

    except Exception as exc:

        traceback.print_exc()

        return jsonify({'error': str(exc)}), 400

_stitch_detector = None

def get_stitch_detector():
    global _stitch_detector
    if _stitch_detector is None:
        _stitch_detector = StitchDetector()
    return _stitch_detector

@app.route('/api/detect', methods=['POST'])

@login_required

def detect_defects():

    try:

        print("=" * 50)

        print("≡ƒô╖ DETECTION REQUEST")

        print("=" * 50)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Keep uploaded images out of static/uploads and out of MySQL.

        file = request.files.get('image')

        if file is None or not file.filename:

            return jsonify({'error': 'No image provided'}), 400

        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}

        if '.' not in file.filename:

            return jsonify({'error': 'Invalid image file type'}), 400

        extension = file.filename.rsplit('.', 1)[1].lower()

        if extension not in allowed_extensions:

            return jsonify({'error': 'Invalid file type. Allowed: JPG, PNG, GIF, BMP'}), 400

        # Read no more than 10 MB + 1 byte to enforce the upload limit.

        image_bytes = file.read(10 * 1024 * 1024 + 1)

        if len(image_bytes) > 10 * 1024 * 1024:

            return jsonify({'error': 'Image too large. Maximum size is 10MB.'}), 400

        # ButtonDetector currently expects an image path. Use a private

        # temporary file that is removed automatically after inference.

        # The ResNet50 color detector accepts image bytes directly.

        import cv2

        import numpy as np

        image_array = np.frombuffer(image_bytes, dtype=np.uint8)

        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:

            return jsonify({'error': 'Could not decode the uploaded image'}), 400

        height, width = image.shape[:2]

        if width > 2048 or height > 1536:

            scale = min(2048 / width, 1536 / height)

            image = cv2.resize(

                image,

                (max(1, int(width * scale)), max(1, int(height * scale))),

                interpolation=cv2.INTER_AREA

            )

        with tempfile.TemporaryDirectory(prefix='garment_inspection_') as temp_dir:

            image_path = os.path.join(temp_dir, 'garment.png')

            if not cv2.imwrite(image_path, image):

                raise RuntimeError('Unable to prepare temporary inspection image')

            detector = ButtonDetector()

            boxes = detector.detect_buttons(image_path)

            # Spacing/alignment needs at least three detected buttons.
            # Insufficient detections are inconclusive, not a server failure.
            try:
                analysis = detector.analyze_buttons(boxes)
            except ValueError as exc:
                if 'Fewer than three buttons detected' not in str(exc):
                    raise
                print(f'Button check NOT_TESTED: {exc}')
                analysis = {
                    'overall_status': 'NOT_TESTED',
                    'count': len(boxes),
                    'expected': None,
                    'alignment_score': None,
                    'spacing_score': None,
                    'misaligned_count': 0,
                    'missing_gap_count': 0,
                    'geometric_gap_count': 0,
                    'defects': [],
                    'message': str(exc),
                    'evaluated': False,
                }


            color_result = interpret_color_prediction(predict_color_imbalance(image_bytes))

            # LabelDetector accepts the decoded OpenCV image; no image is saved.

            label_result = LabelDetector().detect_labels(image)

            # Stitch ROIs and ensemble inference operate entirely in memory.
            stitch_result = get_stitch_detector().detect(image)

            print('Label results:', label_result['product_label'], 'NoLabel:', label_result['no_label_detected'])

            print(f"Color imbalance: {color_result['label']} ({color_result['raw_score']:.6f})")

            # Button, color, and product-label checks contribute to the inspection result.

            module_statuses = (
                analysis['overall_status'],
                color_result['status'],
                label_result['status'],
                stitch_result['status'],
            )
            # A failed check is a FAIL. An unevaluated check must never
            # silently turn an otherwise inconclusive inspection into PASS.
            if 'FAIL' in module_statuses:
                overall_status = 'FAIL'
            elif all(status == 'PASS' for status in module_statuses):
                overall_status = 'PASS'
            else:
                overall_status = 'NOT_TESTED'


        # The temporary image has been deleted; save results only.

        # Save to database

        session_id = f"INS-{timestamp}"

        # Database schema contains required boolean columns for modules not yet

        # integrated. False for those columns is a placeholder, NOT a verified

        # defect-negative result. Track evaluation status in defect_details.

        button_defects = analysis.get('defects', [])

        details = {

            'button_defects': button_defects,

            'button_detection': {

                'evaluated': analysis['overall_status'] in ('PASS', 'FAIL'),

                'status': analysis['overall_status'],

                'model': 'YOLO11 garment button detector',

                'count': analysis['count'],

                'expected': analysis['expected'],

                'alignment_score': analysis.get('alignment_score', 0),

                'spacing_score': analysis.get('spacing_score', 0),

                'misaligned_count': analysis.get('misaligned_count', 0),

                'missing_gap_count': analysis.get('missing_gap_count', 0),

                'geometric_gap_count': analysis.get('geometric_gap_count', 0),

            },

            'color_imbalance': {

                'evaluated': True,

                'classification_verified': True,

                'raw_score': color_result['raw_score'],

                'label': color_result['label'],

                'status': color_result['status'],

                'confidence': color_result['confidence'],

                'model': 'ResNet50',

            },

            'label_detection': label_result,
            'stitch_detection': stitch_result,

            # A model prediction is not proof that an absent label is missing.

            'broken_stitches_evaluated': stitch_result['evaluated'],

            'size_label_evaluated': False,  # Missing-label status not verified

            'product_label_evaluated': True,  # Product-label model evaluated; absence is a prediction

            'note': 'Size label is not evaluated. Stitch and label results are model predictions, not physical confirmation.'

        }

        inspection = InspectionSession(

            session_id=f"INS-{timestamp}-{uuid.uuid4().hex[:8]}",

            operator_id=current_user.operator_id,

            date=datetime.utcnow(),

            shirt_count=1,

            color_balanced=color_result['color_balanced'],

            buttons_missing=bool(analysis.get('missing_gap_count') or analysis.get('geometric_gap_count')),

            broken_stitches=stitch_result['broken_stitches'] is True,

            size_label_missing=False,  # Not evaluated

            product_label_missing=False,  # Not evaluated

            overall_status=overall_status,

            defect_details=json.dumps(details)

        )

        session_id = inspection.session_id

        db.session.add(inspection)

        db.session.commit()

        print(f"≡ƒÆ╛ Inspection saved: {session_id}")

        # Persist defect records for both integrated detectors.

        for defect_desc in button_defects:

            db.session.add(Defect(

                session_id=inspection.id,

                defect_type='button_defect',

                defect_status='FAIL',

                description=str(defect_desc),

                severity='HIGH' if 'missing' in str(defect_desc).lower() else 'MEDIUM'

            ))

        if color_result['status'] == 'FAIL':

            db.session.add(Defect(

                session_id=inspection.id,

                defect_type='color_imbalance',

                defect_status='FAIL',

                description=(

                    f"ResNet50 detected color imbalance "

                    f"(confidence: {color_result['confidence']:.2%})"

                ),

                severity='HIGH'

            ))

        if stitch_result['status'] == 'FAIL':
            failed_regions = sorted(set(
                roi['roi_name'] for roi in stitch_result['rois']
                if roi['status'] == 'Broken Stitches'
            ))
            db.session.add(Defect(
                session_id=inspection.id,
                defect_type='broken_stitch',
                defect_status='FAIL',
                description='Predicted broken stitches in: ' + ', '.join(failed_regions),
                severity='HIGH'
            ))

        if label_result['status'] == 'FAIL':
            db.session.add(Defect(
                session_id=inspection.id,
                defect_type='label_defect',
                defect_status='FAIL',
                description='Product label check failed (model prediction): ' +
                            label_result.get('message', 'Product label not confirmed'),
                severity='MEDIUM'
            ))

        db.session.commit()

        if overall_status == 'FAIL':

            # ============================================

            # PLAY ALARM - ENHANCED

            # ============================================

            print("≡ƒöè ALARM TRIGGERED!")

            try:

                alarm = AlarmManager()

                alarm.play_alarm()

                print("Γ£à Server alarm played successfully")

            except Exception as e:

                print(f"Γ¥î Alarm error: {e}")

                # Try simple beep as fallback

                try:

                    sys.stdout.write('\a')

                    sys.stdout.flush()

                    print("≡ƒöö Terminal bell played")

                except:

                    pass

            # Also try to play sound via system

            try:

                import platform

                if platform.system() == 'Windows':

                    import winsound

                    winsound.Beep(880, 400)

                    winsound.Beep(880, 400)

                    winsound.Beep(880, 400)

                    print("≡ƒöö Windows beep played")

            except:

                pass

        print(f"Detection complete: {overall_status}")

        print("=" * 50)

        # Clean up memory

        gc.collect()

        return jsonify({

            'success': True,

            'session_id': session_id,

            'overall_status': overall_status,

            'has_defect': overall_status == 'FAIL',

            'button_count': analysis['count'],

            'expected': analysis['expected'],

            'alignment_score': analysis.get('alignment_score', 0),

            'defects': analysis.get('defects', []),

            'button_detection': analysis,

            'color_imbalance': color_result,

            'label_detection': label_result,
            'stitch_detection': stitch_result

        })

    except Exception as e:

        print(f"Γ¥î Detection error: {e}")

        import traceback

        traceback.print_exc()

        gc.collect()

        return jsonify({'error': str(e)}), 500

# ============================================

# REPORT ROUTES

# ============================================

@app.route('/api/generate-report', methods=['POST'])

@login_required

def generate_report():

    try:

        period = request.form.get('period', 'weekly')

        end = datetime.utcnow()

        if period == 'weekly':

            start = end - timedelta(days=7)

        elif period == 'monthly':

            start = end - timedelta(days=30)

        elif period == 'annual':

            start = end - timedelta(days=365)

        else:

            start = end - timedelta(days=7)

        inspections = InspectionSession.query.filter(

            InspectionSession.operator_id == current_user.operator_id,

            InspectionSession.date >= start,

            InspectionSession.date <= end

        ).all()

        defects = Defect.query.join(InspectionSession).filter(

            InspectionSession.operator_id == current_user.operator_id,

            Defect.created_at >= start,

            Defect.created_at <= end

        ).all()

        if not inspections:

            gc.collect()

            return jsonify({'error': 'No inspections found for this period'}), 400

        # Legacy report templates may use old result attribute names.

        # Set transient Python attributes; these are not database columns.

        for item in inspections:

            item.result_summary = item.overall_status

            item.has_defect = item.overall_status == 'FAIL'

            try:

                saved_details = json.loads(item.defect_details or '{}')

                if not isinstance(saved_details, dict):

                    saved_details = {}

            except (ValueError, TypeError):

                saved_details = {}

            item.label_status = get_saved_label_status(saved_details)
            stitch = saved_details.get('stitch_detection') or {}
            item.stitch_status = stitch.get('status', 'Not Tested') if stitch.get('evaluated') is True else 'Not Tested'

            item.label_detection = saved_details.get('label_detection') or {}

            try:

                detail = json.loads(item.defect_details or '{}')

                button = detail.get('button_detection', {}) if isinstance(detail, dict) else {}

            except (ValueError, TypeError):

                button = {}

            item.button_count = button.get('count', 0)

            item.expected_count = button.get('expected', 7)

            item.alignment_score = button.get('alignment_score', 0)

            item.spacing_score = button.get('spacing_score', 0)

        report_gen = ReportGenerator()

        filename = report_gen.generate_report(

            inspections=inspections,

            defects=defects,

            period=period,

            user_name=current_user.operator_name

        )

        filename_only = os.path.basename(filename)

        gc.collect()

        return jsonify({

            'success': True,

            'message': 'Report generated successfully!',

            'download_url': f"/download/{filename_only}"

        })

    except Exception as e:

        gc.collect()

        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')

@login_required

def download_report(filename):

    """Download generated report"""

    from flask import send_file

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    file_path = os.path.join(root_dir, 'reports', filename)

    if not os.path.exists(file_path):

        gc.collect()

        return jsonify({'error': 'Report file not found'}), 404

    gc.collect()

    return send_file(file_path, as_attachment=True)

@app.route('/api/recent-reports')

@login_required

def recent_reports():

    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    reports_dir = os.path.join(root_dir, 'reports')

    if not os.path.exists(reports_dir):

        gc.collect()

        return jsonify({'reports': []})

    files = []

    for f in os.listdir(reports_dir):

        if f.endswith('.pdf'):

            file_path = os.path.join(reports_dir, f)

            files.append({

                'name': f,

                'url': f"/download/{f}",

                'date': datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M')

            })

    files.sort(key=lambda x: x['date'], reverse=True)

    gc.collect()

    return jsonify({'reports': files[:10]})

@app.route('/api/defect-stats')

@login_required

def defect_stats():

    try:

        counts = get_operator_defect_summary(current_user.operator_id)

        return jsonify({

            'total_defects': sum(counts.values()),

            'defect_breakdown': [

                {'type': kind, 'count': count}

                for kind, count in counts.items()

            ]

        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])

def health_check():

    return jsonify({

        'status': 'ok',

        'color_model': 'loaded',

        'stitch_model': 'integrated (lazy loading)',

        'label_model': 'integrated (ProductLabel/NoLabel; model PASS/FAIL)',

        'mail_configured': bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD')),

        'timestamp': datetime.now().isoformat()

    })

if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0', port=5000)
