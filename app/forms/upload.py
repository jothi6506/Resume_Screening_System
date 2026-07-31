"""Upload-related forms."""

from flask_wtf import FlaskForm
from wtforms import FileField, SelectField, SubmitField
from wtforms.validators import Optional


class ResumeUploadForm(FlaskForm):
    job_id = SelectField("Apply to Job", coerce=int, validators=[Optional()])
    resumes = FileField(
        "Resume Files",
        render_kw={
            "multiple": True,
            "accept": ".pdf",
            "class": "d-none",
            "id": "resumeFiles",
        },
    )
    submit = SubmitField("Upload & Parse")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.job_id.choices = [(0, "— No specific job —")]
