# Resume Authenticity Knowledge Base

## Overview

This knowledge base documents the rule-based validation and AI reasoning system for detecting fake or suspicious resumes. The system uses evidence-based scoring to identify resumes with clear indicators of fraud or misleading information while being fair to legitimate candidates including freshers and students.

## Scoring System

- **Suspicious Score**: 0-100 (higher = more suspicious)
- **Classification**:
  - 0-24: Genuine
  - 25-49: Needs Review
  - 50-100: Suspicious
- **Validation Weights**: Each failed validation adds specific points to the suspicious score

## Fresher/Student Detection

The system automatically identifies entry-level candidates to adjust validation rules appropriately. A candidate is classified as a fresher/student if they have at least 2 of the following indicators:

- No years of experience specified or ≤ 1 year
- No experience section
- Recent education (within 2 years)
- Student status indicated in education (e.g., "pursuing", "current", "bachelor")
- Fresher/entry-level keywords in objective/summary (e.g., "fresher", "entry level", "recent graduate")

**Impact on Validation**: For freshers, experience-related checks are skipped or adjusted to avoid false positives. Missing experience, few projects, or limited information are not considered suspicious for entry-level candidates.

---

## EMAIL VALIDATION (Weight: 25)

### Mark as Suspicious if:

**Fake/Placeholder Domains:**
- example.com
- test.com
- sample.com
- fake.com
- demo.com
- invalid.com
- placeholder.com
- notreal.com
- temp.com

**Disposable Email Providers:**
- mailinator.com
- guerrillamail.com
- temp-mail.org
- 10minutemail.com
- throwawaymail.com
- getairmail.com
- yopmail.com
- sharklasers.com

