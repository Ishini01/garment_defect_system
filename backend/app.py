from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message          # ⭐ NEW
from dotenv import load_dotenv                # ⭐ NEW
from datetime import datetime, timedelta
import os
import uuid
import json
import sys
import gc
import traceback

from backend.models import db, User, InspectionSession, Defect
from backend.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from backend.utils.button_detector import ButtonDetector
from backend.utils.color_detector import ColorImbalanceDetector
from backend.utils.alarm import AlarmManager
from backend.utils.report_generator import ReportGenerator

# ⭐ Load .env variables
load_dotenv()

# ============================================
# ABSOLUTE PATHS
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

print("=" * 60)
print(f"RUNNING: {os.path.abspath(__file__)}")
print(f"TEMPLATES: {app.template_folder}")
print(f"STATIC: {app.static_folder}")
print("=" * 60)

# ============================================
# CONFIG
# ============================================
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/garment_defect_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# ⭐ Email (SMTP) config — reads from .env file
app.config['MAIL_SERVER']         = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT']           = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS']        = os.getenv('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME']       = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD']       = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

CAMERA_TYPE = 'camo'
CAMERA_INDEX = 1
PHONE_URL = 'http://localhost:8080/shot.jpg'

# ============================================
# EXTENSIONS
# ============================================
db.init_app(app)
mail = Mail(app)                              # ⭐ NEW

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_now():
    return {'now': datetime.now()}


# ============================================
# ⭐ EMAIL HELPER
# ============================================
def send_reset_email(user, reset_url):
    """Send PIN reset link via email."""
    subject = "🔐 Garment Detect — PIN Reset Request"
    body = f"""Hello {user.operator_name},

We received a request to reset your PIN for the Garment Defect Detection System.

Click the link below to reset your PIN:
{reset_url}

This link will expire in 1 hour.

If you did not request this, please ignore this email.

— Garment Detect System
Rajarata University of Sri Lanka
"""
    msg = Message(subject=subject, recipients=[user.email], body=body)
    mail.send(msg)


# ============================================
# LOAD MODELS ONCE
# ============================================
color_detector = None
stitch_detector = None
label_detector = None


def init_all_detectors():
    """Load all 4 AI models at startup. Failures are non-fatal."""
    global color_detector, stitch_detector, label_detector

    # ---- Color model (existing) ----
    try:
        color_detector = ColorImbalanceDetector()
        print("✅ Color Imbalance model loaded successfully!")
    except FileNotFoundError as e:
        print(f"⚠️ Color model NOT found: {e}")
        color_detector = None
    except Exception as e:
        print(f"⚠️ Color model failed to load: {e}")
        color_detector = None

    # ---- Stitch model (add when ready) ----
    # ---- Label model (add when ready) ----


with app.app_context():
    db.create_all()
    print("✅ MySQL Database tables created successfully!")
    init_all_detectors()


# ============================================
# ROUTES — PUBLIC
# ============================================

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        existing_op = User.query.filter_by(operator_id=form.operator_id.data).first()
        if existing_op:
            flash('❌ Operator ID already exists.', 'danger')
            return render_template('register.html', form=form)

        if form.email.data:
            if User.query.filter_by(email=form.email.data).first():
                flash('❌ Email already registered.', 'danger')
                return render_template('register.html', form=form)

        try:
            user = User(
                operator_id=form.operator_id.data,
                operator_name=form.operator_name.data,
                email=form.email.data or None,
                nic=form.nic.data
            )
            user.set_pin(form.pin.data)
            db.session.add(user)
            db.session.commit()
            flash('✅ Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Registration failed: {e}', 'danger')

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
            flash(f'👋 Welcome back, {user.operator_name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        flash('❌ Invalid Operator ID or PIN.', 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 You have been logged out.', 'info')
    return redirect(url_for('login'))


