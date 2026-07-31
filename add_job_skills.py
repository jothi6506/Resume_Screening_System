from app import create_app
from app.extensions import db
from app.models import Job, Skill, JobSkill
from dotenv import load_dotenv

load_dotenv()

app = create_app()

def get_or_create_skill(name, category="technical"):
    skill = Skill.query.filter_by(name=name).first()
    if not skill:
        skill = Skill(name=name, category=category)
        db.session.add(skill)
        db.session.commit()
    return skill

with app.app_context():
    job_skills_mapping = {
        "Data Scientist": ["Python", "Machine Learning", "SQL", "TensorFlow", "Pandas", "Scikit-Learn", "Deep Learning"],
        "Frontend Developer": ["React", "JavaScript", "HTML", "CSS", "TypeScript", "Redux", "UI/UX"],
        "Product Manager": ["Product Management", "Agile", "Scrum", "Jira", "Leadership", "Communication", "Data Analysis"],
        "UX Designer": ["Figma", "UI/UX", "User Research", "Wireframing", "Prototyping", "Adobe XD", "Design Thinking"],
        "Backend Developer (Java)": ["Java", "Spring Boot", "Microservices", "REST API", "SQL", "Hibernate", "AWS"]
    }

    for job_title, skills in job_skills_mapping.items():
        job = Job.query.filter_by(title=job_title).first()
        if job:
            for skill_name in skills:
                skill = get_or_create_skill(skill_name)
                # Check if already exists
                existing = JobSkill.query.filter_by(job_id=job.id, skill_id=skill.id).first()
                if not existing:
                    job_skill = JobSkill(job_id=job.id, skill_id=skill.id, is_required=True, weight=1.0)
                    db.session.add(job_skill)
    
    db.session.commit()
    print("Successfully added skills to jobs!")
