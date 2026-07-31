"""Forms for creating and editing job postings."""

from flask_wtf import FlaskForm
from wtforms import (
    FloatField, SelectField, StringField, SubmitField, TextAreaField
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


EMPLOYMENT_CHOICES = [
    ("full-time", "Full-Time"),
    ("part-time", "Part-Time"),
    ("contract", "Contract"),
    ("internship", "Internship"),
    ("freelance", "Freelance"),
]

STATUS_CHOICES = [
    ("open", "Active / Open"),
    ("draft", "Draft"),
    ("closed", "Closed"),
    ("archived", "Archived"),
]

QUALIFICATION_CHOICES = [
    ("", "— Any —"),
    ("10th", "10th / SSLC"),
    ("12th", "12th / HSC"),
    ("Diploma", "Diploma"),
    ("Bachelor's", "Bachelor's Degree (B.E / B.Tech / BCA / B.Sc …)"),
    ("Master's", "Master's Degree (M.E / M.Tech / MCA / M.Sc …)"),
    ("MBA", "MBA"),
    ("PhD", "PhD / Doctorate"),
]

JOB_TEMPLATES = {
    "Python Developer": {
        "description": "We are looking for a Python Developer to join our engineering team.",
        "requirements": "3+ years of Python experience. Proficiency in Django/Flask, REST APIs, SQL databases.",
        "skills": ["Python", "Django", "Flask", "REST API", "SQL", "Git"],
        "min_experience": 3.0,
        "min_qualification": "Bachelor's",
    },
    "Java Developer": {
        "description": "Seeking an experienced Java Developer for backend services.",
        "requirements": "3+ years Java. Spring Boot, Microservices, REST APIs.",
        "skills": ["Java", "Spring Boot", "REST API", "SQL", "Maven", "Git"],
        "min_experience": 3.0,
        "min_qualification": "Bachelor's",
    },
    "Full Stack Developer": {
        "description": "Full Stack Developer for building end-to-end web applications.",
        "requirements": "Experience with React/Angular and Node.js or Django.",
        "skills": ["JavaScript", "React", "Node.js", "Python", "SQL", "Git", "HTML", "CSS"],
        "min_experience": 2.0,
        "min_qualification": "Bachelor's",
    },
    "Frontend Developer": {
        "description": "Frontend Developer to build beautiful, responsive UIs.",
        "requirements": "Strong HTML, CSS, JavaScript skills. React preferred.",
        "skills": ["HTML", "CSS", "JavaScript", "React", "Bootstrap", "TypeScript"],
        "min_experience": 1.0,
        "min_qualification": "Bachelor's",
    },
    "Data Analyst": {
        "description": "Data Analyst to transform data into actionable insights.",
        "requirements": "SQL, Excel, Python or R. Experience with data visualization tools.",
        "skills": ["SQL", "Python", "Excel", "Power BI", "Tableau", "Statistics"],
        "min_experience": 1.0,
        "min_qualification": "Bachelor's",
    },
    "Data Scientist": {
        "description": "Data Scientist to develop ML models and analytical solutions.",
        "requirements": "Python, ML algorithms, statistical analysis.",
        "skills": ["Python", "Machine Learning", "scikit-learn", "TensorFlow", "SQL", "Statistics"],
        "min_experience": 2.0,
        "min_qualification": "Master's",
    },
    "Machine Learning Engineer": {
        "description": "ML Engineer to design, build, and deploy ML models at scale.",
        "requirements": "Deep learning frameworks, MLOps, Python.",
        "skills": ["Python", "TensorFlow", "PyTorch", "Machine Learning", "MLOps", "Docker"],
        "min_experience": 3.0,
        "min_qualification": "Master's",
    },
    "DevOps Engineer": {
        "description": "DevOps Engineer to automate and optimize our CI/CD pipelines.",
        "requirements": "Kubernetes, Docker, AWS/GCP, CI/CD pipelines.",
        "skills": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Terraform", "Ansible"],
        "min_experience": 3.0,
        "min_qualification": "Bachelor's",
    },
    "QA Engineer": {
        "description": "QA Engineer to ensure software quality through rigorous testing.",
        "requirements": "Manual & automated testing. Selenium, JIRA.",
        "skills": ["Selenium", "JIRA", "Manual Testing", "Automation Testing", "SQL", "Python"],
        "min_experience": 2.0,
        "min_qualification": "Bachelor's",
    },
}


class JobForm(FlaskForm):
    title = StringField(
        "Job Title",
        validators=[DataRequired(message="Job title is required."), Length(max=200)],
        render_kw={"placeholder": "e.g. Senior Python Developer"},
    )
    department = StringField(
        "Department",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g. Engineering"},
    )
    location = StringField(
        "Location",
        validators=[Optional(), Length(max=120)],
        render_kw={"placeholder": "e.g. Chennai, India / Remote"},
    )
    employment_type = SelectField(
        "Employment Type",
        choices=EMPLOYMENT_CHOICES,
        default="full-time",
    )
    status = SelectField(
        "Status",
        choices=STATUS_CHOICES,
        default="open",
    )
    min_experience = FloatField(
        "Minimum Experience (years)",
        validators=[Optional(), NumberRange(min=0, max=50)],
        default=0.0,
        render_kw={"placeholder": "0"},
    )
    min_qualification = SelectField(
        "Minimum Qualification",
        choices=QUALIFICATION_CHOICES,
        default="",
    )
    required_skills_text = StringField(
        "Required Skills (comma-separated)",
        validators=[Optional(), Length(max=1000)],
        render_kw={"placeholder": "Python, Django, REST API, SQL ..."},
    )
    description = TextAreaField(
        "Job Description",
        validators=[Optional(), Length(max=5000)],
        render_kw={"rows": 5, "placeholder": "Describe the role, responsibilities, and team."},
    )
    requirements = TextAreaField(
        "Requirements",
        validators=[Optional(), Length(max=5000)],
        render_kw={"rows": 4, "placeholder": "Qualifications, experience, and skills required."},
    )
    submit = SubmitField("Save Job")
