"""
Intelligent Fake/Suspicious Resume Detection Service
====================================================
Advanced validation system using logical analysis and evidence-based scoring.

Scoring System:
- Suspicious Score: 0-100 (higher = more suspicious)
- Classification: Genuine (0-24), Needs Review (25-49), Suspicious (50-100)
- Each failed validation adds weighted points to the suspicious score

Validation Rules with Weights:
- Fake/placeholder email: +25
- Dummy/invalid phone: +20
- Invalid/fake location: +15
- Impossible experience timeline: +30
- Overlapping full-time employment: +25
- Unrealistic experience: +20
- Impossible achievements: +20
- Unrealistic projects: +15
- Keyword stuffing: +15
- Section contradictions: +15
- AI-generated repetitive content: +10
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import TYPE_CHECKING

try:
    import phonenumbers
    PHONENUMBERS_AVAILABLE = True
except ImportError:
    PHONENUMBERS_AVAILABLE = False

try:
    from email_validator import validate_email as validate_email_lib
    EMAIL_VALIDATOR_AVAILABLE = True
except ImportError:
    EMAIL_VALIDATOR_AVAILABLE = False

from dateutil import parser as date_parser

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.candidate import Candidate


# ─────────────────────────────────────────────────────────────────────────────
# Validation Patterns and Lists
# ─────────────────────────────────────────────────────────────────────────────

# Fake/placeholder domains
FAKE_DOMAINS = {
    "example.com", "test.com", "sample.com", "fake.com", "demo.com",
    "invalid.com", "placeholder.com", "notreal.com", "temp.com",
}

# Disposable email providers
DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "temp-mail.org", "10minutemail.com",
    "throwawaymail.com", "getairmail.com", "yopmail.com", "sharklasers.com",
}

# Dummy phone patterns
DUMMY_PHONE_PATTERNS = [
    r"9999999999", r"1111111111", r"1234567890", r"0000000000",
    r"5555555555", r"8888888888", r"7777777777", r"4444444444",
    r"3333333333", r"2222222222", r"6666666666",
]

# Indian cities and states for validation (can be expanded)
INDIAN_CITIES = {
    "chennai": "tamil nadu", "coimbatore": "tamil nadu", "madurai": "tamil nadu",
    "trichy": "tamil nadu", "salem": "tamil nadu", "tirunelveli": "tamil nadu",
    "erode": "tamil nadu", "vellore": "tamil nadu", "tiruppur": "tamil nadu",
    "bangalore": "karnataka", "bengaluru": "karnataka", "mysore": "karnataka",
    "hubli": "karnataka", "mangalore": "karnataka",
    "mumbai": "maharashtra", "pune": "maharashtra", "nagpur": "maharashtra",
    "nashik": "maharashtra", "aurangabad": "maharashtra",
    "delhi": "delhi", "new delhi": "delhi",
    "hyderabad": "telangana", "secunderabad": "telangana",
    "kolkata": "west bengal", "howrah": "west bengal",
    "ahmedabad": "gujarat", "surat": "gujarat", "vadodara": "gujarat",
    "jaipur": "rajasthan", "jodhpur": "rajasthan", "udaipur": "rajasthan",
    "lucknow": "uttar pradesh", "kanpur": "uttar pradesh", "agra": "uttar pradesh",
    "chandigarh": "punjab", "amritsar": "punjab", "ludhiana": "punjab",
}

# Invalid location indicators
INVALID_LOCATION_INDICATORS = {
    "n/a", "na", "not provided", "unknown", "anywhere", "remote only",
    "worldwide", "global", "earth", "planet", "universe",
}

# AI-generated content patterns
AI_GENERATED_PATTERNS = [
    r"as an ai language model",
    r"i am writing this resume to",
    r"\[your name\]", r"\[your email\]", r"\[company name\]",
    r"lorem ipsum", r"insert your", r"your address here",
    r"passionate about contributing", r"eager to leverage my skills",
    r"seeking an opportunity to", r"looking for a challenging position",
]

# Buzzwords that may indicate keyword stuffing
BUZZWORDS = [
    "innovative", "dynamic", "cutting-edge", "groundbreaking", "revolutionary",
    "world-class", "best-in-class", "state-of-the-art", "industry-leading",
    "transformative", "disruptive", "visionary", "strategic", "synergy",
]

# Unrealistic achievement indicators
UNREALISTIC_METRICS = [
    r"increased by \d{3,4}%", r"reduced by \d{3,4}%", r"saved \$\d{3,}",
    r"generated \$\d{4,}", r"improved by \d{3,4}%", r"grew by \d{3,4}%",
]

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def _validation_result(key: str, weight: int, passed: bool, detail: str, evidence: str = "", rule_name: str = "") -> dict:
    """Standard validation result format."""
    return {
        "key": key,
        "rule_name": rule_name,
        "weight": weight,
        "passed": passed,
        "detail": detail,
        "evidence": evidence,
    }


def _extract_domain(email: str) -> str | None:
    """Extract domain from email address."""
    if not email or "@" not in email:
        return None
    return email.split("@")[-1].lower().strip()


def _is_repeated_digit_number(phone: str) -> bool:
    """Check if phone number consists of repeated digits."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 7:
        return False
    return len(set(digits)) <= 2


