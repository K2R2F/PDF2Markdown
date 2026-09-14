import socket
import unittest
from io import BytesIO
from unittest.mock import patch
from zipfile import ZipFile

from inputs import PdfInput, check_batch, fetch_pdf, public_target, read_zip, safe_name, validate_pdf


class InputTests(unittest.TestCase):
    def test_safe_names_preserve_pdf_extension(self):
        self.assertTrue(safe_name('a' * 200 + '.pdf').endswith('.pdf'))
        self.assertEqual(safe_name('../../CON.pdf'), '_CON.pdf')

    def test_html_instead_of_pdf_rejected(self):
        with self.assertRaises(ValueError):
            validate_pdf('fake.pdf', b'<html>login required</html>')

    def test_zip_nested_paths_never_extracted(self):
        buffer = BytesIO()
        with ZipFile(buffer, 'w') as archive:
            archive.writestr('../../first.pdf', b'%PDF-1.4\n')
            archive.writestr('nested/second.PDF', b'%PDF-1.7\n')
            archive.writestr('notes.txt', 'ignore')
        items = read_zip(buffer.getvalue())
        self.assertEqual([i.name for i in items], ['first.pdf', 'second.PDF'])

    def test_zip_expansion_limit(self):
        buffer = BytesIO()
        with ZipFile(buffer, 'w') as archive:
            archive.writestr('large.pdf', b'%PDF-' + b'0' * 30)
        with patch('core.zip_input.MAX_FILE', 500), patch('core.zip_input.MAX_TOTAL', 20):
            with self.assertRaises(ValueError):
                read_zip(buffer.getvalue())

    def test_batch_limits(self):
        with self.assertRaises(ValueError):
            check_batch([])
        with self.assertRaises(ValueError):
            check_batch([PdfInput('a.pdf', b'%PDF-')] * 31)

    def test_private_and_mixed_dns_rejected(self):
        for addresses in [['127.0.0.1'], ['169.254.169.254'], ['::1'], ['8.8.8.8', '10.0.0.1']]:
            records = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443)) for ip in addresses]
            with patch('core.url_input.socket.getaddrinfo', return_value=records):
                with self.assertRaises(ValueError):
                    public_target('https://example.com/a.pdf')

    def test_unsupported_urls_rejected_before_dns(self):
        for url in ['file:///etc/passwd', 'https://user:secret@example.com/a', 'http://example.com:9000']:
            with self.assertRaises(ValueError):
                public_target(url)

    def test_redirect_to_private_host_rejected(self):
        class Response:
            status = 302
            def getheader(self, name):
                return 'http://127.0.0.1/secret.pdf'
        class Connection:
            def __init__(self, *args, **kwargs): pass
            def request(self, *args, **kwargs): pass
            def getresponse(self): return Response()
            def close(self): pass
        def resolve(host, port, **kwargs):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '',
                     ('127.0.0.1' if host == '127.0.0.1' else '8.8.8.8', port))]
        with patch('core.url_input.socket.getaddrinfo', side_effect=resolve), patch('core.url_input.http.client.HTTPSConnection', Connection):
            with self.assertRaises(ValueError):
                fetch_pdf('https://example.com/report')


if __name__ == '__main__':
    unittest.main()
