from dotenv import load_dotenv
load_dotenv()
from app import create_app
from app.models import Candidate

app = create_app()
with app.app_context():
    for c in Candidate.query.all():
        print(f"\n{'='*60}")
        print(f"Name    : {c.full_name}")
        print(f"Email   : {c.email}")
        print(f"Phone   : {c.phone}")
        print(f"Location: {c.location}")
        print(f"LinkedIn: {c.linkedin_url}")
        print(f"GitHub  : {c.github_url}")
        print(f"Summary : {c.summary[:150] if c.summary else 'NONE'}...")
