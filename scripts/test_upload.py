"""Upload and parsing smoke tests."""

import io
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///dev.db")

from app import create_app
from app.extensions import db
from app.models import Candidate, Resume
from app.services.resume_extractor import extract_candidate_fields
from app.services.resume_parser import extract_text_from_pdf
from app.services.upload_service import process_resume_file

SAMPLE_TEXT = """
Jane Smith
Senior Python Developer
jane.smith@example.com
+1 (555) 123-4567
linkedin.com/in/janesmith

5 years of experience in Python and Flask development.
"""

MINIMAL_PDF = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj
4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
5 0 obj<</Length 120>>stream
BT /F1 12 Tf 100 700 Td (Jane Smith) Tj 0 -20 Td (jane.smith@example.com) Tj 0 -20 Td (Python Developer) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000261 00000 n 
0000000340 00000 n 
trailer<</Size 6/Root 1 0 R>>
startxref
511
%%EOF"""


def test_extractor():
    fields = extract_candidate_fields(SAMPLE_TEXT, "jane_smith_resume.pdf")
    assert fields["full_name"] == "Jane Smith"
    assert fields["email"] == "jane.smith@example.com"
    assert fields["years_experience"] == 5.0
    print("Extractor test passed.")


def test_parser_and_upload_service():
    app = create_app("development")

    pdf_path = os.path.join(tempfile.gettempdir(), "test_resume_upload.pdf")
    with open(pdf_path, "wb") as f:
        f.write(MINIMAL_PDF)

    with app.app_context():
        text = extract_text_from_pdf(pdf_path)
        assert len(text) > 0
        print("PDF parser test passed.")

        from werkzeug.datastructures import FileStorage

        with open(pdf_path, "rb") as f:
            storage = FileStorage(stream=f, filename="jane_smith.pdf", content_type="application/pdf")
            result = process_resume_file(storage)

        assert result["success"] is True
        assert result["candidate_name"]
        candidate = db.session.get(Candidate, result["candidate_id"])
        assert candidate is not None
        resume = db.session.get(Resume, result["resume_id"])
        assert resume.parse_status == "completed"
        print("Upload service test passed.")

    os.remove(pdf_path)


def test_upload_page():
    app = create_app("development")
    client = app.test_client()

    resp = client.get("/auth/login")
    csrf = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resp.data.decode()).group(1)
    client.post(
        "/auth/login",
        data={"csrf_token": csrf, "email": "admin@resume.local", "password": "Admin@123"},
    )

    resp = client.get("/upload")
    assert resp.status_code == 200
    assert "Bulk Resume Upload" in resp.data.decode()
    print("Upload page test passed.")


if __name__ == "__main__":
    test_extractor()
    test_parser_and_upload_service()
    test_upload_page()
    print("All upload tests passed.")
