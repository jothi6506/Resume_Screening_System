"""Suspicious Resume Detection Service

Checks resumes for suspicious patterns and calculates a risk status.
"""

import re

# Advanced technologies list for fresher claims checking
ADVANCED_TECH = {
    'kubernetes', 'aws', 'docker', 'machine learning', 'deep learning', 'nlp', 
    'microservices', 'system design', 'blockchain', 'devops', 'tensorflow', 
    'pytorch', 'cloud computing', 'hadoop', 'spark', 'artificial intelligence',
    'ansible', 'jenkins', 'ci/cd', 'terraform', 'graphql', 'apache spark'
}

# Expert keywords in skill descriptions
EXPERT_KEYWORDS = {'expert', 'expert-level', 'advanced', 'specialist', 'master', 'lead', 'architect'}

def validate_email_format(email):
    """Validate email address format strictly. Does NOT check for existence.
    
    Rules:
    - Must contain exactly one '@'
    - Username must exist before '@'
    - Domain must exist after '@'
    - Domain must have a valid extension (.com, .in, .org, .edu, etc.)
    - No spaces
    - No consecutive dots
    - No invalid characters
    """
    if not email or email.strip().lower() in {"not provided", "none", ""}:
        return False, "Email address not provided"
        
    email = email.strip()
    
    if " " in email:
        return False, "Email contains spaces"
        
    if email.count("@") != 1:
        return False, "Email must contain exactly one '@'"
        
    username, domain = email.split("@")
    
    if not username:
        return False, "Username must exist before '@'"
        
    if not domain:
        return False, "Domain must exist after '@'"
        
    if ".." in email:
        return False, "Email contains consecutive dots"
        
    # Invalid character check
    if not re.match(r"^[a-zA-Z0-9._%+\-]+$", username):
        return False, "Email contains invalid characters in username"
        
    if not re.match(r"^[a-zA-Z0-9.\-]+$", domain):
        return False, "Email contains invalid characters in domain"
        
    # Domain must have a valid extension (.com, .in, .org, .edu, etc.)
    parts = domain.split(".")
    if len(parts) < 2 or not parts[-1]:
        return False, "Domain must have a valid extension"
        
    ext = parts[-1].lower()
    if not ext.isalpha() or len(ext) < 2:
        return False, "Domain must have a valid extension"
        
    return True, "Valid Email Format"


def validate_phone_number(phone):
    """Validate phone number format. Does NOT verify if active.
    
    Rules:
    - Accept Indian mobile numbers
    - Accept +91 optionally
    - Must contain exactly 10 digits
    - First digit must be 6, 7, 8 or 9
    - Ignore spaces and hyphens
    - Reject alphabets
    - Reject all identical digits
    - Reject obvious dummy or sequential numbers
    """
    if not phone or phone.strip().lower() in {"not provided", "none", ""}:
        return "invalid", "Phone number not provided"
        
    phone_clean = phone.strip()
    
    # Reject alphabets/letters
    if any(c.isalpha() for c in phone_clean):
        return "invalid", "Phone number contains letters"
        
    # Ignore spaces and hyphens
    digits_only = phone_clean.replace(" ", "").replace("-", "")
    
    # Accept +91 optionally (remove country code if present)
    if digits_only.startswith("+91"):
        digits_only = digits_only[3:]
    elif digits_only.startswith("91") and len(digits_only) == 12:
        digits_only = digits_only[2:]
        
    # Reject non-digits
    if not digits_only.isdigit():
        return "invalid", "Phone number contains invalid characters"
        
    # Reject short or long numbers (must contain exactly 10 digits after removing prefix)
    if len(digits_only) != 10:
        return "invalid", "Phone number must contain exactly 10 digits"
        
    # Reject all identical digits (e.g. 9999999999, 1111111111)
    if len(set(digits_only)) == 1:
        return "suspicious", "All digits in phone number are identical"
        
    # Reject obvious dummy or sequential numbers
    dummy_patterns = {"1234567890", "0123456789", "9876543210"}
    if digits_only in dummy_patterns:
        return "suspicious", "Sequential dummy phone number"
        
    # First digit must be 6, 7, 8 or 9
    if digits_only[0] not in {'6', '7', '8', '9'}:
        return "invalid", "Phone number must start with 6, 7, 8 or 9"
        
    return "valid", "Valid Phone Number"


