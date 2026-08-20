"""Recruitment AI Service Layer for candidate recommendations, comparison, question generation, evaluation, and final recommendation reasoning."""

from app.extensions import db
from app.models import Candidate, Job, Application, InterviewEvaluation
from app.services.ats_scorer import calculate_ats_score
from app.services.duplicate_detector import check_duplicate_candidate


def rank_candidates_for_job(job_id):
    """
    Ranks candidates for a given job using ATS Score, skills, experience, education, and authenticity.
    Returns ordered candidate cards with ranks (🥇 #1, 🥈 #2, 🥉 #3) and "Why recommended" for Rank #1.
    """
    job = db.session.get(Job, job_id)
    if not job:
        return {"job": None, "candidates": []}

    # Fetch candidates applied for this job or all system candidates if no applications exist yet
    applications = Application.query.filter_by(job_id=job.id).all()
    candidate_map = {}

    if applications:
        for app in applications:
            if app.candidate and app.candidate.id not in candidate_map:
                candidate_map[app.candidate.id] = (app.candidate, app)
    else:
        # Fallback to all candidates if job has no explicit applications
        all_candidates = Candidate.query.all()
        for cand in all_candidates:
            candidate_map[cand.id] = (cand, None)

    ranked_list = []
    for cand_id, (cand, app) in candidate_map.items():
        primary_resume = cand.primary_resume
        ats_info = calculate_ats_score(cand, job, primary_resume)

        # Authenticity / Suspicious check
        sus_score = primary_resume.suspicious_score if primary_resume and primary_resume.suspicious_score is not None else 0
        is_suspicious = (primary_resume.is_suspicious if primary_resume else False) or (sus_score > 30)

        # Total skills, experience, education
        skills_count = cand.total_skills_count
        exp_years = cand.years_experience or 0
        edu_count = cand.total_education or (1 if cand.education else 0)

        ranked_list.append({
            "candidate_id": cand.id,
            "application_id": app.id if app else None,
            "full_name": cand.full_name,
            "email": cand.email,
            "phone": cand.phone,
            "current_title": cand.current_title or "Candidate",
            "ats_score": ats_info["ats_score"],
            "skill_match_score": ats_info["skill_match_score"],
            "experience_score": ats_info["experience_score"],
            "matched_skills": ats_info["matched_skills"],
            "missing_skills": ats_info["missing_skills"],
            "recommendation": ats_info["recommendation"],
            "ai_confidence": ats_info["ai_confidence"],
            "skills_count": skills_count,
            "experience_years": exp_years,
            "education_count": edu_count,
            "education_summary": cand.education[:60] if cand.education else "Not Provided",
            "is_suspicious": is_suspicious,
            "suspicious_score": sus_score,
            "status": cand.status,
            "primary_resume_filename": primary_resume.original_filename if primary_resume else None,
        })

    # Sort descending by ATS Score
    ranked_list.sort(key=lambda x: x["ats_score"], reverse=True)

    # Assign Ranks & Badges
    for idx, item in enumerate(ranked_list, start=1):
        item["rank"] = idx
        if idx == 1:
            item["rank_badge"] = "🥇 Rank #1"
            item["rank_class"] = "rank-gold"
            
            # Explicit "Why this candidate is recommended" reasons for Rank #1
            reasons = []
            if item["ats_score"] >= 70:
                reasons.append(f"✔ Highest ATS Score ({item['ats_score']}%)")
            else:
                reasons.append(f"✔ Top ATS Score for position ({item['ats_score']}%)")

            if item["skill_match_score"] >= 60:
                reasons.append(f"✔ Strong Skill Match ({item['skill_match_score']}%)")
            elif item["matched_skills"]:
                reasons.append(f"✔ Key Skills Matched: {', '.join(item['matched_skills'][:3])}")

            if item["experience_years"] > 0:
                reasons.append(f"✔ Required Experience ({item['experience_years']} years)")
            else:
                reasons.append("✔ Relevant Qualifications & Background")

            if item["education_count"] > 0:
                reasons.append("✔ Resume & Education Verified")
            else:
                reasons.append("✔ Profile Verification Passed")

            if not item["is_suspicious"]:
                reasons.append("✔ No suspicious activity detected")
            else:
                reasons.append("⚠️ Requires secondary authenticity review")

            item["why_recommended"] = reasons
        elif idx == 2:
            item["rank_badge"] = "🥈 Rank #2"
            item["rank_class"] = "rank-silver"
        elif idx == 3:
            item["rank_badge"] = "🥉 Rank #3"
            item["rank_class"] = "rank-bronze"
        else:
            item["rank_badge"] = f"Rank #{idx}"
            item["rank_class"] = "rank-standard"

    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "department": job.department,
            "required_skills": [js.skill.name for js in job.required_skills if js.skill] if job.required_skills else [],
        },
        "candidates": ranked_list
    }


