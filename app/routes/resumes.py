"""Resume upload routes."""

from flask import Blueprint, flash, render_template, request
from flask_login import login_required

from app.forms.upload import ResumeUploadForm
from app.models import Job
from app.services.upload_service import process_multiple_files
from app.models.activity import log_activity

resumes_bp = Blueprint("resumes", __name__)


@resumes_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    form = ResumeUploadForm()
    open_jobs = Job.query.order_by(Job.title).all()
    form.job_id.choices = [(0, "— No specific job —")] + [
        (job.id, job.title) for job in open_jobs
    ]

    results = []

    if request.method == "POST":
        files = request.files.getlist("resumes")

        if not files or all(not f.filename for f in files):
            flash("Please select at least one PDF resume to upload.", "warning")
        else:
            job_id = form.job_id.data if form.job_id.data else None
            if job_id == 0:
                job_id = None

            results = process_multiple_files(files, job_id=job_id)

            success_count = sum(1 for r in results if r.get("success"))
            fail_count = len(results) - success_count

            if success_count:
                for r in results:
                    if r.get("success"):
                        log_activity("Resume Uploaded", f"Uploaded resume: {r.get('filename', 'Unknown')}")
                scored = [r for r in results if r.get("ats_score") is not None]
                if scored:
                    flash(
                        f"Processed {success_count} resume(s) with ATS scoring.",
                        "success",
                    )
                else:
                    flash(
                        f"Processed {success_count} resume(s). "
                        "Select a job to enable ATS scoring.",
                        "success",
                    )
            if fail_count:
                flash(f"{fail_count} file(s) could not be processed.", "danger")

    return render_template(
        "upload/index.html",
        form=form,
        results=results,
        open_jobs=open_jobs,
        active_nav="upload",
    )
