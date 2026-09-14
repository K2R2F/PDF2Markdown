from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    engine: str = 'easyocr'
    language: str = 'ja_en'
    ocr_mode: str = 'auto'
    tables: bool = True
    images: bool = False
    max_pages: int = 200



@dataclass
class Result:
    name: str
    status: str
    markdown: str = ''
    error: str = ''
    seconds: float = 0
    pages: int = 0



@dataclass(frozen=True)
class PdfInput:
    name: str
    data: bytes
