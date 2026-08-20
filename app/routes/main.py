"""Main application routes."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app.extensions import db
from app.forms.job import JOB_TEMPLATES, JobForm
from app.models import Application, Candidate, CandidateSkill, Job, JobSkill, Resume, Skill
from app.models.activity import log_activity
from app.utils.dashboard import get_dashboard_stats

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("landing.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    stats = get_dashboard_stats()
    return render_template("dashboard/index.html", stats=stats, active_nav="dashboard")


# ── Candidates ───────────────────────────────────────────────────────────────


@main_bp.route("/candidates")
@login_required
def candidates():
    status_filter = request.args.get("status", "all")
    search_query = request.args.get("q", "").strip()

    query = db.select(Application).join(Candidate).join(Job).order_by(Application.applied_at.desc())

    if status_filter == "suspicious":
        # Filter applications where candidate has at least one suspicious resume
        query = query.join(Resume, Resume.candidate_id == Candidate.id)\
                     .where(Resume.is_suspicious == True)
    elif status_filter and status_filter != "all":
        # Handle backward compatibility with old status strings
        if status_filter == "new":
            query = query.where(db.or_(Application.status == "new", Application.status == "applied"))
        elif status_filter == "hired":
            query = query.where(db.or_(Application.status == "hired", Application.status == "offer"))
        else:
            query = query.where(Application.status == status_filter)

    if search_query:
        like_pattern = f"%{search_query}%"
        search_id = int(search_query) if search_query.isdigit() else None
        
        if status_filter != "suspicious":
            query = query.outerjoin(Resume, Resume.candidate_id == Candidate.id)
            
        query = query.where(
            db.or_(
                Candidate.full_name.ilike(like_pattern),
                Candidate.email.ilike(like_pattern),
                Candidate.current_title.ilike(like_pattern),
                Candidate.phone.ilike(like_pattern),
                Candidate.location.ilike(like_pattern),
                Candidate.technical_skills.ilike(like_pattern),
                Job.title.ilike(like_pattern),
                Resume.id == search_id if search_id else False
            )
        )
        
    query = query.distinct()

    applications_list = db.session.execute(query).scalars().all()

    # Status counts for filter badges (Count of Applications by Application status)
    status_counts_db = dict(
        db.session.execute(
            db.select(Application.status, func.count(Application.id.distinct()))
            .group_by(Application.status)
        ).all()
    )
    
    status_counts = {
        "all": sum(status_counts_db.values()),
        "new": status_counts_db.get("new", 0) + status_counts_db.get("applied", 0),
        "reviewing": status_counts_db.get("reviewing", 0),
        "shortlisted": status_counts_db.get("shortlisted", 0),
        "rejected": status_counts_db.get("rejected", 0),
        "hired": status_counts_db.get("hired", 0) + status_counts_db.get("offer", 0)
    }

    # Suspicious count: applications where candidate has at least one suspicious resume
    suspicious_count = db.session.scalar(
        db.select(func.count(Application.id.distinct()))
        .select_from(Application)
        .join(Candidate)
        .join(Resume, Resume.candidate_id == Candidate.id)
        .where(Resume.is_suspicious == True)
    ) or 0
    status_counts["suspicious"] = suspicious_count

    return render_template(
        "candidates/index.html",
        applications=applications_list,
        status_filter=status_filter,
        search_query=search_query,
        status_counts=status_counts,
        active_nav="candidates",
    )


@main_bp.route("/candidates/<int:candidate_id>")
@login_required
def candidate_detail(candidate_id):
    candidate = db.get_or_404(Candidate, candidate_id)
    
    # Pre-calculate AI predictions for applications
    from app.services.ats_scorer import calculate_ats_score
    predictions = {}
    for app in candidate.applications:
        scores = calculate_ats_score(candidate, app.job, candidate.primary_resume)
        predictions[app.id] = scores

    # Check for possible duplicate candidate
    from app.services.duplicate_detector import check_duplicate_candidate
    primary_resume = candidate.primary_resume
    duplicate_info = check_duplicate_candidate(
        email=candidate.email,
        phone=candidate.phone,
        extracted_text=primary_resume.extracted_text if primary_resume else None,
        candidate_id=candidate.id
    )

    return render_template(
        "candidates/detail.html",
        candidate=candidate,
        predictions=predictions,
        duplicate_info=duplicate_info,
        active_nav="candidates",
    )


@main_bp.route("/applications/<int:app_id>/status", methods=["POST"])
@login_required
def update_application_status(app_id):
    from app.services.email_service import send_status_email
    
    application = db.get_or_404(Application, app_id)
    candidate = application.candidate
    new_status = request.form.get("status")
    
    valid = {"new", "reviewing", "shortlisted", "rejected", "hired"}
    if new_status in valid:
        application.status = new_status
        # Keep candidate global status in sync with the most recent action
        candidate.status = new_status
        db.session.commit()
        log_activity(f"Application {new_status.title()}", f"Application for '{candidate.full_name}' to '{application.job.title}' changed to {new_status.title()}")
        
        # Auto-send email for shortlisted, hired (selected), and rejected
        email_statuses = {"shortlisted", "hired", "rejected"}
        if new_status in email_statuses and candidate.email:
            success, result = send_status_email(candidate, new_status, application.job)
            if success:
                flash(f"Status updated to '{new_status}' — email sent to {candidate.email}.", "success")
            else:
                flash(f"Status updated to '{new_status}', but email failed to send.", "warning")
        else:
            flash(f"Status updated to '{new_status}'.", "success")
            
    return redirect(url_for("main.candidate_detail", candidate_id=candidate.id))

@main_bp.route("/candidates/<int:candidate_id>/status_action", methods=["POST"])
@login_required
def update_candidate_status_action(candidate_id):
    app_id = request.form.get("app_id")
    if not app_id:
        flash("Please select a job application to update.", "warning")
        return redirect(url_for("main.candidate_detail", candidate_id=candidate_id))
    return update_application_status(app_id)

@main_bp.route("/candidates/<int:candidate_id>/send_custom_email", methods=["POST"])
@login_required
def send_custom_email(candidate_id):
    from app.services.email_service import send_email
    
    candidate = db.get_or_404(Candidate, candidate_id)
    subject = request.form.get("subject")
    body = request.form.get("body")
    
    if candidate.email and subject and body:
        success, _ = send_email(candidate.email, subject, body, candidate.full_name, candidate.id)
        if success:
            flash("Email sent successfully.", "success")
        else:
            flash("Failed to send email.", "danger")
    else:
        flash("Missing email address, subject, or body.", "warning")
        
    return redirect(url_for("main.candidate_detail", candidate_id=candidate_id))


@main_bp.route("/candidates/<int:candidate_id>/delete", methods=["POST"])
@login_required
def delete_candidate(candidate_id):
    """Delete a candidate and all associated data including resume files."""
    from app.services.storage_service import get_storage_service

    candidate = db.get_or_404(Candidate, candidate_id)
    candidate_name = candidate.full_name

    storage = get_storage_service()
    for resume in candidate.resumes:
        if resume.stored_filename:
            storage.delete_file(resume.stored_filename)

    # SQLAlchemy cascade will remove: resumes, skills, applications
    db.session.delete(candidate)
    db.session.commit()
    log_activity("Candidate Deleted", f"Candidate '{candidate_name}' deleted")

    flash(f"Candidate '{candidate_name}' and all associated data have been deleted.", "success")
    return redirect(url_for("main.candidates"))



# ── Jobs ─────────────────────────────────────────────────────────────────────


@main_bp.route("/jobs")
@login_required
def jobs():
    query = db.select(Job).order_by(Job.created_at.desc())
    jobs_list = db.session.execute(query).scalars().all()

    status_counts = dict(
        db.session.execute(
            db.select(Job.status, func.count()).group_by(Job.status)
        ).all()
    )
    status_counts["all"] = sum(status_counts.values())

    return render_template(
        "jobs/index.html",
        jobs=jobs_list,
        status_filter=request.args.get("status", "all"),
        status_counts=status_counts,
        active_nav="jobs",
    )


@main_bp.route("/jobs/new", methods=["GET", "POST"])
@login_required
def job_new():
    form = JobForm()
    template_name = request.args.get("template", "")
    prefill = JOB_TEMPLATES.get(template_name, {})

    if form.validate_on_submit():
        job = Job(
            title=form.title.data.strip(),
            department=form.department.data.strip() if form.department.data else None,
            location=form.location.data.strip() if form.location.data else None,
            employment_type=form.employment_type.data,
            status=form.status.data,
            min_experience=form.min_experience.data or 0.0,
            min_qualification=form.min_qualification.data or None,
            description=form.description.data.strip() if form.description.data else None,
            requirements=form.requirements.data.strip() if form.requirements.data else None,
            created_by_id=current_user.id,
        )
        db.session.add(job)
        db.session.flush()

        # Process required skills
        skills_text = form.required_skills_text.data or ""
        _attach_skills_to_job(job, skills_text)

        db.session.commit()
        log_activity("Job Created", f"Job '{job.title}' created")
        flash(f"Job '{job.title}' created successfully.", "success")
        return redirect(url_for("main.job_detail", job_id=job.id))

    # Pre-fill from template
    if prefill and request.method == "GET":
        form.title.data = template_name
        form.description.data = prefill.get("description", "")
        form.requirements.data = prefill.get("requirements", "")
        form.min_experience.data = prefill.get("min_experience", 0.0)
        form.min_qualification.data = prefill.get("min_qualification", "")
        form.required_skills_text.data = ", ".join(prefill.get("skills", []))

    return render_template(
        "jobs/form.html",
        form=form,
        job=None,
        templates=list(JOB_TEMPLATES.keys()),
        active_nav="jobs",
    )


@main_bp.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
@login_required
def job_edit(job_id):
    job = db.get_or_404(Job, job_id)
    form = JobForm(obj=job)

    if form.validate_on_submit():
        job.title = form.title.data.strip()
        job.department = form.department.data.strip() if form.department.data else None
        job.location = form.location.data.strip() if form.location.data else None
        job.employment_type = form.employment_type.data
        job.status = form.status.data
        job.min_experience = form.min_experience.data or 0.0
        job.min_qualification = form.min_qualification.data or None
        job.description = form.description.data.strip() if form.description.data else None
        job.requirements = form.requirements.data.strip() if form.requirements.data else None

        # Replace skills
        for js in list(job.required_skills):
            db.session.delete(js)
        db.session.flush()
        skills_text = form.required_skills_text.data or ""
        _attach_skills_to_job(job, skills_text)

        db.session.commit()
        log_activity("Job Updated", f"Job '{job.title}' updated")
        flash(f"Job '{job.title}' updated successfully.", "success")
        return redirect(url_for("main.job_detail", job_id=job.id))

    # Pre-fill skills text on GET
    if request.method == "GET":
        form.required_skills_text.data = ", ".join(
            js.skill.name for js in job.required_skills
        )

    return render_template(
        "jobs/form.html",
        form=form,
        job=job,
        templates=list(JOB_TEMPLATES.keys()),
        active_nav="jobs",
    )


@main_bp.route("/jobs/<int:job_id>/status", methods=["POST"])
@login_required
def job_update_status(job_id):
    job = db.get_or_404(Job, job_id)
    new_status = request.form.get("status")
    valid = {"draft", "open", "closed", "archived"}
    if new_status in valid:
        job.status = new_status
        db.session.commit()
        log_activity(f"Job {new_status.title()}", f"Job '{job.title}' status changed to {new_status.title()}")
        flash(f"Job status updated to '{new_status}'.", "success")
    else:
        flash("Invalid status.", "danger")
    return redirect(url_for("main.job_detail", job_id=job_id))


@main_bp.route("/jobs/<int:job_id>/delete", methods=["POST"])
@login_required
def job_delete(job_id):
    job = db.get_or_404(Job, job_id)
    title = job.title
    db.session.delete(job)
    db.session.commit()
    log_activity("Job Deleted", f"Job '{title}' deleted")
    flash(f"Job '{title}' deleted.", "warning")
    return redirect(url_for("main.jobs"))


@main_bp.route("/jobs/<int:job_id>")
@login_required
def job_detail(job_id):
    job = db.get_or_404(Job, job_id)
    status_filter = request.args.get("status", "all")

    # Base query for applications linked to this job
    query = db.select(Application).where(Application.job_id == job_id)
    
    if status_filter != "all":
        query = query.join(Candidate, Application.candidate_id == Candidate.id)\
                     .where(Candidate.status == status_filter)

    # Applicants ranked by ATS score
    ranked_apps = (
        db.session.execute(query.order_by(Application.ats_score.desc()))
        .scalars()
        .all()
    )
    
    # Calculate counts per status for this job's candidates
    counts_query = db.session.execute(
        db.select(Candidate.status, func.count())\
          .join(Application, Application.candidate_id == Candidate.id)\
          .where(Application.job_id == job_id)\
          .group_by(Candidate.status)
    ).all()
    
    status_counts = dict(counts_query)
    status_counts["all"] = sum(status_counts.values())

    return render_template(
        "jobs/detail.html",
        job=job,
        applications=ranked_apps,
        status_filter=status_filter,
        status_counts=status_counts,
        active_nav="jobs",
    )


def _attach_skills_to_job(job, skills_text: str):
    """Parse a comma-separated skill string and attach them to a job safely."""
    if not skills_text or not skills_text.strip():
        return
    skill_names = [s.strip() for s in skills_text.split(",") if s.strip()]
    added_skill_ids = set()

    for name in skill_names:
        if not name:
            continue
        skill = Skill.query.filter_by(name=name).first()
        if not skill:
            skill = Skill.query.filter(func.lower(Skill.name) == func.lower(name)).first()
        if not skill:
            try:
                with db.session.begin_nested():
                    skill = Skill(name=name, category="technical")
                    db.session.add(skill)
                    db.session.flush()
            except Exception:
                skill = Skill.query.filter(func.lower(Skill.name) == func.lower(name)).first()

        if skill and skill.id not in added_skill_ids:
            added_skill_ids.add(skill.id)
            exists = JobSkill.query.filter_by(job_id=job.id, skill_id=skill.id).first()
            if not exists:
                db.session.add(JobSkill(job_id=job.id, skill_id=skill.id, is_required=True, weight=1.0))



# ── Analytics ────────────────────────────────────────────────────────────────


@main_bp.route("/analytics")
@login_required
def analytics():
    # Pipeline breakdown
    pipeline = dict(
        db.session.execute(
            db.select(Candidate.status, func.count())
            .group_by(Candidate.status)
        ).all()
    )

    # ATS score distribution (buckets: 0-20, 20-40, 40-60, 60-80, 80-100)
    ats_scores = [
        row[0]
        for row in db.session.execute(
            db.select(Application.ats_score)
        ).all()
        if row[0] is not None
    ]

    score_buckets = [0, 0, 0, 0, 0]
    for score in ats_scores:
        idx = min(int(score // 20), 4)
        score_buckets[idx] += 1

    # Top skills (most common among candidates)
    top_skills = (
        db.session.execute(
            db.select(Skill.name, func.count(CandidateSkill.id).label("cnt"))
            .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
            .group_by(Skill.name)
            .order_by(func.count(CandidateSkill.id).desc())
            .limit(10)
        ).all()
    )

    # Summary stats
    total_candidates = db.session.scalar(
        db.select(func.count()).select_from(Candidate)
    ) or 0
    total_applications = db.session.scalar(
        db.select(func.count()).select_from(Application)
    ) or 0
    avg_ats = db.session.scalar(
        db.select(func.avg(Application.ats_score))
    ) or 0
    total_jobs = db.session.scalar(
        db.select(func.count()).select_from(Job)
    ) or 0
    total_resumes = db.session.scalar(
        db.select(func.count()).select_from(Resume)
    ) or 0

    # Top candidate per job
    top_apps = []
    active_jobs = db.session.execute(db.select(Job)).scalars().all()
    for job in active_jobs:
        top_app = db.session.execute(
            db.select(Application)
            .where(Application.job_id == job.id)
            .where(Application.ats_score != None)
            .order_by(Application.ats_score.desc())
            .limit(1)
        ).scalar()
        if top_app:
            top_apps.append(top_app)
    
    # Sort the list by highest score first
    top_apps.sort(key=lambda x: x.ats_score, reverse=True)

    # Recent candidates
    recent_candidates = (
        db.session.execute(
            db.select(Candidate)
            .order_by(Candidate.created_at.desc())
            .limit(8)
        )
        .scalars()
        .all()
    )

    return render_template(
        "analytics/index.html",
        pipeline=pipeline,
        score_buckets=score_buckets,
        top_skills=top_skills,
        total_candidates=total_candidates,
        total_applications=total_applications,
        avg_ats=round(float(avg_ats), 1),
        total_jobs=total_jobs,
        total_resumes=total_resumes,
        top_apps=top_apps,
        recent_candidates=recent_candidates,
        active_nav="analytics",
    )


@main_bp.route("/health")
def health():
    return {"status": "ok", "service": "resume-screening-system"}


# ── APIs for Dashboard & Job Management ──────────────────────────────────────

@main_bp.route("/api/jobs/<int:job_id>", methods=["GET"])
@login_required
def api_job_get(job_id):
    """Return a single job as JSON (for the edit modal)."""
    job = db.get_or_404(Job, job_id)
    skills_text = ", ".join(js.skill.name for js in job.required_skills)
    return {
        "id": job.id,
        "title": job.title,
        "department": job.department or "",
        "location": job.location or "",
        "employment_type": job.employment_type,
        "status": job.status,
        "min_experience": job.min_experience,
        "min_qualification": job.min_qualification or "",
        "description": job.description or "",
        "requirements": job.requirements or "",
        "required_skills_text": skills_text,
        "application_count": job.application_count,
        "status_label": job.status_label,
        "skills": [js.skill.name for js in job.required_skills],
        "created_at": job.created_at.strftime("%b %d, %Y") if job.created_at else "",
    }


@main_bp.route("/api/jobs/<int:job_id>/update", methods=["POST"])
@login_required
def api_job_update(job_id):
    """Update a job via JSON. Called by the edit modal Save button."""
    job = db.get_or_404(Job, job_id)
    data = request.get_json(silent=True) or request.form

    title = (data.get("title") or "").strip()
    if not title:
        return {"success": False, "error": "Job title is required."}, 400

    job.title = title
    job.department = (data.get("department") or "").strip() or None
    job.location = (data.get("location") or "").strip() or None
    job.employment_type = data.get("employment_type") or job.employment_type
    job.status = data.get("status") or job.status
    job.min_experience = float(data.get("min_experience") or 0.0)
    job.min_qualification = (data.get("min_qualification") or "").strip() or None
    job.description = (data.get("description") or "").strip() or None
    job.requirements = (data.get("requirements") or "").strip() or None

    # Replace skills
    for js in list(job.required_skills):
        db.session.delete(js)
    db.session.flush()
    skills_text = (data.get("required_skills_text") or "").strip()
    _attach_skills_to_job(job, skills_text)

    db.session.commit()
    log_activity("Job Updated", f"Job '{job.title}' updated")

    return {
        "success": True,
        "message": f"Job '{job.title}' updated successfully.",
        "job": {
            "id": job.id,
            "title": job.title,
            "department": job.department or "",
            "location": job.location or "",
            "status": job.status,
            "status_label": job.status_label,
            "employment_type": job.employment_type,
            "min_experience": job.min_experience,
            "skills": [js.skill.name for js in job.required_skills],
        }
    }


@main_bp.route("/api/search")
@login_required
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return {"candidates": [], "jobs": []}

    like_pattern = f"%{q}%"
    
    candidates = db.session.execute(
        db.select(Candidate).where(
            db.or_(
                Candidate.full_name.ilike(like_pattern),
                Candidate.email.ilike(like_pattern),
                Candidate.current_title.ilike(like_pattern),
            )
        ).limit(5)
    ).scalars().all()
    
    jobs = db.session.execute(
        db.select(Job).where(
            db.or_(
                Job.title.ilike(like_pattern),
                Job.department.ilike(like_pattern),
                Job.location.ilike(like_pattern),
            )
        ).limit(5)
    ).scalars().all()

    return {
        "candidates": [{"id": c.id, "name": c.full_name, "email": c.email, "title": c.current_title} for c in candidates],
        "jobs": [{"id": j.id, "title": j.title, "department": j.department, "status": j.status} for j in jobs]
    }


@main_bp.route("/api/dashboard-stats")
@login_required
def api_dashboard_stats():
    stats = get_dashboard_stats()
    
    from app.models.activity import ActivityLog
    recent_activities = db.session.execute(
        db.select(ActivityLog).order_by(ActivityLog.timestamp.desc()).limit(10)
    ).scalars().all()
    
    return {
        "total_candidates": stats["total_candidates"],
        "total_applicants": stats["total_applicants"],
        "shortlisted": stats["shortlisted"],
        "rejected": stats["rejected"],
        "total_jobs": stats["total_jobs"],
        "active_jobs": stats["active_jobs"],
        "draft_jobs": stats["draft_jobs"],
        "closed_jobs": stats["closed_jobs"],
        "suspicious_resumes": stats["suspicious_resumes"],
        "pipeline": stats["pipeline"],
        "recent_activities": [
            {
                "action": log.action,
                "description": log.description,
                "timestamp": log.timestamp.strftime("%b %d, %I:%M %p")
            } for log in recent_activities
        ]
    }


@main_bp.route("/api/jobs/<int:job_id>/<action>", methods=["POST"])
@login_required
def api_job_action(job_id, action):
    job = db.get_or_404(Job, job_id)
    title = job.title
    
    if action == "delete":
        db.session.delete(job)
        db.session.commit()
        log_activity("Job Deleted", f"Job '{title}' deleted")
        return {"success": True, "message": f"Job '{title}' deleted."}
        
    elif action == "archive":
        job.status = "archived"
        db.session.commit()
        log_activity("Job Archived", f"Job '{title}' archived")
        return {"success": True, "message": f"Job '{title}' archived."}
        
    elif action == "close":
        job.status = "closed"
        db.session.commit()
        log_activity("Job Closed", f"Job '{title}' closed")
        return {"success": True, "message": f"Job '{title}' closed."}
        
    elif action == "duplicate":
        new_job = Job(
            title=f"{job.title} (Copy)",
            department=job.department,
            location=job.location,
            employment_type=job.employment_type,
            status="draft",
            min_experience=job.min_experience,
            min_qualification=job.min_qualification,
            description=job.description,
            requirements=job.requirements,
            created_by_id=current_user.id,
        )
        db.session.add(new_job)
        db.session.flush()
        for js in job.required_skills:
            db.session.add(JobSkill(job_id=new_job.id, skill_id=js.skill_id, is_required=js.is_required, weight=js.weight))
        db.session.commit()
        log_activity("Job Duplicated", f"Job '{job.title}' duplicated to '{new_job.title}'")
        return {"success": True, "message": f"Job '{title}' duplicated.", "new_job_id": new_job.id}
        
    return {"success": False, "message": "Invalid action."}, 400


# ── Emails ───────────────────────────────────────────────────────────────────

@main_bp.route("/emails")
@login_required
def email_history():
    from app.models.email import EmailHistory
    emails = EmailHistory.query.order_by(EmailHistory.sent_at.desc()).all()
    return render_template(
        "emails/history.html",
        emails=emails,
        active_nav="emails"
    )

@main_bp.route("/emails/<int:id>")
@login_required
def email_detail(id):
    from app.models.email import EmailHistory
    email = db.get_or_404(EmailHistory, id)
    return {"body": email.body}

@main_bp.route("/emails/<int:id>/retry", methods=["POST"])
@login_required
def retry_email_route(id):
    from app.services.email_service import retry_email
    success, message = retry_email(id)
    if success:
        flash("Email resent successfully.", "success")
    else:
        flash(f"Failed to resend email: {message}", "danger")
    return redirect(url_for("main.email_history"))


@main_bp.route("/applications/<int:app_id>/send_selected", methods=["POST"])
@login_required
def send_selected_email_route(app_id):
    from app.services.email_service import send_selected_email

    application = db.get_or_404(Application, app_id)
    candidate = application.candidate
    if not candidate.email:
        flash("Cannot send email — no email address on file.", "warning")
        return redirect(url_for("main.candidate_detail", candidate_id=candidate.id))

    success, result = send_selected_email(candidate, application.job)
    if success:
        flash(f"Selected email sent to {candidate.email} for {application.job.title}.", "success")
    else:
        error_msg = result.error_message if hasattr(result, "error_message") else str(result)
        flash(f"Failed to send email: {error_msg}", "danger")

    return redirect(url_for("main.candidate_detail", candidate_id=candidate.id))


@main_bp.route("/applications/<int:app_id>/send_rejected", methods=["POST"])
@login_required
def send_rejected_email_route(app_id):
    from app.services.email_service import send_rejected_email

    application = db.get_or_404(Application, app_id)
    candidate = application.candidate
    if not candidate.email:
        flash("Cannot send email — no email address on file.", "warning")
        return redirect(url_for("main.candidate_detail", candidate_id=candidate.id))

    success, result = send_rejected_email(candidate, application.job)
    if success:
        flash(f"Rejected email sent to {candidate.email} for {application.job.title}.", "success")
    else:
        error_msg = result.error_message if hasattr(result, "error_message") else str(result)
        flash(f"Failed to send email: {error_msg}", "danger")

    return redirect(url_for("main.candidate_detail", candidate_id=candidate.id))


@main_bp.route("/candidates/<int:candidate_id>/email_action/<action_type>", methods=["POST"])
@login_required
def send_email_action(candidate_id, action_type):
    app_id = request.form.get("app_id")
    if not app_id:
        flash("Please select a job application.", "warning")
        return redirect(url_for("main.candidate_detail", candidate_id=candidate_id))
    
    if action_type == "selected":
        return send_selected_email_route(app_id)
    elif action_type == "rejected":
        return send_rejected_email_route(app_id)
    
    return redirect(url_for("main.candidate_detail", candidate_id=candidate_id))


@main_bp.route("/candidates/<int:candidate_id>/send_interview", methods=["POST"])
@login_required
def send_interview_email_route(candidate_id):
    from app.services.email_service import generate_email_content, send_email

    candidate = db.get_or_404(Candidate, candidate_id)
    if not candidate.email:
        flash("Cannot send email — no email address on file.", "warning")
        return redirect(url_for("main.candidate_detail", candidate_id=candidate_id))

    custom_fields = {
        "interview_date": request.form.get("interview_date"),
        "interview_time": request.form.get("interview_time"),
        "interview_mode": request.form.get("interview_mode"),
        "meeting_link": request.form.get("meeting_link"),
        "venue": request.form.get("venue"),
        "interviewer_name": request.form.get("interviewer_name"),
        "notes": request.form.get("notes"),
    }
    
    job = candidate.applications[-1].job if candidate.applications else None
    subject, body = generate_email_content("interview", candidate, job, custom_fields)
    
    success, result = send_email(candidate.email, subject, body, candidate.full_name, candidate.id)
    if success:
        flash(f"Interview email sent to {candidate.email}.", "success")
    else:
        error_msg = result.error_message if hasattr(result, "error_message") else str(result)
        flash(f"Failed to send email: {error_msg}", "danger")

    return redirect(url_for("main.candidate_detail", candidate_id=candidate_id))


@main_bp.route("/candidates/<int:candidate_id>/send_hired", methods=["POST"])
@login_required
def send_hired_email_route(candidate_id):
    from app.services.email_service import generate_email_content, send_email

    candidate = db.get_or_404(Candidate, candidate_id)
    if not candidate.email:
        flash("Cannot send email — no email address on file.", "warning")
        return redirect(url_for("main.candidate_detail", candidate_id=candidate_id))

    custom_fields = {
        "joining_date": request.form.get("joining_date"),
        "reporting_time": request.form.get("reporting_time"),
        "office_address": request.form.get("office_address"),
        "hr_contact": request.form.get("hr_contact"),
    }
    
    job = candidate.applications[-1].job if candidate.applications else None
    subject, body = generate_email_content("hired", candidate, job, custom_fields)
    
    success, result = send_email(candidate.email, subject, body, candidate.full_name, candidate.id)
    if success:
        flash(f"Hired email sent to {candidate.email}.", "success")
    else:
        error_msg = result.error_message if hasattr(result, "error_message") else str(result)
        flash(f"Failed to send email: {error_msg}", "danger")

    return redirect(url_for("main.candidate_detail", candidate_id=candidate_id))


@main_bp.route("/settings/email", methods=["GET", "POST"])
@login_required
def email_settings():
    from app.forms.email import EmailSettingsForm
    from app.models.email import EmailSettings
    from app.services.email_service import test_smtp_connection

    form = EmailSettingsForm()
    settings = EmailSettings.query.first()

    if form.validate_on_submit():
        if not settings:
            settings = EmailSettings()
            db.session.add(settings)
        
        settings.smtp_host = form.smtp_host.data.strip()
        settings.smtp_port = form.smtp_port.data
        settings.sender_email = form.sender_email.data.strip()
        
        if form.sender_password.data:
            settings.sender_password = form.sender_password.data
            
        db.session.commit()

        # Test connection
        success, error_msg = test_smtp_connection(
            settings.smtp_host,
            settings.smtp_port,
            settings.sender_email,
            settings.sender_password
        )

        if success:
            flash("Settings saved. SMTP Connection Successful.", "success")
        else:
            flash(f"Settings saved, but SMTP Connection Failed: {error_msg}", "danger")
            
        return redirect(url_for("main.email_settings"))

    if request.method == "GET" and settings:
        form.smtp_host.data = settings.smtp_host
        form.smtp_port.data = settings.smtp_port
        form.sender_email.data = settings.sender_email
        # Password intentionally left blank

    return render_template(
        "settings/email.html",
        form=form,
        active_nav="email_settings"
    )


# ── New Feature API Routes ───────────────────────────────────────────────────

@main_bp.route("/api/jobs/parse-jd", methods=["POST"])
@login_required
def api_parse_job_description():
    """Parse uploaded Job Description file (PDF, DOCX, TXT) and return extracted fields."""
    if "file" not in request.files:
        return {"success": False, "error": "No file uploaded."}, 400

    file = request.files["file"]
    if not file or not file.filename:
        return {"success": False, "error": "No file selected."}, 400

    try:
        from app.services.jd_parser import extract_jd_text, parse_job_description
        raw_text = extract_jd_text(file)
        parsed = parse_job_description(raw_text, original_filename=file.filename)
        return {"success": True, "parsed": parsed}
    except Exception as exc:
        return {"success": False, "error": str(exc)}, 500





@main_bp.route("/candidates/<int:candidate_id>/export-pdf")
@login_required
def export_candidate_pdf(candidate_id):
    """Generate and return downloadable PDF report for candidate."""
    from flask import send_file
    candidate = db.get_or_404(Candidate, candidate_id)
    app_id = request.args.get("app_id")
    
    from app.services.pdf_report_generator import generate_candidate_pdf_report
    pdf_buffer = generate_candidate_pdf_report(candidate, app_id=app_id)
    
    clean_name = "".join(c for c in candidate.full_name if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
    filename = f"Candidate_Report_{clean_name}_{candidate.id}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


# ══════════════════════════════════════════════════════════════════════════════
# RECRUITMENT AI MODULE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@main_bp.route("/recruitment-ai")
@login_required
def recruitment_ai():
    """Main dashboard page for Recruitment AI module."""
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    selected_job_id = request.args.get("job_id", type=int)
    if not selected_job_id and jobs:
        selected_job_id = jobs[0].id

    return render_template(
        "recruitment_ai/index.html",
        jobs=jobs,
        selected_job_id=selected_job_id,
        active_nav="recruitment_ai",
    )


@main_bp.route("/api/recruitment-ai/recommendations/<int:job_id>")
@login_required
def api_recruitment_recommendations(job_id):
    """API returning ranked candidates for job with Rank badges & Rank #1 Why Recommended."""
    from app.services.recruitment_ai_service import rank_candidates_for_job
    data = rank_candidates_for_job(job_id)
    return {"success": True, "data": data}


