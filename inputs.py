"""Compatibility imports; implementations live in core/."""
from core.models import PdfInput
from core.pdf_validation import MAX_FILE, MAX_TOTAL, MAX_FILES, safe_name, validate_pdf, check_batch
from core.zip_input import read_zip
from core.url_input import public_target, fetch_pdf
