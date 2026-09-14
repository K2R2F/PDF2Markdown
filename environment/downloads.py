from __future__ import annotations

import hashlib
from pathlib import Path
import urllib.request

def download(url: str, destination: Path, expected_hash: str | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + '.part')
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as stream:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 150 * 1024 * 1024:
                    raise ValueError('ダウンロードがサイズ上限を超えました。')
                stream.write(chunk)
                digest.update(chunk)
        if expected_hash and digest.hexdigest() != expected_hash:
            raise ValueError('インストーラーのSHA-256が一致しません。実行を中止しました。')
        if not size:
            raise ValueError('空のファイルを受信しました。')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