@main_bp.route("/api/recruitment-ai/compare", methods=["POST"])
@login_required
def api_recruitment_compare():
    """API returning candidate comparison matrix."""
    payload = request.get_json(force=True, silent=True)
    if not payload and request.data:
        import json
        try:
            payload = json.loads(request.data.decode("utf-8"))
        except Exception:
            payload = {}
    if not payload:
        payload = {}

    candidate_ids = payload.get("candidate_ids", [])
    job_id = payload.get("job_id")

    if not candidate_ids:
        return {"success": False, "error": "No candidates selected for comparison."}, 400

    from app.services.recruitment_ai_service import compare_candidates
    data = compare_candidates(candidate_ids, job_id=job_id)
    return {"success": True, "data": data}


@main_bp.route("/api/recruitment-ai/interview-questions", methods=["GET", "POST"])
@login_required
def api_recruitment_questions():
    """API to generate custom technical, HR, and scenario interview questions."""
    payload = request.get_json(force=True, silent=True) or request.json or {}
    candidate_id = request.args.get("candidate_id", type=int) or payload.get("candidate_id")
    job_id = request.args.get("job_id", type=int) or payload.get("job_id")

    if not candidate_id:
        return {"success": False, "error": "Candidate ID is required."}, 400

    candidate = db.get_or_404(Candidate, candidate_id)
    job = db.session.get(Job, int(job_id)) if job_id else (candidate.applications[0].job if candidate.applications else None)

    from app.services.recruitment_ai_service import generate_recruitment_questions
    questions = generate_recruitment_questions(candidate, job)
    return {"success": True, "questions": questions}


