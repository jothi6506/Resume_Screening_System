"""Test the new job API endpoints (GET and UPDATE)."""
from app import create_app
from flask_login import login_user
from app.models.user import User
from app.models.job import Job
import json

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False

@app.route('/_test_login')
def _test_login():
    u = User.query.first()
    login_user(u)
    return 'ok'

with app.test_client() as c:
    c.get('/_test_login')
    
    with app.app_context():
        job = Job.query.first()
    
    if not job:
        print('No jobs in DB — create a job first to test the API.')
    else:
        jid = job.id
        orig_title = job.title
        orig_status = job.status
        print(f'Testing job #{jid}: {orig_title}')
        
        # Test GET
        r = c.get(f'/api/jobs/{jid}')
        data = json.loads(r.data)
        assert r.status_code == 200, f'Expected 200, got {r.status_code}'
        expected_keys = ['id', 'title', 'status', 'skills', 'required_skills_text', 'created_at']
        for k in expected_keys:
            assert k in data, f'Missing key: {k}'
        print(f'  GET /api/jobs/{jid}: 200 OK  title="{data["title"]}"')
        
        # Test UPDATE - change title and status
        new_title = orig_title + ' (EDITED)'
        payload = {
            'title': new_title,
            'status': data['status'],
            'employment_type': data['employment_type'],
            'min_experience': data['min_experience'],
        }
        r2 = c.post(f'/api/jobs/{jid}/update',
                    data=json.dumps(payload),
                    content_type='application/json')
        d2 = json.loads(r2.data)
        assert r2.status_code == 200, f'Expected 200, got {r2.status_code}: {d2}'
        assert d2['success'] is True, f'Expected success=True: {d2}'
        assert d2['job']['title'] == new_title
        print(f'  POST /api/jobs/{jid}/update: 200 OK  success=True  title="{d2["job"]["title"]}"')
        
        # Test missing title validation
        r3 = c.post(f'/api/jobs/{jid}/update',
                    data=json.dumps({'title': ''}),
                    content_type='application/json')
        d3 = json.loads(r3.data)
        assert r3.status_code == 400
        assert d3['success'] is False
        print(f'  Validation test (empty title): 400 Bad Request  success=False ✓')
        
        # Restore original title
        c.post(f'/api/jobs/{jid}/update',
               data=json.dumps({'title': orig_title, 'status': orig_status, 'employment_type': data['employment_type'], 'min_experience': data['min_experience']}),
               content_type='application/json')
        print(f'  Restored original title.')
        
        print('\nAll Job API tests PASSED! ✓')
