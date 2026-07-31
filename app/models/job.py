"""Job posting model."""

from app.extensions import db
from app.models.mixins import TimestampMixin


class Job(db.Model, TimestampMixin):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    department = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    employment_type = db.Column(db.String(50), default="full-time", nullable=False)
    description = db.Column(db.Text, nullable=True)
    requirements = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default="open", nullable=False, index=True)
    # draft | open | closed | archived

    # ATS criteria per job
    min_experience = db.Column(db.Float, default=0.0, nullable=False)
    min_qualification = db.Column(db.String(100), nullable=True)
    # e.g. "Bachelor's", "Master's", "10th", "12th"

    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_by = db.relationship("User", back_populates="jobs")
    required_skills = db.relationship(
        "JobSkill", back_populates="job", cascade="all, delete-orphan"
    )
    applications = db.relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Job {self.title}>"

    @property
    def application_count(self):
        return len(self.applications)

    @property
    def status_label(self):
        return {
            "draft": "Draft",
            "open": "Active",
            "closed": "Closed",
            "archived": "Archived",
        }.get(self.status, self.status.capitalize())
