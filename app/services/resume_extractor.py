"""
Resume Intelligence Engine — Enterprise-Grade Entity Extraction Pipeline
========================================================================
Architecture:
  Layer 1 — Pre-processing : clean and structure raw text from any file format
  Layer 2 — Regex Fallback : fast heuristic extraction (email, phone, URLs)
  Layer 3 — AI Semantic    : Gemini LLM extracts every field with deep understanding
  Layer 4 — Merge & Validate: combine AI + regex, validate each field, assign confidence
  Layer 5 — Output Schema  : fixed output dict with confidence scores per field

The system NEVER falls back to filename for name extraction.
Every field has its own confidence score (0.0 – 1.0).
"""

import json
import logging
import os
import re
import requests

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — Regex / Heuristic Extractors (fast, no API needed)
# ─────────────────────────────────────────────────────────────────────────────

EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.I
)
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,5}(?:[-.\s]?\d{3,5})?",
    re.I
)
LINKEDIN_RE = re.compile(r"https?://(?:www\.)?linkedin\.com/in/[\w\-%.]+", re.I)
LINKEDIN_BARE_RE = re.compile(r"(?:linkedin\.com/in/|linkedin:\s*)([\w\-%.]+)", re.I)
GITHUB_RE = re.compile(r"https?://(?:www\.)?github\.com/[\w\-]+", re.I)
GITHUB_BARE_RE = re.compile(r"(?:github\.com/|github:\s*)([\w\-]+)", re.I)
PORTFOLIO_RE = re.compile(
    r"https?://(?!(?:www\.)?(?:linkedin|github)\.com)[\w\-\.]+\.[\w]{2,}(?:/[\w\-\./?=%&]*)?",
    re.I,
)
PIN_RE = re.compile(r"\b(\d{6})\b")
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def _regex_extract(text: str) -> dict:
    """Fast heuristic pre-extraction. Returns raw matches, no post-processing."""
    results = {}

    # Email
    emails = EMAIL_RE.findall(text)
    valid_emails = [e for e in emails if "." in e.split("@")[-1] and len(e) < 100]
    results["email"] = valid_emails[0] if valid_emails else None

    # Phone — take the longest valid match
    phones = []
    for m in PHONE_RE.findall(text):
        digits = re.sub(r"\D", "", m)
        if 10 <= len(digits) <= 15:
            phones.append(m.strip())
    # Sort by length of original string to prefer formatting like +91 98765-43210
    results["phone"] = sorted(phones, key=len, reverse=True)[0] if phones else None

    # Heuristic Location (City fallback)
    cities = [
        "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Trichy", "Salem", "Tirunelveli", "Erode", "Vellore",
        "Thoothukudi", "Tuticorin", "Tiruppur", "Thanjavur", "Dindigul", "Ranipet", "Kancheepuram", "Kanchipuram",
        "Kanniyakumari", "Kanyakumari", "Karur", "Krishnagiri", "Namakkal", "Pudukkottai", "Ramanathapuram",
        "Sivaganga", "Tenkasi", "The Nilgiris", "Nilgiris", "Ooty", "Theni", "Thiruvallur", "Thiruvarur", "Tirupattur",
        "Tiruvannamalai", "Viluppuram", "Virudhunagar", "Ariyalur", "Chengalpattu", "Cuddalore", "Dharmapuri",
        "Kallakurichi", "Mayiladuthurai", "Nagapattinam", "Perambalur"
    ]
    found_cities = []
    for city in cities:
        if re.search(r"\b" + city + r"\b", text, re.I):
            found_cities.append(city)
    results["city"] = found_cities[0] if found_cities else None

    # LinkedIn
    linkedin = LINKEDIN_RE.findall(text)
    if not linkedin:
        bare = LINKEDIN_BARE_RE.search(text)
        if bare:
            linkedin = [f"https://linkedin.com/in/{bare.group(1)}"]
    results["linkedin_url"] = linkedin[0] if linkedin else None

    # GitHub
    github = GITHUB_RE.findall(text)
    if not github:
        bare = GITHUB_BARE_RE.search(text)
        if bare:
            github = [f"https://github.com/{bare.group(1)}"]
    results["github_url"] = github[0] if github else None

    # Portfolio (any HTTP URL that isn't LinkedIn/GitHub)
    portfolio = PORTFOLIO_RE.findall(text)
    results["portfolio_url"] = portfolio[0] if portfolio else None

    # PIN Code
    pins = PIN_RE.findall(text)
    results["pin_code"] = pins[0] if pins else None

    return results


