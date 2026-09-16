import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
from conversion import Result, Settings
from inputs import PdfInput


class AppTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        override = patch.dict('os.environ', {'PDF2MARKDOWN_DATA_DIR': folder.name})
        override.start()
        self.addCleanup(override.stop)

    def test_environment_panel_detects_missing_tool_and_starts_one_job(self):
        from environment_ui import environment_report
        environment_report.clear()
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
        with patch('environment_ui.start_setup') as start:
            app.button(key='install_tesseract').click().run()
        self.assertFalse(app.exception)
        start.assert_called_once_with('tesseract')

    def test_empty_ui_and_url_batch_with_partial_failure(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertTrue(app.button[0].disabled)
        app.segmented_control[0].set_value('URL').run()
        app.text_area[0].set_value('https://example.com/good.pdf\nhttps://example.com/bad.pdf').run()
        with patch('ui.converter_cache.Converter') as constructor:
            constructor.return_value.convert.return_value = Result('good.pdf', 'success', '# 完了', pages=1)
            with patch('ui.batch_panel.fetch_pdf', side_effect=[PdfInput('good.pdf', b'%PDF-'), ValueError('HTTP 404')]):
                app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state['results']), 2)
        self.assertEqual([m.value for m in app.metric], ['1', '0', '1'])
        self.assertFalse(app.button(key='save_zip').disabled)
        self.assertFalse(app.button(key='save_1').disabled)
        from storage import state
        saved = state.load_batch(state.list_batches()[0][0])
        self.assertEqual(saved[2], 'failure')
        self.assertEqual([r.status for r in saved[1]], ['failure', 'success'])

    def test_one_click_save_writes_markdown_and_zip_without_reconversion(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
        app.session_state['results'] = [Result('report.pdf', 'success', '# 日本語\n', pages=1)]
        app.session_state['result_settings'] = Settings()
        with tempfile.TemporaryDirectory() as folder:
            app.text_input(key='save_directory').set_value(folder).run()
            app.button(key='save_0').click().run()
            self.assertFalse(app.exception)
            self.assertEqual((Path(folder) / 'report.md').read_text(encoding='utf-8'), '# 日本語\n')
            self.assertTrue(app.success)
            app.button(key='save_zip').click().run()
            self.assertTrue((Path(folder) / 'markdown-results.zip').is_file())
            self.assertEqual(app.session_state['results'][0].markdown, '# 日本語\n')


if __name__ == '__main__':
    unittest.main()
