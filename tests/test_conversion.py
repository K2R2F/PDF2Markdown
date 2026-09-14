import json
import threading
import unittest
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

from conversion import Converter, Result, Settings, make_zip, output_names, pipeline_options
from inputs import PdfInput


class OutputTests(unittest.TestCase):
    def test_zip_has_unique_names_and_failure_manifest(self):
        results = [Result('a/report.pdf', 'success', '# 日本語'),
                   Result('REPORT.pdf', 'partial_success', 'partial', 'page warning'),
                   Result('report_2.pdf', 'success', 'other'),
                   Result('bad.pdf', 'failure', error='invalid PDF')]
        with ZipFile(BytesIO(make_zip(results, Settings()))) as archive:
            self.assertEqual(len(archive.namelist()), len(set(n.lower() for n in archive.namelist())))
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(archive.read('report.md').decode(), '# 日本語')
            self.assertIsNone(manifest['results'][3]['output'])
            self.assertNotIn('bad.md', archive.namelist())
            self.assertEqual(manifest['results'][1]['status'], 'partial_success')

    def test_options_accept_languages_for_installed_engines(self):
        for engine in ('easyocr', 'rapidocr'):
            for language in ('ja_en', 'en', 'zh_en'):
                options = pipeline_options(Settings(engine=engine, language=language, ocr_mode='force'))
                self.assertTrue(options.do_ocr)
                self.assertEqual(options.ocr_options.mode.value, 'full_page')
        self.assertFalse(pipeline_options(Settings(ocr_mode='off')).do_ocr)

    def test_conversion_failure_does_not_prevent_next_document(self):
        converter = Converter.__new__(Converter)
        converter.settings = Settings()
        converter.lock = threading.Lock()
        class Backend:
            def convert(self, source, **kwargs):
                if source.name == 'bad.pdf':
                    raise ValueError('broken')
                return SimpleNamespace(status=SimpleNamespace(value='success'), errors=[],
                    document=SimpleNamespace(pages={1: None}, export_to_markdown=lambda **kw: '# ok'))
        converter.converter = Backend()
        self.assertEqual(converter.convert(PdfInput('bad.pdf', b'%PDF-')).status, 'failure')
        self.assertEqual(converter.convert(PdfInput('good.pdf', b'%PDF-')).markdown, '# ok')


if __name__ == '__main__':
    unittest.main()
