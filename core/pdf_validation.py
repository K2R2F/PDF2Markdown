from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath
from core.models import PdfInput

MAX_FILE = 100 * 1024 * 1024
MAX_TOTAL = 300 * 1024 * 1024
MAX_FILES = 30

def safe_name(name: str) -> str:
    name = PurePosixPath(name.replace('\\', '/')).name
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name).strip(' .')
    if not name:
        return 'document.pdf'
    suffix = PurePosixPath(name).suffix[:12]
    stem = name[:-len(suffix)] if suffix else name
    if PureWindowsPath(name).is_reserved():
        stem = '_' + stem
    return stem[:160 - len(suffix)] + suffix



def validate_pdf(name: str, data: bytes) -> PdfInput:
    if len(data) > MAX_FILE:
        raise ValueError('PDFは1件100 MBまでです。')
    if b'%PDF-' not in data[:1024]:
        raise ValueError('PDFのヘッダーがありません。PDF本体を指定してください。')
    return PdfInput(safe_name(name), data)



def check_batch(items: list[PdfInput]) -> None:
    if not items:
        raise ValueError('PDFを1件以上選択してください。')
    if len(items) > MAX_FILES:
        raise ValueError('一度に変換できるPDFは30件までです。')
    if sum(len(item.data) for item in items) > MAX_TOTAL:
        raise ValueError('PDFの合計サイズは300 MBまでです。')
