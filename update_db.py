"""Re-extract and update all existing candidate records with the new parser."""
import os
from dotenv import load_dotenv
load_dotenv()
from app import create_app
from app.extensions import db
from app.models import Candidate
from app.services.resume_parser import extract_text, ResumeParserError
from app.services.resume_extractor import extract_candidate_fields

app = create_app()
with app.app_context():
    upload_folder = os.path.join(
        app.root_path, "..", app.config["UPLOAD_FOLDER"]
    )
    upload_folder = os.path.abspath(upload_folder)

    candidates = Candidate.query.all()
    updated = 0
    errors = 0

    for c in candidates:
        if not c.resumes:
            print(f"  SKIP {c.full_name}: no resumes")
            continue

        # Use the most recent resume
        r = max(c.resumes, key=lambda x: x.uploaded_at)
        file_path = os.path.join(upload_folder, r.stored_filename)

        if not os.path.exists(file_path):
            print(f"  SKIP {c.full_name}: file missing ({r.stored_filename})")
            continue

        try:
            text = extract_text(file_path, r.file_type or "pdf")
            fields = extract_candidate_fields(text, filename=r.original_filename)

            # Update ALL fields from fresh parse
            if fields.get("email"):
                c.email = fields["email"]
            if fields.get("phone"):
                c.phone = fields["phone"]
            if fields.get("location"):
                c.location = fields["location"]
            if fields.get("linkedin_url"):
                c.linkedin_url = fields["linkedin_url"]
            if fields.get("github_url"):
                c.github_url = fields["github_url"]
            if fields.get("current_title"):
                c.current_title = fields["current_title"]
            if fields.get("years_experience"):
                c.years_experience = fields["years_experience"]
            # Always overwrite summary with strict objective extraction
            c.summary = fields.get("summary")

            db.session.commit()
            print(f"  OK {c.full_name}: summary={'Yes' if c.summary else 'No'}, "
                  f"loc={c.location}, github={bool(c.github_url)}")
            updated += 1
        except ResumeParserError as e:
            print(f"  PARSER ERROR {c.full_name}: {e}")
            errors += 1
        except Exception as e:
            db.session.rollback()
            print(f"  ERROR {c.full_name}: {e}")
            errors += 1

    print(f"\nDone. Updated: {updated}, Errors: {errors}")
