from app import create_app, db
from app.models.resume import Resume
import json

app = create_app()

with app.app_context():
    resumes = Resume.query.all()
    updated = 0
    for r in resumes:
        if r.authenticity_report:
            try:
                report = json.loads(r.authenticity_report)
                classification = report.get('classification', 'Genuine')
                is_suspicious = classification != 'Genuine'
                if r.is_suspicious != is_suspicious:
                    r.is_suspicious = is_suspicious
                    updated += 1
            except Exception as e:
                print(f"Error parsing resume {r.id}: {e}")
    
    db.session.commit()
    print(f"Updated {updated} resumes.")
