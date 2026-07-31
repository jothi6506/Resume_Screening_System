import re

with open('app/services/authenticity_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Signature update for _validation_result
content = re.sub(
    r'def _validation_result\(key: str, weight: int, passed: bool, detail: str\) -> dict:\n\s+"""Standard validation result format\."""\n\s+return \{\n\s+"key": key,\n\s+"weight": weight,\n\s+"passed": passed,\n\s+"detail": detail,\n\s+\}',
    'def _validation_result(key: str, weight: int, passed: bool, detail: str, evidence: str = "", rule_name: str = "") -> dict:\n    """Standard validation result format."""\n    return {\n        "key": key,\n        "rule_name": rule_name,\n        "weight": weight,\n        "passed": passed,\n        "detail": detail,\n        "evidence": evidence,\n    }',
    content
)

# 2. Update all validation functions to pass rule_name and evidence
# Instead of complex regex, let's use a simpler approach: define replacements
replacements = [
    # Email
    ('key = "email_validation"', 'key = "email_validation"\n    rule_name = "Email Validation"'),
    ('return _validation_result(key, weight, False, "Email address not provided")', 'return _validation_result(key, weight, False, "Email address not provided", evidence="None", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Invalid email format: {email}")', 'return _validation_result(key, weight, False, "Invalid email format", evidence=email, rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Fake/placeholder domain detected: {domain}")', 'return _validation_result(key, weight, False, "Placeholder email detected", evidence=domain, rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Disposable email provider detected: {domain}")', 'return _validation_result(key, weight, False, "Disposable email provider detected", evidence=domain, rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Obviously generated email pattern: {email}")', 'return _validation_result(key, weight, False, "Obviously generated email pattern", evidence=email, rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Email validation failed: {str(e)}")', 'return _validation_result(key, weight, False, "Email validation failed", evidence=email, rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, f"Valid email address: {email}")', 'return _validation_result(key, weight, True, "Valid email address", evidence=email, rule_name=rule_name)'),

    # Phone
    ('key = "phone_validation"', 'key = "phone_validation"\n    rule_name = "Phone Validation"'),
    ('return _validation_result(key, weight, False, "Phone number not provided")', 'return _validation_result(key, weight, False, "Phone number not provided", evidence="None", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Dummy phone pattern detected: {phone}")', 'return _validation_result(key, weight, False, "Dummy phone number", evidence=phone, rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Repeated digit pattern detected: {phone}")', 'return _validation_result(key, weight, False, "Repeated digit pattern", evidence=phone, rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Phone number too short: {len(digits)} digits")', 'return _validation_result(key, weight, False, "Phone number too short", evidence=f"{len(digits)} digits", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Phone number too long: {len(digits)} digits")', 'return _validation_result(key, weight, False, "Phone number too long", evidence=f"{len(digits)} digits", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Invalid phone number for country: {phone}")', 'return _validation_result(key, weight, False, "Invalid phone number for country", evidence=phone, rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, f"Valid phone number: {phone}")', 'return _validation_result(key, weight, True, "Valid phone number", evidence=phone, rule_name=rule_name)'),

    # Location
    ('key = "location_validation"', 'key = "location_validation"\n    rule_name = "Location Validation"'),
    ('return _validation_result(key, weight, False, f"Invalid location indicator detected: {location}")', 'return _validation_result(key, weight, False, "Invalid location indicator detected", evidence=location, rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, "Location information not provided")', 'return _validation_result(key, weight, False, "Location information not provided", evidence="None", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, \n                f"City-state mismatch: {city.title()} should be in {expected_state.title()}, not {state.title()}")', 'return _validation_result(key, weight, False, "City-state mismatch", evidence=f"{city.title()} vs {state.title()}", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, \n                    "Phone country code (India) doesn\'t match location (USA)")', 'return _validation_result(key, weight, False, "Phone country code doesn\'t match location", evidence=location, rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, f"Valid location: {location.title()}")', 'return _validation_result(key, weight, True, "Valid location", evidence=location.title(), rule_name=rule_name)'),

    # Experience timeline
    ('key = "experience_timeline"', 'key = "experience_timeline"\n    rule_name = "Experience Timeline"'),
    ('return _validation_result(key, weight, True, "No experience section (valid for fresher/student)")', 'return _validation_result(key, weight, True, "No experience section", evidence="Fresher/Student", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "Experience section not provided (not required)")', 'return _validation_result(key, weight, True, "Experience section not provided", evidence="None", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "Could not parse experience dates (may be non-standard format)")', 'return _validation_result(key, weight, True, "Could not parse experience dates", evidence="Non-standard format", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Experience start date is in future: {exp_start}")', 'return _validation_result(key, weight, False, "Experience start date is in future", evidence=str(exp_start.date() if exp_start else ""), rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, \n            f"Impossible timeline: End date ({exp_end}) before start date ({exp_start})")', 'return _validation_result(key, weight, False, "Impossible experience timeline", evidence=f"Start: {exp_start.date() if exp_start else \'\'}, End: {exp_end.date() if exp_end else \'\'}", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                f"Timeline inconsistency: Claimed {claimed_years} years experience, but timeline shows {actual_years:.1f} years")', 'return _validation_result(key, weight, False, "Timeline inconsistency", evidence=f"Claimed {claimed_years}y, timeline {actual_years:.1f}y", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                    f"Timeline inconsistency: Work experience starts before education completion ({overlap_years:.1f} years overlap)")', 'return _validation_result(key, weight, False, "Timeline inconsistency", evidence=f"Education/Work overlap {overlap_years:.1f} years", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "Experience timeline is consistent")', 'return _validation_result(key, weight, True, "Experience timeline is consistent", evidence="Consistent", rule_name=rule_name)'),

    # Overlapping Employment
    ('key = "overlapping_employment"', 'key = "overlapping_employment"\n    rule_name = "Employment Overlap"'),
    ('return _validation_result(key, weight, True, "Overlapping employment check skipped (fresher/student)")', 'return _validation_result(key, weight, True, "Overlapping employment check skipped", evidence="Fresher/Student", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "Cannot check overlaps - no experience data")', 'return _validation_result(key, weight, True, "Cannot check overlaps", evidence="No data", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "Insufficient data to detect overlaps")', 'return _validation_result(key, weight, True, "Insufficient data to detect overlaps", evidence="Not enough periods", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                        f"Overlapping employment detected: {overlap_months:.1f} months overlap between roles")', 'return _validation_result(key, weight, False, "Overlapping employment detected", evidence=f"{overlap_months:.1f} months overlap", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "No overlapping full-time employment detected")', 'return _validation_result(key, weight, True, "No overlapping full-time employment detected", evidence="None", rule_name=rule_name)'),

    # Experience realism
    ('key = "experience_realism"', 'key = "experience_realism"\n    rule_name = "Experience Realism"'),
    ('return _validation_result(key, weight, True, "No experience (valid for fresher/student)")', 'return _validation_result(key, weight, True, "No experience", evidence="Fresher/Student", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, f"Low experience ({years} years) valid for fresher/student")', 'return _validation_result(key, weight, True, "Low experience", evidence=f"{years} years", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "Years of experience not specified")', 'return _validation_result(key, weight, True, "Years of experience not specified", evidence="None", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Negative experience claimed: {years} years")', 'return _validation_result(key, weight, False, "Negative experience claimed", evidence=f"{years} years", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False, f"Unrealistic experience: {years} years exceeds typical career span")', 'return _validation_result(key, weight, False, "Unrealistic experience", evidence=f"{years} years claimed", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                    f"Experience ({years} years) exceeds time since education ({max_possible_years:.1f} years)")', 'return _validation_result(key, weight, False, "Experience exceeds time since education", evidence=f"{years}y vs {max_possible_years:.1f}y possible", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, f"Experience ({years} years) is realistic")', 'return _validation_result(key, weight, True, "Experience is realistic", evidence=f"{years} years", rule_name=rule_name)'),

    # Keyword stuffing
    ('key = "keyword_stuffing"', 'key = "keyword_stuffing"\n    rule_name = "Keyword Stuffing"'),
    ('return _validation_result(key, weight, True, "No skills section to analyze")', 'return _validation_result(key, weight, True, "No skills section to analyze", evidence="None", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                f"Excessive keyword stuffing: {skill_count} skills in {total_words} words ({skill_density:.1f}% density)")', 'return _validation_result(key, weight, False, "Excessive keyword stuffing", evidence=f"{skill_density:.1f}% density", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                f"Repetitive skill mention: \'{skill}\' appears {count} times")', 'return _validation_result(key, weight, False, "Repetitive skill mention", evidence=f"\'{skill}\' {count} times", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n            f"Excessive buzzword usage: {buzzword_count} buzzwords detected in skills")', 'return _validation_result(key, weight, False, "Excessive buzzword usage", evidence=f"{buzzword_count} buzzwords", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "Skill section appears natural")', 'return _validation_result(key, weight, True, "Skill section appears natural", evidence="Natural", rule_name=rule_name)'),

    # Projects achievements
    ('key = "projects_achievements"', 'key = "projects_achievements"\n    rule_name = "Projects Achievements"'),
    ('return _validation_result(key, weight, True, "No projects section (valid for fresher/student)")', 'return _validation_result(key, weight, True, "No projects section", evidence="Fresher/Student", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "No projects section to validate")', 'return _validation_result(key, weight, True, "No projects section to validate", evidence="None", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                f"Unrealistic achievement metric detected: {matches[0]}")', 'return _validation_result(key, weight, False, "Unrealistic achievement metric", evidence=matches[0], rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                f"Generic project description detected: \'{phrase}\'")', 'return _validation_result(key, weight, False, "Generic project description", evidence=phrase, rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                f"Unrealistic project count: {project_count} projects for a fresher")', 'return _validation_result(key, weight, False, "Unrealistic project count", evidence=f"{project_count} projects", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                f"Unrealistic project count: {project_count} projects for {years} years of experience")', 'return _validation_result(key, weight, False, "Unrealistic project count", evidence=f"{project_count} projects for {years}y", rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "Projects and achievements appear realistic")', 'return _validation_result(key, weight, True, "Projects and achievements appear realistic", evidence="Realistic", rule_name=rule_name)'),

    # Section contradictions
    ('key = "section_contradictions"', 'key = "section_contradictions"\n    rule_name = "Section Contradictions"'),
    ('return _validation_result(key, weight, False, \n            f"Section contradictions detected: {\'; \'.join(contradictions[:2])}")', 'return _validation_result(key, weight, False, "Section contradictions detected", evidence=\'; \'.join(contradictions[:2]), rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "No contradictions detected between sections")', 'return _validation_result(key, weight, True, "No contradictions detected", evidence="Consistent", rule_name=rule_name)'),

    # AI Generated Content
    ('key = "ai_generated_content"', 'key = "ai_generated_content"\n    rule_name = "AI Generated Content"'),
    ('return _validation_result(key, weight, True, "Insufficient text for AI detection")', 'return _validation_result(key, weight, True, "Insufficient text", evidence="Short text", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n            f"AI-generated pattern detected: {ai_hits[0]}")', 'return _validation_result(key, weight, False, "AI-generated pattern detected", evidence=ai_hits[0], rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n                "Unnatural sentence structure: very low length variance")', 'return _validation_result(key, weight, False, "Unnatural sentence structure", evidence="Low length variance", rule_name=rule_name)'),
    ('return _validation_result(key, weight, False,\n            f"Repetitive content detected: \'{repeated_phrases[0]}\' appears multiple times")', 'return _validation_result(key, weight, False, "Repetitive content detected", evidence=repeated_phrases[0], rule_name=rule_name)'),
    ('return _validation_result(key, weight, True, "Content appears to be human-written")', 'return _validation_result(key, weight, True, "Content appears human-written", evidence="Human-like", rule_name=rule_name)')
]

for old, new in replacements:
    content = content.replace(old, new)

# 3. Update analyse_resume block
override_block = """    # Override: Never mark as Genuine if multiple strong checks fail
    strong_failures = [f for f in failed_validations if f["weight"] >= 20]
    if len(strong_failures) >= 2 and classification == "Genuine":
        classification = "Needs Review"
        suspicious_score = max(suspicious_score, 25)"""

new_override = """    # Calculate suspicious score (sum of weights from failed validations)
    # The previous logic is preserved but we don't override the score artificially."""

content = content.replace(override_block, new_override)

with open('app/services/authenticity_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated authenticity_service.py")
