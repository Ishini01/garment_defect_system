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



@app.route('/dashboard')

@login_required

def dashboard():

    total = InspectionSession.query.filter_by(operator_id=current_user.operator_id).count()

    pass_count = InspectionSession.query.filter_by(operator_id=current_user.operator_id, overall_status='PASS').count()

    fail_count = total - pass_count

    pass_rate = (pass_count / total * 100) if total > 0 else 0



    return render_template('dashboard.html',

                          total=total,

                          pass_count=pass_count,

                          fail_count=fail_count,

                          pass_rate=pass_rate)



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

    """API endpoint to capture image from iPhone"""

    try:

        print("=" * 50)

        print("≡ƒô▒ IPHONE CAPTURE REQUEST")

        print("=" * 50)



        detector = ButtonDetector(camera_type='camo', camera_index=1)



        if not detector.test_camera():

            gc.collect()

            return jsonify({'error': 'iPhone camera not connected. Please connect via USB and launch Camo app.'}), 500



        image_path = detector.capture_and_save(prefix='iphone')

        if image_path is None:

            gc.collect()

            return jsonify({'error': 'Could not capture from iPhone.'}), 500



        print(f"Γ£à Image captured: {image_path}")

        print("=" * 50)



        gc.collect()



        return jsonify({

            'success': True,

            'message': 'Image captured successfully from iPhone!',

            'image_path': image_path,

            'image_url': f"/{image_path}"

        })



    except Exception as e:

        print(f"Γ¥î Capture error: {e}")

        import traceback

        traceback.print_exc()

        gc.collect()

        return jsonify({'error': str(e)}), 500



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
        return jsonify({'success': True, **result, 'classification_verified': False})
    except Exception as exc:
        traceback.print_exc()
        return jsonify({'error': str(exc)}), 400


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
            analysis = detector.analyze_buttons(boxes)

            # Raw score only; class-to-defect mapping is not verified yet.
            color_result = predict_color_imbalance(image_bytes)
            print(f"Color imbalance raw prediction: {color_result['raw_score']:.6f}")

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
                'evaluated': True,
                'count': analysis['count'],
                'expected': analysis['expected'],
                'alignment_score': analysis.get('alignment_score', 0),
                'spacing_score': analysis.get('spacing_score', 0),
            },
            'color_imbalance': {
                'evaluated': True,
                'classification_verified': False,
                'raw_score': color_result['raw_score'],
                'model': 'ResNet50',
            },
            'broken_stitches_evaluated': False,
            'size_label_evaluated': False,
            'product_label_evaluated': False,
            'note': 'Unevaluated boolean fields are placeholders; do not treat as PASS/FAIL.'
        }
        inspection = InspectionSession(
            session_id=f"INS-{timestamp}-{uuid.uuid4().hex[:8]}",
            operator_id=current_user.operator_id,
            date=datetime.utcnow(),
            shirt_count=1,
            color_balanced=False,  # Unknown until class mapping is verified
            buttons_missing=any('missing' in str(d).lower() for d in button_defects),
            broken_stitches=False,  # Not evaluated
            size_label_missing=False,  # Not evaluated
            product_label_missing=False,  # Not evaluated
            overall_status=analysis['overall_status'],  # Button-only status
            defect_details=json.dumps(details)
        )
        session_id = inspection.session_id

        db.session.add(inspection)

        db.session.commit()

        print(f"≡ƒÆ╛ Inspection saved: {session_id}")



        # Add defects if found

        if analysis['has_defect']:

            for defect_desc in analysis.get('defects', []):

                defect = Defect(

                    session_id=inspection.id,

                    defect_type='button_defect',

                    defect_status='FAIL',

                    description=defect_desc,

                    severity='HIGH' if 'missing' in defect_desc.lower() else 'MEDIUM'

                )

                db.session.add(defect)

            db.session.commit()

            print(f"ΓÜá∩╕Å Defects saved: {len(analysis.get('defects', []))}")



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



        print(f"Γ£à Detection complete: {analysis['overall_status']}")

        print("=" * 50)



        # Clean up memory

        gc.collect()



        return jsonify({

            'success': True,

            'session_id': session_id,

            'overall_status': analysis['overall_status'],

            'has_defect': analysis['has_defect'],

            'button_count': analysis['count'],

            'expected': analysis['expected'],

            'alignment_score': analysis.get('alignment_score', 0),

            'defects': analysis.get('defects', []),
            'color_imbalance': {
                'model': 'ResNet50',
                'raw_score': color_result['raw_score']
            }
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

        total_defects = Defect.query.join(InspectionSession).filter(

            InspectionSession.operator_id == current_user.operator_id

        ).count()



        defect_counts = db.session.query(

            Defect.defect_type, 

            db.func.count(Defect.id)

        ).join(InspectionSession).filter(

            InspectionSession.operator_id == current_user.operator_id

        ).group_by(Defect.defect_type).all()



        gc.collect()



        return jsonify({

            'total_defects': total_defects,

            'defect_breakdown': [{'type': d[0], 'count': d[1]} for d in defect_counts]

        })



    except Exception as e:

        gc.collect()

        return jsonify({'error': str(e)}), 500




@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'color_model': 'loaded',
        'stitch_model': 'not integrated',
        'label_model': 'not integrated',
        'mail_configured': bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD')),
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0', port=5000)
