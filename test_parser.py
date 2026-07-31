import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.services.resume_extractor import extract_candidate_fields
from pprint import pprint

text = """
John Doe
Senior Software Engineer
Email: john.doe@example.com Phone: +91 9876543210
Address: M Tirunelveli-627425 Email GitHub: jdoe99 LinkedIn: linkedin.com/in/jdoe99

OBJECTIVE
I am an AI language model but I want to be a real boy. Phone: 12345
Experience with Python, Django, React.

EDUCATION
B.Tech in Computer Science
Anna University, Chennai

SKILLS
Python, Flask, JavaScript, React

EXPERIENCE
Senior Developer at TechCorp (2020 - Present)
Developed scalable web applications.
"""

fields = extract_candidate_fields(text, "John_Doe_Resume.pdf")
print("Extracted fields:")
pprint(fields)
