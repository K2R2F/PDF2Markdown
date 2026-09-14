from __future__ import annotations

import http.client
import ipaddress
import socket
import time
from urllib.parse import unquote, urljoin, urlsplit
from core.models import PdfInput
from core.pdf_validation import MAX_FILE, validate_pdf, safe_name

def public_target(url: str) -> tuple[str, str, int, str]:
    parts = urlsplit(url)
    if parts.scheme not in ('https', 'http') or not parts.hostname:
        raise ValueError('http:// または https:// のPDF URLを指定してください。')
    if parts.username is not None or parts.password is not None:
        raise ValueError('認証情報を含むURLは使用できません。')
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    if port not in (80, 443):
        raise ValueError('URLのポートは80または443にしてください。')
    host = parts.hostname.encode('idna').decode('ascii')
    records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    addresses = [record[4][0] for record in records]
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError('公開インターネット上のPDF URLのみ利用できます。')
    return parts.scheme, host, port, addresses[0]



def fetch_pdf(url: str) -> PdfInput:
    deadline = time.monotonic() + 90
    for _ in range(6):
        if time.monotonic() > deadline:
            raise TimeoutError('PDF取得が90秒を超えました。')
        scheme, host, port, address = public_target(url)
        parts = urlsplit(url)
        cls = http.client.HTTPSConnection if scheme == 'https' else http.client.HTTPConnection
        conn = cls(host, port, timeout=20)
        # Pin the validated address, preserving the original hostname for TLS/SNI.
        # This avoids a second DNS lookup and DNS-rebinding into a private address.
        conn._create_connection = lambda addr, timeout, source_address=None: socket.create_connection(
            (address, port), timeout, source_address
        )
        try:
            path = (parts.path or '/') + ('?' + parts.query if parts.query else '')
            conn.request('GET', path,
                         headers={'User-Agent': 'PDF2Markdown/1.0', 'Accept': 'application/pdf'})
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location:
                    raise ValueError('リダイレクト先がありません。')
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError(f'PDFを取得できませんでした（HTTP {response.status}）。')
            size = response.getheader('Content-Length')
            if size and int(size) > MAX_FILE:
                raise ValueError('URL先のPDFは100 MBを超えています。')
            data = bytearray()
            while chunk := response.read(64 * 1024):
                data.extend(chunk)
                if len(data) > MAX_FILE:
                    raise ValueError('URL先のPDFは100 MBを超えています。')
                if time.monotonic() > deadline:
                    raise TimeoutError('PDF取得が90秒を超えました。')
            name = safe_name(unquote(parts.path.rsplit('/', 1)[-1]))
            if not name.lower().endswith('.pdf'):
                name += '.pdf'
            return validate_pdf(name, bytes(data))
        finally:
            conn.close()
    raise ValueError('リダイレクト回数が上限を超えました。')
