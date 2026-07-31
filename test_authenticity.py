"""Quick test of the new authenticity service."""
from app import create_app
app = create_app()

with app.app_context():
    from app.services.authenticity_service import analyse_resume

    class FakeResume:
        def __init__(self, text):
            self.extracted_text = text

    class NormalCandidate:
        full_name = "John Doe"
        email = "john@gmail.com"
        phone = "9876543210"
        location = "Chennai"
        address = "62D VK Puram"
        city = "Chennai"
        state = "Tamil Nadu"
        linkedin_url = None
        github_url = None
        years_experience = 3
        education = "B.Tech Computer Science, Anna University 2018-2022"
        experience = "Software Engineer at TCS, 2022-2024"
        projects = "Built a web app for inventory management"
        technical_skills = "Python, Django, SQL, REST APIs"
        soft_skills = None
        skills = []
        professional_summary = "Experienced Python developer"
        career_objective = None

    class TemplateCandidate:
        full_name = "[Your Name]"
        email = "insert@email.com"
        phone = "1234"
        location = None
        address = None
        city = None
        state = None
        linkedin_url = None
        github_url = None
        years_experience = None
        education = None
        experience = None
        projects = None
        technical_skills = None
        soft_skills = None
        skills = []
        professional_summary = None
        career_objective = None

    normal_text = """
John Doe
Email: john@gmail.com | Phone: 9876543210
Chennai, Tamil Nadu

EDUCATION
B.Tech Computer Science, Anna University 2018-2022

EXPERIENCE
Software Engineer at TCS, 2022-2024

SKILLS
Python, Django, SQL, REST APIs

PROJECTS
Built a web app for inventory management
    """

    template_text = "Lorem ipsum [Your Name] [your email] [company name] insert your experience here"

    r1 = analyse_resume(NormalCandidate(), FakeResume(normal_text))
    print(f"Test 1 (Normal Resume):")
    print(f"  Score     = {r1['score']}%")
    print(f"  Status    = {r1['status']}")
    print(f"  Suspicious= {r1['is_suspicious']}")
    print(f"  Reasons   = {r1['suspicious_reasons']}")

    print()

    r2 = analyse_resume(TemplateCandidate(), FakeResume(template_text))
    print(f"Test 2 (Template/Placeholder Resume):")
    print(f"  Score     = {r2['score']}%")
    print(f"  Status    = {r2['status']}")
    print(f"  Suspicious= {r2['is_suspicious']}")
    print(f"  Reasons   = {r2['suspicious_reasons']}")
