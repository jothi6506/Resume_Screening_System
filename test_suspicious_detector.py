"""Unit tests for the Suspicious Resume Detection service.
"""

import unittest
import sys
import os

# Ensure project app is in import path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.suspicious_detector import (
    validate_email_format,
    validate_phone_number,
    check_skill_evidence,
    detect_suspicious_patterns
)

class MockResume:
    def __init__(self, text):
        self.extracted_text = text

class MockCandidate:
    def __init__(self, **kwargs):
        self.full_name = kwargs.get("full_name", "Test Candidate")
        self.email = kwargs.get("email", "candidate@example.com")
        self.phone = kwargs.get("phone", "9876543210")
        self.education = kwargs.get("education", "B.Tech Computer Science, 2020")
        self.experience = kwargs.get("experience", "Software Engineer at Google, 2 years")
        self.projects = kwargs.get("projects", "Built a Python-based web app")
        self.technical_skills = kwargs.get("technical_skills", "Python, SQL")
        self.soft_skills = kwargs.get("soft_skills", "Communication")
        self.certifications = kwargs.get("certifications", "Google Cloud Certification")
        self.professional_summary = kwargs.get("professional_summary", "Experienced programmer")
        self.career_objective = kwargs.get("career_objective", "To get a job")
        self.summary = kwargs.get("summary", "Summary of candidate")
        self.years_experience = kwargs.get("years_experience", 2.0)
        self.skills = []
        self.primary_resume = kwargs.get("primary_resume", None)


