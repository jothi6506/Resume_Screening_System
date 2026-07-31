"""Quick smoke test for all dashboard features."""
from app import create_app
from app.extensions import db
from app.models.user import User
from flask_login import login_user

app = create_app()
app.config["WTF_CSRF_ENABLED"] = False

errors = []
passed = []

with app.test_request_context():
    with app.test_client() as c:
        # Force login by setting session
        with c.session_transaction() as sess:
            user = User.query.first()
            if not user:
                print("ERROR: No users in database!")
                exit(1)
        
        # Login through the app 
        with app.test_request_context():
            user = User.query.first()

        # Use a workaround: directly login
        @app.route("/_test_login")
        def _test_login():
            user = User.query.first()
            login_user(user)
            return "ok"
        
        c.get("/_test_login")
        
        # Now test all endpoints
        tests = {
            "Dashboard": "/dashboard",
            "Dashboard Stats API": "/api/dashboard-stats",
            "Search API": "/api/search?q=a",
            "Jobs Page": "/jobs",
            "Candidates Page": "/candidates",
            "Candidates Shortlisted": "/candidates?status=shortlisted",
            "Candidates Rejected": "/candidates?status=rejected",
            "Analytics": "/analytics",
            "Email History": "/emails",
            "Email Settings": "/settings/email",
            "Upload Page": "/upload",
        }
        
        for name, url in tests.items():
            try:
                r = c.get(url)
                if r.status_code == 200:
                    passed.append(name)
                elif r.status_code == 302:
                    errors.append(f"{name}: Got redirect (302) - likely auth issue")
                else:
                    errors.append(f"{name}: Got status {r.status_code}")
            except Exception as e:
                errors.append(f"{name}: Exception - {e}")

        # Test the stats API response
        r = c.get("/api/dashboard-stats")
        if r.status_code == 200:
            import json
            data = json.loads(r.data)
            expected_keys = ["total_candidates", "total_applicants", "shortlisted", "rejected", 
                           "total_jobs", "active_jobs", "draft_jobs", "closed_jobs", 
                           "suspicious_resumes", "pipeline", "recent_activities"]
            for key in expected_keys:
                if key not in data:
                    errors.append(f"Stats API: Missing key '{key}'")
            if "pipeline" in data:
                for stage in ["new", "reviewing", "shortlisted", "rejected", "hired"]:
                    if stage not in data["pipeline"]:
                        errors.append(f"Stats API: Pipeline missing '{stage}'")
            passed.append("Stats API Structure")

        # Test search API response
        r = c.get("/api/search?q=a")
        if r.status_code == 200:
            data = json.loads(r.data)
            if "candidates" in data and "jobs" in data:
                passed.append("Search API Structure")
            else:
                errors.append("Search API: Missing candidates/jobs keys")

print(f"\n{'='*50}")
print(f"PASSED: {len(passed)}")
for t in passed:
    print(f"  ✓ {t}")
print(f"\nFAILED: {len(errors)}")
for e in errors:
    print(f"  ✗ {e}")
print(f"{'='*50}")
