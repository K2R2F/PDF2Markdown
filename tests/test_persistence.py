from dataclasses import asdict
from pathlib import Path
import sqlite3
import json
import tempfile
import unittest
from unittest.mock import patch

from core.models import Settings, Result
from storage import state
from storage.paths import data_directory
from streamlit.testing.v1 import AppTest


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        override = patch.dict('os.environ', {'PDF2MARKDOWN_DATA_DIR': self.folder.name})
        override.start()
        self.addCleanup(override.stop)

    def app(self):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()

    def test_preferences_survive_fresh_app(self):
        app = self.app()
        app.selectbox(key='setting_engine').set_value('rapidocr').run()
        app.text_input(key='save_directory').set_value(str(Path(self.folder.name) / 'saved')).run()
        app.number_input(key='setting_max_pages').set_value(17).run()
        fresh = self.app()
        self.assertFalse(fresh.exception)
        self.assertEqual(fresh.selectbox(key='setting_engine').value, 'rapidocr')
        self.assertEqual(fresh.number_input(key='setting_max_pages').value, 17)
        self.assertEqual(fresh.text_input(key='save_directory').value, str(Path(self.folder.name) / 'saved'))

    def test_incomplete_result_restore_and_history_delete(self):
        state.save_batch('aborted', Settings(), [Result('日本語.pdf', 'success', '# 日本語')], 'running')
        fresh = self.app()
        fresh.button(key='restore_history').click().run()
        self.assertFalse(fresh.exception)
        self.assertEqual(fresh.session_state['results'][0].markdown, '# 日本語')
        self.assertTrue(any('完了を確認できない' in item.value for item in fresh.info))
        external = Path(self.folder.name) / 'export.md'
        external.write_text('keep', encoding='utf-8')
        fresh.button(key='delete_history').click().run()
        self.assertEqual(state.list_batches(), [])
        self.assertEqual(external.read_text(encoding='utf-8'), 'keep')

    def test_transaction_rollback_keeps_previous_result(self):
        state.save_batch('one', Settings(), [Result('a.pdf', 'success', 'old')], 'complete')
        with self.assertRaises(RuntimeError):
            with state.connection() as db:
                db.execute('DELETE FROM batches')
                raise RuntimeError('simulated interrupted transaction')
        self.assertEqual(state.load_batch('one')[1][0].markdown, 'old')

    def test_corrupt_database_not_silently_replaced(self):
        path = data_directory() / 'state.sqlite3'
        path.write_bytes(b'not a database')
        app = self.app()
        self.assertFalse(app.exception)
        self.assertTrue(app.warning)
        self.assertEqual(path.read_bytes(), b'not a database')

    def test_failed_checkpoint_does_not_claim_saved(self):
        from ui.persistence import checkpoint
        session = type('Session', (), dict(batch_id='a', result_settings=Settings(), results=[]))()
        with patch('ui.persistence.st.session_state', session), \
             patch('ui.persistence.state.save_batch', side_effect=sqlite3.OperationalError('disk full')), \
             patch('ui.persistence.st.error') as error:
            checkpoint('running')
        self.assertIn('履歴を保存できません', error.call_args.args[0])

    def test_invalid_settings_are_rejected(self):
        for field, value in [('engine', 'unknown'), ('max_pages', True), ('images', 'yes')]:
            with self.subTest(field=field):
                raw = asdict(Settings())
                raw[field] = value
                with self.assertRaises(ValueError): state.validate_settings(raw)

    def test_relative_data_path_is_rejected(self):
        with patch.dict('os.environ', {'PDF2MARKDOWN_DATA_DIR': 'relative'}):
            with self.assertRaises(ValueError): data_directory()

    def test_corrupt_result_payload_is_rejected_without_ui_crash(self):
        state.save_batch('bad', Settings(), [Result('a.pdf', 'success', 'valid')], 'complete')
        with state.connection() as db:
            raw = json.loads(db.execute('SELECT payload FROM batches').fetchone()[0])
            raw['results'][0]['markdown'] = 123
            db.execute('UPDATE batches SET payload=?', (json.dumps(raw),))
        app = self.app()
        app.button(key='restore_history').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertNotIn('results', app.session_state.filtered_state)
