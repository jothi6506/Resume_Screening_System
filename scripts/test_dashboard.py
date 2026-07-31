"""Dashboard smoke test."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///dev.db")

from app import create_app

app = create_app("development")
client = app.test_client()

resp = client.get("/auth/login")
csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resp.data.decode())
csrf = csrf_match.group(1)

client.post(
    "/auth/login",
    data={"csrf_token": csrf, "email": "admin@resume.local", "password": "Admin@123"},
)

resp = client.get("/dashboard")
body = resp.data.decode()
assert resp.status_code == 200
assert "dashboard-sidebar" in body
assert "Total Candidates" in body
assert "Hiring Pipeline" in body
print("Dashboard test passed.")

resp2 = client.get("/candidates")
assert resp2.status_code == 200
assert "Candidates" in resp2.data.decode()
print("Navigation test passed.")