class TestSuspiciousDetector(unittest.TestCase):

    def test_email_validation(self):
        # Valid cases
        self.assertTrue(validate_email_format("abc@gmail.com")[0])
        self.assertTrue(validate_email_format("student123@outlook.com")[0])
        self.assertTrue(validate_email_format("user_name@yahoo.in")[0])
        
        # Invalid cases
        self.assertFalse(validate_email_format("abcgmail.com")[0])
        self.assertFalse(validate_email_format("abc@")[0])
        self.assertFalse(validate_email_format("@gmail.com")[0])
        self.assertFalse(validate_email_format("abc @gmail.com")[0])
        self.assertFalse(validate_email_format("abc@gmail")[0])
        self.assertFalse(validate_email_format("abc..123@gmail.com")[0])
        self.assertFalse(validate_email_format("")[0])
        self.assertFalse(validate_email_format("Not Provided")[0])

    def test_phone_validation(self):
        # Valid cases
        self.assertEqual(validate_phone_number("9876543211")[0], "valid")
        self.assertEqual(validate_phone_number("+91 98765 43211")[0], "valid")
        self.assertEqual(validate_phone_number("91-98765-43211")[0], "valid")
        self.assertEqual(validate_phone_number("6789123456")[0], "valid")

        # Invalid cases
        self.assertEqual(validate_phone_number("987654321")[0], "invalid") # Short
        self.assertEqual(validate_phone_number("987654321012")[0], "invalid") # Long
        self.assertEqual(validate_phone_number("98AB543210")[0], "invalid") # Letters
        self.assertEqual(validate_phone_number("5876543210")[0], "invalid") # Starts with 5
        self.assertEqual(validate_phone_number("")[0], "invalid")
        self.assertEqual(validate_phone_number("Not Provided")[0], "invalid")

        # Suspicious cases
        self.assertEqual(validate_phone_number("9999999999")[0], "suspicious")
        self.assertEqual(validate_phone_number("1111111111")[0], "suspicious")
        self.assertEqual(validate_phone_number("0000000000")[0], "suspicious")
        self.assertEqual(validate_phone_number("1234567890")[0], "suspicious")
        self.assertEqual(validate_phone_number("0123456789")[0], "suspicious")
        self.assertEqual(validate_phone_number("9876543210")[0], "suspicious")

    def test_skill_evidence(self):
        sources = [
            "Project: Resume Screening System using Python Flask MySQL",
            "Experience: Worked with AWS Cloud Infrastructure"
        ]
        self.assertTrue(check_skill_evidence("Python", sources))
        self.assertTrue(check_skill_evidence("AWS", sources))
        self.assertFalse(check_skill_evidence("Java", sources))
        
        # Test special characters in skills
        sources_special = ["C++ Developer with .NET and C# experience"]
        self.assertTrue(check_skill_evidence("C++", sources_special))
        self.assertTrue(check_skill_evidence(".NET", sources_special))
        self.assertTrue(check_skill_evidence("C#", sources_special))

    def test_clean_candidate_score(self):
        # 100% clean candidate
        candidate = MockCandidate(
            email="clean.candidate@gmail.com",
            phone="9876543211",
            education="Graduated from Anna University with B.E. CSE in 2021",
            experience="Worked at Infosys as developer using Python.",
            projects="Built a Resume parser using Python Flask.",
            technical_skills="Python",
            years_experience=2.0
        )
        report = detect_suspicious_patterns(candidate)
        self.assertEqual(report["score"], 0)
        self.assertEqual(report["status"], "Low Risk")
        self.assertTrue(report["email_validation"]["valid"])
        self.assertEqual(report["phone_validation"]["status"], "valid")
        self.assertEqual(len(report["warnings"]), 0)

    def test_suspicious_scoring_and_warnings(self):
        # Dummy candidate with:
        # Invalid email format (missing extension) (+15)
        # Suspicious phone pattern (+10)
        # Missing Education section (+15)
        # Missing Projects section (+15)
        # Duplicate skills (+10)
        # Unsupported skills: Python & SQL have no evidence in text (+20 for multiple unsupported skills)
        candidate = MockCandidate(
            email="invalid_email@domain",
            phone="9999999999",
            education="Not Provided",
            experience="No experience.",
            projects="None",
            technical_skills="Python, SQL, Python", # Python is duplicated
            years_experience=0.0
        )
        
        report = detect_suspicious_patterns(candidate)
        
        # Check warnings
        self.assertIn("Invalid Email Format", report["warnings"])
        self.assertIn("Suspicious Phone Number Pattern", report["warnings"])
        self.assertIn("Education section is missing.", report["warnings"])
        self.assertIn("Projects section is missing.", report["warnings"])
        self.assertIn("Duplicate content detected", report["warnings"])
        self.assertIn("Python skill has no supporting evidence", report["warnings"])
        
        # Score calculation:
        # Invalid Email (+15)
        # Suspicious Phone (+10)
        # Missing Education (+15)
        # Missing Projects (+15)
        # Duplicate Content (+10)
        # Multiple Unsupported Skills (Python, SQL) (+20)
        # Total expected: 85.
        self.assertEqual(report["score"], 85)
        self.assertEqual(report["status"], "Needs Manual Review")

    def test_fresher_unrealistic_claims(self):
        # Fresher candidate listing AWS, Kubernetes, DevOps, Machine Learning without evidence
        candidate = MockCandidate(
            email="fresher@gmail.com",
            phone="9876543211",
            education="B.Sc CS, 2025",
            experience="Not Provided",
            projects="None", # Missing projects (+15)
            technical_skills="AWS, Kubernetes, DevOps, Machine Learning",
            years_experience=0.0
        )
        report = detect_suspicious_patterns(candidate)
        
        # Should flag fresher warning
        self.assertIn("Multiple advanced skills found without supporting evidence. Manual review recommended.", report["warnings"])
        
        # Expected Score:
        # Valid email (+0)
        # Valid phone (+0)
        # Education present (+0)
        # Missing Skills: present (+0)
        # Missing Projects: +15
        # Duplicate content: none (+0)
        # Multiple unsupported skills: AWS, Kubernetes, DevOps, Machine Learning all unsupported (>=2) (+20)
        # Unrealistic claims fresher warning: +20
        # Total expected: 15 (projects) + 20 (unsupported) + 20 (unrealistic claims) = 55.
        self.assertEqual(report["score"], 55)
        self.assertEqual(report["status"], "Medium Risk")


if __name__ == "__main__":
    unittest.main()
