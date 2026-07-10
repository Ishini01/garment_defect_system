from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
import uuid
import json

from backend.models import db, User, InspectionSession, Defect
from backend.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from backend.utils.button_detector import ButtonDetector
from backend.utils.alarm import AlarmManager
from backend.utils.report_generator import ReportGenerator

# Create Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')

# ============================================
# CONFIGURATION - MYSQL (NO PASSWORD)
# ============================================
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'

# MySQL Connection - NO PASSWORD (XAMPP default)
# Note: root:@localhost means username=root, password=blank
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/garment_defect_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# ============================================
# INITIALIZE EXTENSIONS
# ============================================
db.init_app(app)

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
    print("✅ MySQL Database tables created successfully!")

# ============================================
# ROUTES
# ============================================

@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    total = InspectionSession.query.filter_by(operator_id=current_user.operator_id).count()
    pass_count = InspectionSession.query.filter_by(operator_id=current_user.operator_id, result_summary='PASS').count()
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
        flash('✅ Registration successful! Please login.', 'success')
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

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(operator_id=form.operator_id.data, nic=form.nic.data).first()
        if user:
            token = user.get_reset_token()
            flash(f'📧 Reset link: http://localhost:5000/reset-password/{token}', 'info')
            flash('🔑 In production, this would be sent to your email.', 'info')
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
    pass_count = InspectionSession.query.filter_by(operator_id=current_user.operator_id, result_summary='PASS').count()
    fail_count = total - pass_count
    pass_rate = (pass_count / total * 100) if total > 0 else 0
    
    return render_template('profile.html', 
                          user=current_user,
                          total_inspections=total,
                          pass_count=pass_count,
                          fail_count=fail_count,
                          pass_rate=pass_rate)

# ============================================
# API ROUTES
# ============================================

@app.route('/api/detect', methods=['POST'])
@login_required
def detect_defects():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        upload_dir = 'static/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        image_path = os.path.join(upload_dir, filename)
        file.save(image_path)
        
        detector = ButtonDetector()
        boxes = detector.detect_buttons(image_path)
        analysis = detector.analyze_buttons(boxes)
        
        session_id = f"INS-{timestamp}"
        inspection = InspectionSession(
            session_id=session_id,
            operator_id=current_user.operator_id,
            date=datetime.utcnow(),
            image_path=image_path,
            shirt_count=1,
            result_summary=analysis['overall_status'],
            has_defect=analysis['has_defect'],
            button_count=analysis['count'],
            expected_count=analysis['expected'],
            alignment_score=analysis.get('alignment_score', 0),
            spacing_score=analysis.get('spacing_score', 0),
            defect_details=json.dumps(analysis.get('defects', []))
        )
        db.session.add(inspection)
        db.session.commit()
        
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
            alarm = AlarmManager()
            alarm.play_alarm()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'overall_status': analysis['overall_status'],
            'has_defect': analysis['has_defect'],
            'button_count': analysis['count'],
            'expected': analysis['expected'],
            'alignment_score': analysis.get('alignment_score', 0),
            'defects': analysis.get('defects', [])
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
            return jsonify({'error': 'No inspections found for this period'}), 400
        
        report_gen = ReportGenerator()
        filename = report_gen.generate_report(
            inspections=inspections,
            defects=defects,
            period=period,
            user_name=current_user.operator_name
        )
        
        # Extract just the filename for download
        filename_only = os.path.basename(filename)
        
        return jsonify({
            'success': True,
            'message': 'Report generated successfully!',
            'download_url': f"/download/{filename_only}"
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
@login_required
def download_report(filename):
    """Download generated report"""
    from flask import send_file
    
    # Get the root directory of the project
    # app.py is in backend/, so go up one level to get root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(root_dir, 'reports', filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        return jsonify({'error': 'Report file not found'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/api/recent-reports')
@login_required
def recent_reports():
    # Get the root directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(root_dir, 'reports')
    
    if not os.path.exists(reports_dir):
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
        
        return jsonify({
            'total_defects': total_defects,
            'defect_breakdown': [{'type': d[0], 'count': d[1]} for d in defect_counts]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)