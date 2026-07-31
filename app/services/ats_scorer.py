"""ATS score calculation for job applications."""

import re
from datetime import datetime, timezone

from app.models import Candidate, Job, JobSkill


# Score weights (must sum to 1.0)
WEIGHT_SKILL = 0.60
WEIGHT_EXPERIENCE = 0.25
WEIGHT_PROFILE = 0.15

EXPERIENCE_YEARS_RE = re.compile(
    r"(\d+)\+?\s*(?:years?|yrs?)", re.IGNORECASE
)


def _candidate_skill_map(candidate):
    """Return {skill_id: confidence} for candidate."""
    return {
        cs.skill_id: cs.confidence
        for cs in candidate.skills
        if cs.skill_id
    }


def _required_experience_years(job):
    """Parse minimum years from job requirements text."""
    title = (job.title or "").lower()
    reqs = (job.requirements or "").lower()

    # Explicitly handle fresher and entry-level roles
    if "fresher" in title or "fresher" in reqs or "entry level" in title or "entry level" in reqs:
        return 0.0

    match = EXPERIENCE_YEARS_RE.search(job.requirements or "")
    if match:
        return float(match.group(1))

    if "senior" in title or "lead" in title or "manager" in title:
        return 5.0
    if "junior" in title or "associate" in title:
        return 1.0
        
    return 2.0


def calculate_skill_match_score(candidate, job):
    """
    Skill Match = (Matched Skills / Required Skills) × 100
    Always between 0.0 and 100.0
    """
    job_skills = JobSkill.query.filter_by(job_id=job.id).all()
    if not job_skills:
        return 0.0

    candidate_skills = {cs.skill_id for cs in candidate.skills if cs.skill_id}
    
    matched_count = sum(1 for js in job_skills if js.skill_id in candidate_skills)
    required_count = len(job_skills)

    if required_count == 0:
        return 0.0

    score = (matched_count / required_count) * 100.0
    return round(min(100.0, score), 1)


def calculate_experience_score(candidate, job):
    """
    Compare candidate years of experience to job requirement.
    Returns 0–100.
    """
    required = _required_experience_years(job)
    years = candidate.years_experience

    # Handling candidates where years of experience wasn't explicitly extracted
    if years is None:
        if candidate.experience or candidate.current_title:
            # They clearly have some experience, but the parser couldn't determine the exact years.
            # Give a moderate assumption based on the job requirements to avoid penalizing them.
            years = min(2.0, required) if required > 0 else 1.0
        else:
            # No experience section found -> Treat as Fresher (0 years)
            years = 0.0

    # If the job explicitly requires 0 years (Fresher role), anyone applying gets full experience match.
    if required == 0.0:
        return 100.0

    # If candidate meets or exceeds the required years
    if years >= required:
        return min(100.0, 80.0 + (years - required) * 10)

    # For candidates with less experience than required (or freshers applying to experienced roles)
    ratio = years / required
    return round(ratio * 80, 1)


def calculate_profile_score(candidate, resume=None):
    """
    Resume completeness bonus.
    Returns 0–100.
    """
    score = 0.0
    if candidate.email:
        score += 25
    if candidate.phone:
        score += 20
    if candidate.summary:
        score += 20
    if candidate.current_title:
        score += 15
    if candidate.linkedin_url:
        score += 10
    if resume and resume.parse_status == "completed" and resume.extracted_text:
        score += 10
    return min(100.0, score)


def calculate_ats_score(candidate, job, resume=None):
    """
    Composite ATS score.
    Returns dict with component scores, matched/missing skills, recommendation, and confidence.
    """
    # ── Scores ──
    skill_match = calculate_skill_match_score(candidate, job)
    experience = calculate_experience_score(candidate, job)
    profile = calculate_profile_score(candidate, resume)

    ats = (
        skill_match * WEIGHT_SKILL
        + experience * WEIGHT_EXPERIENCE
        + profile * WEIGHT_PROFILE
    )
    ats = round(ats, 1)

    # ── Skills Analysis ──
    job_skills = JobSkill.query.filter_by(job_id=job.id).all()
    candidate_skills_set = {cs.skill_id for cs in candidate.skills if cs.skill_id}
    
    matched_skills = []
    missing_skills = []
    for js in job_skills:
        if js.skill_id in candidate_skills_set:
            matched_skills.append(js.skill.name)
        else:
            missing_skills.append(js.skill.name)
            
    # ── AI Recommendation & Confidence ──
    # Simple logic based on ATS score to mimic AI decision
    if ats >= 75:
        recommendation = "Shortlist"
        confidence = round(ats * 0.95, 1)  # High score -> High confidence in shortlisting
    elif ats >= 40:
        recommendation = "Review"
        confidence = round(50 + (ats - 40), 1)
    else:
        recommendation = "Reject"
        confidence = round((100 - ats) * 0.9, 1)  # Low score -> High confidence in rejecting
        
    if not job_skills:
        recommendation = "Review"
        confidence = 50.0

    return {
        "ats_score": ats,
        "skill_match_score": skill_match,
        "experience_score": experience,
        "profile_score": profile,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "recommendation": recommendation,
        "ai_confidence": min(99.0, confidence),
        "scored_at": datetime.now(timezone.utc),
    }
