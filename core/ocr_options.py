from __future__ import annotations

from core.models import Settings
from environment.detection import tesseract_configuration

def pipeline_options(settings: Settings):
    from docling.datamodel.pipeline_options import (
        EasyOcrOptions, OcrMode, PdfPipelineOptions, RapidOcrOptions,
        TableFormerMode, TesseractCliOcrOptions,
    )
    options = PdfPipelineOptions()
    options.do_ocr = settings.ocr_mode != 'off'
    options.do_table_structure = settings.tables
    options.table_structure_options.mode = TableFormerMode.ACCURATE
    options.generate_picture_images = settings.images
    options.document_timeout = 600
    if options.do_ocr:
        mode = OcrMode.FULL_PAGE if settings.ocr_mode == 'force' else OcrMode.DEFAULT
        if settings.engine == 'easyocr':
            languages = {'ja_en': ['ja', 'en'], 'en': ['en'], 'zh_en': ['ch_sim', 'en']}
            options.ocr_options = EasyOcrOptions(lang=languages[settings.language], mode=mode)
        elif settings.engine == 'rapidocr':
            languages = {'ja_en': ['japan'], 'en': ['en'], 'zh_en': ['ch']}
            options.ocr_options = RapidOcrOptions(lang=languages[settings.language], backend='onnxruntime',
                                                  mode=mode)
        elif settings.engine == 'tesseract':
            languages = {'ja_en': ['jpn', 'eng'], 'en': ['eng'], 'zh_en': ['chi_sim', 'eng']}
            options.ocr_options = TesseractCliOcrOptions(lang=languages[settings.language], mode=mode,
                                                       **tesseract_configuration())
        else:
            raise ValueError('未対応のOCRエンジンです。')
    return options