@main_bp.route("/api/recruitment-ai/evaluate-interview", methods=["POST"])
@login_required
def api_recruitment_evaluate():
    """API to save HR interview ratings, calculate score, and generate final recommendation."""
    payload = request.get_json(force=True, silent=True)
    if not payload and request.data:
        import json
        try:
            payload = json.loads(request.data.decode("utf-8"))
        except Exception:
            payload = {}
    if not payload:
        payload = {}

    candidate_id = payload.get("candidate_id")
    job_id = payload.get("job_id")
    ratings = payload.get("ratings", {})
    comments = payload.get("comments", "")

    if not candidate_id or not job_id:
        return {"success": False, "error": "Candidate ID and Job ID are required."}, 400

    from app.services.recruitment_ai_service import save_interview_evaluation
    result = save_interview_evaluation(candidate_id, job_id, ratings, comments)
    return {"success": True, "evaluation": result}


@main_bp.route("/recruitment-ai/export-pdf/<int:candidate_id>/<int:job_id>")
@login_required
def export_recruitment_pdf(candidate_id, job_id):
    """Export complete Recruitment AI PDF Report for candidate & job."""
    from flask import send_file
    from app.services.pdf_report_generator import generate_recruitment_pdf_report
    
    candidate = db.get_or_404(Candidate, candidate_id)
    pdf_buffer = generate_recruitment_pdf_report(candidate_id, job_id)
    
    clean_name = "".join(c for c in candidate.full_name if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
    filename = f"Recruitment_Report_{clean_name}_{candidate_id}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM & CLOUD STATUS MODULE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@main_bp.route("/system/status")
@login_required
def system_status_route():
    from app.services.system_status_service import get_system_status
    status_data = get_system_status()
    return render_template(
        "system/status.html",
        status=status_data,
        active_nav="system_status"
    )


@main_bp.route("/api/system/status")
@login_required
def api_system_status():
    from app.services.system_status_service import get_system_status
    return {"success": True, "data": get_system_status()}




