"""Dashboard statistics helpers."""

from sqlalchemy import func

from app.extensions import db
from app.models import Application, Candidate, Job, Resume


def get_dashboard_stats():
    """Aggregate KPIs for the main dashboard."""
    total_candidates = db.session.scalar(
        db.select(func.count()).select_from(Candidate)
    ) or 0

    # Job counts by status
    job_status_rows = db.session.execute(
        db.select(Job.status, func.count()).group_by(Job.status)
    ).all()
    job_status_map = dict(job_status_rows)

    total_jobs = sum(job_status_map.values())
    active_jobs = job_status_map.get("open", 0)
    draft_jobs = job_status_map.get("draft", 0)
    closed_jobs = job_status_map.get("closed", 0)
    archived_jobs = job_status_map.get("archived", 0)

    total_resumes = db.session.scalar(
        db.select(func.count()).select_from(Resume)
    ) or 0

    suspicious_resumes = db.session.scalar(
        db.select(func.count()).select_from(Resume).where(Resume.is_suspicious == True)
    ) or 0

    avg_ats_score = db.session.scalar(
        db.select(func.avg(Application.ats_score))
    ) or 0

    shortlisted = db.session.scalar(
        db.select(func.count())
        .select_from(Application)
        .where(Application.status == "shortlisted")
    ) or 0

    rejected = db.session.scalar(
        db.select(func.count())
        .select_from(Application)
        .where(Application.status == "rejected")
    ) or 0

    total_applicants = db.session.scalar(
        db.select(func.count()).select_from(Application)
    ) or 0

    pipeline = {
        "new": db.session.scalar(
            db.select(func.count())
            .select_from(Application)
            .where(db.or_(Application.status == "new", Application.status == "applied"))
        )
        or 0,
        "reviewing": db.session.scalar(
            db.select(func.count())
            .select_from(Application)
            .where(Application.status == "reviewing")
        )
        or 0,
        "shortlisted": shortlisted,
        "rejected": rejected,
        "hired": db.session.scalar(
            db.select(func.count())
            .select_from(Application)
            .where(db.or_(Application.status == "hired", Application.status == "offer"))
        )
        or 0,
    }

    recent_jobs = (
        db.session.execute(
            db.select(Job).where(Job.status == "open").order_by(Job.created_at.desc()).limit(5)
        )
        .scalars()
        .all()
    )

    return {
        "total_candidates": total_candidates,
        # Job stats
        "total_jobs": total_jobs,
        "open_jobs": active_jobs,    # alias kept for backward compat
        "active_jobs": active_jobs,
        "draft_jobs": draft_jobs,
        "closed_jobs": closed_jobs,
        "archived_jobs": archived_jobs,
        # Resume stats
        "total_resumes": total_resumes,
        "suspicious_resumes": suspicious_resumes,
        # Candidate pipeline
        "total_applicants": total_applicants,
        "shortlisted": shortlisted,
        "rejected": rejected,
        "avg_ats_score": round(float(avg_ats_score), 1),
        "pipeline": pipeline,
        "recent_jobs": recent_jobs,
    }