def compare_candidates(candidate_ids, job_id=None):
    """
    Compares multiple candidates side-by-side on ATS Score, skills, experience, education, validation, suspicious status, strengths, and missing skills.
    """
    candidates = Candidate.query.filter(Candidate.id.in_(candidate_ids)).all()
    job = db.session.get(Job, int(job_id)) if job_id else None

    comparison_data = []
    for cand in candidates:
        primary_resume = cand.primary_resume
        ats_info = calculate_ats_score(cand, job, primary_resume) if job else {
            "ats_score": 0.0,
            "skill_match_score": 0.0,
            "experience_score": 0.0,
            "matched_skills": [s.skill.name for s in cand.skills[:5]],
            "missing_skills": [],
            "recommendation": "Review"
        }

        # Strengths (Top 5 candidate skills)
        strengths = [cs.skill.name for cs in cand.skills[:5]] if cand.skills else []

        # Missing skills for target job
        missing = ats_info.get("missing_skills", [])

        # Suspicious detection
        sus_score = primary_resume.suspicious_score if primary_resume and primary_resume.suspicious_score is not None else 0
        is_suspicious = (primary_resume.is_suspicious if primary_resume else False) or (sus_score > 30)

        # Existing interview evaluation if any
        eval_record = InterviewEvaluation.query.filter_by(candidate_id=cand.id, job_id=job.id if job else None).order_by(InterviewEvaluation.id.desc()).first()

        comparison_data.append({
            "candidate_id": cand.id,
            "full_name": cand.full_name,
            "current_title": cand.current_title or "Candidate",
            "email": cand.email,
            "phone": cand.phone or "N/A",
            "ats_score": ats_info["ats_score"],
            "skill_match_score": ats_info["skill_match_score"],
            "experience_score": ats_info["experience_score"],
            "skills": [cs.skill.name for cs in cand.skills],
            "skills_count": cand.total_skills_count,
            "experience": f"{cand.years_experience} years" if cand.years_experience else (cand.experience[:80] + "..." if cand.experience else "Not Provided"),
            "education": cand.education[:80] + "..." if cand.education else "Not Provided",
            "education_count": cand.total_education or (1 if cand.education else 0),
            "resume_validation": "Valid Format" if cand.email and cand.phone else "Missing Info",
            "is_suspicious": is_suspicious,
            "suspicious_score": sus_score,
            "suspicious_status": "Flagged" if is_suspicious else "Genuine",
            "strengths": strengths,
            "missing_skills": missing,
            "interview_score": eval_record.interview_score if eval_record else None,
            "final_recommendation": eval_record.final_recommendation if eval_record else None,
        })

    return {
        "job_title": job.title if job else "General Comparison",
        "candidates": comparison_data
    }


def generate_recruitment_questions(candidate, job=None):
    """
    Generates dynamic interview questions tailored to candidate's skills, experience, projects, and target job.
    """
    job_title = job.title if job else (candidate.current_title or "Software Developer")
    cand_skills = [cs.skill.name for cs in candidate.skills] if candidate.skills else ["Python", "Problem Solving", "Communication"]
    
    # 1. Technical Questions
    tech_qs = []
    primary_skill = cand_skills[0] if cand_skills else "Core Domain"
    secondary_skill = cand_skills[1] if len(cand_skills) > 1 else "Database/Architecture"
    tertiary_skill = cand_skills[2] if len(cand_skills) > 2 else "Software Development"

    tech_qs.append({
        "question": f"Can you explain your experience working with {primary_skill} in your recent projects for a {job_title} role?",
        "focus": f"Core Expertise ({primary_skill})"
    })
    tech_qs.append({
        "question": f"How do you approach debugging and performance optimization when using {secondary_skill} in a production environment?",
        "focus": f"Troubleshooting & Performance ({secondary_skill})"
    })
    tech_qs.append({
        "question": f"Walk us through how you would architect a scalable system integration utilizing {tertiary_skill}.",
        "focus": f"System Design ({tertiary_skill})"
    })
    if (candidate.total_projects or 0) > 0:
        tech_qs.append({
            "question": f"Describe the most technically challenging project you have delivered. What key design decisions did you make?",
            "focus": "Hands-on Technical Leadership"
        })

    # 2. HR & Behavioral Questions
    hr_qs = []
    hr_qs.append({
        "question": f"What attracted you to apply for the {job_title} position at our company?",
        "focus": "Role Alignment & Motivation"
    })
    hr_qs.append({
        "question": "Tell us about a time when you had to manage tight project deadlines or changing requirements. How did you prioritize tasks?",
        "focus": "Adaptability & Time Management"
    })
    hr_qs.append({
        "question": "Describe a scenario where you had a disagreement with a team member or stakeholder on technical architecture. How was it resolved?",
        "focus": "Conflict Resolution & Collaboration"
    })

    # 3. Scenario-Based Questions
    scenario_qs = []
    scenario_qs.append({
        "question": f"If a critical service fails in production during high-traffic hours, what step-by-step process do you take as a {job_title}?",
        "focus": "Production Incident Management"
    })
    scenario_qs.append({
        "question": f"Suppose you are tasked with implementing {primary_skill} for a legacy system without test coverage. How would you ensure safety and zero downtime?",
        "focus": "Risk Mitigation & Code Safety"
    })
    scenario_qs.append({
        "question": "If you are assigned two high-priority tasks simultaneously by different managers, how do you handle stakeholder communication?",
        "focus": "Stakeholder & Expectation Management"
    })

    return {
        "candidate_id": candidate.id,
        "candidate_name": candidate.full_name,
        "role_title": job_title,
        "technical": tech_qs,
        "hr": hr_qs,
        "scenario": scenario_qs,
    }


