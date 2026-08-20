"""Orchestrate resume upload, parsing, and candidate creation."""

import os
import uuid

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Application, Candidate, Job, Resume
from app.services.authenticity_service import analyse_resume
from app.services.resume_extractor import extract_candidate_fields
from app.services.resume_parser import ResumeParserError, extract_text
from app.services.scoring_service import extract_and_score_after_upload
from app.utils import allowed_file, ensure_dir


class UploadServiceError(Exception):
    """Raised when upload processing fails."""


def _upload_dir():
    path = os.path.join(
        current_app.root_path, "..", current_app.config["UPLOAD_FOLDER"]
    )
    ensure_dir(path)
    return os.path.abspath(path)


def _get_file_type(filename):
    return filename.rsplit(".", 1)[1].lower()


def _find_or_create_candidate(fields):
    import json as _json

    def _real(v):
        """Return value only if not 'Not Provided' / None / empty."""
        if not v or str(v).strip().lower() in {"not provided", "n/a", "none", ""}:
            return None
        return v

    confidence_json = _json.dumps(fields.get("_confidence", {}))
    candidate = None
    email = _real(fields.get("email"))
    if email:
        candidate = Candidate.query.filter_by(email=email).first()

    if candidate is None:
        candidate = Candidate(
            full_name=fields["full_name"],
            email=email,
            phone=_real(fields.get("phone")),
            location=_real(fields.get("location")),
            address=_real(fields.get("address")),
            city=_real(fields.get("city")),
            state=_real(fields.get("state")),
            pin_code=_real(fields.get("pin_code")),
            linkedin_url=_real(fields.get("linkedin_url")),
            github_url=_real(fields.get("github_url")),
            portfolio_url=_real(fields.get("portfolio_url")),
            career_objective=_real(fields.get("career_objective")),
            professional_summary=_real(fields.get("professional_summary")),
            technical_skills=_real(fields.get("technical_skills")),
            soft_skills=_real(fields.get("soft_skills")),
            languages=_real(fields.get("languages")),
            education=_real(fields.get("education")),
            experience=_real(fields.get("experience")),
            projects=_real(fields.get("projects")),
            certifications=_real(fields.get("certifications")),
            current_title=_real(fields.get("current_title")),
            years_experience=fields.get("years_experience"),
            summary=_real(fields.get("summary")),
            extraction_confidence=confidence_json,
            status="new",
        )
        db.session.add(candidate)
        db.session.flush()
    else:
        # Update with fresh data — only overwrite if new value is meaningful
        def _upd(field, val):
            v = _real(val)
            if v:
                setattr(candidate, field, v)

        _upd("phone", fields.get("phone"))
        _upd("location", fields.get("location"))
        _upd("address", fields.get("address"))
        _upd("city", fields.get("city"))
        _upd("state", fields.get("state"))
        _upd("pin_code", fields.get("pin_code"))
        _upd("linkedin_url", fields.get("linkedin_url"))
        _upd("github_url", fields.get("github_url"))
        _upd("portfolio_url", fields.get("portfolio_url"))
        _upd("career_objective", fields.get("career_objective"))
        _upd("professional_summary", fields.get("professional_summary"))
        _upd("technical_skills", fields.get("technical_skills"))
        _upd("soft_skills", fields.get("soft_skills"))
        _upd("languages", fields.get("languages"))
        _upd("education", fields.get("education"))
        _upd("experience", fields.get("experience"))
        _upd("projects", fields.get("projects"))
        _upd("certifications", fields.get("certifications"))
        _upd("current_title", fields.get("current_title"))
        if fields.get("years_experience") is not None:
            candidate.years_experience = fields["years_experience"]
        _upd("summary", fields.get("summary"))
        candidate.extraction_confidence = confidence_json

    return candidate