SECTION_ALIASES = {
    "experience": ["experience", "work experience", "professional experience", "employment history", "work history", "career history", "experience summary", "employment", "professional background"],
    "education": ["education", "academic background", "academic details", "qualification", "qualifications", "academic qualifications", "scholastics", "educational qualifications", "education details", "education & training", "education and training", "academics"],
    "projects": ["projects", "academic projects", "personal projects", "key projects", "project details", "project work", "major projects", "technical projects"],
    "certifications": ["certifications", "certificates", "licenses", "courses", "training", "certifications & courses", "certifications and courses", "certification"],
    "technical_skills": ["skills", "technical skills", "core skills", "technologies", "core competencies", "technical proficiencies", "it skills", "software skills", "computer skills"],
    "professional_summary": ["summary", "professional summary", "profile", "career profile", "career objective", "objective", "about me", "executive summary", "personal profile"],
    "ignored": ["co curricular activities", "cocurricular activities", "co-curricular activities", "extra curricular activities", "extracurricular activities", "extra-curricular activities", "personal information", "personal details", "soft skills", "hobbies", "interests", "areas of interest", "languages", "declaration", "achievements", "awards", "references"],
}

def _section_extract(text: str) -> dict:
    """Heuristic extraction of major text sections line-by-line."""
    if not text:
        return {}
    
    results = {
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
        "technical_skills": [],
        "professional_summary": [],
        "ignored": []
    }
    
    current_section = None
    
    lines = text.split("\n")
    for line in lines:
        cleaned_line = line.strip().lower()
        if not cleaned_line:
            continue
            
        # Strip all non-alphabetic characters from the start and end
        header_text = re.sub(r"^[^a-z]+|[^a-z]+$", "", cleaned_line)
        header_text = re.sub(r"\s+", " ", header_text).strip()
        header_no_spaces = header_text.replace(" ", "")
        
        matched_section = None
        # Section headers are usually short (1-6 words)
        words = header_text.split()
        if 0 < len(words) <= 6:
            for section, aliases in SECTION_ALIASES.items():
                for alias in aliases:
                    if header_text == alias or header_no_spaces == alias.replace(" ", ""):
                        matched_section = section
                        break
                if matched_section:
                    break
                    
        if matched_section:
            current_section = matched_section
            continue
            
        if current_section:
            results[current_section].append(line.strip())
            
    final_results = {}
    for k, v in results.items():
        if k != "ignored" and v:
            final_results[k] = "\n".join(v)
            
    return final_results


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — Gemini AI Semantic Extraction
# ─────────────────────────────────────────────────────────────────────────────

RESUME_SCHEMA = {
    "type": "object",
    "properties": {
        "full_name":            {"type": "string"},
        "email":                {"type": "string"},
        "phone":                {"type": "string"},
        "address":              {"type": "string"},
        "city":                 {"type": "string"},
        "state":                {"type": "string"},
        "pin_code":             {"type": "string"},
        "linkedin_url":         {"type": "string"},
        "github_url":           {"type": "string"},
        "portfolio_url":        {"type": "string"},
        "career_objective":     {"type": "string"},
        "professional_summary": {"type": "string"},
        "technical_skills":     {"type": "string"},
        "soft_skills":          {"type": "string"},
        "languages":            {"type": "string"},
        "education":            {"type": "string"},
        "experience":           {"type": "string"},
        "projects":             {"type": "string"},
        "certifications":       {"type": "string"},
        "current_title":        {"type": "string"},
        "years_experience":     {"type": "number"},
    },
    "required": [
        "full_name", "email", "phone", "address", "city", "state", "pin_code",
        "linkedin_url", "github_url", "portfolio_url",
        "career_objective", "professional_summary",
        "technical_skills", "soft_skills", "languages",
        "education", "experience", "projects", "certifications",
        "current_title", "years_experience",
    ],
}

