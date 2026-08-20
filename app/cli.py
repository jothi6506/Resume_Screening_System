"""Flask CLI commands for database management."""

import click
from flask.cli import with_appcontext

from app.extensions import db
from app.models import Job, JobSkill, Skill, User


DEFAULT_SKILLS = [
    ("Python", "technical"),
    ("Flask", "technical"),
    ("MySQL", "technical"),
    ("JavaScript", "technical"),
    ("React", "technical"),
    ("Docker", "tool"),
    ("Git", "tool"),
    ("Communication", "soft"),
    ("Leadership", "soft"),
    ("SQL", "technical"),
    ("REST API", "technical"),
    ("Machine Learning", "technical"),
]

DEFAULT_JOB = {
    "title": "Senior Python Developer",
    "department": "Engineering",
    "location": "Remote",
    "employment_type": "full-time",
    "description": (
        "We are looking for an experienced Python developer to build and "
        "maintain our resume screening platform."
    ),
    "requirements": (
        "5+ years Python experience, Flask or Django, MySQL, REST APIs, "
        "strong problem-solving skills."
    ),
    "required_skill_names": ["Python", "Flask", "MySQL", "REST API", "Git"],
}


def register_commands(app):
    @app.cli.command("init-db")
    @with_appcontext
    def init_db():
        """Create all database tables."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("seed")
    @click.option("--email", default="admin@resume.local", help="Admin email")
    @click.option("--password", default="Admin@123", help="Admin password")
    @click.option("--name", default="HR Admin", help="Admin full name")
    @with_appcontext
    def seed(email, password, name):
        """Seed default admin user, skills, and sample job."""
        db.create_all()

        for admin_email in [email, "admin@resume.com"]:
            admin = User.query.filter_by(email=admin_email).first()
            if not admin:
                admin = User(email=admin_email, full_name=name, role="admin")
                admin.set_password(password)
                db.session.add(admin)
                click.echo(f"Created admin user: {admin_email}")
            else:
                click.echo(f"Admin user already exists: {admin_email}")


        skill_map = {}
        for skill_name, category in DEFAULT_SKILLS:
            skill = Skill.query.filter_by(name=skill_name).first()
            if not skill:
                skill = Skill(name=skill_name, category=category)
                db.session.add(skill)
            skill_map[skill_name] = skill

        db.session.flush()

        job = Job.query.filter_by(title=DEFAULT_JOB["title"]).first()
        if not job:
            job = Job(
                title=DEFAULT_JOB["title"],
                department=DEFAULT_JOB["department"],
                location=DEFAULT_JOB["location"],
                employment_type=DEFAULT_JOB["employment_type"],
                description=DEFAULT_JOB["description"],
                requirements=DEFAULT_JOB["requirements"],
                status="open",
                created_by=admin,
            )
            db.session.add(job)
            db.session.flush()

            for skill_name in DEFAULT_JOB["required_skill_names"]:
                skill = skill_map.get(skill_name)
                if skill:
                    db.session.add(
                        JobSkill(job_id=job.id, skill_id=skill.id, is_required=True)
                    )
            click.echo(f"Created sample job: {job.title}")
        else:
            click.echo(f"Sample job already exists: {job.title}")

        db.session.commit()
        click.echo("Seed completed successfully.")

    @app.cli.command("score-all")
    @with_appcontext
    def score_all():
        """Re-score and re-rank all applications."""
        from app.services.scoring_service import score_all_applications

        count = score_all_applications()
        click.echo(f"Scored and ranked {count} application(s).")

    @app.cli.command("drop-db")
    @click.confirmation_option(prompt="This will drop ALL tables. Continue?")
    @with_appcontext
    def drop_db():
        """Drop all database tables (development only)."""
        db.drop_all()
        click.echo("All tables dropped.")
