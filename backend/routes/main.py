from flask import Blueprint, render_template
from flask_login import login_required, current_user
from backend.models import InspectionSession

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
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

@main_bp.route('/inspect')
@login_required
def inspect():
    return render_template('inspect.html')

@main_bp.route('/history')
@login_required
def history():
    inspections = InspectionSession.query.filter_by(
        operator_id=current_user.operator_id
    ).order_by(InspectionSession.date.desc()).all()
    return render_template('history.html', inspections=inspections)

@main_bp.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)