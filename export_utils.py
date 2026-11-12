"""
Export Utilities
-----------------
Converts a generated report (markdown-style text) into downloadable
PDF and DOCX files at runtime, using python-docx and reportlab.
These are lightweight pure-python libraries suitable for on-demand
export inside a running Flask app (as opposed to one-off document
generation, which would use the heavier docx/pptx/pdf skills).
"""
import os
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT

EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)


def _parse_markdown_lines(content):
    """Very small markdown parser: returns list of (type, text) tuples."""
    lines = content.split('\n')
    parsed = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('# '):
            parsed.append(('h1', stripped[2:]))
        elif stripped.startswith('## '):
            parsed.append(('h2', stripped[3:]))
        elif stripped.startswith('### '):
            parsed.append(('h3', stripped[4:]))
        elif stripped.startswith('*') and stripped.endswith('*') and len(stripped) > 2:
            parsed.append(('italic', stripped.strip('*')))
        elif stripped.startswith('**') and 'confidence' in stripped.lower():
            parsed.append(('bold', re.sub(r'\*\*', '', stripped)))
        else:
            parsed.append(('p', stripped))
    return parsed


def export_to_docx(report_title, report_content, filename):
    """Generate a .docx file from the report content."""
    doc = Document()

    parsed = _parse_markdown_lines(report_content)
    for line_type, text in parsed:
        if line_type == 'h1':
            heading = doc.add_heading(text, level=1)
        elif line_type == 'h2':
            doc.add_heading(text, level=2)
        elif line_type == 'h3':
            doc.add_heading(text, level=3)
        elif line_type == 'italic':
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.italic = True
            run.font.size = Pt(10)
        elif line_type == 'bold':
            p = doc.add_paragraph()
            run = p.add_run(text)
            run.bold = True
        else:
            doc.add_paragraph(text)

    filepath = os.path.join(EXPORT_DIR, filename)
    doc.save(filepath)
    return filepath


def export_to_pdf(report_title, report_content, filename):
    """Generate a .pdf file from the report content."""
    filepath = os.path.join(EXPORT_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                             leftMargin=1 * inch, rightMargin=1 * inch,
                             topMargin=1 * inch, bottomMargin=1 * inch)
    styles = getSampleStyleSheet()

    h1_style = ParagraphStyle('H1Custom', parent=styles['Heading1'], spaceAfter=12)
    h2_style = ParagraphStyle('H2Custom', parent=styles['Heading2'], spaceAfter=10)
    h3_style = ParagraphStyle('H3Custom', parent=styles['Heading3'], spaceAfter=8)
    body_style = ParagraphStyle('BodyCustom', parent=styles['Normal'],
                                 alignment=TA_LEFT, spaceAfter=8, leading=15)
    italic_style = ParagraphStyle('ItalicCustom', parent=styles['Italic'], spaceAfter=10)

    story = []
    parsed = _parse_markdown_lines(report_content)
    for line_type, text in parsed:
        safe_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if line_type == 'h1':
            story.append(Paragraph(safe_text, h1_style))
        elif line_type == 'h2':
            story.append(Paragraph(safe_text, h2_style))
        elif line_type == 'h3':
            story.append(Paragraph(safe_text, h3_style))
        elif line_type == 'italic':
            story.append(Paragraph(f"<i>{safe_text}</i>", italic_style))
        elif line_type == 'bold':
            story.append(Paragraph(f"<b>{safe_text}</b>", body_style))
        else:
            story.append(Paragraph(safe_text, body_style))
        story.append(Spacer(1, 4))

    doc.build(story)
    return filepath
