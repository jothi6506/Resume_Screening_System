"""
Resume Validation Service
=========================
Provides simple, accurate validation for:
  1. Core Format Validation  — email format, phone format
  2. Section Validation      — Education, Skills, Projects (mandatory)
                             — Certifications, Experience (optional)

Section detection scans the raw extracted resume text for common
headings so it works regardless of how the AI parser classified data.
"""

import re

# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------

def validate_email_format(email):
    """
    Validate email address format only. Does NOT check existence.

    Returns (valid: bool, message: str)
    """
    if not email or email.strip().lower() in {"not provided", "none", "n/a", ""}:
        return False, "Email address not provided"

    email = email.strip()

    if " " in email:
        return False, "Email contains spaces"

    if email.count("@") != 1:
        return False, "Must contain exactly one '@'"

    username, domain = email.split("@")

    if not username:
        return False, "Username missing before '@'"

    if not domain:
        return False, "Domain missing after '@'"

    if ".." in email:
        return False, "Contains consecutive dots"

    if not re.match(r"^[a-zA-Z0-9._%+\-]+$", username):
        return False, "Invalid characters in username"

    if not re.match(r"^[a-zA-Z0-9.\-]+$", domain):
        return False, "Invalid characters in domain"

    parts = domain.split(".")
    if len(parts) < 2 or not parts[-1]:
        return False, "Domain missing a valid extension"

    ext = parts[-1].lower()
    if not ext.isalpha() or len(ext) < 2:
        return False, "Domain extension must be alphabetic (e.g. .com, .in)"

    return True, "Valid email format"


# ---------------------------------------------------------------------------
# Phone validation
# ---------------------------------------------------------------------------

# Obvious sequential/dummy patterns
_DUMMY_PHONES = {"1234567890", "0123456789", "9876543210"}


def validate_phone_format(phone):
    """
    Validate Indian mobile number format only. Does NOT verify if active.

    Returns (status: str, message: str)
    status values: 'valid' | 'invalid'
    """
    if not phone or phone.strip().lower() in {"not provided", "none", "n/a", ""}:
        return "invalid", "Phone number not provided"

    raw = phone.strip()

    # Reject anything containing letters
    if re.search(r"[a-zA-Z]", raw):
        return "invalid", "Phone number contains letters"

    # Strip allowed separators: spaces and hyphens
    stripped = raw.replace(" ", "").replace("-", "")

    # Remove country code prefix if present
    if stripped.startswith("+91"):
        stripped = stripped[3:]
    elif stripped.startswith("91") and len(stripped) == 12:
        stripped = stripped[2:]

    if not stripped.isdigit():
        return "invalid", "Phone number contains invalid characters"

    if len(stripped) != 10:
        return "invalid", f"Must be 10 digits (got {len(stripped)})"

    # Dummy / sequential patterns — still format-valid but flag informatively
    if len(set(stripped)) == 1:
        return "invalid", "All digits identical — not a valid number"

    if stripped in _DUMMY_PHONES:
        return "invalid", "Sequential dummy number not accepted"

    if stripped[0] not in {"6", "7", "8", "9"}:
        return "invalid", "Must start with 6, 7, 8, or 9"

    return "valid", "Valid phone number format"


# ---------------------------------------------------------------------------
# Section detection — scans raw resume text for common headings
# ---------------------------------------------------------------------------

# Each key maps to a list of heading patterns (case-insensitive)
SECTION_PATTERNS = {
    "education": [
        r"\beducation\b",
        r"\bacademic\s+details?\b",
        r"\bacademic\s+background\b",
        r"\bqualification[s]?\b",
        r"\beducational\s+qualification[s]?\b",
    ],
    "skills": [
        r"\bskills?\b",
        r"\btechnical\s+skills?\b",
        r"\bcore\s+competencies\b",
        r"\bkey\s+skills?\b",
        r"\bprofessional\s+skills?\b",
        r"\bsoft\s+skills?\b",
        r"\bcompetencies\b",
    ],
    "projects": [
        r"\bprojects?\b",
        r"\bacademic\s+projects?\b",
        r"\bpersonal\s+projects?\b",
        r"\bproject\s+work\b",
        r"\bproject\s+details?\b",
    ],
    "certifications": [
        r"\bcertification[s]?\b",
        r"\bcertificate[s]?\b",
        r"\bcourses?\b",
        r"\bonline\s+courses?\b",
        r"\bprofessional\s+certif",
        r"\btraining[s]?\b",
        r"\bworkshop[s]?\b",
    ],
    "experience": [
        r"\bexperience\b",
        r"\bwork\s+experience\b",
        r"\bprofessional\s+experience\b",
        r"\binternship[s]?\b",
        r"\bemployment\b",
        r"\bjob\s+history\b",
        r"\bwork\s+history\b",
        r"\bcareer\s+history\b",
    ],
}


