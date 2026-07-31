import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app import create_app
from app.extensions import db
from app.models import Job, Skill, JobSkill, User
from app.forms.job import JOB_TEMPLATES

app = create_app()

with app.app_context():
    admin = User.query.filter_by(role="admin").first()
    if not admin:
        print("No admin user found. Please run 'flask seed' first.")
        sys.exit(1)

    print("Seeding jobs from templates...")
    for title, tmpl in JOB_TEMPLATES.items():
        if Job.query.filter_by(title=title).first():
            print(f"Skipping {title}, already exists.")
            continue
        
        job = Job(
            title=title,
            department="Engineering" if "Developer" in title or "Engineer" in title else "Data",
            location="Remote",
            employment_type="full-time",
            description=tmpl.get("description", ""),
            requirements=tmpl.get("requirements", ""),
            min_experience=tmpl.get("min_experience", 0.0),
            min_qualification=tmpl.get("min_qualification", ""),
            status="open",
            created_by_id=admin.id
        )
        db.session.add(job)
        db.session.flush()

        for skill_name in tmpl.get("skills", []):
            skill = Skill.query.filter(Skill.name.ilike(skill_name)).first()
            if not skill:
                skill = Skill(name=skill_name.title(), category="technical")
                db.session.add(skill)
                db.session.flush()
            db.session.add(JobSkill(job_id=job.id, skill_id=skill.id, is_required=True, weight=1.0))

    db.session.commit()
    print("Successfully seeded all job templates!")