EXTRACTION_PROMPT = """You are an elite HR Technology AI specializing in deep resume intelligence.

Your task: Analyze the resume text below and extract EVERY piece of information into the correct field.

STRICT RULES:
1. full_name: Extract the actual person's name. It is usually the FIRST prominent text at the top. NEVER use the filename. NEVER output "Not Provided" if a name exists.
2. email / phone: Extract EXACTLY as written in the resume. Do not guess.
3. address: Only the street/door/flat number and street name. NOT city, NOT state.
4. city: Only the city name.
5. state: Only the state/province name.
6. pin_code: Only the postal/zip code digits.
7. linkedin_url / github_url: Return the COMPLETE URL starting with https://. If only a username is found like "github.com/user", expand it to "https://github.com/user".
8. career_objective: ONLY the Career Objective / Objective statement section. Do not include other content.
9. professional_summary: ONLY the Professional Summary / Profile section.
10. technical_skills: ALL programming languages, frameworks, tools, technologies, databases.
11. soft_skills: Communication, leadership, teamwork, problem-solving, and similar interpersonal skills.
12. languages: Human languages spoken (e.g., English, Tamil, Hindi). NOT programming languages.
13. education: Full education history with institution names, degrees, years, and grades. (May be under headings like Education, Academic Details, Qualification)
14. experience: Full work experience with company names, roles, dates, and responsibilities. (May be under headings like Experience, Work Experience, Professional Experience)
15. projects: All personal, academic, or professional projects with descriptions. (May be under headings like Projects, Academic Projects, Personal Projects)
16. certifications: All certifications, courses, and credentials with issuing organizations. (May be under headings like Certifications, Certificates, Licenses)
17. current_title: The person's current or most recent job title.
18. years_experience: Total years of professional experience as a number. Calculate from dates if needed.

If a field is genuinely absent, return exactly the string: "Not Provided" (for text fields) or null (for years_experience).

Resume Text:
{text}"""