def _section_present_in_text(section_key, text):
    """Return True if any heading pattern for *section_key* is found in *text*."""
    patterns = SECTION_PATTERNS.get(section_key, [])
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def _section_present_in_fields(section_key, candidate):
    """Fallback: check whether the corresponding candidate field has real content."""
    null_vals = {"not provided", "none", "n/a", ""}
    if section_key == "education":
        val = candidate.education or ""
        return val.strip().lower() not in null_vals
    if section_key == "skills":
        tech = (candidate.technical_skills or "").strip().lower()
        soft = (candidate.soft_skills or "").strip().lower()
        has_obj_skills = bool(candidate.skills)
        return (tech not in null_vals) or (soft not in null_vals) or has_obj_skills
    if section_key == "projects":
        val = candidate.projects or ""
        return val.strip().lower() not in null_vals
    if section_key == "certifications":
        val = candidate.certifications or ""
        return val.strip().lower() not in null_vals
    if section_key == "experience":
        val = candidate.experience or ""
        return val.strip().lower() not in null_vals
    return False


def detect_sections(candidate):
    """
    Detect presence of resume sections.

    Uses raw extracted text (best accuracy) and falls back to parsed
    candidate fields when no resume text is available.

    Returns a dict with section keys → True / False / 'na' (fresher).
    """
    # Get raw text from primary resume
    raw_text = ""
    if candidate.primary_resume and candidate.primary_resume.extracted_text:
        raw_text = candidate.primary_resume.extracted_text

    # Determine if fresher (no experience / 0–1 yr)
    null_vals = {"not provided", "none", "n/a", ""}
    exp_field = (candidate.experience or "").strip().lower()
    exp_years = candidate.years_experience
    is_fresher = (
        (exp_field in null_vals)
        or (exp_years is not None and exp_years <= 1.0)
    )

    results = {}
    for key in ("education", "skills", "projects", "certifications", "experience"):
        if raw_text:
            found = _section_present_in_text(key, raw_text)
            # Also check candidate fields as a supplementary signal
            if not found:
                found = _section_present_in_fields(key, candidate)
        else:
            found = _section_present_in_fields(key, candidate)

        if key == "experience" and is_fresher and not found:
            results[key] = "fresher"
        else:
            results[key] = found

    return results, is_fresher


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_validation_report(candidate):
    """
    Build the Resume Validation Report for a candidate.

    Returns:
        dict with keys:
          email      — {valid, message, suspicious}
          phone      — {valid, message}
          sections   — {education, skills, projects, certifications, experience}
          is_fresher — bool
    """
    email_valid, email_msg = validate_email_format(candidate.email)
    phone_status, phone_msg = validate_phone_format(candidate.phone)

    sections, is_fresher = detect_sections(candidate)

    # Detect if the email is flagged suspicious by the authenticity / suspicious detector.
    # An email is considered suspicious when:
    #   1. The primary resume has is_suspicious=True AND the authenticity report
    #      contains an "Invalid Email Format" warning, OR
    #   2. The suspicious_detector's own validate_email_format marks it invalid
    #      while the basic format check passes (edge case where the two validators differ).
    email_suspicious = False
    primary = candidate.primary_resume
    if primary and primary.is_suspicious:
        report_dict = primary.authenticity_report_dict
        failed_validations = report_dict.get("failed_validations", [])
        
        for v in failed_validations:
            if v.get("key") == "email_validation":
                email_suspicious = True
                break

    return {
        "email": {
            "valid": email_valid,
            "message": email_msg,
            "suspicious": email_suspicious,
        },
        "phone": {
            "valid": phone_status == "valid",
            "message": phone_msg,
        },
        "sections": sections,
        "is_fresher": is_fresher,
    }
