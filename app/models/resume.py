"""Uploaded resume file model."""

import json
from datetime import datetime, timezone

from app.extensions import db


class Resume(db.Model):
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(
        db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True
    )
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=True)
    file_type = db.Column(db.String(20), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    parse_status = db.Column(db.String(30), default="pending", nullable=False)
    # pending | processing | completed | failed
    parse_error = db.Column(db.String(500), nullable=True)
    uploaded_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Authenticity / Fake-resume detection
    authenticity_score = db.Column(db.Integer, nullable=True)        # 0–100
    authenticity_report = db.Column(db.Text, nullable=True)          # JSON blob
    is_suspicious = db.Column(db.Boolean, default=False, nullable=False)

    candidate = db.relationship("Candidate", back_populates="resumes")

    @property
    def authenticity_report_dict(self):
        if self.authenticity_report:
            try:
                return json.loads(self.authenticity_report)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @property
    def risk_level(self):
        if self.authenticity_score is None:
            return "unknown"
        if self.authenticity_score >= 70:
            return "low"
        if self.authenticity_score >= 45:
            return "medium"
        return "high"

    @property
    def suspicious_score(self):
        """Get suspicious score directly from authenticity report."""
        report = self.authenticity_report_dict
        if report and "suspicious_score" in report:
            return report.get("suspicious_score", 0)
        if report:
            return 0
        return None

    @property
    def classification(self):
        """Get classification based on suspicious score."""
        score = self.suspicious_score
        if score is None:
            return "unknown"
        if score <= 24:
            return "Genuine"
        elif score <= 49:
            return "Needs Review"
        else:
            return "Suspicious"

    def __repr__(self):
        return f"<Resume {self.original_filename}>"
