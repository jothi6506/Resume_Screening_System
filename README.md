# ResumeScreen AI

Production-ready AI Resume Screening System built with **Python Flask**, **MySQL**, and **Bootstrap 5**.

## Project Structure

```
Resume_Screening_System/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Environment configs
│   ├── extensions.py        # db, migrate, login_manager
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # Flask blueprints
│   ├── services/            # ATS, parsing, AI hooks
│   ├── static/              # CSS, JS, images
│   ├── templates/           # Jinja2 templates
│   └── utils/               # Shared helpers
├── uploads/resumes/         # Uploaded resume files
├── migrations/              # Database migrations
├── .env.example
├── requirements.txt
└── run.py
```

## Build Roadmap

| Step | Status | Description |
|------|--------|-------------|
| 1 | ✅ Done | Project foundation & Flask factory |
| 2 | ✅ Done | MySQL models (Candidate, Resume, Job, Skills) |
| 3 | ✅ Done | Authentication & login page |
| 4 | ✅ Done | HR dashboard UI (dark theme) |
| 5 | ✅ Done | Resume upload & PDF parsing |
| 6 | ✅ Done | ATS scoring, skill extraction, ranking |
| 7 | Pending | Candidate list & detail pages |
| 8 | Pending | Analytics dashboard with charts |

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
# Edit .env with your MySQL credentials

# 4. Create MySQL database
mysql -u root -p < scripts/init_db.sql
# Or manually: CREATE DATABASE resume_screening ...

# 5. Run migrations & seed
set FLASK_APP=run.py          # Windows CMD
# export FLASK_APP=run.py     # macOS/Linux
flask db upgrade
flask seed

# Default admin credentials (change in production):
# Email:    admin@resume.local
# Password: Admin@123

# 6. Start the server
python run.py
```

Visit `http://localhost:5000` — health check at `/health`.

## Future AI Integration

Set in `.env`:

```
AI_ENABLED=true
OPENAI_API_KEY=sk-...
```

The `app/services/` layer is designed for pluggable AI providers without changing routes or templates.

## Database Schema (Step 2)

| Table | Purpose |
|-------|---------|
| `users` | HR recruiters and admins |
| `jobs` | Open job postings |
| `candidates` | Candidate profiles (parsed from resumes) |
| `resumes` | Uploaded PDF/DOC files + extracted text |
| `skills` | Normalized skill catalog |
| `job_skills` | Required skills per job (with weights) |
| `candidate_skills` | Extracted skills per candidate |
| `applications` | Candidate ↔ Job link with ATS score & rank |

### CLI Commands

```bash
flask init-db    # Create tables (without migrations)
flask db upgrade # Apply migrations (recommended)
flask seed       # Seed admin user, skills, sample job
flask score-all  # Re-score and re-rank all applications
flask drop-db    # Drop all tables (dev only)
```

## ATS Scoring (Step 6)

When a resume is uploaded with a job selected, the system automatically:

1. **Extracts skills** from resume text (catalog + aliases + extras)
2. **Calculates ATS score** (0–100) using:
   - 60% skill match vs job requirements
   - 25% experience fit
   - 15% profile completeness
3. **Ranks candidates** per job by ATS score

Set `AI_ENABLED=true` in `.env` for future AI-enhanced skill extraction.