**Invalid Patterns:**
- Invalid email format (doesn't match standard email regex)
- Random generated usernames (e.g., abc123xyz999@test.com)
- Obviously generated patterns (test123@, user456@, example789@)
- Non-existent or malformed domains (detected via email-validator library)

### Mark as Genuine if:

- gmail.com
- outlook.com
- hotmail.com
- yahoo.com
- icloud.com
- proton.me
- Company domains (e.g., microsoft.com, google.com)
- University domains (e.g., mit.edu, stanford.edu)
- Valid domain with proper MX records

---

## PHONE VALIDATION (Weight: 20)

### Mark as Suspicious if:

**Dummy Number Patterns:**
- 9999999999
- 1111111111
- 1234567890
- 9876543210
- 0000000000
- 5555555555
- 8888888888
- 7777777777
- 4444444444
- 3333333333
- 2222222222
- 6666666666

**Invalid Characteristics:**
- Repeated digits (e.g., 777-777-7777)
- Invalid country code for detected location
- Wrong length (too short < 7 digits or too long > 15 digits)
- Impossible number patterns
- Invalid format for country (detected via phonenumbers library)

### Mark as Genuine if:

- Valid phone number matching the detected country
- Proper country code and format
- Passes phonenumbers library validation

---

## LOCATION VALIDATION (Weight: 15)

### Mark as Suspicious if:

**Invalid Indicators:**
- Unknown city
- Invalid state
- Fake locations
- Random text
- "n/a", "na", "not provided", "unknown"
- "anywhere", "remote only", "worldwide", "global"
- "earth", "planet", "universe"

**City-State Mismatches (India):**
- City in wrong state (e.g., Chennai in Maharashtra)
- Location doesn't match phone country code (e.g., India phone with USA location)

### Mark as Genuine if:

- Real city/state/country combinations
- Valid city-state pairs for known regions
- Location consistent with phone country code

---

## EXPERIENCE VALIDATION (Weight: 30)

### Mark as Suspicious if:

**Impossible Timeline:**
- 20 years experience after graduating in 2025
- Experience start date in the future
- End date before start date
- Work experience starts significantly before education completion (>1 year overlap)
- Claimed years of experience doesn't match timeline (difference > 2 years)

**Note**: For freshers/students, missing experience is NOT suspicious. This check is skipped for entry-level candidates.

### Mark as Genuine if:

- Career timeline is logically consistent
- Experience dates align with education
- Claimed experience matches timeline
- No experience section (for freshers/students)

---

## EMPLOYMENT HISTORY (Weight: 25)

### Mark as Suspicious if:

**Overlapping Full-Time Jobs:**
- Multiple full-time employment periods overlap significantly (>1 month)
- Simultaneous full-time roles without explanation

**Note**: For freshers/students, this check is skipped as they may have internships or part-time work.

### Mark as Genuine if:

- No overlapping full-time employment
- Sequential career progression
- Overlaps explained (part-time, consulting, etc.)
- No experience data (for freshers/students)

---

## EDUCATION VALIDATION (Weight: 20)

### Mark as Suspicious if:

**Impossible Education:**
- Education years impossible (e.g., graduation before birth)
- Work before school completion without explanation
- Conflicting education dates
- Experience significantly exceeds time since education (>2 years)

**Note**: For freshers/students, missing or recent education is not suspicious.

### Mark as Genuine if:

- Education timeline is consistent
- Education aligns with career timeline
- Recent education (for freshers/students)
- No major contradictions

---

## SKILL VALIDATION (Weight: 15)

### Mark as Suspicious if:

**Excessive Skills:**
- 100+ expert skills
- Every programming language listed
- Every cloud platform
- Every AI framework
- Every database technology
- Every DevOps tool
- Skill density > 15% of total words
- Excessive buzzword usage (>5 buzzwords)
- Repetitive skill mentions (same skill appears >3 times)

**Buzzwords:**
- innovative, dynamic, cutting-edge, groundbreaking, revolutionary
- world-class, best-in-class, state-of-the-art, industry-leading
- transformative, disruptive, visionary, strategic, synergy

### Mark as Genuine if:

- Skills match education and experience level
- Reasonable number of skills for experience level
- Skills are relevant to job role
- No excessive keyword stuffing
- Natural skill distribution

---

## PROJECT VALIDATION (Weight: 15)

### Mark as Suspicious if:

**Unrealistic Claims:**
- Built ChatGPT
- Created Windows
- Built Google Search
- Developed Android OS
- Built Tesla Autopilot alone
- Unrealistic achievement metrics (e.g., "increased by 5000%")
- Generic descriptions ("worked on various projects")
- Unrealistic project count (>10 projects per year of experience, >20 for freshers)

### Mark as Genuine if:

- Realistic projects (Student Management System, Hospital Management, Portfolio Website)
- Achievable metrics
- Specific, detailed descriptions
- Project count appropriate for experience level
- No projects (for freshers/students)

---

## ACHIEVEMENT VALIDATION

### Mark as Suspicious if:

**Impossible Achievements:**
- Nobel Prize in Computer Science
- World's Best Engineer
- Invented Artificial Intelligence
- Created Python Language
- Unrealistic metrics (e.g., "saved $1,000,000", "generated $100,000")

### Mark as Genuine if:

- Realistic, verifiable achievements
- Specific, measurable results
- Achievements appropriate for experience level

---

## CONSISTENCY VALIDATION (Weight: 15)

### Mark as Suspicious if:

**Section Contradictions:**
- Summary mentions 5 years experience, experience section shows 2 years
- Skills indicate senior level (architect, lead) but experience shows junior roles
- Experience starts before education completion
- Different years mentioned in different sections (>3 year difference)

### Mark as Genuine if:

- No contradictions between sections
- Consistent information across summary, skills, projects, education, experience
- Aligned career narrative

---

## AI CONTENT DETECTION (Weight: 10)

### Mark as Suspicious if:

**AI-Generated Patterns:**
- "as an AI language model"
- "i am writing this resume to"
- Placeholder text: "[Your Name]", "[Your Email]", "[Company Name]"
- "lorem ipsum"
- "insert your", "your address here"
- Generic AI phrases: "passionate about contributing", "eager to leverage my skills"
- Unnatural sentence structure (very low length variance)
- Repetitive phrases (same 4-word phrase appears >2 times)

### Mark as Genuine if:

- Natural writing style
- Varied sentence structure
- No template patterns
- Human-like content

---

## FINAL DECISION LOGIC

### Classification Rules:

1. **Calculate Suspicious Score**: Sum of weights from all failed validations (capped at 100)

2. **Base Classification**:
   - 0-24: Genuine
   - 25-49: Needs Review
   - 50-100: Suspicious

3. **Override Rule**: Never mark as "Genuine" if multiple strong checks fail (weight ≥ 20)
   - If 2+ strong failures exist, upgrade to "Needs Review" minimum

4. **Context Awareness**: Fresher/student status adjusts validation thresholds
   - Experience-related checks skipped for freshers
   - Missing information not penalized for entry-level candidates
   - Only contradictory evidence flagged

### Decision Examples:

**Genuine (0-24 points)**:
- Valid email, phone, location
- Consistent timeline
- No major contradictions
- No AI-generated patterns
- May have missing sections (for freshers)

**Needs Review (25-49 points)**:
- Minor inconsistencies
- Some missing information (for experienced candidates)
- 1-2 strong validation failures
- Possible but not definitive fraud indicators

**Suspicious (50+ points)**:
- Multiple strong validation failures
- Clear evidence of fraud (fake email, dummy phone, impossible timeline)
- Major contradictions
- AI-generated content
- Unrealistic claims

---

## Important Principles

1. **Evidence-Based**: Only flag resumes with clear evidence of fraud or inconsistency
2. **Context-Aware**: Adjust rules for freshers/students vs experienced candidates
3. **Fair to Entry-Level**: Missing experience, few skills, or limited information are NOT suspicious for freshers
4. **Clear Explanations**: Every classification must explain WHY it was chosen
5. **No False Positives**: Avoid penalizing legitimate candidates with incomplete information
6. **Focus on Fraud**: Suspicious score only increases for actual misleading information, not missing information

## Validation Weights Summary

| Validation | Weight | Skipped for Freshers? |
|------------|--------|---------------------|
| Email Validation | 25 | No |
| Phone Validation | 20 | No |
| Location Validation | 15 | No |
| Experience Timeline | 30 | Yes (adjusted) |
| Overlapping Employment | 25 | Yes |
| Experience Realism | 20 | Yes (adjusted) |
| Keyword Stuffing | 15 | No |
| Projects/Achievements | 15 | Yes (adjusted) |
| Section Contradictions | 15 | No |
| AI-Generated Content | 10 | No |

**Total Maximum Score**: 200 (capped at 100)
