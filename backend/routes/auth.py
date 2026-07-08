from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from backend.models import db, User
from backend.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
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
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(operator_id=form.operator_id.data).first()
        if user and user.check_pin(form.pin.data):
            login_user(user, remember=form.remember.data)
            flash(f'👋 Welcome back, {user.operator_name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        flash('❌ Invalid Operator ID or PIN.', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(operator_id=form.operator_id.data, nic=form.nic.data).first()
        if user:
            token = user.get_reset_token()
            flash(f'📧 Reset link: /reset-password/{token}', 'info')
            flash('🔑 In production, this would be sent to your email.', 'info')
            return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    operator_id = User.verify_reset_token(token)
    if not operator_id:
        flash('❌ Invalid or expired reset link.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    user = User.query.filter_by(operator_id=operator_id).first()
    if not user:
        flash('❌ User not found.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_pin(form.pin.data)
        db.session.commit()
        flash('✅ PIN reset successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', form=form, token=token)