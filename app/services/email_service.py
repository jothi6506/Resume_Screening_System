"""Service for sending emails to candidates via Gmail SMTP."""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import current_app, render_template

from app.extensions import db
from app.models.email import EmailHistory, EmailSettings
from app.models.activity import log_activity

logger = logging.getLogger(__name__)


# ── SMTP helpers ─────────────────────────────────────────────────────────────

def test_smtp_connection(host, port, username, password):
    """Test SMTP connection synchronously. Returns (success, error_message)."""
    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
        
        server.login(username, password)
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)


def _get_smtp_config():
    """Return a dict with SMTP connection settings from the database."""
    settings = EmailSettings.query.first()
    if settings:
        return {
            "host": settings.smtp_host,
            "port": settings.smtp_port,
            "username": settings.sender_email,
            "password": settings.sender_password,
            "use_ssl": True,
        }
    
    # Fallback if no settings exist
    return {
        "host": "smtp.gmail.com",
        "port": 587,
        "username": "",
        "password": "",
        "use_ssl": True,
    }


def _get_sender_email():
    """Return the sender address from EmailSettings."""
    settings = EmailSettings.query.first()
    if settings and settings.sender_email:
        return settings.sender_email
    return ""


# ── Email content generators ────────────────────────────────────────────────

# Fixed email bodies the user specified (plain-text versions used as fallback).
SELECTED_SUBJECT = "Congratulations! You Have Been Selected"
SELECTED_BODY_PLAIN = (
    "Dear {candidate_name},\n\n"
    "Congratulations!\n\n"
    "We are pleased to inform you that you have been selected for the next stage of our recruitment process for the position of {job_title}.\n\n"
    "Our HR team will contact you shortly.\n\n"
    "Best Regards\n\n"
    "{company_name}"
)

REJECTED_SUBJECT = "Application Status Update"
REJECTED_BODY_PLAIN = (
    "Dear {candidate_name},\n\n"
    "Thank you for applying for the position of {job_title}.\n\n"
    "After carefully reviewing your application, we have decided to continue with other candidates whose qualifications better match our requirements.\n\n"
    "We sincerely appreciate your interest in our company and encourage you to apply again in the future.\n\n"
    "Best Regards\n\n"
    "{company_name}"
)


def generate_email_content(status, candidate, job=None, custom_fields=None):
    """Generate subject and HTML body based on candidate status.

    Supports: selected / hired, rejected, shortlisted, interview, on hold.
    Returns (subject, html_body) or (None, None).
    """
    status_lower = status.lower()

    templates = {
        "shortlisted": ("Congratulations! You have been shortlisted.", "emails/shortlisted.html"),
        "selected":    (SELECTED_SUBJECT, "emails/selected.html"),
        "rejected":    (REJECTED_SUBJECT, "emails/rejected.html"),
        "interview":   ("Interview Invitation", "emails/interview.html"),
        "hired":       ("Welcome to the Team!", "emails/hired.html"),
        "on hold":     ("Application Status Update: On Hold.", "emails/on_hold.html"),
    }

    if status_lower not in templates:
        return None, None

    subject, template_name = templates[status_lower]

    import datetime
    
    app_name = current_app.config.get("APP_NAME", "ResumeScreen AI")
    body = render_template(
        template_name,
        candidate=candidate,
        job=job,
        app_name=app_name,
        company_name=app_name,  # Bind company_name for user templates
        current_date=datetime.date.today().strftime("%B %d, %Y"),
        **(custom_fields or {}),
    )
    return subject, body


# ── Core send function ──────────────────────────────────────────────────────

