"""Resume duplicate detection service using email, phone number, and text similarity."""

import re
from difflib import SequenceMatcher
from app.models import Candidate, Resume


def _normalize_phone(phone_str):
    """Normalize phone number to digits only (last 10 digits)."""
    if not phone_str:
        return ""
    digits = re.sub(r"\D", "", str(phone_str))
    return digits[-10:] if len(digits) >= 10 else digits


def _calculate_text_similarity(text1, text2):
    """Calculate similarity percentage between two texts (0.0 to 100.0)."""
    if not text1 or not text2:
        return 0.0
    
    # Fast set jaccard word similarity first
    words1 = set(re.findall(r"\w+", text1.lower()))
    words2 = set(re.findall(r"\w+", text2.lower()))
    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)
    jaccard = (intersection / union) * 100.0 if union > 0 else 0.0

    # If jaccard > 50%, run SequenceMatcher sample for finer accuracy
    if jaccard >= 50.0:
        sample1 = text1[:2000].lower()
        sample2 = text2[:2000].lower()
        seq_ratio = SequenceMatcher(None, sample1, sample2).ratio() * 100.0
        return round((jaccard * 0.4) + (seq_ratio * 0.6), 1)

    return round(jaccard, 1)


def check_duplicate_candidate(email=None, phone=None, extracted_text=None, candidate_id=None):
    """
    Check if candidate / resume matches existing candidate in DB by:
    1. Email
    2. Phone number
    3. Resume text similarity (> 75%)
    
    Returns dict:
    {
        "is_duplicate": bool,
        "reasons": list of str,
        "matched_candidate_id": int or None,
        "matched_candidate_name": str or None,
        "similarity_score": float
    }
    """
    reasons = []
    matched_candidate = None
    max_similarity = 0.0

    # 1. Email check
    if email and str(email).strip().lower() not in {"not provided", "n/a", "none", ""}:
        clean_email = str(email).strip().lower()
        q = Candidate.query.filter(Candidate.email.ilike(clean_email))
        if candidate_id:
            q = q.filter(Candidate.id != candidate_id)
        existing = q.first()
        if existing:
            reasons.append(f"Matching email address ({existing.email}) with candidate '{existing.full_name}' (ID: #{existing.id})")
            matched_candidate = existing

    # 2. Phone check
    norm_phone = _normalize_phone(phone)
    if norm_phone and len(norm_phone) >= 7:
        all_candidates = Candidate.query.all()
        for cand in all_candidates:
            if candidate_id and cand.id == candidate_id:
                continue
            if cand.phone and _normalize_phone(cand.phone) == norm_phone:
                reason = f"Matching phone number ({cand.phone}) with candidate '{cand.full_name}' (ID: #{cand.id})"
                if reason not in reasons:
                    reasons.append(reason)
                if not matched_candidate:
                    matched_candidate = cand

    # 3. Resume text similarity check
    if extracted_text and len(extracted_text.strip()) > 50:
        resumes_query = Resume.query.filter(Resume.extracted_text != None)
        if candidate_id:
            resumes_query = resumes_query.filter(Resume.candidate_id != candidate_id)
        
        existing_resumes = resumes_query.all()
        for res in existing_resumes:
            if not res.extracted_text:
                continue
            sim = _calculate_text_similarity(extracted_text, res.extracted_text)
            if sim > max_similarity:
                max_similarity = sim
            if sim >= 75.0:
                target_cand = res.candidate
                cand_name = target_cand.full_name if target_cand else f"Candidate #{res.candidate_id}"
                reason = f"High resume similarity ({sim}%) with candidate '{cand_name}' (ID: #{res.candidate_id})"
                if reason not in reasons:
                    reasons.append(reason)
                if not matched_candidate and target_cand:
                    matched_candidate = target_cand

    is_duplicate = len(reasons) > 0

    return {
        "is_duplicate": is_duplicate,
        "reasons": reasons,
        "matched_candidate_id": matched_candidate.id if matched_candidate else None,
        "matched_candidate_name": matched_candidate.full_name if matched_candidate else None,
        "similarity_score": max_similarity
    }
