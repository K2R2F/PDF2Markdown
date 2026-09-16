"""Writable user data, independent of the application installation directory."""
import os
from pathlib import Path


def data_directory() -> Path:
    override = os.environ.get('PDF2MARKDOWN_DATA_DIR')
    if override:
        path = Path(override).expanduser()
        if not path.is_absolute():
            raise ValueError('PDF2MARKDOWN_DATA_DIRは絶対パスを指定してください。')
        return path
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.local' / 'share')))
    return base / 'PDF2Markdown'