def save_interview_evaluation(candidate_id, job_id, ratings, comments=None):
    """
    Saves HR interview evaluation ratings, calculates Interview Score, and computes Final Recommendation with rationale.
    ratings dictionary expected:
    - technical_knowledge (1-5)
    - communication (1-5)
    - problem_solving (1-5)
    - confidence (1-5)
    - cultural_fit (1-5)
    """
    candidate = db.get_or_404(Candidate, candidate_id)
    job = db.get_or_404(Job, job_id)

    tech = float(ratings.get("technical_knowledge", 3.0))
    comm = float(ratings.get("communication", 3.0))
    prob = float(ratings.get("problem_solving", 3.0))
    conf = float(ratings.get("confidence", 3.0))
    fit  = float(ratings.get("cultural_fit", 3.0))

    # Weighted calculation (Scale 1-5 converted to percentage 0-100)
    # Weights: Tech (25%), Comm (20%), Problem Solving (25%), Confidence (15%), Fit (15%)
    weighted_rating = (tech * 0.25) + (comm * 0.20) + (prob * 0.25) + (conf * 0.15) + (fit * 0.15)
    interview_score = round((weighted_rating / 5.0) * 100, 1)

    # Fetch candidate's ATS Score for this job
    primary_resume = candidate.primary_resume
    ats_info = calculate_ats_score(candidate, job, primary_resume)
    ats_score = ats_info["ats_score"]

    # Composite Score = 40% ATS Score + 60% Interview Score
    composite_score = round((ats_score * 0.4) + (interview_score * 0.6), 1)

    # Authenticity check
    sus_score = primary_resume.suspicious_score if primary_resume and primary_resume.suspicious_score is not None else 0

    # Final Recommendation Logic (Hire | Hold | Reject)
    if composite_score >= 75.0 and sus_score <= 30:
        recommendation = "Hire"
        reason = (f"Candidate demonstrated strong overall performance with an Interview Score of {interview_score}% "
                  f"and ATS Score of {ats_score}%. Passed all authenticity and skill matching checks.")
    elif composite_score >= 55.0:
        recommendation = "Hold"
        reason = (f"Candidate shows good potential with a Composite Score of {composite_score}%. "
                  f"Recommended for second-round review or backup pool.")
    else:
        recommendation = "Reject"
        reason = (f"Candidate did not meet the required threshold for this role (Composite Score: {composite_score}%). "
                  f"Interview Score: {interview_score}%, ATS Score: {ats_score}%.")

    # Check for existing evaluation or create new
    eval_record = InterviewEvaluation.query.filter_by(
        candidate_id=candidate.id, job_id=job.id
    ).first()

    if not eval_record:
        eval_record = InterviewEvaluation(
            candidate_id=candidate.id,
            job_id=job.id,
        )
        db.session.add(eval_record)

    eval_record.technical_knowledge = tech
    eval_record.communication = comm
    eval_record.problem_solving = prob
    eval_record.confidence = conf
    eval_record.cultural_fit = fit
    eval_record.overall_comments = comments or ""
    eval_record.interview_score = interview_score
    eval_record.final_recommendation = recommendation
    eval_record.recommendation_reason = reason

    db.session.commit()

    return {
        "evaluation_id": eval_record.id,
        "candidate_id": candidate.id,
        "job_id": job.id,
        "interview_score": interview_score,
        "composite_score": composite_score,
        "ats_score": ats_score,
        "final_recommendation": recommendation,
        "recommendation_reason": reason,
    }


def generate_final_recommendation(candidate_id, job_id):
    """
    Generates a consolidated Final Recommendation summary merging ATS score, interview evaluation, skill match, and authenticity checks.
    """
    candidate = db.get_or_404(Candidate, candidate_id)
    job = db.get_or_404(Job, job_id)
    primary_resume = candidate.primary_resume

    ats_info = calculate_ats_score(candidate, job, primary_resume)
    eval_record = InterviewEvaluation.query.filter_by(candidate_id=candidate.id, job_id=job.id).first()

    interview_score = eval_record.interview_score if eval_record else None
    recommendation = eval_record.final_recommendation if eval_record else (
        "Hire" if ats_info["ats_score"] >= 75 else ("Hold" if ats_info["ats_score"] >= 50 else "Reject")
    )
    reason = eval_record.recommendation_reason if eval_record else (
        f"Based on ATS Score of {ats_info['ats_score']}% and Skill Match of {ats_info['skill_match_score']}%. Interview pending."
    )

    return {
        "candidate_name": candidate.full_name,
        "job_title": job.title,
        "ats_score": ats_info["ats_score"],
        "skill_match_score": ats_info["skill_match_score"],
        "interview_score": interview_score,
        "final_recommendation": recommendation,
        "recommendation_reason": reason,
        "evaluated": eval_record is not None,
    }
