"""Interview evaluation model for Recruitment AI module."""

from datetime import datetime, timezone
from app.extensions import db


class InterviewEvaluation(db.Model):
    __tablename__ = "interview_evaluations"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(
        db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True
    )
    job_id = db.Column(
        db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True
    )
    application_id = db.Column(
        db.Integer, db.ForeignKey("applications.id"), nullable=True, index=True
    )

    # 1-5 or 1-10 Ratings
    technical_knowledge = db.Column(db.Float, default=0.0, nullable=False)
    communication = db.Column(db.Float, default=0.0, nullable=False)
    problem_solving = db.Column(db.Float, default=0.0, nullable=False)
    confidence = db.Column(db.Float, default=0.0, nullable=False)
    cultural_fit = db.Column(db.Float, default=0.0, nullable=False)

    overall_comments = db.Column(db.Text, nullable=True)
    interview_score = db.Column(db.Float, default=0.0, nullable=False)  # 0 - 100 %
    final_recommendation = db.Column(db.String(20), default="Hold", nullable=False)  # Hire | Hold | Reject
    recommendation_reason = db.Column(db.Text, nullable=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    candidate = db.relationship("Candidate", backref=db.backref("evaluations", cascade="all, delete-orphan"))
    job = db.relationship("Job", backref=db.backref("evaluations", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "application_id": self.application_id,
            "technical_knowledge": self.technical_knowledge,
            "communication": self.communication,
            "problem_solving": self.problem_solving,
            "confidence": self.confidence,
            "cultural_fit": self.cultural_fit,
            "overall_comments": self.overall_comments,
            "interview_score": self.interview_score,
            "final_recommendation": self.final_recommendation,
            "recommendation_reason": self.recommendation_reason,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M") if self.created_at else None,
        }

    def __repr__(self):
        return f"<InterviewEvaluation candidate={self.candidate_id} job={self.job_id} score={self.interview_score}>"
