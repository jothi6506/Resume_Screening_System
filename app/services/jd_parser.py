"""Parse uploaded Job Description documents (PDF, DOCX, TXT) and extract structured details."""

import os
import re
import logging
from app.services.resume_parser import extract_text, ResumeParserError
from app.services.skill_extractor import extract_skills_from_text

logger = logging.getLogger(__name__)

# Regular expressions for experience extraction
EXP_PATTERNS = [
    r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?',
    r'(\d+)\s*-\s*(\d+)\s*(?:years?|yrs?)',
    r'experience\s*:\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)'
]

# Qualification keywords mapping to form options
QUALIFICATION_MAP = [
    (r'\b(?:phd|doctorate)\b', "PhD"),
    (r'\b(?:mba)\b', "MBA"),
    (r'\b(?:master\'?s|m\.e|m\.tech|mca|m\.sc|post\s*graduate)\b', "Master's"),
    (r'\b(?:bachelor\'?s|b\.e|b\.tech|bca|b\.sc|undergraduate|degree|graduate)\b', "Bachelor's"),
    (r'\b(?:diploma)\b', "Diploma"),
    (r'\b(?:12th|hsc)\b', "12th"),
    (r'\b(?:10th|sslc)\b', "10th"),
]

# Common certification patterns
CERTIFICATION_PATTERNS = [
    r'\b(?:aws\s+certified[^\n,.]*)',
    r'\b(?:azure\s+certified[^\n,.]*)',
    r'\b(?:pmp|prince2)\b',
    r'\b(?:scrum\s+master|csm)\b',
    r'\b(?:cissp|cisa|cism)\b',
    r'\b(?:google\s+cloud\s+certified[^\n,.]*)',
    r'\b(?:certified\s+[a-z0-9\s]+)',
]


def extract_jd_text(file_storage):
    """Extract plain text from uploaded file storage (PDF, DOCX, TXT)."""
    filename = file_storage.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "txt":
        content = file_storage.read()
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="ignore")

    # For PDF/DOCX, temporarily save file to extract using existing parser
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
        file_storage.save(temp_file.name)
        temp_path = temp_file.name

    try:
        text = extract_text(temp_path, ext)
        return text
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def parse_job_description(text, original_filename=""):
    """
    Parse Job Description text and return extracted fields:
    title, required_skills, min_experience, min_qualification,
    certifications, description, requirements, keywords.
    """
    if not text or not text.strip():
        return {
            "title": "",
            "required_skills": [],
            "required_skills_text": "",
            "min_experience": 0.0,
            "min_qualification": "",
            "certifications": [],
            "description": "",
            "requirements": "",
            "keywords": [],
        }

    normalized = text.strip()
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]

    # 1. Job Title Extraction
    title = ""
    # Try finding explicit title tag line
    for line in lines[:10]:
        title_match = re.search(r'(?:job\s*title|position|role)\s*[:|-]\s*(.*)', line, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            break

    if not title:
        # Check first non-empty header-like line
        for line in lines[:5]:
            if len(line) < 80 and not line.lower().startswith(("about", "company", "overview")):
                title = line
                break

    if not title and original_filename:
        # Use filename as title clean fallback
        base = original_filename.rsplit(".", 1)[0]
        title = re.sub(r'[-_]', ' ', base).title()

    # 2. Extract Required Skills
    extracted_skills = extract_skills_from_text(normalized)
    skill_names = [s["name"] for s in extracted_skills]

    # 3. Minimum Experience Extraction
    min_exp = 0.0
    text_lower = normalized.lower()

    if "fresher" in text_lower or "entry level" in text_lower:
        min_exp = 0.0
    else:
        for pattern in EXP_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                groups = match.groups()
                if len(groups) >= 2 and groups[1]:
                    min_exp = float(groups[0])
                elif groups[0]:
                    min_exp = float(groups[0])
                break

    # 4. Minimum Qualification Extraction
    min_qual = ""
    for pattern, qual_value in QUALIFICATION_MAP:
        if re.search(pattern, text_lower):
            min_qual = qual_value
            break

    # 5. Certifications Extraction
    certifications = []
    for cert_pat in CERTIFICATION_PATTERNS:
        matches = re.findall(cert_pat, text_lower)
        for m in matches:
            cert_str = m.strip().title()
            if cert_str not in certifications:
                certifications.append(cert_str)

    # 6. Description & Requirements Split
    req_split = re.split(r'\n(?=requirements|qualifications|what you need|responsibilities|what we are looking for)', normalized, flags=re.IGNORECASE)
    if len(req_split) > 1:
        description = req_split[0].strip()
        requirements = "\n".join(req_split[1:]).strip()
    else:
        description = normalized[:1500].strip()
        requirements = normalized[1500:].strip() if len(normalized) > 1500 else normalized

    # 7. Keywords
    keywords = list(dict.fromkeys(skill_names + certifications))

    return {
        "title": title,
        "required_skills": skill_names,
        "required_skills_text": ", ".join(skill_names),
        "min_experience": min_exp,
        "min_qualification": min_qual,
        "certifications": certifications,
        "description": description,
        "requirements": requirements,
        "keywords": keywords,
    }