def send_email(to_email, subject, body_html, candidate_name="Unknown", candidate_id=None):
    """Send an email via Gmail SMTP and log it to EmailHistory.

    Returns (success: bool, EmailHistory instance).
    """
    smtp_cfg = _get_smtp_config()
    from_email = _get_sender_email()

    if not smtp_cfg["username"] or not smtp_cfg["password"]:
        return _log_email(
            candidate_id, candidate_name, to_email, subject, body_html,
            "Failed",
            "SMTP settings not configured. Please configure Email Settings in the Admin Panel first."
        )

    # Build MIME message
    msg = MIMEMultipart("alternative")
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Plain-text fallback (strip HTML tags naively)
    import re
    plain = re.sub(r"<[^>]+>", "", body_html)
    plain = re.sub(r"\n{3,}", "\n\n", plain).strip()

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        if smtp_cfg["port"] == 465:
            server = smtplib.SMTP_SSL(smtp_cfg["host"], smtp_cfg["port"], timeout=15)
        else:
            server = smtplib.SMTP(smtp_cfg["host"], smtp_cfg["port"], timeout=15)
            server.starttls()
            
        server.login(smtp_cfg["username"], smtp_cfg["password"])
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()

        logger.info("Email sent via SMTP to %s (subject=%s)", to_email, subject)
        log_activity("Email Sent", f"Email sent to {to_email} (Subject: {subject})")
        return _log_email(candidate_id, candidate_name, to_email, subject, body_html, "Sent", None)

    except smtplib.SMTPAuthenticationError as e:
        error_msg = f"SMTP Authentication failed: {e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else e.smtp_error}"
        logger.error(error_msg)
        return _log_email(candidate_id, candidate_name, to_email, subject, body_html, "Failed", error_msg)

    except smtplib.SMTPRecipientsRefused as e:
        error_msg = f"Recipient refused: {e.recipients}"
        logger.error(error_msg)
        return _log_email(candidate_id, candidate_name, to_email, subject, body_html, "Failed", error_msg)

    except smtplib.SMTPException as e:
        error_msg = f"SMTP error: {e}"
        logger.error(error_msg)
        return _log_email(candidate_id, candidate_name, to_email, subject, body_html, "Failed", error_msg)

    except Exception as e:
        error_msg = f"Failed to send email: {e}"
        logger.error(error_msg)
        return _log_email(candidate_id, candidate_name, to_email, subject, body_html, "Failed", error_msg)


# ── Status-based email ──────────────────────────────────────────────────────

def send_status_email(candidate, status, job=None):
    """Send a status notification email for a candidate.

    Maps 'hired' -> 'selected' for email templates.
    Returns (success: bool, message: str).
    """
    if not candidate.email:
        return False, "No email address"

    template_status = "selected" if status == "hired" else status
    subject, body = generate_email_content(template_status, candidate, job)

    if not subject or not body:
        return False, f"No email template for status '{status}'"

    success, history = send_email(
        candidate.email, subject, body,
        candidate.full_name, candidate.id,
    )
    return success, history


def send_selected_email(candidate, job=None):
    """Send the 'Selected' congratulations email."""
    if not candidate.email:
        return False, "No email address on file"

    if job is None and candidate.applications:
        job = candidate.applications[-1].job

    subject, body = generate_email_content("selected", candidate, job)
    if not subject or not body:
        return False, "Could not generate email content"

    return send_email(candidate.email, subject, body, candidate.full_name, candidate.id)


def send_rejected_email(candidate, job=None):
    """Send the 'Rejected' notification email."""
    if not candidate.email:
        return False, "No email address on file"

    if job is None and candidate.applications:
        job = candidate.applications[-1].job

    subject, body = generate_email_content("rejected", candidate, job)
    if not subject or not body:
        return False, "Could not generate email content"

    return send_email(candidate.email, subject, body, candidate.full_name, candidate.id)


# ── Retry ────────────────────────────────────────────────────────────────────

def retry_email(history_id):
    """Retry sending a failed email from history."""
    history = db.session.get(EmailHistory, history_id)
    if not history or history.status == "Sent":
        return False, "Invalid or already sent email."

    success, new_history = send_email(
        to_email=history.email_address,
        subject=history.subject,
        body_html=history.body,
        candidate_name=history.candidate_name,
        candidate_id=history.candidate_id,
    )

    # Remove the old failed entry since we created a new one
    if new_history and new_history.id != history.id:
        db.session.delete(history)
        db.session.commit()

    return success, new_history


# ── Logging helper ───────────────────────────────────────────────────────────

def _log_email(candidate_id, name, email, subject, body, status, error):
    """Log an email send attempt to the database."""
    history = EmailHistory(
        candidate_id=candidate_id,
        candidate_name=name,
        email_address=email,
        subject=subject,
        body=body,
        status=status,
        error_message=error,
    )
    db.session.add(history)
    db.session.commit()
    return status == "Sent", history