def process_resume_file(file_storage, job_id=None):
    """
    Save, parse, and persist a single resume file.
    Returns a result dict with status and metadata.
    """
    allowed = current_app.config["ALLOWED_EXTENSIONS"]

    if not file_storage or not file_storage.filename:
        return {"success": False, "filename": "", "error": "No file provided."}

    original_name = secure_filename(file_storage.filename)
    if not original_name:
        return {"success": False, "filename": file_storage.filename, "error": "Invalid filename."}

    if not allowed_file(original_name, allowed):
        return {
            "success": False,
            "filename": original_name,
            "error": f"File type not allowed. Accepted: {', '.join(sorted(allowed))}",
        }

    from app.services.storage_service import get_storage_service
    storage = get_storage_service()

    file_type = _get_file_type(original_name)
    stored_name = f"{uuid.uuid4().hex}.{file_type}"

    try:
        saved_info = storage.save_file(file_storage, stored_name)
        stored_path = saved_info["file_path"]
        file_size = saved_info.get("file_size", 0)

        local_extract_path = storage.get_temp_local_path(stored_name) or stored_path

        resume_record = None
        parse_status = "processing"
        extracted_text = None
        parse_error = None

        try:
            extracted_text = extract_text(local_extract_path, file_type)
            fields = extract_candidate_fields(extracted_text, original_name)
            candidate = _find_or_create_candidate(fields)
            parse_status = "completed"

            resume_record = Resume(
                candidate_id=candidate.id,
                original_filename=original_name,
                stored_filename=stored_name,
                file_path=stored_path,
                file_size=file_size,
                file_type=file_type,
                extracted_text=extracted_text,
                parse_status=parse_status,
            )
            db.session.add(resume_record)
            db.session.flush()

            application = None
            if job_id:
                job = db.session.get(Job, job_id)
                if job:
                    application = Application.query.filter_by(
                        candidate_id=candidate.id, job_id=job_id
                    ).first()
                    if not application:
                        application = Application(
                            candidate_id=candidate.id,
                            job_id=job_id,
                            status="applied",
                        )
                        db.session.add(application)

            db.session.commit()

            scoring = {}
            if extracted_text:
                scoring = extract_and_score_after_upload(
                    candidate.id,
                    job_id=job_id if application else None,
                    text=extracted_text,
                    resume=resume_record,
                )

            # ── Authenticity / fake-resume check ────────────────────────────
            job_obj = db.session.get(Job, job_id) if job_id else None
            auth_result = analyse_resume(candidate, resume_record, job=job_obj)
            resume_record.authenticity_score = auth_result["score"]
            resume_record.authenticity_report = auth_result["report_json"]
            resume_record.is_suspicious = auth_result["is_suspicious"]

            # ── Duplicate resume check ──────────────────────────────────────
            from app.services.duplicate_detector import check_duplicate_candidate
            dup_result = check_duplicate_candidate(
                email=candidate.email,
                phone=candidate.phone,
                extracted_text=extracted_text,
                candidate_id=candidate.id
            )
            db.session.commit()

            return {
                "success": True,
                "filename": original_name,
                "candidate_id": candidate.id,
                "candidate_name": candidate.full_name,
                "email": candidate.email,
                "resume_id": resume_record.id,
                "parse_status": parse_status,
                "text_length": len(extracted_text) if extracted_text else 0,
                "job_applied": job_id if application else None,
                "skills": scoring.get("skills", []),
                "ats_score": scoring.get("ats_score"),
                "skill_match_score": scoring.get("skill_match_score"),
                "rank": scoring.get("rank"),
                "authenticity_score": auth_result["score"],
                "authenticity_status": auth_result["status"],
                "risk_level": auth_result["risk_level"],
                "is_duplicate": dup_result["is_duplicate"],
                "duplicate_reasons": dup_result["reasons"],
            }

        except ResumeParserError as exc:
            parse_status = "failed"
            parse_error = str(exc)
            fields = extract_candidate_fields("", original_name)
            candidate = _find_or_create_candidate(fields)

            resume_record = Resume(
                candidate_id=candidate.id,
                original_filename=original_name,
                stored_filename=stored_name,
                file_path=stored_path,
                file_size=file_size,
                file_type=file_type,
                extracted_text=None,
                parse_status=parse_status,
                parse_error=parse_error,
            )
            db.session.add(resume_record)
            db.session.commit()

            return {
                "success": True,
                "filename": original_name,
                "candidate_id": candidate.id,
                "candidate_name": candidate.full_name,
                "email": candidate.email,
                "resume_id": resume_record.id,
                "parse_status": parse_status,
                "warning": parse_error,
                "job_applied": None,
            }

    except Exception as exc:
        db.session.rollback()
        storage.delete_file(stored_name)
        return {
            "success": False,
            "filename": original_name,
            "error": str(exc),
        }


def process_multiple_files(files, job_id=None):
    """Process a list of uploaded files and return per-file results."""
    results = []
    for file_storage in files:
        if file_storage and file_storage.filename:
            results.append(process_resume_file(file_storage, job_id=job_id))
    return results
