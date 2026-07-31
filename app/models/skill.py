"""Skill models and association tables."""

from app.extensions import db
from app.models.mixins import TimestampMixin


class Skill(db.Model, TimestampMixin):
    __tablename__ = "skills"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    category = db.Column(db.String(50), default="technical", nullable=False)
    # technical | soft | tool | language

    job_requirements = db.relationship(
        "JobSkill", back_populates="skill", cascade="all, delete-orphan"
    )
    candidate_skills = db.relationship(
        "CandidateSkill", back_populates="skill", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Skill {self.name}>"


class JobSkill(db.Model):
    """Required/preferred skills for a job posting."""

    __tablename__ = "job_skills"

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False)
    is_required = db.Column(db.Boolean, default=True, nullable=False)
    weight = db.Column(db.Float, default=1.0, nullable=False)

    job = db.relationship("Job", back_populates="required_skills")
    skill = db.relationship("Skill", back_populates="job_requirements")

    __table_args__ = (
        db.UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),
    )


class CandidateSkill(db.Model):
    """Skills extracted from or assigned to a candidate."""

    __tablename__ = "candidate_skills"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(
        db.Integer, db.ForeignKey("candidates.id"), nullable=False
    )
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False)
    confidence = db.Column(db.Float, default=0.0, nullable=False)
    source = db.Column(db.String(30), default="extracted", nullable=False)
    # extracted | manual | ai

    candidate = db.relationship("Candidate", back_populates="skills")
    skill = db.relationship("Skill", back_populates="candidate_skills")

    __table_args__ = (
        db.UniqueConstraint("candidate_id", "skill_id", name="uq_candidate_skill"),
    )
