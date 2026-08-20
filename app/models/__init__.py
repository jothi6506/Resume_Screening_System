"""SQLAlchemy models — import all models for migrations."""

from app.models.application import Application
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.resume import Resume
from app.models.skill import CandidateSkill, JobSkill, Skill
from app.models.user import User
from app.models.email import EmailHistory, EmailSettings
from app.models.activity import ActivityLog
from app.models.interview_evaluation import InterviewEvaluation

__all__ = [
    "User",
    "Job",
    "Candidate",
    "Resume",
    "Skill",
    "JobSkill",
    "CandidateSkill",
    "Application",
    "EmailHistory",
    "EmailSettings",
    "ActivityLog",
    "InterviewEvaluation",
]
