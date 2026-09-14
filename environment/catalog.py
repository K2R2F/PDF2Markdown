"""Pinned dependencies and source-mode installation paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
TESSDATA = RUNTIME / 'tessdata'
TESS_EXE = RUNTIME / 'tesseract' / 'tesseract.exe'
PACKAGES = {
    'docling': {'docling': '2.126.0'},
    'easyocr': {'easyocr': '1.7.2'},
    'rapidocr': {'rapidocr': '3.9.2', 'onnxruntime': '1.30.0'},
}
LABELS = {'docling': 'Docling', 'easyocr': 'EasyOCR',
          'rapidocr': 'RapidOCR / ONNX Runtime', 'tesseract': 'Tesseract'}
LANGUAGES = ('eng', 'jpn', 'chi_sim', 'osd')
INSTALLER_URL = ('https://github.com/UB-Mannheim/tesseract/releases/download/'
                 'v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe')
INSTALLER_SHA256 = 'c885fff6998e0608ba4bb8ab51436e1c6775c2bafc2559a19b423e18678b60c9'
