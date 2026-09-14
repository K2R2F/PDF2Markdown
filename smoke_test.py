"""Optional real-model integration check. Downloads models on the first run."""
import argparse
import json
from pathlib import Path

from conversion import Converter, Settings
from inputs import validate_pdf

parser = argparse.ArgumentParser()
parser.add_argument('pdf', type=Path)
parser.add_argument('--engine', choices=['easyocr', 'rapidocr'], default='easyocr')
parser.add_argument('--ocr', choices=['auto', 'force', 'off'], default='force')
parser.add_argument('--expect', default='Dummy PDF file')
args = parser.parse_args()
result = Converter(Settings(engine=args.engine, ocr_mode=args.ocr)).convert(
    validate_pdf(args.pdf.name, args.pdf.read_bytes())
)
print(json.dumps({'status': result.status, 'pages': result.pages, 'seconds': result.seconds,
                  'error': result.error, 'markdown': result.markdown}, ensure_ascii=False, indent=2))
assert result.status == 'success', result.error
assert args.expect.casefold() in result.markdown.casefold(), 'Expected text was not recognized'
