"""Extract skills from resume text against the skill catalog."""

import re

from flask import current_app

from app.models import Skill

# Aliases map skill catalog names to common resume variants
SKILL_ALIASES = {
    "REST API": ["rest api", "restful api", "restful", "rest apis", "rest services"],
    "Machine Learning": ["machine learning", "deep learning", "ml ", " ml,"],
    "JavaScript": ["javascript", "js ", " js,", "node.js", "nodejs"],
    "MySQL": ["mysql", "mariadb"],
    "SQL": ["sql", "postgresql", "postgres", "sqlite"],
    "Git": ["git", "github", "gitlab", "bitbucket"],
    "Docker": ["docker", "kubernetes", "k8s"],
    "React": ["react", "react.js", "reactjs"],
    "Flask": ["flask", "django"],
    "Python": ["python", "python3", "py "],
    "Communication": ["communication", "interpersonal"],
    "Leadership": ["leadership", "team lead", "mentoring"],
}

# Extra skills detectable in text but may not exist in DB yet
EXTRA_SKILL_PATTERNS = [
    ("AWS", "technical", ["aws", "amazon web services"]),
    ("Azure", "technical", ["azure", "microsoft azure"]),
    ("TypeScript", "technical", ["typescript", "ts "]),
    ("FastAPI", "technical", ["fastapi"]),
    ("PostgreSQL", "technical", ["postgresql", "postgres"]),
    ("CI/CD", "tool", ["ci/cd", "continuous integration", "jenkins"]),
    ("Agile", "soft", ["agile", "scrum", "kanban"]),
]


def _normalize_text(text):
    return re.sub(r"\s+", " ", text.lower())


def _match_patterns(text, patterns):
    for pattern in patterns:
        if pattern in text:
            return True
    return False


def _word_match(text, skill_name):
    """Match whole skill name with word boundaries where possible."""
    escaped = re.escape(skill_name.lower())
    if " " in skill_name:
        return skill_name.lower() in text
    return bool(re.search(rf"\b{escaped}\b", text))


def _confidence_for_match(skill_name, text, via_alias=False):
    if via_alias:
        return 0.85
    count = len(re.findall(re.escape(skill_name.lower()), text))
    if count >= 3:
        return 0.98
    if count >= 2:
        return 0.95
    return 0.90


def extract_skills_from_text(text, include_extras=True):
    """
    Detect skills in resume text.
    Returns list of dicts: {name, category, confidence, matched_term}
    """
    if not text or not text.strip():
        return []

    normalized = _normalize_text(text)
    found = {}
    catalog = Skill.query.all()

    for skill in catalog:
        name = skill.name
        patterns = [name.lower()] + SKILL_ALIASES.get(name, [])
        matched = None
        via_alias = False

        for i, pattern in enumerate(patterns):
            if _word_match(normalized, pattern) if i == 0 else _match_patterns(normalized, [pattern]):
                matched = pattern
                via_alias = i > 0
                break

        if matched:
            conf = _confidence_for_match(name, normalized, via_alias=via_alias)
            found[name.lower()] = {
                "name": name,
                "category": skill.category,
                "confidence": conf,
                "matched_term": matched,
                "skill_id": skill.id,
            }

    if include_extras:
        for name, category, patterns in EXTRA_SKILL_PATTERNS:
            key = name.lower()
            if key in found:
                continue
            if _match_patterns(normalized, patterns):
                found[key] = {
                    "name": name,
                    "category": category,
                    "confidence": 0.80,
                    "matched_term": patterns[0],
                    "skill_id": None,
                }

    return sorted(found.values(), key=lambda x: x["confidence"], reverse=True)


def extract_skills_with_ai(text):
    """
    Future AI integration hook.
    Returns enhanced skill list when AI_ENABLED, else None.
    """
    if not current_app.config.get("AI_ENABLED"):
        return None

    api_key = current_app.config.get("OPENAI_API_KEY", "")
    if not api_key:
        return None

    # Placeholder for OpenAI / other provider integration (Step 6+)
    return None
