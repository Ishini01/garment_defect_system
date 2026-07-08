from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from backend.models import User

class LoginForm(FlaskForm):
    operator_id = StringField('Operator ID', validators=[DataRequired(), Length(min=3, max=80)])
    pin = PasswordField('PIN', validators=[DataRequired(), Length(min=4, max=10)])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class RegistrationForm(FlaskForm):
    operator_id = StringField('Operator ID', validators=[DataRequired(), Length(min=3, max=80)])
    operator_name = StringField('Operator Name', validators=[DataRequired(), Length(min=2, max=100)])
    nic = StringField('NIC', validators=[DataRequired(), Length(min=10, max=20)])
    pin = PasswordField('PIN', validators=[DataRequired(), Length(min=4, max=10)])
    confirm_pin = PasswordField('Confirm PIN', validators=[DataRequired(), EqualTo('pin')])
    email = EmailField('Email', validators=[Email()])
    submit = SubmitField('Register')
    
    def validate_operator_id(self, operator_id):
        user = User.query.filter_by(operator_id=operator_id.data).first()
        if user:
            raise ValidationError('Operator ID already exists.')
    
    def validate_nic(self, nic):
        user = User.query.filter_by(nic=nic.data).first()
        if user:
            raise ValidationError('NIC already registered.')


class ForgotPasswordForm(FlaskForm):
    operator_id = StringField('Operator ID', validators=[DataRequired()])
    nic = StringField('NIC', validators=[DataRequired(), Length(min=10, max=20)])
    submit = SubmitField('Verify Identity')
    
    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        user = User.query.filter_by(operator_id=self.operator_id.data, nic=self.nic.data).first()
        if not user:
            self.operator_id.errors.append('Invalid Operator ID or NIC combination.')
            return False
        return True


class ResetPasswordForm(FlaskForm):
    pin = PasswordField('New PIN', validators=[DataRequired(), Length(min=4, max=10)])
    confirm_pin = PasswordField('Confirm PIN', validators=[DataRequired(), EqualTo('pin')])
    submit = SubmitField('Reset PIN')