# ============================================
# ⭐ FORGOT PASSWORD — NOW SENDS EMAIL
# ============================================
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(
            operator_id=form.operator_id.data,
            nic=form.nic.data
        ).first()

        # Security: don't reveal whether the account exists
        if user and user.email:
            token = user.get_reset_token()
            reset_url = url_for('reset_password', token=token, _external=True)
            print(f"📧 Sending reset email to: {user.email}")
            print(f"🔗 Reset URL: {reset_url}")

            try:
                send_reset_email(user, reset_url)
                print("✅ Reset email sent successfully")
                flash('📧 A PIN reset link has been sent to your registered email address.', 'success')
            except Exception as e:
                print(f"❌ Email send failed: {e}")
                traceback.print_exc()
                flash('❌ Failed to send reset email. Please try again later.', 'danger')
        else:
            # Same message even if user/email not found — prevents account enumeration
            flash('📧 If your account exists and has a registered email, a reset link has been sent.', 'info')

        return redirect(url_for('login'))

    return render_template('forgot_password.html', form=form)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    operator_id = User.verify_reset_token(token)
    if not operator_id:
        flash('❌ Invalid or expired reset link.', 'danger')
        return redirect(url_for('forgot_password'))

    user = User.query.filter_by(operator_id=operator_id).first()
    if not user:
        flash('❌ User not found.', 'danger')
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_pin(form.pin.data)
        db.session.commit()
        flash('✅ PIN reset successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form, token=token)


# ============================================
# ROUTES — PROTECTED
# ============================================

@app.route('/dashboard')
@login_required
def dashboard():
    total = InspectionSession.query.filter_by(operator_id=current_user.operator_id).count()
    pass_count = InspectionSession.query.filter_by(
        operator_id=current_user.operator_id, result_summary='PASS'
    ).count()
    fail_count = total - pass_count
    pass_rate = (pass_count / total * 100) if total > 0 else 0

    stitch_count = InspectionSession.query.filter_by(
        operator_id=current_user.operator_id, has_broken_stitch=True
    ).count()
    button_count = InspectionSession.query.filter_by(
        operator_id=current_user.operator_id, has_button_defect=True
    ).count()
    label_count = InspectionSession.query.filter_by(
        operator_id=current_user.operator_id, has_label_defect=True
    ).count()
    color_count = InspectionSession.query.filter_by(
        operator_id=current_user.operator_id, color_has_imbalance=True
    ).count()

    recent_inspections = InspectionSession.query.filter_by(
        operator_id=current_user.operator_id
    ).order_by(InspectionSession.date.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        total=total, pass_count=pass_count,
        fail_count=fail_count, pass_rate=pass_rate,
        stitch_count=stitch_count,
        button_count=button_count,
        label_count=label_count,
        color_count=color_count,
        recent_inspections=recent_inspections
    )


@app.route('/inspect')
@login_required
def inspect():
    return render_template('inspect.html')


@app.route('/history')
@login_required
def history():
    inspections = InspectionSession.query.filter_by(
        operator_id=current_user.operator_id
    ).order_by(InspectionSession.date.desc()).all()
    return render_template('history.html', inspections=inspections)


@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')


@app.route('/profile')
@login_required
def profile():
    total = InspectionSession.query.filter_by(operator_id=current_user.operator_id).count()
    pass_count = InspectionSession.query.filter_by(
        operator_id=current_user.operator_id, result_summary='PASS'
    ).count()
    fail_count = total - pass_count
    pass_rate = (pass_count / total * 100) if total > 0 else 0

    return render_template(
        'profile.html', user=current_user,
        total_inspections=total, pass_count=pass_count,
        fail_count=fail_count, pass_rate=pass_rate
    )


@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')


@app.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy_policy.html')


# ============================================
# API — PROFILE / PIN / DATA
# ============================================

@app.route('/api/update-profile', methods=['POST'])
@login_required
def update_profile():
    try:
        user = User.query.get(current_user.id)
        user.operator_name = request.form.get('operator_name')
        user.nic = request.form.get('nic')
        user.email = request.form.get('email')
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/change-pin', methods=['POST'])
@login_required
def change_pin():
    try:
        current_pin = request.form.get('current_pin')
        new_pin = request.form.get('new_pin')
        user = User.query.get(current_user.id)
        if not user.check_pin(current_pin):
            return jsonify({'error': 'Current PIN is incorrect'}), 400
        if len(new_pin) < 4 or len(new_pin) > 10:
            return jsonify({'error': 'PIN must be 4–10 characters'}), 400
        user.set_pin(new_pin)
        db.session.commit()
        return jsonify({'success': True, 'message': 'PIN changed!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear-data', methods=['POST'])
@login_required
def clear_data():
    try:
        inspections = InspectionSession.query.filter_by(
            operator_id=current_user.operator_id
        ).all()
        for inspection in inspections:
            Defect.query.filter_by(session_id=inspection.id).delete()
            db.session.delete(inspection)
        db.session.commit()
        return jsonify({'success': True, 'message': 'All data cleared!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete-account', methods=['POST'])
@login_required
def delete_account():
    try:
        inspections = InspectionSession.query.filter_by(
            operator_id=current_user.operator_id
        ).all()
        for inspection in inspections:
            Defect.query.filter_by(session_id=inspection.id).delete()
            db.session.delete(inspection)
        user = User.query.get(current_user.id)
        db.session.delete(user)
        db.session.commit()
        logout_user()
        return jsonify({'success': True, 'message': 'Account deleted!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# API — CAMERA
# ============================================

@app.route('/api/iphone-status', methods=['GET'])
@login_required
def iphone_status():
    try:
        detector = ButtonDetector(camera_type='camo', camera_index=1)
        is_connected = detector.test_camera()
        gc.collect()
        return jsonify({
            'connected': is_connected,
            'camera_type': 'camo',
            'camera_index': 1,
            'message': 'iPhone camera connected!' if is_connected else 'Not connected.'
        })
    except Exception as e:
        gc.collect()
        return jsonify({'error': str(e)}), 500


@app.route('/api/capture-phone', methods=['POST'])
@login_required
def capture_phone():
    try:
        detector = ButtonDetector(camera_type='camo', camera_index=1)
        if not detector.test_camera():
            gc.collect()
            return jsonify({'error': 'iPhone camera not connected.'}), 500
        image_path = detector.capture_and_save(prefix='iphone')
        if image_path is None:
            gc.collect()
            return jsonify({'error': 'Could not capture from iPhone.'}), 500
        gc.collect()
        return jsonify({
            'success': True,
            'message': 'Image captured!',
            'image_path': image_path,
            'image_url': f"/{image_path}"
        })
    except Exception as e:
        traceback.print_exc()
        gc.collect()
        return jsonify({'error': str(e)}), 500


@app.route('/api/find-camera', methods=['GET'])
@login_required
def find_camera():
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
# COLOR-ONLY TEST ENDPOINT
# ============================================

@app.route('/api/detect-color', methods=['POST'])
@login_required
def detect_color_only():
    if color_detector is None:
        return jsonify({'error': 'Color model not loaded'}), 503

    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{timestamp}_color_{uuid.uuid4().hex[:8]}.jpg"
    upload_dir = os.path.join(BASE_DIR, 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    image_path = os.path.join(upload_dir, filename)
    file.save(image_path)

    try:
        result = color_detector.analyze(image_path)
        gc.collect()
        return jsonify({
            'success': True,
            'image_url': f"/static/uploads/{filename}",
            'status': result.get('predicted_class', 'Balanced'),
            'has_defect': bool(result.get('has_defect', False)),
            'confidence': result.get('confidence', 0.0),
            'balanced_probability': result.get('balanced_probability', 0.0),
            'imbalanced_probability': result.get('imbalanced_probability', 0.0)
        }), 200
    except Exception as e:
        traceback.print_exc()
        gc.collect()
        return jsonify({'error': str(e)}), 500


# ============================================
# MAIN DETECTION API
# ============================================

@app.route('/api/detect', methods=['POST'])
@login_required
def detect_defects():
    try:
        print("=" * 50)
        print("📷 DETECTION REQUEST")
        print("=" * 50)

        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': 'Invalid file type'}), 400

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        upload_dir = os.path.join(BASE_DIR, 'static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        image_path = os.path.join(upload_dir, filename)
        file.save(image_path)
        print(f"📤 Saved: {image_path}")

        # Button
        analysis = {
            'count': 0, 'expected': 7, 'has_defect': False,
            'defects': [], 'alignment_score': 0, 'spacing_score': 0
        }
        try:
            detector = ButtonDetector()
            boxes = detector.detect_buttons(image_path)
            analysis = detector.analyze_buttons(boxes)
            print(f"🔘 Button: {analysis['count']}/{analysis['expected']}")
        except Exception as e:
            print(f"⚠️ Button detection error: {e}")
            traceback.print_exc()

        # Color
        color_verdict = "Unknown"
        color_has_defect = False
        color_confidence = 0.0
        color_balanced_prob = 0.0
        color_imbalanced_prob = 0.0

        if color_detector is not None:
            try:
                color_result = color_detector.analyze(image_path)
                color_has_defect = bool(color_result.get('has_defect', False))
                color_confidence = float(color_result.get('confidence', 0.0))
                color_balanced_prob = float(color_result.get('balanced_probability', 0.0))
                color_imbalanced_prob = float(color_result.get('imbalanced_probability', 0.0))
                color_verdict = "Imbalanced" if color_has_defect else "Balanced"
                print(f"🎨 Color: {color_verdict} ({color_confidence * 100:.1f}%)")
            except Exception as e:
                print(f"⚠️ Color detection error: {e}")
                traceback.print_exc()
                color_verdict = "Error"
        else:
            print("⚠️ Color model not loaded")
            color_verdict = "Model not loaded"

        # Stitch placeholder
        has_broken_stitch = False
        stitch_confidence = 0.0
        if stitch_detector is not None:
            try:
                pass
            except Exception as e:
                print(f"⚠️ Stitch detection error: {e}")

        # Label placeholder
        has_label_defect = False
        size_label_status = None
        if label_detector is not None:
            try:
                pass
            except Exception as e:
                print(f"⚠️ Label detection error: {e}")

        has_button_defect = bool(analysis.get('has_defect', False))

        # Combine
        combined_defects = list(analysis.get('defects', []))
        if color_has_defect:
            combined_defects.append(f"Color imbalance ({color_confidence * 100:.1f}% confidence)")
        if has_broken_stitch:
            combined_defects.append("Broken stitch detected")
        if has_label_defect:
            combined_defects.append(f"Label defect: {size_label_status or 'unknown'}")

        overall_has_defect = any([
            has_button_defect,
            color_has_defect,
            has_broken_stitch,
            has_label_defect,
        ])
        overall_status = 'FAIL' if overall_has_defect else 'PASS'

        # Save session
        session_id = f"INS-{timestamp}"
        inspection = None
        try:
            inspection = InspectionSession(
                session_id=session_id,
                operator_id=current_user.operator_id,
                date=datetime.utcnow(),
                image_path=image_path,
                shirt_count=1,
                result_summary=overall_status,
                has_defect=overall_has_defect,
                button_count=analysis.get('count', 0),
                expected_count=analysis.get('expected', 7),
                alignment_score=analysis.get('alignment_score', 0),
                spacing_score=analysis.get('spacing_score', 0),
                defect_details=json.dumps(combined_defects),

                color_prediction=color_verdict,
                color_has_imbalance=color_has_defect,
                color_confidence=color_confidence,
                color_balanced_probability=color_balanced_prob,
                color_imbalanced_probability=color_imbalanced_prob,

                has_broken_stitch=has_broken_stitch,
                has_button_defect=has_button_defect,
                has_label_defect=has_label_defect,
                size_label_status=size_label_status,
                overall_status=overall_status,
            )
            db.session.add(inspection)
            db.session.commit()
            print(f"💾 DB saved: {session_id} (overall={overall_status})")
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ DB save failed: {e}")
            traceback.print_exc()
            inspection = None

        # Save individual defects
        try:
            if overall_has_defect and inspection is not None:
                for defect_desc in analysis.get('defects', []):
                    db.session.add(Defect(
                        session_id=inspection.id,
                        defect_type='button_defect',
                        defect_status='FAIL',
                        description=defect_desc,
                        severity='MEDIUM'
                    ))
                if color_has_defect:
                    db.session.add(Defect(
                        session_id=inspection.id,
                        defect_type='color_imbalance',
                        defect_status='FAIL',
                        description=f"Color imbalance ({color_confidence * 100:.1f}%)",
                        severity='MEDIUM'
                    ))
                if has_broken_stitch:
                    db.session.add(Defect(
                        session_id=inspection.id,
                        defect_type='broken_stitch',
                        defect_status='FAIL',
                        description='Broken stitch detected',
                        severity='HIGH'
                    ))
                if has_label_defect:
                    db.session.add(Defect(
                        session_id=inspection.id,
                        defect_type='label_defect',
                        defect_status='FAIL',
                        description=f"Label defect: {size_label_status or 'unknown'}",
                        severity='MEDIUM'
                    ))
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"⚠️ Defect save failed: {e}")

        # Alarm
        try:
            if overall_has_defect:
                print("🔊 ALARM")
                try:
                    alarm = AlarmManager()
                    alarm.play_alarm()
                except Exception:
                    sys.stdout.write('\a')
                    sys.stdout.flush()
        except Exception as e:
            print(f"⚠️ Alarm error: {e}")

        print(f"✅ Result: {overall_status}")
        print("=" * 50)
        gc.collect()

        return jsonify({
            'success': True,
            'session_id': session_id,
            'overall_status': overall_status,
            'has_defect': overall_has_defect,

            'has_broken_stitch': has_broken_stitch,
            'has_button_defect': has_button_defect,
            'has_label_defect': has_label_defect,
            'has_color_imbalance': color_has_defect,

            'size_label_status': size_label_status,
            'button_count': analysis.get('count', 0),
            'expected': analysis.get('expected', 7),
            'alignment_score': analysis.get('alignment_score', 0),
            'defects': combined_defects,

            'color_status': color_verdict,
            'color_confidence': color_confidence,
            'color_balanced_probability': color_balanced_prob,
            'color_imbalanced_probability': color_imbalanced_prob
        })

    except Exception as e:
        print(f"❌ Fatal detection error: {e}")
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
        days = {'weekly': 7, 'monthly': 30, 'annual': 365}.get(period, 7)
        start = end - timedelta(days=days)

        inspections = InspectionSession.query.filter(
            InspectionSession.operator_id == current_user.operator_id,
            InspectionSession.date >= start
        ).all()

        defects = Defect.query.join(InspectionSession).filter(
            InspectionSession.operator_id == current_user.operator_id,
            Defect.created_at >= start
        ).all()

        if not inspections:
            return jsonify({'error': 'No inspections found'}), 400

        report_gen = ReportGenerator()
        filename = report_gen.generate_report(
            inspections=inspections,
            defects=defects,
            period=period,
            user_name=current_user.operator_name
        )

        gc.collect()
        return jsonify({
            'success': True,
            'message': 'Report generated!',
            'download_url': f"/download/{os.path.basename(filename)}"
        })
    except Exception as e:
        traceback.print_exc()
        gc.collect()
        return jsonify({'error': str(e)}), 500


@app.route('/download/<filename>')
@login_required
def download_report(filename):
    root_dir = os.path.dirname(BASE_DIR)
    file_path = os.path.join(root_dir, 'reports', filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Report not found'}), 404
    return send_file(file_path, as_attachment=True)


@app.route('/api/recent-reports')
@login_required
def recent_reports():
    root_dir = os.path.dirname(BASE_DIR)
    reports_dir = os.path.join(root_dir, 'reports')
    if not os.path.exists(reports_dir):
        return jsonify({'reports': []})

    files = []
    for f in os.listdir(reports_dir):
        if f.endswith('.pdf'):
            fp = os.path.join(reports_dir, f)
            files.append({
                'name': f,
                'url': f"/download/{f}",
                'date': datetime.fromtimestamp(os.path.getctime(fp)).strftime('%Y-%m-%d %H:%M')
            })
    files.sort(key=lambda x: x['date'], reverse=True)
    return jsonify({'reports': files[:10]})


@app.route('/api/defect-stats')
@login_required
def defect_stats():
    try:
        total_defects = Defect.query.join(InspectionSession).filter(
            InspectionSession.operator_id == current_user.operator_id
        ).count()

        defect_counts = db.session.query(
            Defect.defect_type, db.func.count(Defect.id)
        ).join(InspectionSession).filter(
            InspectionSession.operator_id == current_user.operator_id
        ).group_by(Defect.defect_type).all()

        return jsonify({
            'total_defects': total_defects,
            'defect_breakdown': [{'type': d[0], 'count': d[1]} for d in defect_counts]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# HEALTH CHECK
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'button_model': 'loaded',
        'color_model': 'loaded' if color_detector is not None else 'NOT loaded',
        'stitch_model': 'loaded' if stitch_detector is not None else 'NOT loaded',
        'label_model': 'loaded' if label_detector is not None else 'NOT loaded',
        'mail_configured': bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD')),
        'timestamp': datetime.now().isoformat()
    })


# ============================================
# RUN
# ============================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)