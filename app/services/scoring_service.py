"""Orchestrate skill extraction, ATS scoring, and ranking."""

from flask import current_app

from app.extensions import db
from app.models import Application, Candidate, CandidateSkill, Job, Resume, Skill
from app.services.ats_scorer import calculate_ats_score
from app.services.ranking_service import rank_applications_for_job
from app.services.skill_extractor import extract_skills_from_text, extract_skills_with_ai


def _get_or_create_skill(name, category="technical"):
    skill = Skill.query.filter_by(name=name).first()
    if not skill:
        skill = Skill(name=name, category=category)
        db.session.add(skill)
        db.session.flush()
    return skill


def persist_candidate_skills(candidate_id, text, source="extracted"):
    """
    Extract skills from text and save to candidate_skills.
    Replaces prior skills from the same source.
    Returns list of skill names found.
    """
    candidate = db.session.get(Candidate, candidate_id)
    if not candidate:
        return []

    extracted = extract_skills_from_text(text)

    ai_skills = extract_skills_with_ai(text)
    if ai_skills:
        extracted.extend(ai_skills)

    CandidateSkill.query.filter_by(
        candidate_id=candidate_id, source=source
    ).delete()

    skill_names = []
    for item in extracted:
        skill = (
            db.session.get(Skill, item["skill_id"])
            if item.get("skill_id")
            else _get_or_create_skill(item["name"], item.get("category", "technical"))
        )

        existing = CandidateSkill.query.filter_by(
            candidate_id=candidate_id, skill_id=skill.id
        ).first()

        if existing:
            existing.confidence = item["confidence"]
            existing.source = source
        else:
            db.session.add(
                CandidateSkill(
                    candidate_id=candidate_id,
                    skill_id=skill.id,
                    confidence=item["confidence"],
                    source=source,
                )
            )
        skill_names.append(skill.name)

    db.session.flush()
    return skill_names


def score_application(application_id, resume=None):
    """
    Calculate ATS scores for a single application and persist.
    Returns score dict or None.
    """
    application = db.session.get(Application, application_id)
    if not application:
        return None

    candidate = application.candidate
    job = application.job

    if resume is None:
        resume = candidate.primary_resume

    scores = calculate_ats_score(candidate, job, resume)
    application.ats_score = scores["ats_score"]
    application.skill_match_score = scores["skill_match_score"]
    application.experience_score = scores["experience_score"]
    application.scored_at = scores["scored_at"]

    if scores["ats_score"] >= 75 and application.status == "applied":
        application.status = "screening"
        if candidate.status == "new":
            candidate.status = "reviewing"

    db.session.flush()
    return scores


def score_candidate_for_job(candidate_id, job_id, text=None, resume=None):
    """
    Full pipeline: extract skills, score application, rank job applicants.
    Returns result dict.
    """
    candidate = db.session.get(Candidate, candidate_id)
    job = db.session.get(Job, job_id)
    if not candidate or not job:
        return {"success": False, "error": "Candidate or job not found."}

    if text is None and resume and resume.extracted_text:
        text = resume.extracted_text
    elif text is None and candidate.primary_resume:
        text = candidate.primary_resume.extracted_text or ""

    skill_names = persist_candidate_skills(candidate_id, text or "")

    application = Application.query.filter_by(
        candidate_id=candidate_id, job_id=job_id
    ).first()

    if not application:
        application = Application(
            candidate_id=candidate_id,
            job_id=job_id,
            status="applied",
        )
        db.session.add(application)
        db.session.flush()

    scores = score_application(application.id, resume=resume)
    rank_applications_for_job(job_id)

    db.session.commit()

    return {
        "success": True,
        "candidate_id": candidate_id,
        "job_id": job_id,
        "application_id": application.id,
        "skills": skill_names,
        "ats_score": scores["ats_score"] if scores else 0,
        "skill_match_score": scores["skill_match_score"] if scores else 0,
        "experience_score": scores["experience_score"] if scores else 0,
        "rank": application.rank,
    }


def score_all_applications():
    """Re-score every application in the database."""
    applications = Application.query.all()
    count = 0
    job_ids = set()

    for app in applications:
        score_application(app.id)
        job_ids.add(app.job_id)
        count += 1

    for job_id in job_ids:
        rank_applications_for_job(job_id)

    db.session.commit()
    return count


def extract_and_score_after_upload(candidate_id, job_id=None, text=None, resume=None):
    """
    Called after resume upload — extract skills; score and rank if job linked.
    """
    text_content = text or (resume.extracted_text if resume else "") or ""

    if job_id:
        return score_candidate_for_job(
            candidate_id, job_id, text=text_content, resume=resume
        )

    skill_names = persist_candidate_skills(candidate_id, text_content)
    db.session.commit()
    return {"skills": skill_names}
