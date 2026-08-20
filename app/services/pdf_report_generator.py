"""PDF candidate report generator using ReportLab."""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from app.services.ats_scorer import calculate_ats_score


def generate_candidate_pdf_report(candidate, app_id=None):
    """
    Generate PDF report for candidate and return BytesIO buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0d1117'),
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#57606a'),
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#0969da'),
        spaceBefore=10,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#24292f'),
    )

    bold_label = ParagraphStyle(
        'BoldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#0d1117'),
    )

    elements = []

    # Header
    elements.append(Paragraph(candidate.full_name, title_style))
    sub_text = f"{candidate.current_title or 'Candidate'} | Status: {candidate.status.capitalize()} | Generated: {datetime.now().strftime('%b %d, %Y')}"
    elements.append(Paragraph(sub_text, subtitle_style))
    elements.append(Spacer(1, 8))

    # Contact table
    contact_data = [
        [
            Paragraph("<b>Email:</b> " + (candidate.email or "N/A"), body_style),
            Paragraph("<b>Phone:</b> " + (candidate.phone or "N/A"), body_style),
        ],
        [
            Paragraph("<b>LinkedIn:</b> " + (candidate.linkedin_url or "N/A"), body_style),
            Paragraph("<b>Experience:</b> " + (f"{candidate.years_experience} years" if candidate.years_experience else "N/A"), body_style),
        ]
    ]
    contact_table = Table(contact_data, colWidths=[270, 270])
    contact_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f6f8fa')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d7de')),
    ]))
    elements.append(contact_table)
    elements.append(Spacer(1, 10))

    # Job & ATS Score & Skill Gap Analysis
    application = None
    if app_id:
        from app.models import Application
        application = Application.query.get(app_id)
    elif candidate.applications:
        application = candidate.applications[0]

    job = application.job if application else None

    if application and job:
        ats_info = calculate_ats_score(candidate, job, candidate.primary_resume)

        elements.append(Paragraph(f"ATS Score & Skill Gap Analysis — Job: {job.title}", section_heading))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0969da'), spaceAfter=8))

        ats_data = [
            [
                Paragraph("<b>Overall ATS Score</b>", bold_label),
                Paragraph("<b>Skill Match</b>", bold_label),
                Paragraph("<b>Experience Score</b>", bold_label),
                Paragraph("<b>Recommendation</b>", bold_label),
            ],
            [
                Paragraph(f"<font color='#0969da' size='12'><b>{ats_info['ats_score']}%</b></font>", body_style),
                Paragraph(f"<b>{ats_info['skill_match_score']}%</b>", body_style),
                Paragraph(f"<b>{ats_info['experience_score']}%</b>", body_style),
                Paragraph(f"<b>{ats_info['recommendation']}</b> ({ats_info['ai_confidence']}% conf)", body_style),
            ]
        ]
        ats_table = Table(ats_data, colWidths=[135, 135, 135, 135])
        ats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ddf4ff')),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#f6f8fa')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d7de')),
        ]))
        elements.append(ats_table)
        elements.append(Spacer(1, 8))

        # Skill Gap Breakdown
        matched_str = ", ".join(ats_info['matched_skills']) if ats_info['matched_skills'] else "None"
        missing_str = ", ".join(ats_info['missing_skills']) if ats_info['missing_skills'] else "None (All Required Skills Matched!)"

        gap_data = [
            [Paragraph("<b>Matched Skills:</b>", bold_label), Paragraph(f"<font color='#1a7f37'>{matched_str}</font>", body_style)],
            [Paragraph("<b>Missing Skills:</b>", bold_label), Paragraph(f"<font color='#cf222e'>{missing_str}</font>", body_style)],
        ]
        gap_table = Table(gap_data, colWidths=[120, 420])
        gap_table.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d7de')),
        ]))
        elements.append(gap_table)
        elements.append(Spacer(1, 12))

    # Candidate Resume Summary & Skills
    elements.append(Paragraph("Candidate Summary & Profile Details", section_heading))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0969da'), spaceAfter=8))

    summary_text = candidate.professional_summary or candidate.career_objective or candidate.summary or "No summary available."
    elements.append(Paragraph("<b>Professional Summary:</b> " + summary_text, body_style))
    elements.append(Spacer(1, 6))

    if candidate.technical_skills:
        elements.append(Paragraph("<b>Technical Skills:</b> " + candidate.technical_skills, body_style))
        elements.append(Spacer(1, 4))

    if candidate.education:
        elements.append(Paragraph("<b>Education:</b> " + candidate.education.replace('\n', ' | '), body_style))
        elements.append(Spacer(1, 4))

    if candidate.experience:
        elements.append(Paragraph("<b>Work Experience:</b> " + candidate.experience[:400].replace('\n', ' | ') + ("..." if len(candidate.experience) > 400 else ""), body_style))
        elements.append(Spacer(1, 10))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_recruitment_pdf_report(candidate_id, job_id):
    """
    Generate comprehensive Recruitment AI Report PDF for candidate and job.
    Includes ATS score, Interview Evaluation scores, Final Recommendation, and Reason.
    """
    from app.models import Candidate, Job, InterviewEvaluation
    candidate = Candidate.query.get_or_404(candidate_id)
    job = Job.query.get_or_404(job_id)
    eval_record = InterviewEvaluation.query.filter_by(candidate_id=candidate.id, job_id=job.id).first()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'RecTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#0d1117')
    )
    subtitle_style = ParagraphStyle(
        'RecSubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#57606a')
    )
    section_heading = ParagraphStyle(
        'RecHeading', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#0969da'), spaceBefore=8, spaceAfter=4
    )
    body_style = ParagraphStyle(
        'RecBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#24292f')
    )
    bold_label = ParagraphStyle(
        'RecBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.HexColor('#0d1117')
    )

    elements = []

    # Title Banner
    elements.append(Paragraph(f"Recruitment AI Report — {candidate.full_name}", title_style))
    sub_text = f"Target Position: {job.title} ({job.department or 'HR'}) | Generated: {datetime.now().strftime('%b %d, %Y')}"
    elements.append(Paragraph(sub_text, subtitle_style))
    elements.append(Spacer(1, 10))

    # Candidate Meta Table
    meta_data = [
        [Paragraph("<b>Candidate Name:</b> " + candidate.full_name, body_style), Paragraph("<b>Email:</b> " + (candidate.email or "N/A"), body_style)],
        [Paragraph("<b>Phone:</b> " + (candidate.phone or "N/A"), body_style), Paragraph("<b>Experience:</b> " + (f"{candidate.years_experience} years" if candidate.years_experience else "N/A"), body_style)],
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f6f8fa')),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d7de')),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 10))

    # ATS & Skill Gap Analysis
    ats_info = calculate_ats_score(candidate, job, candidate.primary_resume)
    elements.append(Paragraph("1. ATS Screening & Skill Gap Analysis", section_heading))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0969da'), spaceAfter=6))

    ats_data = [
        [Paragraph("<b>ATS Score</b>", bold_label), Paragraph("<b>Skill Match</b>", bold_label), Paragraph("<b>Experience Score</b>", bold_label), Paragraph("<b>ATS Recommendation</b>", bold_label)],
        [Paragraph(f"<font color='#0969da'><b>{ats_info['ats_score']}%</b></font>", body_style), Paragraph(f"<b>{ats_info['skill_match_score']}%</b>", body_style), Paragraph(f"<b>{ats_info['experience_score']}%</b>", body_style), Paragraph(f"<b>{ats_info['recommendation']}</b>", body_style)]
    ]
    ats_table = Table(ats_data, colWidths=[135, 135, 135, 135])
    ats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ddf4ff')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#ffffff')),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d7de')),
    ]))
    elements.append(ats_table)
    elements.append(Spacer(1, 8))

    matched_str = ", ".join(ats_info['matched_skills']) if ats_info['matched_skills'] else "None"
    missing_str = ", ".join(ats_info['missing_skills']) if ats_info['missing_skills'] else "None"
    elements.append(Paragraph(f"<b>Matched Skills:</b> <font color='#1a7f37'>{matched_str}</font>", body_style))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph(f"<b>Missing Skills:</b> <font color='#cf222e'>{missing_str}</font>", body_style))
    elements.append(Spacer(1, 10))

    # Interview Evaluation Section
    elements.append(Paragraph("2. HR Interview Evaluation Breakdown", section_heading))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0969da'), spaceAfter=6))

    if eval_record:
        eval_data = [
            [Paragraph("<b>Evaluation Category</b>", bold_label), Paragraph("<b>Rating (1-5)</b>", bold_label), Paragraph("<b>Weighted Score</b>", bold_label)],
            [Paragraph("Technical Knowledge", body_style), Paragraph(f"{eval_record.technical_knowledge} / 5", body_style), Paragraph(f"{round((eval_record.technical_knowledge/5.0)*25, 1)} pts (25%)", body_style)],
            [Paragraph("Communication", body_style), Paragraph(f"{eval_record.communication} / 5", body_style), Paragraph(f"{round((eval_record.communication/5.0)*20, 1)} pts (20%)", body_style)],
            [Paragraph("Problem Solving", body_style), Paragraph(f"{eval_record.problem_solving} / 5", body_style), Paragraph(f"{round((eval_record.problem_solving/5.0)*25, 1)} pts (25%)", body_style)],
            [Paragraph("Confidence", body_style), Paragraph(f"{eval_record.confidence} / 5", body_style), Paragraph(f"{round((eval_record.confidence/5.0)*15, 1)} pts (15%)", body_style)],
            [Paragraph("Cultural Fit", body_style), Paragraph(f"{eval_record.cultural_fit} / 5", body_style), Paragraph(f"{round((eval_record.cultural_fit/5.0)*15, 1)} pts (15%)", body_style)],
            [Paragraph("<b>Overall Interview Score</b>", bold_label), Paragraph(f"<b>{eval_record.interview_score}%</b>", bold_label), Paragraph("<b>100% Total</b>", bold_label)],
        ]
        eval_table = Table(eval_data, colWidths=[200, 170, 170])
        eval_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f6f8fa')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d0d7de')),
        ]))
        elements.append(eval_table)
        elements.append(Spacer(1, 6))

        if eval_record.overall_comments:
            elements.append(Paragraph("<b>HR Interview Notes:</b> " + eval_record.overall_comments, body_style))
            elements.append(Spacer(1, 8))
    else:
        elements.append(Paragraph("<i>Interview Evaluation pending. Ratings have not been submitted yet.</i>", body_style))
        elements.append(Spacer(1, 8))

    # Final Recommendation
    elements.append(Paragraph("3. Final Recruitment Decision", section_heading))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#0969da'), spaceAfter=6))

    rec_val = eval_record.final_recommendation if eval_record else ("Hire" if ats_info['ats_score'] >= 75 else ("Hold" if ats_info['ats_score'] >= 50 else "Reject"))
    reason_val = eval_record.recommendation_reason if eval_record else f"Based on ATS Score of {ats_info['ats_score']}%."

    rec_color = '#1a7f37' if rec_val == 'Hire' else ('#9a6700' if rec_val == 'Hold' else '#cf222e')
    rec_box = [
        [Paragraph(f"<b>Final Decision: <font color='{rec_color}'>{rec_val.upper()}</font></b>", ParagraphStyle('RecDec', parent=bold_label, fontSize=11))],
        [Paragraph(f"<b>Rationale:</b> {reason_val}", body_style)]
    ]
    rec_table = Table(rec_box, colWidths=[540])
    rec_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f6f8fa')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(rec_color)),
    ]))
    elements.append(rec_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

