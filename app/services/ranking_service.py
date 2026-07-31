"""Rank candidates per job by ATS score."""

from app.extensions import db
from app.models import Application


def rank_applications_for_job(job_id):
    """
    Assign rank 1..N to all applications for a job ordered by ATS score desc.
    Returns number of applications ranked.
    """
    applications = (
        Application.query.filter_by(job_id=job_id)
        .order_by(Application.ats_score.desc(), Application.applied_at.asc())
        .all()
    )

    for rank, app in enumerate(applications, start=1):
        app.rank = rank

    db.session.commit()
    return len(applications)


def get_ranked_applications(job_id, limit=None):
    """Return applications for a job sorted by rank."""
    query = (
        Application.query.filter_by(job_id=job_id)
        .order_by(Application.rank.asc(), Application.ats_score.desc())
    )
    if limit:
        query = query.limit(limit)
    return query.all()
