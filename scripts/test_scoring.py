"""ATS scoring and skill extraction smoke tests."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///dev.db")

from app import create_app
from app.extensions import db
from app.models import Application, Candidate, CandidateSkill, Job
from app.services.ats_scorer import calculate_ats_score
from app.services.scoring_service import score_candidate_for_job
from app.services.skill_extractor import extract_skills_from_text

SAMPLE_RESUME = """
John Doe
Senior Python Developer
john.doe@techcorp.com
+1 555-987-6543
linkedin.com/in/johndoe

8 years of experience building scalable web applications.

Skills: Python, Flask, MySQL, REST API, Git, Docker, JavaScript, React,
Machine Learning, Communication, Leadership.

Professional Summary
Experienced backend engineer specializing in Python microservices and REST APIs.
"""


def test_skill_extraction():
    app = create_app("development")
    with app.app_context():
        skills = extract_skills_from_text(SAMPLE_RESUME)
        names = [s["name"] for s in skills]
        assert "Python" in names
        assert "Flask" in names
        assert "REST API" in names
        print(f"Skills found: {', '.join(names)}")
        print("Skill extraction test passed.")


def test_ats_scoring_pipeline():
    app = create_app("development")
    with app.app_context():
        job = Job.query.filter_by(title="Senior Python Developer").first()
        assert job is not None, "Run flask seed first"

        candidate = Candidate(
            full_name="John Doe",
            email="john.doe.scoring@test.local",
            years_experience=8.0,
            current_title="Senior Python Developer",
            summary="Python and Flask expert.",
            status="new",
        )
        db.session.add(candidate)
        db.session.commit()

        result = score_candidate_for_job(
            candidate.id, job.id, text=SAMPLE_RESUME
        )

        assert result["success"] is True
        assert result["ats_score"] > 0
        assert len(result["skills"]) >= 5
        assert result["rank"] is not None

        app_record = db.session.get(Application, result["application_id"])
        assert app_record.ats_score == result["ats_score"]
        assert app_record.rank == result["rank"]

        skills = CandidateSkill.query.filter_by(candidate_id=candidate.id).all()
        assert len(skills) >= 5

        scores = calculate_ats_score(candidate, job)
        assert scores["skill_match_score"] >= 50

        print(f"ATS score: {result['ats_score']}%")
        print(f"Skill match: {result['skill_match_score']}%")
        print(f"Rank: #{result['rank']}")
        print("ATS scoring pipeline test passed.")


if __name__ == "__main__":
    test_skill_extraction()
    test_ats_scoring_pipeline()
    print("All scoring tests passed.")