def check_skill_evidence(skill_name, text_sources):
    """Check if there is supporting evidence for a skill in text sources.
    
    Case-insensitive search matching the skill name as a bounded word.
    """
    if not skill_name:
        return False
        
    cleaned_skill = re.escape(skill_name.strip())
    # Match skill name bounded by non-alphanumeric chars (excluding standard programming symbols) or start/end of string
    pattern = r"(?:^|[^a-zA-Z0-9_#\+\.\-])" + cleaned_skill + r"(?:$|[^a-zA-Z0-9_#\+\.\-])"
    
    for text in text_sources:
        if text and text.strip().lower() not in {"not provided", "none", ""}:
            if re.search(pattern, text, re.IGNORECASE):
                return True
    return False


def detect_suspicious_patterns(candidate):
    """Analyze candidate and calculate a Suspicious Score (0-100) and Risk Level.
    
    Returns:
        dict: report containing score, status, warnings, and details of checks.
    """
    # 1. Check for missing fields / sections
    is_education_missing = not candidate.education or candidate.education.strip().lower() in {"not provided", "none", ""}
    
    # Skills missing if no technical/soft skills text and no parsed candidate skill items
    has_skills_text = candidate.technical_skills and candidate.technical_skills.strip().lower() not in {"not provided", "none", ""}
    has_soft_skills = candidate.soft_skills and candidate.soft_skills.strip().lower() not in {"not provided", "none", ""}
    has_candidate_skills = len(candidate.skills) > 0 if candidate.skills else False
    is_skills_missing = not (has_skills_text or has_soft_skills or has_candidate_skills)
    
    is_projects_missing = not candidate.projects or candidate.projects.strip().lower() in {"not provided", "none", ""}
    
    # Compile warnings list
    warnings = []
    
    # Email Validation
    email_valid, email_err = validate_email_format(candidate.email)
    if not email_valid:
        warnings.append("Invalid Email Format")
        
    # Phone Validation
    phone_status, phone_err = validate_phone_number(candidate.phone)
    if phone_status == "invalid":
        warnings.append("Invalid Phone Number Format")
    elif phone_status == "suspicious":
        warnings.append("Suspicious Phone Number Pattern")
        
    # Mandatory Sections existence warnings
    if is_education_missing:
        warnings.append("Education section is missing.")
    if is_skills_missing:
        warnings.append("Skills section is missing.")
    if is_projects_missing:
        warnings.append("Projects section is missing.")
        
    # Resume Completeness warnings
    if not candidate.email or candidate.email.strip().lower() in {"not provided", "none", ""}:
        warnings.append("Missing email")
    if not candidate.phone or candidate.phone.strip().lower() in {"not provided", "none", ""}:
        warnings.append("Missing phone number")
    if is_education_missing:
        warnings.append("Missing education")
    if is_skills_missing:
        warnings.append("Missing skills")
    if is_projects_missing:
        warnings.append("Missing projects")
        
    # Extract Skills from candidate
    skills_list = []
    if candidate.technical_skills and candidate.technical_skills.strip().lower() not in {"not provided", "none", ""}:
        for s in candidate.technical_skills.split(","):
            s_clean = s.strip()
            if s_clean and s_clean not in skills_list:
                skills_list.append(s_clean)
                
    if candidate.skills:
        for cs in candidate.skills:
            if cs.skill and cs.skill.name:
                s_name = cs.skill.name.strip()
                if s_name and s_name not in skills_list:
                    skills_list.append(s_name)
                    
    # Evidence Validation
    # Search inside Projects, Internships (Experience), Certifications, Achievements (Summary fields)
    text_sources = [
        candidate.projects,
        candidate.experience,
        candidate.certifications,
        candidate.professional_summary,
        candidate.career_objective,
        candidate.summary
    ]
    
    skills_report = []
    unsupported_skills = []
    
    for skill in skills_list:
        found = check_skill_evidence(skill, text_sources)
        skills_report.append({
            "skill": skill,
            "found": found,
            "display": f"{skill} → Evidence Found" if found else f"{skill} → No Supporting Evidence"
        })
        if not found:
            unsupported_skills.append(skill)
            warnings.append(f"{skill} skill has no supporting evidence")
            
    # Duplicate Content Detection
    duplicate_warnings = []
    
    # Duplicate skills check
    skills_raw = []
    if candidate.technical_skills and candidate.technical_skills.strip().lower() not in {"not provided", "none", ""}:
        skills_raw.extend([s.strip().lower() for s in candidate.technical_skills.split(",") if s.strip()])
    if candidate.skills:
        skills_raw.extend([cs.skill.name.strip().lower() for cs in candidate.skills])
        
    seen_skills = set()
    dup_skills = set()
    for s in skills_raw:
        if s in seen_skills:
            dup_skills.add(s)
        else:
            seen_skills.add(s)
            
    if dup_skills:
        duplicate_warnings.append(f"Duplicate skills detected: {', '.join(dup_skills)}")
        
    # Duplicate paragraphs / repeated text check
    text_blocks = []
    for field in [candidate.education, candidate.experience, candidate.projects, 
                  candidate.professional_summary, candidate.career_objective, candidate.summary]:
        if field and field.strip().lower() not in {"not provided", "none", ""}:
            for p in re.split(r'\n+', field):
                p_clean = p.strip()
                if len(p_clean) > 30:
                    text_blocks.append(p_clean)
                    
    if candidate.primary_resume and candidate.primary_resume.extracted_text:
        for p in re.split(r'\n+', candidate.primary_resume.extracted_text):
            p_clean = p.strip()
            if len(p_clean) > 30:
                text_blocks.append(p_clean)
                
    seen_blocks = {}
    dup_blocks = False
    for block in text_blocks:
        norm = re.sub(r'\s+', '', block.lower())
        if norm in seen_blocks:
            dup_blocks = True
            break
        else:
            seen_blocks[norm] = block
            
    if dup_blocks or duplicate_warnings:
        warnings.append("Duplicate content detected")
        
    # Fresher Validation
    is_fresher = (candidate.years_experience is None or candidate.years_experience <= 1.0) or \
                 (not candidate.experience or candidate.experience.strip().lower() in {"not provided", "none", ""})
                 
    fresher_warning = None
    if is_fresher:
        # Check for unrealistic claims
        unrealistic_claims = False
        
        # Expert / advanced level skills count
        advanced_skills_count = 0
        unsupported_advanced_skills = 0
        
        for skill in skills_list:
            s_lower = skill.lower()
            is_advanced = s_lower in ADVANCED_TECH or any(kw in s_lower for kw in EXPERT_KEYWORDS)
            if is_advanced:
                advanced_skills_count += 1
                if skill in unsupported_skills:
                    unsupported_advanced_skills += 1
                    
        # Check condition for unrealistic claims
        # e.g., fresher has too many advanced technologies or Expert skills with no evidence
        if len(unsupported_skills) >= 3 or unsupported_advanced_skills >= 2 or advanced_skills_count >= 5:
            unrealistic_claims = True
            
        if unrealistic_claims:
            fresher_warning = "Multiple advanced skills found without supporting evidence. Manual review recommended."
            warnings.append(fresher_warning)
            
    # Calculate Suspicious Score (aggregated using specific weights)
    score = 0
    
    # 1. Invalid Email Format (+15)
    if not email_valid:
        score += 15
        
    # 2. Invalid Phone Format (+15) or Suspicious Phone Pattern (+10)
    if phone_status == "invalid":
        score += 15
    elif phone_status == "suspicious":
        score += 10
        
    # 3. Missing Education (+15)
    if is_education_missing:
        score += 15
        
    # 4. Missing Skills (+10)
    if is_skills_missing:
        score += 10
        
    # 5. Missing Projects (+15)
    if is_projects_missing:
        score += 15
        
    # 6. Duplicate Content (+10)
    if dup_blocks or len(duplicate_warnings) > 0:
        score += 10
        
    # 7. Multiple Unsupported Skills (+20) (defined as unsupported count >= 2)
    if len(unsupported_skills) >= 2:
        score += 20
        
    # 8. Too Many Unrealistic Claims (+20) (fresher validation failed)
    if fresher_warning:
        score += 20
        
    # Cap score at 100
    score = min(score, 100)
    
    # Risk Level mapping
    if score <= 30:
        status = "Low Risk"
    elif score <= 60:
        status = "Medium Risk"
    else:
        status = "Needs Manual Review"
        
    # Filter unique warnings for the explainable output section
    unique_warnings = []
    seen_warnings = set()
    
    # Ensure warnings order and display matches expectations
    for w in warnings:
        if w not in seen_warnings:
            unique_warnings.append(w)
            seen_warnings.add(w)
            
    return {
        "score": score,
        "status": status,
        "email_validation": {
            "valid": email_valid,
            "display": "Valid Email Format" if email_valid else "Invalid Email Format",
            "icon": "✅" if email_valid else "❌"
        },
        "phone_validation": {
            "status": phone_status,
            "display": "Valid Phone Number" if phone_status == "valid" else ("Suspicious Phone Number Pattern" if phone_status == "suspicious" else "Invalid Phone Number Format"),
            "icon": "✅" if phone_status == "valid" else ("⚠" if phone_status == "suspicious" else "❌")
        },
        "mandatory_sections": {
            "education": not is_education_missing,
            "skills": not is_skills_missing,
            "projects": not is_projects_missing
        },
        "skills_evidence": skills_report,
        "duplicate_content": dup_blocks or len(duplicate_warnings) > 0,
        "fresher_warning": fresher_warning,
        "warnings": unique_warnings
    }
