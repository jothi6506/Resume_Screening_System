"""Job application with ATS scoring and ranking."""

from datetime import datetime, timezone

from app.extensions import db


class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(
        db.Integer, db.ForeignKey("candidates.id"), nullable=False, index=True
    )
    job_id = db.Column(
        db.Integer, db.ForeignKey("jobs.id"), nullable=False, index=True
    )
    ats_score = db.Column(db.Float, default=0.0, nullable=False, index=True)
    skill_match_score = db.Column(db.Float, default=0.0, nullable=False)
    experience_score = db.Column(db.Float, default=0.0, nullable=False)
    rank = db.Column(db.Integer, nullable=True, index=True)
    status = db.Column(db.String(30), default="new", nullable=False)
    # new | reviewing | shortlisted | hired | rejected
    notes = db.Column(db.Text, nullable=True)
    applied_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    scored_at = db.Column(db.DateTime, nullable=True)

    candidate = db.relationship("Candidate", back_populates="applications")
    job = db.relationship("Job", back_populates="applications")

    __table_args__ = (
        db.UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job"),
    )

    def __repr__(self):
        return f"<Application candidate={self.candidate_id} job={self.job_id}>"
