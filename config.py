import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"
FRONTPAGE_DOCX = TEMPLATES_DIR / "frontpage.docx"
FRONTPAGE_PDF = TEMPLATES_DIR / "frontpage_template.pdf"
REPORT_PDF = TEMPLATES_DIR / "report.pdf"

SECRET_KEY = os.environ.get("STUDENT_PDF_SECRET_KEY") or secrets.token_hex(32)
MAX_NAME_LENGTH = 100
MAX_REGISTER_LENGTH = 50
OUTPUT_MAX_AGE_SECONDS = 60 * 60
OUTPUT_DELETE_AFTER_SECONDS = 10

# Coordinates are ReportLab points, measured from the bottom-left of page one.
# The x coordinate is the horizontal center because both fields are centered.
OVERLAY = {
    "student_name": {
        "x": 297.64,
        "y": 737.0,
        "font_size": 16,
        "font_name": "Times-Bold",
        "mask_width": 220.0,
        "mask_height": 22.0,
        "align": "center",
    },
    "register_number": {
        "x": 297.64,
        "y": 714.0,
        "font_size": 15,
        "font_name": "Times-Bold",
        "mask_width": 250.0,
        "mask_height": 22.0,
        "align": "center",
    },
}
