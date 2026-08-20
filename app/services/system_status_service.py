"""
System & Cloud Status Service

Performs real-time diagnostics on:
- Database connectivity & engine properties
- Object / File Storage mode & health
- Application environment & WSGI server info
- SMTP email configuration
- AI integration key status
"""

import os
import sys
import socket
from flask import current_app
from sqlalchemy import text
from app.extensions import db
from app.services.storage_service import get_storage_service


def get_system_status():
    """Execute live runtime diagnostics and return real status dictionary."""
    
    # ── 1. Application Environment ─────────────────────────────────────────────
    flask_env = os.environ.get("FLASK_ENV", "development")
    try:
        debug_mode = current_app.config.get("DEBUG", False)
    except RuntimeError:
        debug_mode = False
    
    # Detect running WSGI / Server
    server_info = "Werkzeug Dev Server"
    if "gunicorn" in sys.modules or os.environ.get("SERVER_SOFTWARE", "").startswith("gunicorn"):
        server_info = "Gunicorn WSGI Production Server"
    elif "waitress" in sys.modules:
        server_info = "Waitress WSGI Server"
    
    env_status = {
        "environment": flask_env.title(),
        "is_production": flask_env.lower() == "production",
        "debug_mode": "Enabled" if debug_mode else "Disabled",
        "server_engine": server_info,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "status": "Healthy"
    }

    # ── 2. Database Connection Diagnostics ────────────────────────────────────
    db_status = {}
    try:
        # Perform live query
        result = db.session.execute(text("SELECT 1")).scalar()
        
        url = db.engine.url
        host = url.host or "localhost"
        db_name = url.database or "resume_screening"
        driver = url.drivername or "mysql"
        
        is_cloud_db = host not in ("localhost", "127.0.0.1", "::1", "mysql")
        
        # Query record counts to prove live database interaction
        candidate_count = db.session.scalar(text("SELECT COUNT(*) FROM candidate")) or 0
        job_count = db.session.scalar(text("SELECT COUNT(*) FROM job")) or 0
        resume_count = db.session.scalar(text("SELECT COUNT(*) FROM resume")) or 0
        
        db_status = {
            "connected": True,
            "status": "Connected & Active",
            "db_type": "Cloud Centralized MySQL" if is_cloud_db else "Local MySQL Database",
            "host": host,
            "database": db_name,
            "driver": driver,
            "is_cloud_db": is_cloud_db,
            "candidate_records": candidate_count,
            "job_records": job_count,
            "resume_records": resume_count,
            "details": f"Dialect: {driver} | Host: {host} | DB: {db_name}"
        }
    except Exception as exc:
        db_status = {
            "connected": False,
            "status": f"Connection Failure: {str(exc)}",
            "db_type": "MySQL Database",
            "host": "Offline / Unreachable",
            "database": "Unknown",
            "driver": "pymysql",
            "is_cloud_db": False,
            "candidate_records": 0,
            "job_records": 0,
            "resume_records": 0,
            "details": f"Connection error: {str(exc)}"
        }

    # ── 3. Resume Storage Diagnostics ──────────────────────────────────────────
    storage = get_storage_service()
    storage_status = storage.get_status()

    # ── 4. Email / SMTP Diagnostics ───────────────────────────────────────────
    try:
        mail_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        mail_port = current_app.config.get("MAIL_PORT", 465)
        mail_username = current_app.config.get("MAIL_USERNAME", "")
    except RuntimeError:
        mail_server = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
        mail_port = int(os.environ.get("MAIL_PORT", 465))
        mail_username = os.environ.get("MAIL_USERNAME", "")
    
    smtp_reachable = False
    if mail_username:
        try:
            s = socket.create_connection((mail_server, mail_port), timeout=3)
            s.close()
            smtp_reachable = True
        except Exception:
            smtp_reachable = False
            
    email_status = {
        "configured": bool(mail_username),
        "smtp_server": f"{mail_server}:{mail_port}",
        "sender": mail_username if mail_username else "Not Configured",
        "status": "Connected & Reachable" if smtp_reachable else ("Configured (Port Offline)" if mail_username else "Not Configured")
    }

    # ── 5. AI Integration Status ──────────────────────────────────────────────
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    try:
        ai_enabled = current_app.config.get("AI_ENABLED", True)
    except RuntimeError:
        ai_enabled = True
    
    ai_status = {
        "ai_enabled": ai_enabled,
        "openai_configured": bool(openai_key and len(openai_key) > 5),
        "gemini_configured": bool(gemini_key and len(gemini_key) > 5),
        "status": "Active (Local ATS & Rule-based AI Engine + LLM fallback)"
    }

    return {
        "env": env_status,
        "database": db_status,
        "storage": storage_status,
        "email": email_status,
        "ai": ai_status
    }
