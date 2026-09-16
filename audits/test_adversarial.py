"""Required invariants: failures remain failures; no expectedFailure or skip masking.

Network/install/Docling backends are replaced only where explicitly named.
HTTP framing uses CPython's real HTTPResponse parser. No external hosts contacted.
"""
from concurrent.futures import ThreadPoolExecutor
import http.client
from io import BytesIO
import json
from pathlib import Path, PureWindowsPath
import socket
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

from core import url_input
from core.models import PdfInput, Result, Settings
from core.pdf_validation import safe_name
from core.markdown_export import make_zip
from core.converter import Converter
from environment import detection, downloads, jobs
from saving import save_file


def response(body=b'%PDF-1.4\n', declared=100):
    class Socket:
        def makefile(self, *args):
            return BytesIO(f'HTTP/1.1 200 OK\r\nContent-Length: {declared}\r\n\r\n'.encode() + body)
    parsed = http.client.HTTPResponse(Socket())
    parsed.begin()
    return parsed


class AdversarialIO(unittest.TestCase):
    def test_A01_truncated_http_pdf_is_rejected(self):
        conn = MagicMock()
        conn.getresponse.return_value = response()
        with patch.object(url_input, 'public_target', return_value=('https', 'example.org', 443, '8.8.8.8')), \
             patch.object(url_input.http.client, 'HTTPSConnection', return_value=conn):
            with self.assertRaises((ValueError, http.client.IncompleteRead)):
                url_input.fetch_pdf('https://example.org/report.pdf')

    def test_A02_truncated_model_download_does_not_replace_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'jpn.traineddata'
            target.write_bytes(b'previous-model')
            with patch.object(downloads.urllib.request, 'urlopen', return_value=response(b'partial', 100)):
                with self.assertRaises((ValueError, http.client.IncompleteRead)):
                    downloads.download('https://example.org/model', target)
            self.assertEqual(target.read_bytes(), b'previous-model')

    def test_A03_explicit_port_zero_is_rejected(self):
        records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]
        with patch.object(url_input.socket, 'getaddrinfo', return_value=records):
            with self.assertRaises(ValueError):
                url_input.public_target('https://example.org:0/file.pdf')

    def test_A04_multidot_windows_device_name_is_safe(self):
        self.assertFalse(PureWindowsPath(safe_name('CON.report.pdf')).is_reserved())

    def test_A05_simultaneous_saves_are_unique_and_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            with ThreadPoolExecutor(max_workers=8) as pool:
                paths = list(pool.map(lambda n: save_file(folder, 'same.md', f'document-{n}'), range(24)))
            self.assertEqual(len(set(paths)), 24)
            self.assertEqual({p.read_text(encoding='utf-8') for p in paths}, {f'document-{n}' for n in range(24)})

    def test_A06_failed_write_removes_partial_file(self):
        original = Path.open
        class BrokenWriter:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def write(self, data):
                self.stream.write(data[:2])
                raise OSError('simulated disk full')
            def __exit__(self, *args): self.stream.close()
        def open_file(path, mode='r', *args, **kwargs):
            stream = original(path, mode, *args, **kwargs)
            return BrokenWriter(stream) if mode == 'xb' else stream
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(Path, 'open', open_file):
                with self.assertRaises(OSError): save_file(folder, 'result.md', 'payload')
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_A07_empty_download_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'model'
            target.write_bytes(b'old')
            with patch.object(downloads.urllib.request, 'urlopen', return_value=BytesIO()):
                with self.assertRaises(ValueError): downloads.download('https://example.org/model', target)
            self.assertEqual(target.read_bytes(), b'old')
            self.assertFalse(target.with_suffix('.part').exists())

    def test_A08_transport_timeout_closes_connection(self):
        conn = MagicMock()
        conn.getresponse.side_effect = TimeoutError('simulated read timeout')
        with patch.object(url_input, 'public_target', return_value=('https', 'example.org', 443, '8.8.8.8')), \
             patch.object(url_input.http.client, 'HTTPSConnection', return_value=conn):
            with self.assertRaises(TimeoutError): url_input.fetch_pdf('https://example.org/a.pdf')
        conn.close.assert_called_once()

    def test_A17_complete_http_body_is_accepted(self):
        body = b'%PDF-1.4\n'
        conn = MagicMock()
        conn.getresponse.return_value = response(body, len(body))
        with patch.object(url_input, 'public_target', return_value=('https', 'example.org', 443, '8.8.8.8')), \
             patch.object(url_input.http.client, 'HTTPSConnection', return_value=conn):
            self.assertEqual(url_input.fetch_pdf('https://example.org/a.pdf').data, body)

    def test_A18_chunked_response_ignores_content_length(self):
        class Socket:
            def makefile(self, *args):
                return BytesIO(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n'
                               b'Content-Length: 999999999\r\n\r\n5\r\n%PDF-\r\n0\r\n\r\n')
        parsed = http.client.HTTPResponse(Socket())
        parsed.begin()
        conn = MagicMock()
        conn.getresponse.return_value = parsed
        with patch.object(url_input, 'public_target', return_value=('https', 'example.org', 443, '8.8.8.8')), \
             patch.object(url_input.http.client, 'HTTPSConnection', return_value=conn):
            self.assertEqual(url_input.fetch_pdf('https://example.org/a.pdf').data, b'%PDF-')


