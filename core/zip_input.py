from __future__ import annotations

from io import BytesIO
from zipfile import BadZipFile, ZipFile
from core.models import PdfInput
from core.pdf_validation import MAX_FILE, MAX_TOTAL, MAX_FILES, validate_pdf, check_batch

def read_zip(data: bytes) -> list[PdfInput]:
    if len(data) > MAX_FILE:
        raise ValueError('ZIPは100 MBまでです。')
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = [e for e in archive.infolist() if not e.is_dir()
                       and e.filename.lower().endswith('.pdf')
                       and not e.filename.startswith('__MACOSX/')]
            if not entries or len(entries) > MAX_FILES:
                raise ValueError('ZIP内のPDFは1〜30件にしてください。')
            if sum(e.file_size for e in entries) > MAX_TOTAL:
                raise ValueError('ZIP展開後のPDF合計は300 MBまでです。')
            result = []
            for entry in entries:
                if entry.flag_bits & 1:
                    raise ValueError('暗号化ZIPには対応していません。')
                if entry.file_size > MAX_FILE:
                    raise ValueError('ZIP内のPDFは1件100 MBまでです。')
                # Never extract archive paths to the filesystem.
                with archive.open(entry) as stream:
                    result.append(validate_pdf(entry.filename, stream.read(MAX_FILE + 1)))
            check_batch(result)
            return result
    except BadZipFile as exc:
        raise ValueError('ZIPが破損しているか、ZIP形式ではありません。') from exc
