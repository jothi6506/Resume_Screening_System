from app import create_app
from app.extensions import db
from app.models import Candidate, Resume, Application
from app.services.resume_extractor import extract_candidate_fields
from app.services.scoring_service import score_candidate_for_job, score_all_applications

app = create_app()

with app.app_context():
    candidates = Candidate.query.all()
    count = 0
    for candidate in candidates:
        resume = candidate.primary_resume
        if not resume or not resume.extracted_text:
            continue
            
        print(f"Reparsing: {candidate.full_name}")
        
        # 1. Re-extract all fields
        fields = extract_candidate_fields(resume.extracted_text, resume.original_filename)
        
        # 2. Update candidate fields completely
        if fields.get("email"): candidate.email = fields["email"]
        if fields.get("phone"): candidate.phone = fields["phone"]
        if fields.get("location"): candidate.location = fields["location"]
        if fields.get("linkedin_url"): candidate.linkedin_url = fields["linkedin_url"]
        if fields.get("github_url"): candidate.github_url = fields["github_url"]
        if fields.get("current_title"): candidate.current_title = fields["current_title"]
        if fields.get("years_experience"): candidate.years_experience = fields["years_experience"]
        if fields.get("summary"): candidate.summary = fields["summary"]
        
        # 3. If there are applications, re-score them which also re-extracts skills
        apps = Application.query.filter_by(candidate_id=candidate.id).all()
        if apps:
            for application in apps:
                score_candidate_for_job(candidate.id, application.job_id, text=resume.extracted_text, resume=resume)
        else:
            # Just re-extract skills if no job application
            from app.services.scoring_service import persist_candidate_skills
            persist_candidate_skills(candidate.id, resume.extracted_text)
            
        count += 1
        
    db.session.commit()
    print(f"Successfully re-parsed and updated {count} candidates with the new engine!")