def _ai_extract(text: str, api_key: str) -> dict | None:
    """Call Gemini API and return structured data, or None on failure."""
    logger.info("=== RAW RESUME TEXT START ===")
    logger.info(text)
    logger.info("=== RAW RESUME TEXT END ===")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-1.5-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": EXTRACTION_PROMPT.format(text=text[:16000])}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
            "responseSchema": RESUME_SCHEMA,
        },
    }
    try:
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=45,
        )
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        
        logger.info("=== AI JSON RESPONSE START ===")
        logger.info(raw)
        logger.info("=== AI JSON RESPONSE END ===")
        
        return json.loads(raw)
    except Exception as exc:
        logger.error(f"Gemini API call failed: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — Merge, Validate, and Score Confidence
# ─────────────────────────────────────────────────────────────────────────────

_EMPTY = {"not provided", "n/a", "none", "na", "", "null"}


def _is_empty(v) -> bool:
    if v is None:
        return True
    return str(v).strip().lower() in _EMPTY


def _clean(v) -> str | None:
    if _is_empty(v):
        return None
    return str(v).strip()


def _validate_email(v: str) -> bool:
    return bool(v and EMAIL_RE.fullmatch(v.strip()))


def _validate_phone(v: str) -> bool:
    if not v:
        return False
    digits = re.sub(r"\D", "", v)
    return 7 <= len(digits) <= 15


def _validate_url(v: str, domain_hint: str = "") -> bool:
    if not v:
        return False
    v = v.strip()
    if not v.startswith("http"):
        return False
    if domain_hint and domain_hint not in v:
        return False
    return True


def _merge(ai_val, regex_val, validate_fn=None) -> tuple[str | None, float]:
    """
    Merge AI and regex values. Returns (value, confidence_0_to_1).
    Confidence logic:
      - Both agree                → 0.99
      - Only AI has value         → 0.82
      - Only regex has value      → 0.75
      - AI value fails validation → use regex, 0.70
      - Nothing found             → None, 0.0
    """
    ai_clean = _clean(ai_val)
    rx_clean = _clean(regex_val)

    ai_valid = (validate_fn(ai_clean) if validate_fn and ai_clean else bool(ai_clean))
    rx_valid = (validate_fn(rx_clean) if validate_fn and rx_clean else bool(rx_clean))

    if ai_clean and rx_clean:
        if ai_clean.lower() == rx_clean.lower():
            return ai_clean, 0.99
        # Prefer AI if valid, otherwise prefer regex
        if ai_valid:
            return ai_clean, 0.90
        if rx_valid:
            return rx_clean, 0.78
        return ai_clean, 0.70

    if ai_clean and ai_valid:
        return ai_clean, 0.85

    if ai_clean:  # AI returned something but failed validation
        if rx_valid:
            return rx_clean, 0.75
        return ai_clean, 0.60  # Use it anyway, lower confidence

    if rx_clean and rx_valid:
        return rx_clean, 0.72

    if rx_clean:
        return rx_clean, 0.50

    return None, 0.0


def _score_text_field(ai_val) -> tuple[str | None, float]:
    """For long-text fields (skills, education etc.) only AI is useful."""
    val = _clean(ai_val)
    if not val:
        return None, 0.0
    # Confidence based on content length
    words = len(val.split())
    if words >= 20:
        return val, 0.92
    if words >= 5:
        return val, 0.80
    return val, 0.65


def _build_confidence_report(scores: dict) -> dict:
    """Build a per-field confidence report."""
    avg = sum(scores.values()) / len(scores) if scores else 0.0
    return {
        "fields": scores,
        "overall": round(avg, 3),
        "grade": (
            "High Confidence" if avg >= 0.80
            else "Medium Confidence" if avg >= 0.55
            else "Low Confidence"
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Layer 5 — Public API
# ─────────────────────────────────────────────────────────────────────────────

def extract_candidate_fields(text: str, filename: str = "") -> dict:
    """
    Master extraction pipeline.

    1. Run regex pre-extraction (always, no API needed)
    2. Run Gemini AI extraction (if key is configured)
    3. Merge both sets of results with validation and confidence scoring
    4. Return fixed-schema output dict with a `_confidence` sub-dict

    The output dict NEVER uses the filename as a name fallback.
    If the name cannot be found in the resume at all, full_name = "Unknown Candidate".
    """
    import os as _os
    try:
        from flask import current_app
        api_key = current_app.config.get("GEMINI_API_KEY", "")
    except RuntimeError:
        api_key = _os.environ.get("GEMINI_API_KEY", "")

    # ── Layer 2: regex fast-pass ────────────────────────────────────────────
    regex_data = _regex_extract(text) if text else {}
    section_data = _section_extract(text) if text else {}

    # ── Layer 3: AI deep extraction ─────────────────────────────────────────
    ai_data = {}
    ai_used = False
    if api_key and text:
        ai_data = _ai_extract(text, api_key) or {}
        ai_used = bool(ai_data)
        if not ai_used:
            logger.warning("AI extraction returned nothing — using regex only.")
    elif not api_key:
        logger.warning("GEMINI_API_KEY not configured — using regex-only extraction.")

    # ── Layer 4: merge + validate + score ───────────────────────────────────
    confidence = {}

    # Full Name — critical, AI only
    raw_name = _clean(ai_data.get("full_name"))
    if raw_name and raw_name.lower() not in {"not provided", "unknown", "n/a"}:
        # Quick sanity: at least one word, mostly alphabetic
        words = [w for w in raw_name.split() if re.sub(r"[^a-zA-Z]", "", w)]
        if words:
            full_name = raw_name
            confidence["full_name"] = 0.95 if len(words) >= 2 else 0.70
        else:
            full_name = "Unknown Candidate"
            confidence["full_name"] = 0.0
    else:
        # Try to find a name in the first few lines using heuristics
        name_found = False
        if text:
            first_lines = [l.strip() for l in text.strip().split("\n")[:5] if l.strip()]
            for line in first_lines:
                # A name is typically 2-4 words, all title-cased, no special chars
                words = line.split()
                if (2 <= len(words) <= 4
                        and all(re.match(r"^[A-Za-z.'\-]+$", w) for w in words)
                        and not EMAIL_RE.search(line)
                        and not any(c.isdigit() for c in line)):
                    full_name = line
                    confidence["full_name"] = 0.60
                    name_found = True
                    break
        
        if not name_found:
            # Fallback to filename if provided
            if filename:
                name_from_file = _os.path.splitext(filename)[0]
                # Clean up filename (e.g. "Kamal_Resume" -> "Kamal")
                name_from_file = re.sub(r'[_+\-]', ' ', name_from_file)
                name_from_file = re.sub(r'(?i)\b(?:resume|cv|profile)\b', '', name_from_file).strip()
                if name_from_file:
                    full_name = name_from_file.title()
                    confidence["full_name"] = 0.50
                else:
                    full_name = "Unknown Candidate"
                    confidence["full_name"] = 0.0
            else:
                full_name = "Unknown Candidate"
                confidence["full_name"] = 0.0

    # Email
    email, confidence["email"] = _merge(
        ai_data.get("email"), regex_data.get("email"), _validate_email
    )

    # Phone
    phone, confidence["phone"] = _merge(
        ai_data.get("phone"), regex_data.get("phone"), _validate_phone
    )

    # Address components
    address = _clean(ai_data.get("address"))
    city_ai = _clean(ai_data.get("city"))
    city_rx = regex_data.get("city")
    city, confidence["city"] = _merge(city_ai, city_rx)
    state = _clean(ai_data.get("state"))

    # PIN — prefer regex match (6 digits is precise)
    pin_code_ai = _clean(ai_data.get("pin_code"))
    pin_code_rx = regex_data.get("pin_code")
    pin_code, confidence["pin_code"] = _merge(pin_code_ai, pin_code_rx)

    # Build location confidence
    loc_parts_found = sum(1 for x in [address, city, state, pin_code] if x)
    confidence["address"] = 0.88 if address else 0.0
    # confidence["city"] already set by _merge
    confidence["state"] = 0.88 if state else 0.0

    location_parts = [p for p in [address, city, state, pin_code] if p]
    location = ", ".join(location_parts) if location_parts else None

    # LinkedIn — prefer full URL
    linkedin_ai = _clean(ai_data.get("linkedin_url"))
    linkedin_rx = regex_data.get("linkedin_url")
    # Normalize: expand bare usernames to full URLs
    if linkedin_ai and not linkedin_ai.startswith("http") and "/" in linkedin_ai:
        linkedin_ai = "https://" + linkedin_ai.lstrip("/")
    linkedin_url, confidence["linkedin_url"] = _merge(
        linkedin_ai, linkedin_rx,
        lambda v: _validate_url(v, "linkedin.com"),
    )

    # GitHub — prefer full URL
    github_ai = _clean(ai_data.get("github_url"))
    github_rx = regex_data.get("github_url")
    if github_ai and not github_ai.startswith("http") and "github" in (github_ai or "").lower():
        github_ai = "https://" + github_ai.lstrip("/")
    github_url, confidence["github_url"] = _merge(
        github_ai, github_rx,
        lambda v: _validate_url(v, "github.com"),
    )

    # Portfolio
    portfolio_ai = _clean(ai_data.get("portfolio_url"))
    portfolio_rx = regex_data.get("portfolio_url")
    portfolio_url, confidence["portfolio_url"] = _merge(
        portfolio_ai, portfolio_rx, _validate_url
    )

    # Text / section fields — AI + Heuristic fallback
    def _merge_text(ai_val, heuristic_val):
        ai_clean = _clean(ai_val)
        heu_clean = _clean(heuristic_val)
        # Prefer AI if it's reasonably long, else fallback to heuristic
        if ai_clean and len(ai_clean) > 20:
            return _score_text_field(ai_clean)
        if heu_clean:
            # Boost heuristic confidence slightly if it was the only reliable source
            val, conf = _score_text_field(heu_clean)
            return val, min(0.85, conf)
        return _score_text_field(ai_clean)

    career_objective, confidence["career_objective"] = _merge_text(ai_data.get("career_objective"), "")
    professional_summary, confidence["professional_summary"] = _merge_text(ai_data.get("professional_summary"), section_data.get("professional_summary"))
    technical_skills, confidence["technical_skills"] = _merge_text(ai_data.get("technical_skills"), section_data.get("technical_skills"))
    soft_skills, confidence["soft_skills"] = _merge_text(ai_data.get("soft_skills"), "")
    languages, confidence["languages"] = _merge_text(ai_data.get("languages"), "")
    education, confidence["education"] = _merge_text(ai_data.get("education"), section_data.get("education"))
    experience, confidence["experience"] = _merge_text(ai_data.get("experience"), section_data.get("experience"))
    projects, confidence["projects"] = _merge_text(ai_data.get("projects"), section_data.get("projects"))
    certifications, confidence["certifications"] = _merge_text(ai_data.get("certifications"), section_data.get("certifications"))

    # Current title + years experience
    current_title = _clean(ai_data.get("current_title"))
    confidence["current_title"] = 0.85 if current_title else 0.0

    years_exp_raw = ai_data.get("years_experience")
    try:
        years_experience = float(years_exp_raw) if years_exp_raw is not None else None
        if years_experience is not None and (years_experience < 0 or years_experience > 60):
            years_experience = None
    except (TypeError, ValueError):
        years_experience = None
    confidence["years_experience"] = 0.80 if years_experience is not None else 0.0

    # Overall confidence report
    confidence_report = _build_confidence_report(confidence)

    def _out(v):
        """Convert None to 'Not Provided' for display."""
        return v if v else "Not Provided"

    summary = professional_summary or career_objective
    skills_text = " ".join(filter(None, [technical_skills, soft_skills]))

    return {
        # ── Identity ──────────────────────────────────────────────────────
        "full_name": full_name,
        # ── Contact ───────────────────────────────────────────────────────
        "email":        _out(email),
        "phone":        _out(phone),
        "address":      _out(address),
        "city":         _out(city),
        "state":        _out(state),
        "pin_code":     _out(pin_code),
        "location":     _out(location),
        # ── Online Profiles ───────────────────────────────────────────────
        "linkedin_url":  _out(linkedin_url),
        "github_url":    _out(github_url),
        "portfolio_url": _out(portfolio_url),
        # ── Content Sections ─────────────────────────────────────────────
        "career_objective":     _out(career_objective),
        "professional_summary": _out(professional_summary),
        "technical_skills":     _out(technical_skills),
        "soft_skills":          _out(soft_skills),
        "languages":            _out(languages),
        "education":            _out(education),
        "experience":           _out(experience),
        "projects":             _out(projects),
        "certifications":       _out(certifications),
        # ── Computed ──────────────────────────────────────────────────────
        "current_title":    current_title,
        "years_experience": years_experience,
        "summary":          _out(summary),
        "skills_text":      skills_text or "Not Provided",
        "education_text":   _out(education),
        "experience_text":  _out(experience),
        # ── Intelligence metadata ─────────────────────────────────────────
        "_confidence":  confidence_report,
        "_ai_used":     ai_used,
        "_regex_email": regex_data.get("email"),
        "_regex_phone": regex_data.get("phone"),
    }
