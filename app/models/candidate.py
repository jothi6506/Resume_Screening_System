"""Candidate profile model."""

from app.extensions import db
from app.models.mixins import TimestampMixin


class Candidate(db.Model, TimestampMixin):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True, index=True)
    phone = db.Column(db.String(30), nullable=True)
    location = db.Column(db.String(120), nullable=True)  # Legacy
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    pin_code = db.Column(db.String(20), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    summary = db.Column(db.Text, nullable=True)  # Legacy
    career_objective = db.Column(db.Text, nullable=True)
    professional_summary = db.Column(db.Text, nullable=True)
    technical_skills = db.Column(db.Text, nullable=True)
    soft_skills = db.Column(db.Text, nullable=True)
    education = db.Column(db.Text, nullable=True)
    experience = db.Column(db.Text, nullable=True)
    projects = db.Column(db.Text, nullable=True)
    certifications = db.Column(db.Text, nullable=True)
    languages = db.Column(db.Text, nullable=True)
    portfolio_url = db.Column(db.String(255), nullable=True)
    extraction_confidence = db.Column(db.Text, nullable=True)   # JSON: per-field confidence scores
    years_experience = db.Column(db.Float, nullable=True)
    current_title = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(30), default="new", nullable=False, index=True)
    # new | reviewing | shortlisted | rejected | hired

    resumes = db.relationship(
        "Resume", back_populates="candidate", cascade="all, delete-orphan"
    )
    skills = db.relationship(
        "CandidateSkill", back_populates="candidate", cascade="all, delete-orphan"
    )
    applications = db.relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Candidate {self.full_name}>"

    @property
    def primary_resume(self):
        if not self.resumes:
            return None
        return max(self.resumes, key=lambda r: r.uploaded_at)

    @property
    def best_ats_score(self):
        if not self.applications:
            return None
        return max(app.ats_score or 0 for app in self.applications)

    def _count_items(self, text_field):
        if not text_field or str(text_field).strip().lower() in {"not provided", "none", "n/a"}:
            return 0
        import re
        text_field = str(text_field)
        # If there are explicit bullets, use them
        bullets = re.findall(r'(?:^|\n)\s*[-•*](?=\s)', text_field)
        if len(bullets) > 1:
            return len(bullets)
        # Otherwise, count meaningful blocks/lines
        lines = [l.strip() for l in text_field.split('\n') if l.strip() and len(l.strip()) > 3]
        if not lines:
            return 0
        # Heuristic: 1 item per 3-4 lines on average, but minimum 1
        return max(1, len(lines) // 3 if len(lines) > 3 else len(lines))

    @property
    def total_projects(self):
        return self._count_items(self.projects)

    @property
    def total_certifications(self):
        return self._count_items(self.certifications)
        
    @property
    def total_education(self):
        return self._count_items(self.education)

    @property
    def total_skills_count(self):
        db_count = len(self.skills) if self.skills else 0
        raw_text = (self.technical_skills or "") + "\n" + (self.soft_skills or "")
        if not raw_text.strip() or raw_text.strip().lower() in {"not provided", "none", "n/a"}:
            return db_count
        import re
        # Count words separated by comma, bullet, or newline
        items = [s.strip() for s in re.split(r'[,|•\n]', raw_text) if s.strip()]
        return max(db_count, len(items))

