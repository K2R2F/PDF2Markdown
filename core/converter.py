from __future__ import annotations

import threading
import time
from io import BytesIO
from core.models import PdfInput, Settings, Result
from core.ocr_options import pipeline_options
from environment.locks import OPERATION_LOCK

class Converter:
    def __init__(self, settings: Settings):
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import DocumentConverter, PdfFormatOption
        self.settings = settings
        self.lock = threading.Lock()
        self.converter = DocumentConverter(allowed_formats=[InputFormat.PDF], format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options(settings))
        })

    def convert(self, item: PdfInput) -> Result:
        from docling.datamodel.base_models import DocumentStream
        from docling_core.types.doc import ImageRefMode
        started = time.monotonic()
        try:
            with OPERATION_LOCK, self.lock:
                converted = self.converter.convert(
                    DocumentStream(name=item.name, stream=BytesIO(item.data)),
                    raises_on_error=False, max_num_pages=self.settings.max_pages,
                )
                status = converted.status.value
                if status not in ('success', 'partial_success'):
                    errors = '; '.join(str(e.error_message) for e in converted.errors)
                    raise ValueError(errors or f'変換状態: {status}。破損・暗号化・ページ上限を確認してください。')
                markdown = converted.document.export_to_markdown(
                    image_mode=ImageRefMode.EMBEDDED if self.settings.images else ImageRefMode.PLACEHOLDER
                )
                warning = '; '.join(str(e.error_message) for e in converted.errors)
                return Result(item.name, status, markdown, warning,
                              round(time.monotonic() - started, 2), len(converted.document.pages))
        except Exception as exc:
            return Result(item.name, 'failure', error=str(exc), seconds=round(time.monotonic() - started, 2))
