"""Forms for email settings."""

from flask_wtf import FlaskForm
from wtforms import IntegerField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, NumberRange


class EmailSettingsForm(FlaskForm):
    smtp_host = StringField("SMTP Host", validators=[DataRequired()])
    smtp_port = IntegerField("SMTP Port", validators=[DataRequired(), NumberRange(min=1, max=65535)])
    sender_email = StringField("Sender Email", validators=[DataRequired(), Email()])
    sender_password = PasswordField("Sender Password / App Password")
    submit = SubmitField("Save Settings")