class AdversarialJobs(unittest.TestCase):
    def tearDown(self):
        jobs.JOB.clear()
        if jobs.OPERATION_LOCK.locked(): jobs.OPERATION_LOCK.release()

    def test_A09_thread_start_failure_does_not_leave_live_installer_unlocked(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(jobs, 'RUNTIME', Path(folder)), patch.object(jobs.subprocess, 'Popen') as spawn, \
                 patch.object(jobs.threading, 'Thread') as thread:
                thread.return_value.start.side_effect = RuntimeError('simulated thread creation failure')
                with self.assertRaises(RuntimeError): jobs.start_setup('rapidocr')
                stopped = spawn.return_value.terminate.called or spawn.return_value.kill.called
                self.assertTrue(stopped or jobs.OPERATION_LOCK.locked(),
                    'Installer remains live while the operation lock is released')

    def test_A10_child_wait_failure_is_recorded_as_terminal_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(jobs, 'RUNTIME', Path(folder)), patch.object(jobs.subprocess, 'Popen') as spawn, \
                 patch.object(jobs.threading, 'Thread') as thread:
                spawn.return_value.wait.side_effect = OSError('simulated wait failure')
                jobs.start_setup('rapidocr')
                try:
                    thread.call_args.kwargs['target']()
                except OSError:
                    pass  # Exception is allowed; the job must still record failure.
                self.assertEqual(jobs.job_snapshot()['state'], 'failure')

    def test_A11_spawn_failure_releases_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(jobs, 'RUNTIME', Path(folder)), \
                 patch.object(jobs.subprocess, 'Popen', side_effect=OSError('simulated spawn denial')):
                with self.assertRaises(OSError): jobs.start_setup('rapidocr')
                self.assertFalse(jobs.OPERATION_LOCK.locked())

    def test_A12_nonzero_child_exit_remains_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(jobs, 'RUNTIME', Path(folder)), patch.object(jobs.subprocess, 'Popen') as spawn, \
                 patch.object(jobs.threading, 'Thread') as thread:
                spawn.return_value.wait.return_value = 1
                jobs.start_setup('rapidocr')
                thread.call_args.kwargs['target']()
                self.assertEqual(jobs.job_snapshot()['state'], 'failure')
                self.assertEqual(jobs.job_snapshot()['returncode'], 1)

    def test_A13_unverified_package_version_is_not_ready(self):
        with patch.object(detection.importlib.metadata, 'version', return_value='0.0.0'), \
             patch.object(detection, 'tesseract_path', return_value=None):
            self.assertFalse(detection.inspect_environment()['docling']['ready'])

    def test_A19_failed_cleanup_keeps_exclusion_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(jobs, 'RUNTIME', Path(folder)), patch.object(jobs.subprocess, 'Popen') as spawn, \
                 patch.object(jobs.threading, 'Thread') as thread:
                thread.return_value.start.side_effect = RuntimeError('simulated thread failure')
                spawn.return_value.wait.side_effect = OSError('simulated unreapable child')
                with self.assertRaises(RuntimeError): jobs.start_setup('rapidocr')
                self.assertTrue(jobs.OPERATION_LOCK.locked())
                self.assertTrue(jobs.job_snapshot()['blocked'])
                self.assertEqual(jobs.job_snapshot()['state'], 'failure')
                with self.assertRaises(RuntimeError): jobs.start_setup('easyocr')


class AdversarialUI(unittest.TestCase):
    def app(self, urls):
        from streamlit.testing.v1 import AppTest
        from ui.converter_cache import get_converter
        get_converter.clear()
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=30).run()
        app.segmented_control[0].set_value('URL').run()
        app.text_area[0].set_value(urls).run()
        return app

    def test_A14_batch_limit_abort_retains_failure_record(self):
        app = self.app('https://example.org/a.pdf\nhttps://example.org/b.pdf')
        with patch('ui.batch_panel.MAX_TOTAL', 8), patch('ui.batch_panel.fetch_pdf',
                side_effect=[PdfInput('a.pdf', b'%PDF-'), PdfInput('b.pdf', b'%PDF-')]):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertTrue(any(r.status == 'failure' for r in app.session_state['results']),
                        'Batch stopped but the results contain no failure record')

    def test_A15_invalid_url_does_not_leak_query_secret_to_manifest(self):
        secret = 'AUDIT_DUMMY_SECRET'
        app = self.app('https://example.org/a b.pdf?token=' + secret)
        records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443))]
        # Real HTTPConnection rejects the space before attempting a connection.
        with patch.object(url_input.socket, 'getaddrinfo', return_value=records), \
             patch.object(url_input.socket, 'create_connection', side_effect=AssertionError('Network forbidden')):
            app.button[0].click().run()
        self.assertFalse(app.exception)
        results = app.session_state['results']
        self.assertEqual(len(results), 1)
        with ZipFile(BytesIO(make_zip(results, Settings()))) as archive:
            self.assertNotIn(secret, archive.read('manifest.json').decode('utf-8'))

    def test_A16_partial_timeout_not_promoted_to_success(self):
        converter = Converter.__new__(Converter)
        converter.settings = Settings()
        converter.lock = threading.Lock()
        converted = SimpleNamespace(status=SimpleNamespace(value='partial_success'),
            errors=[SimpleNamespace(error_message='TIMEOUT: processed 1/2 pages')],
            document=SimpleNamespace(pages={1: None}, export_to_markdown=lambda **kw: '# partial'))
        converter.converter = SimpleNamespace(convert=lambda *args, **kwargs: converted)
        result = converter.convert(PdfInput('partial.pdf', b'%PDF-'))
        self.assertEqual(result.status, 'partial_success')
        with ZipFile(BytesIO(make_zip([result], Settings()))) as archive:
            record = json.loads(archive.read('manifest.json'))['results'][0]
            self.assertEqual(record['status'], 'partial_success')
            self.assertIn('TIMEOUT', record['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
