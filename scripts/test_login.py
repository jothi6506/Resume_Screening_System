"""Quick login smoke test — run: python scripts/test_login.py"""

import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///dev.db")

from app import create_app

app = create_app("development")
client = app.test_client()

resp = client.get("/auth/login")
csrf_match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resp.data.decode())
assert csrf_match, "CSRF token not found"
csrf = csrf_match.group(1)

resp = client.post(
    "/auth/login",
    data={
        "csrf_token": csrf,
        "email": "admin@resume.local",
        "password": "Admin@123",
        "remember_me": "y",
    },
    follow_redirects=True,
)
body = resp.data.decode()
assert "Signed in as HR Admin" in body, "Login failed"
print("Login test passed.")
