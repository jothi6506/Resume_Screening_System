"""Email History Model."""

from datetime import datetime, timezone
from app.extensions import db


class EmailHistory(db.Model):
    __tablename__ = "email_history"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=True, index=True)
    candidate_name = db.Column(db.String(200), nullable=False)
    email_address = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False)  # Sent, Failed
    error_message = db.Column(db.Text, nullable=True)
    sent_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    candidate = db.relationship("Candidate", backref=db.backref("emails", lazy="dynamic", cascade="all, delete-orphan"))


class EmailSettings(db.Model):
    __tablename__ = "email_settings"

    id = db.Column(db.Integer, primary_key=True)
    smtp_host = db.Column(db.String(120), nullable=False, default="smtp.gmail.com")
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    sender_email = db.Column(db.String(120), nullable=False)
    sender_password = db.Column(db.String(120), nullable=False)