def _parse_date_range(text: str) -> tuple[datetime | None, datetime | None]:
    """Parse date range from text (e.g., 'Jan 2020 - Dec 2022')."""
    if not text:
        return None, None
    
    # Common date patterns
    date_patterns = [
        r"(\w{3}\s+\d{4})\s*[-–to]+\s*(\w{3}\s+\d{4})",
        r"(\d{1,2}/\d{4})\s*[-–to]+\s*(\d{1,2}/\d{4})",
        r"(\d{4})\s*[-–to]+\s*(\d{4})",
        r"(\w+\s+\d{4})\s*[-–to]+\s*(\w+\s+\d{4})",
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            try:
                start_date = date_parser.parse(match.group(1), fuzzy=True)
                end_str = match.group(2).lower()
                if "present" in end_str or "current" in end_str:
                    end_date = datetime.now()
                else:
                    end_date = date_parser.parse(match.group(2), fuzzy=True)
                return start_date, end_date
            except Exception:
                continue
    
    return None, None


def _calculate_years_between(start: datetime, end: datetime) -> float:
    """Calculate years between two dates."""
    if not start or not end:
        return 0.0
    return (end - start).days / 365.25


def _detect_fresher_status(candidate: Candidate) -> dict:
    """
    Detect if candidate is a fresher/student based on profile indicators.
    
    Returns:
        {
            "is_fresher": bool,
            "reason": str
        }
    """
    # Check for fresher indicators
    fresher_indicators = []
    
    # No experience or very little experience
    years = candidate.years_experience
    if years is None or years == 0:
        fresher_indicators.append("No years of experience specified")
    elif years is not None and years <= 1:
        fresher_indicators.append(f"Low experience ({years} years)")
    
    # Missing experience section
    if not candidate.experience or candidate.experience.strip() == "" or candidate.experience == "Not Provided":
        fresher_indicators.append("No experience section")
    
    # Education indicators (recent graduate or current student)
    education = candidate.education or ""
    if education:
        # Check for current/recent education
        current_year = datetime.now().year
        recent_years = [str(current_year), str(current_year - 1), str(current_year - 2)]
        if any(year in education for year in recent_years):
            fresher_indicators.append("Recent education (within 2 years)")
        
        # Check for student indicators
        student_keywords = ["student", "pursuing", "current", "ongoing", "final year", "bachelor", "b.tech", "b.e.", "bsc", "ba"]
        if any(keyword in education.lower() for keyword in student_keywords):
            fresher_indicators.append("Student status indicated in education")
    
    # Career objective indicators
    objective = candidate.career_objective or ""
    summary = candidate.professional_summary or ""
    combined_text = (objective + " " + summary).lower()
    
    fresher_keywords = ["fresher", "entry level", "recent graduate", "new graduate", "looking for opportunity", "seeking entry", "campus placement"]
    if any(keyword in combined_text for keyword in fresher_keywords):
        fresher_indicators.append("Fresher/entry-level indicator in objective/summary")
    
    # Determine if fresher
    is_fresher = len(fresher_indicators) >= 2  # At least 2 indicators
    
    return {
        "is_fresher": is_fresher,
        "reason": "; ".join(fresher_indicators) if fresher_indicators else "Not identified as fresher"
    }


# ─────────────────────────────────────────────────────────────────────────────
# Validation Functions
# ─────────────────────────────────────────────────────────────────────────────

def _validate_email_advanced(candidate: Candidate) -> dict:
    """Advanced email validation with fake domain detection."""
    key = "email_validation"
    rule_name = "Email Validation"
    weight = 25
    email = (candidate.email or "").strip().lower()
    
    if not email or email == "not provided":
        return _validation_result(key, weight, False, "Email address not provided", evidence="None", rule_name=rule_name)
    
    # Basic format check
    if not re.match(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", email):
        return _validation_result(key, weight, False, "Invalid email format", evidence=email, rule_name=rule_name)
    
    # Check for fake domains
    domain = _extract_domain(email)
    if domain in FAKE_DOMAINS:
        return _validation_result(key, weight, False, "Placeholder email detected", evidence=domain, rule_name=rule_name)
    
    # Check for disposable email providers
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        return _validation_result(key, weight, False, "Disposable email provider detected", evidence=domain, rule_name=rule_name)
    
    # Check for obviously generated patterns
    if re.match(r"(test|user|example|demo|sample)\d*@", email):
        return _validation_result(key, weight, False, "Obviously generated email pattern", evidence=email, rule_name=rule_name)
    
    # Use email-validator library if available
    if EMAIL_VALIDATOR_AVAILABLE:
        try:
            validate_email_lib(email)
        except Exception as e:
            return _validation_result(key, weight, False, "Email validation failed", evidence=email, rule_name=rule_name)
    
    return _validation_result(key, weight, True, "Valid email address", evidence=email, rule_name=rule_name)


def _validate_phone_advanced(candidate: Candidate) -> dict:
    """Advanced phone validation with country-specific rules."""
    key = "phone_validation"
    rule_name = "Phone Validation"
    weight = 20
    phone = (candidate.phone or "").strip()
    
    if not phone or phone == "not provided":
        return _validation_result(key, weight, False, "Phone number not provided", evidence="None", rule_name=rule_name)
    
    digits = re.sub(r"\D", "", phone)
    
    # Check for dummy patterns
    for pattern in DUMMY_PHONE_PATTERNS:
        if re.match(pattern, digits):
            return _validation_result(key, weight, False, "Dummy phone number", evidence=phone, rule_name=rule_name)
    
    # Check for repeated digits
    if _is_repeated_digit_number(phone):
        return _validation_result(key, weight, False, "Repeated digit pattern", evidence=phone, rule_name=rule_name)
    
    # Basic length check
    if len(digits) < 7:
        return _validation_result(key, weight, False, "Phone number too short", evidence=f"{len(digits)} digits", rule_name=rule_name)
    if len(digits) > 15:
        return _validation_result(key, weight, False, "Phone number too long", evidence=f"{len(digits)} digits", rule_name=rule_name)
    
    # Use phonenumbers library if available
    if PHONENUMBERS_AVAILABLE:
        try:
            parsed = phonenumbers.parse(phone, None)
            if not phonenumbers.is_valid_number(parsed):
                return _validation_result(key, weight, False, "Invalid phone number for country", evidence=phone, rule_name=rule_name)
        except Exception:
            # If parsing fails, fall back to basic validation
            pass
    
    return _validation_result(key, weight, True, "Valid phone number", evidence=phone, rule_name=rule_name)


def _validate_location(candidate: Candidate) -> dict:
    """Validate location consistency and realism."""
    key = "location_validation"
    rule_name = "Location Validation"
    weight = 15
    
    city = (candidate.city or "").strip().lower()
    state = (candidate.state or "").strip().lower()
    location = f"{city}, {state}" if city and state else (city or state)
    
    # Check for invalid indicators
    if city in INVALID_LOCATION_INDICATORS or state in INVALID_LOCATION_INDICATORS:
        return _validation_result(key, weight, False, "Invalid location indicator detected", evidence=location, rule_name=rule_name)
    
    if not city and not state:
        return _validation_result(key, weight, False, "Location information not provided", evidence="None", rule_name=rule_name)
    
    # Validate city-state combination for India
    if city in INDIAN_CITIES:
        expected_state = INDIAN_CITIES[city]
        if state and state != expected_state and state not in expected_state:
            return _validation_result(key, weight, False, "City-state mismatch", evidence=f"{city.title()} vs {state.title()}", rule_name=rule_name)
    
    # Compare with phone country code if available
    phone = (candidate.phone or "").strip()
    if phone and PHONENUMBERS_AVAILABLE:
        try:
            parsed = phonenumbers.parse(phone, None)
            phone_country = phonenumbers.region_code_for_number(parsed)
            # If phone is from India (+91) but location mentions US cities, flag it
            if phone_country == "IN" and state and "usa" in state.lower():
                return _validation_result(key, weight, False, "Phone country code doesn't match location", evidence=location, rule_name=rule_name)
        except Exception:
            pass
    
    return _validation_result(key, weight, True, "Valid location", evidence=location.title(), rule_name=rule_name)


def _validate_experience_timeline(candidate: Candidate, text: str, is_fresher: bool = False) -> dict:
    """Validate experience timeline for impossible dates and education alignment."""
    key = "experience_timeline"
    rule_name = "Experience Timeline"
    weight = 30
    
    experience_text = candidate.experience or ""
    education_text = candidate.education or ""
    
    # For freshers, missing experience is not suspicious
    if is_fresher and not experience_text:
        return _validation_result(key, weight, True, "Not Applicable (Fresher)", evidence="None", rule_name=rule_name)
    
    if not experience_text:
        return _validation_result(key, weight, True, "Experience section not provided", evidence="None", rule_name=rule_name)
    
    # Parse experience dates
    exp_start, exp_end = _parse_date_range(experience_text)
    
    if not exp_start:
        return _validation_result(key, weight, True, "Could not parse experience dates", evidence="Non-standard format", rule_name=rule_name)
    
    # Check for future dates
    if exp_start and exp_start > datetime.now():
        return _validation_result(key, weight, False, "Experience start date is in future", evidence=str(exp_start.date() if exp_start else ""), rule_name=rule_name)
    
    # Check for impossible date sequences
    if exp_start and exp_end and exp_end < exp_start:
        return _validation_result(key, weight, False, "Impossible experience timeline", evidence=f"Start: {exp_start.date() if exp_start else ''}, End: {exp_end.date() if exp_end else ''}", rule_name=rule_name)
    
    # Calculate actual years from timeline
    actual_years = 0.0
    if exp_start:
        end = exp_end if exp_end else datetime.now()
        actual_years = _calculate_years_between(exp_start, end)
    
    # Compare with claimed years_experience (only if not fresher or if there's a major discrepancy)
    claimed_years = candidate.years_experience
    if claimed_years is not None and not is_fresher:
        if abs(claimed_years - actual_years) > 2:
            return _validation_result(key, weight, False, "Timeline inconsistency", evidence=f"Claimed {claimed_years}y, timeline {actual_years:.1f}y", rule_name=rule_name)
    
    # Check education alignment (only if there's contradictory evidence)
    if education_text:
        edu_start, edu_end = _parse_date_range(education_text)
        if edu_end and exp_start and exp_start < edu_end:
            # For freshers, this might be internships - only flag if significant overlap
            overlap_years = _calculate_years_between(exp_start, edu_end)
            if overlap_years > 1:  # More than 1 year overlap is suspicious
                return _validation_result(key, weight, False, "Timeline inconsistency", evidence=f"Education/Work overlap {overlap_years:.1f} years", rule_name=rule_name)
    
    return _validation_result(key, weight, True, "Experience timeline is consistent", evidence="Consistent", rule_name=rule_name)


def _detect_overlapping_employment(candidate: Candidate, is_fresher: bool = False) -> dict:
    """Detect overlapping full-time employment periods."""
    key = "overlapping_employment"
    rule_name = "Employment Overlap"
    weight = 25
    
    experience_text = candidate.experience or ""
    
    # For freshers, skip this check
    if is_fresher:
        return _validation_result(key, weight, True, "Not Applicable (Fresher)", evidence="None", rule_name=rule_name)
    
    if not experience_text:
        return _validation_result(key, weight, True, "Cannot check overlaps", evidence="No data", rule_name=rule_name)
    
    # Try to extract multiple employment periods
    # This is a simplified version - in production, you'd use more sophisticated parsing
    periods = []
    
    # Split by common job entry patterns
    job_entries = re.split(r"\n\s*\n", experience_text)
    
    for entry in job_entries:
        start, end = _parse_date_range(entry)
        if start and end:
            periods.append((start, end))
    
    if len(periods) < 2:
        return _validation_result(key, weight, True, "Insufficient data to detect overlaps", evidence="Not enough periods", rule_name=rule_name)
    
    # Check for overlaps (allowing 1-month tolerance)
    for i in range(len(periods)):
        for j in range(i + 1, len(periods)):
            start1, end1 = periods[i]
            start2, end2 = periods[j]
            
            # Check if periods overlap
            if not (end1 < start2 or end2 < start1):
                # Calculate overlap duration
                overlap_start = max(start1, start2)
                overlap_end = min(end1, end2)
                overlap_months = (overlap_end - overlap_start).days / 30
                
                if overlap_months > 1:  # More than 1 month overlap
                    return _validation_result(key, weight, False, "Overlapping employment detected", evidence=f"{overlap_months:.1f} months overlap", rule_name=rule_name)
    
    return _validation_result(key, weight, True, "No overlapping full-time employment detected", evidence="None", rule_name=rule_name)


def _validate_experience_realism(candidate: Candidate, is_fresher: bool = False) -> dict:
    """Validate if claimed experience is realistic."""
    key = "experience_realism"
    rule_name = "Experience Realism"
    weight = 20
    
    years = candidate.years_experience
    
    # For freshers, missing or low experience is not suspicious
    if is_fresher:
        if years is None or years == 0:
            return _validation_result(key, weight, True, "Not Applicable (Fresher)", evidence="None", rule_name=rule_name)
        if years is not None and years <= 2:
            return _validation_result(key, weight, True, "Low experience", evidence=f"{years} years", rule_name=rule_name)
    
    if years is None:
        return _validation_result(key, weight, True, "Years of experience not specified", evidence="None", rule_name=rule_name)
    
    # Check for impossible values
    if years < 0:
        return _validation_result(key, weight, False, "Negative experience claimed", evidence=f"{years} years", rule_name=rule_name)
    
    if years > 50:
        return _validation_result(key, weight, False, "Unrealistic experience", evidence=f"{years} years claimed", rule_name=rule_name)
    
    # Check against education (if available) - only for non-freshers
    education_text = candidate.education or ""
    if education_text and not is_fresher:
        edu_start, edu_end = _parse_date_range(education_text)
        if edu_end:
            career_start = edu_end
            max_possible_years = _calculate_years_between(career_start, datetime.now())
            if years > max_possible_years + 2:
                return _validation_result(key, weight, False, "Experience exceeds time since education", evidence=f"{years}y vs {max_possible_years:.1f}y possible", rule_name=rule_name)
    
    return _validation_result(key, weight, True, "Experience is realistic", evidence=f"{years} years", rule_name=rule_name)


def _detect_keyword_stuffing(candidate: Candidate, text: str) -> dict:
    """Detect excessive keyword stuffing in skills section."""
    key = "keyword_stuffing"
    rule_name = "Keyword Stuffing"
    weight = 15
    
    skills_text = candidate.technical_skills or ""
    if not skills_text:
        return _validation_result(key, weight, True, "No skills section to analyze", evidence="None", rule_name=rule_name)
    
    # Count skills mentioned
    skills = [s.strip() for s in skills_text.split(",") if s.strip()]
    skill_count = len(skills)
    
    # Calculate skill density
    total_words = len(text.split())
    if total_words > 0:
        skill_density = (skill_count / total_words) * 100
        if skill_density > 15:  # More than 15 skills per 100 words
            return _validation_result(key, weight, False, "Excessive keyword stuffing", evidence=f"{skill_density:.1f}% density", rule_name=rule_name)
    
    # Check for repetitive skill mentions across sections
    skill_lower = skills_text.lower()
    for skill in skills[:5]:  # Check first 5 skills
        count = skill_lower.count(skill.lower())
        if count > 3:
            return _validation_result(key, weight, False, "Repetitive skill mention", evidence=f"'{skill}' {count} times", rule_name=rule_name)
    
    # Check for buzzword density
    buzzword_count = sum(1 for buzzword in BUZZWORDS if buzzword in skills_text.lower())
    if buzzword_count > 5:
        return _validation_result(key, weight, False, "Excessive buzzword usage", evidence=f"{buzzword_count} buzzwords", rule_name=rule_name)
    
    return _validation_result(key, weight, True, "Skill section appears natural", evidence="Natural", rule_name=rule_name)


def _validate_projects_achievements(candidate: Candidate, is_fresher: bool = False) -> dict:
    """Validate projects and achievements for unrealistic claims."""
    key = "projects_achievements"
    rule_name = "Projects Achievements"
    weight = 15
    
    projects_text = candidate.projects or ""
    
    # For freshers, missing projects is not suspicious
    if is_fresher and not projects_text:
        return _validation_result(key, weight, True, "No projects section", evidence="Fresher/Student", rule_name=rule_name)
    
    if not projects_text:
        return _validation_result(key, weight, True, "No projects section to validate", evidence="None", rule_name=rule_name)
    
    # Check for unrealistic metrics (always check, even for freshers)
    for pattern in UNREALISTIC_METRICS:
        matches = re.findall(pattern, projects_text, re.I)
        if matches:
            return _validation_result(key, weight, False, "Unrealistic achievement metric", evidence=matches[0], rule_name=rule_name)
    
    # Check for template/generic descriptions
    generic_phrases = [
        "worked on various projects",
        "successfully completed multiple projects",
        "led team of developers",
        "implemented various features",
    ]
    
    for phrase in generic_phrases:
        if phrase in projects_text.lower():
            return _validation_result(key, weight, False, "Generic project description", evidence=phrase, rule_name=rule_name)
    
    # Check project count vs experience (adjust threshold for freshers)
    years = candidate.years_experience or 1
    project_count = len(re.split(r"[,\n•-]", projects_text))
    
    if is_fresher:
        # For freshers, allow academic projects, assignments, and bulleted lists
        if project_count > 80:  # Allow bullet points and academic projects
            return _validation_result(key, weight, False, "Unrealistic project count", evidence=f"{project_count} projects", rule_name=rule_name)
    else:
        # For experienced candidates, check against years of experience
        if project_count > years * 15:  # More than 15 projects per year of experience
            return _validation_result(key, weight, False, "Unrealistic project count", evidence=f"{project_count} projects for {years}y", rule_name=rule_name)
    
    return _validation_result(key, weight, True, "Projects and achievements appear realistic", evidence="Realistic", rule_name=rule_name)


def _detect_section_contradictions(candidate: Candidate) -> dict:
    """Detect contradictions between different resume sections."""
    key = "section_contradictions"
    rule_name = "Section Contradictions"
    weight = 15
    
    contradictions = []
    
    # Check summary vs experience
    summary = candidate.professional_summary or candidate.career_objective or ""
    experience = candidate.experience or ""
    
    if summary and experience:
        # Extract years mentioned in summary
        summary_years = re.findall(r"(\d+)\+?\s*years?", summary, re.I)
        exp_years = re.findall(r"(\d+)\+?\s*years?", experience, re.I)
        
        if summary_years and exp_years:
            try:
                summary_year = int(summary_years[0])
                exp_year = int(exp_years[0])
                if abs(summary_year - exp_year) > 3:
                    contradictions.append(
                        f"Summary mentions {summary_year} years experience, experience section shows {exp_year} years")
            except ValueError:
                pass
    
    # Check skills vs experience
    skills = candidate.technical_skills or ""
    if skills and experience:
        # If skills mention advanced technologies but experience is junior level
        advanced_skills = ["architect", "lead", "principal", "senior", "expert"]
        if any(skill in skills.lower() for skill in advanced_skills):
            if "junior" in experience.lower() or "entry" in experience.lower():
                contradictions.append("Skills indicate senior level but experience shows junior roles")
    
    # Check education vs experience timeline
    education = candidate.education or ""
    if education and experience:
        edu_dates = re.findall(r"(19|20)\d{2}", education)
        exp_dates = re.findall(r"(19|20)\d{2}", experience)
        
        if edu_dates and exp_dates:
            try:
                edu_year = int(edu_dates[-1])  # Last education year
                exp_year = int(exp_dates[0])  # First experience year
                if exp_year < edu_year - 1:
                    contradictions.append(
                        f"Experience starts in {exp_year} but education completes in {edu_year}")
            except ValueError:
                pass
    
    if contradictions:
        return _validation_result(key, weight, False, "Section contradictions detected", evidence='; '.join(contradictions[:2]), rule_name=rule_name)
    
    return _validation_result(key, weight, True, "No contradictions detected", evidence="Consistent", rule_name=rule_name)


def _detect_ai_generated_content(text: str) -> dict:
    """Detect AI-generated or template-based repetitive content."""
    key = "ai_generated_content"
    rule_name = "AI Generated Content"
    weight = 10
    
    if not text or len(text) < 100:
        return _validation_result(key, weight, True, "Insufficient text", evidence="Short text", rule_name=rule_name)
    
    # Check for AI-generated patterns
    ai_hits = []
    for pattern in AI_GENERATED_PATTERNS:
        if re.search(pattern, text, re.I):
            ai_hits.append(pattern)
    
    if ai_hits:
        return _validation_result(key, weight, False, "AI-generated pattern detected", evidence=ai_hits[0], rule_name=rule_name)
    
    # Check for repetitive sentence structure
    sentences = re.split(r"[.!?]", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if len(sentences) > 5:
        # Check sentence length variance
        lengths = [len(s.split()) for s in sentences]
        if len(set(lengths)) < 3:  # Very low variance
            return _validation_result(key, weight, False, "Unnatural sentence structure", evidence="Low length variance", rule_name=rule_name)
    
    # Check for repetitive phrases (excluding formatting symbols like pipes/bullets)
    clean_text = re.sub(r"[|•\-_:\t]+", " ", text.lower())
    words = clean_text.split()
    repeated_phrases = []
    for i in range(len(words) - 3):
        phrase = " ".join(words[i:i+4])
        # Only check meaningful word phrases (not single character symbols)
        if len(phrase.strip()) > 15:
            count = clean_text.count(phrase)
            if count > 4:  # Allow standard resume header repeats
                repeated_phrases.append(phrase)
    
    if repeated_phrases:
        return _validation_result(key, weight, False, "Repetitive content detected", evidence=repeated_phrases[0], rule_name=rule_name)
    
    return _validation_result(key, weight, True, "Content appears human-written", evidence="Human-like", rule_name=rule_name)


# ─────────────────────────────────────────────────────────────────────────────
# Main Analysis Function
# ─────────────────────────────────────────────────────────────────────────────

def analyse_resume(candidate: Candidate, resume: Resume, job=None) -> dict:
    """
    Run all fake resume detection validations and return results.
    
    Returns:
        {
            "suspicious_score": int (0-100),
            "classification": "Genuine" | "Needs Review" | "Suspicious",
            "failed_validations": list of validation results,
            "total_checks": int,
            "passed_checks": int,
            "report_json": str,
        }
    """
    text = (resume.extracted_text or "") if resume else ""
    
    # Detect if candidate is a fresher/student
    fresher_status = _detect_fresher_status(candidate)
    is_fresher = fresher_status["is_fresher"]
    
    # Run all validation checks with fresher awareness
    validations = [
        _validate_email_advanced(candidate),
        _validate_phone_advanced(candidate),
        _validate_location(candidate),
        _validate_experience_timeline(candidate, text, is_fresher=is_fresher),
        _detect_overlapping_employment(candidate, is_fresher=is_fresher),
        _validate_experience_realism(candidate, is_fresher=is_fresher),
        _detect_keyword_stuffing(candidate, text),
        _validate_projects_achievements(candidate, is_fresher=is_fresher),
        _detect_section_contradictions(candidate),
        _detect_ai_generated_content(text),
    ]
    
    # Calculate suspicious score (sum of weights from failed validations)
    suspicious_points = sum(v["weight"] for v in validations if not v["passed"])
    suspicious_score = min(suspicious_points, 100)  # Cap at 100
    
    # Separate failed validations
    failed_validations = [v for v in validations if not v["passed"]]
    passed_validations = [v for v in validations if v["passed"]]
    
    # Determine classification
    if suspicious_score <= 24:
        classification = "Genuine"
    elif suspicious_score <= 49:
        classification = "Needs Review"
    else:
        classification = "Suspicious"
    
    # Calculate suspicious score (sum of weights from failed validations)
    # The previous logic is preserved but we don't override the score artificially.
    
    # Build report
    report = {
        "suspicious_score": suspicious_score,
        "classification": classification,
        "failed_validations": failed_validations,
        "passed_validations": passed_validations,
        "total_checks": len(validations),
        "passed_checks": len(passed_validations),
        "failed_checks": len(failed_validations),
        "is_fresher": is_fresher,
        "fresher_reason": fresher_status["reason"],
    }
    
    # Convert to legacy format for backward compatibility
    # The existing system expects authenticity_score (higher = more genuine)
    authenticity_score = 100 - suspicious_score
    is_suspicious = classification != "Genuine"
    
    # Map classification to legacy status
    if classification == "Genuine":
        legacy_status = "Genuine Resume"
        legacy_risk = "low"
    elif classification == "Needs Review":
        legacy_status = "Needs Review"
        legacy_risk = "medium"
    else:
        legacy_status = "Suspicious Resume"
        legacy_risk = "high"
    
    return {
        "suspicious_score": suspicious_score,
        "classification": classification,
        "failed_validations": failed_validations,
        "total_checks": len(validations),
        "passed_checks": len(passed_validations),
        "report_json": json.dumps(report),
        # Legacy fields for backward compatibility
        "score": authenticity_score,
        "status": legacy_status,
        "risk_level": legacy_risk,
        "is_suspicious": is_suspicious,
        "checks": validations,  # Reuse validations as checks
        "suspicious_reasons": [v["detail"] for v in failed_validations],
    }
