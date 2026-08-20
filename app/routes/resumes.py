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


@resumes_bp.route("/resumes/<int:resume_id>/download")
@login_required
def download_resume(resume_id):
    import io
    from flask import send_file, redirect, flash, url_for
    from app.extensions import db
    from app.models import Resume
    from app.services.storage_service import get_storage_service

    resume = db.get_or_404(Resume, resume_id)
    storage = get_storage_service()

    file_bytes = storage.get_file_bytes(resume.stored_filename)
    if not file_bytes:
        flash("Resume file could not be found in storage.", "danger")
        return redirect(request.referrer or url_for("main.candidates"))

    mime = "application/pdf" if resume.file_type == "pdf" else "application/octet-stream"
    return send_file(
        io.BytesIO(file_bytes),
        mimetype=mime,
        as_attachment=True,
        download_name=resume.original_filename or f"resume_{resume.id}.pdf"
    )


@resumes_bp.route("/resumes/<int:resume_id>/view")
@login_required
def view_resume(resume_id):
    import io
    from flask import send_file, redirect, flash, url_for
    from app.extensions import db
    from app.models import Resume
    from app.services.storage_service import get_storage_service

    resume = db.get_or_404(Resume, resume_id)

    if resume.file_path and (resume.file_path.startswith("http://") or resume.file_path.startswith("https://")):
        return redirect(resume.file_path)

    storage = get_storage_service()
    file_bytes = storage.get_file_bytes(resume.stored_filename)
    if not file_bytes:
        flash("Resume file could not be found in storage.", "danger")
        return redirect(request.referrer or url_for("main.candidates"))

    mime_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "doc": "application/msword"
    }
    mime = mime_map.get(resume.file_type.lower(), "application/octet-stream")
    return send_file(
        io.BytesIO(file_bytes),
        mimetype=mime,
        as_attachment=False
    )

