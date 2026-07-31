from app import create_app
from app.extensions import db
from app.models import Job, User
from dotenv import load_dotenv

load_dotenv()

app = create_app()

with app.app_context():
    # Find admin user to assign as creator
    admin = User.query.first()
    admin_id = admin.id if admin else None

    jobs = [
        Job(
            title="Data Scientist",
            department="Data",
            location="Remote",
            employment_type="full-time",
            description="Looking for a data scientist with strong ML skills.",
            requirements="3+ years of experience in Python and machine learning.",
            status="open",
            created_by_id=admin_id
        ),
        Job(
            title="Frontend Developer",
            department="Engineering",
            location="Chennai, Tamil Nadu",
            employment_type="full-time",
            description="Looking for an experienced Frontend Developer.",
            requirements="3+ years of experience with React.",
            status="open",
            created_by_id=admin_id
        ),
        Job(
            title="Product Manager",
            department="Product",
            location="Bangalore",
            employment_type="full-time",
            description="Manage the product lifecycle from start to finish.",
            requirements="5+ years of PM experience.",
            status="closed",
            created_by_id=admin_id
        ),
        Job(
            title="UX Designer",
            department="Design",
            location="Remote",
            employment_type="contract",
            description="Design modern and intuitive user interfaces.",
            requirements="Portfolio of previous work. 2+ years experience.",
            status="draft",
            created_by_id=admin_id
        ),
        Job(
            title="Backend Developer (Java)",
            department="Engineering",
            location="Pune",
            employment_type="full-time",
            description="Java Spring Boot backend developer.",
            requirements="4+ years experience with Java, Spring Boot, and Microservices.",
            status="open",
            created_by_id=admin_id
        )
    ]

    for job in jobs:
        db.session.add(job)
    
    db.session.commit()
    print("Successfully added new jobs!")
