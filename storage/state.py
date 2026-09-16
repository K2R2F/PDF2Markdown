"""Transactional SQLite persistence. Original PDFs and URLs are never stored."""
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import sqlite3

from core.models import Settings, Result
from storage.paths import data_directory


@contextmanager
def connection():
    folder = data_directory()
    folder.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(folder / 'state.sqlite3', timeout=5)
    try:
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
            db.execute('''CREATE TABLE IF NOT EXISTS batches
                (id TEXT PRIMARY KEY, updated TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL)''')
            yield db
    finally:
        db.close()


def validate_settings(value: dict) -> Settings:
    settings = Settings(**value)
    if (settings.engine not in ('easyocr', 'rapidocr', 'tesseract')
        or settings.language not in ('ja_en', 'en', 'zh_en')
        or settings.ocr_mode not in ('auto', 'force', 'off')
        or type(settings.tables) is not bool or type(settings.images) is not bool
        or type(settings.max_pages) is not int or not 1 <= settings.max_pages <= 1000):
        raise ValueError('保存された変換設定が不正です。')
    return settings


def load_preferences():
    with connection() as db:
        row = db.execute('SELECT payload FROM preferences WHERE id=1').fetchone()
    if row is None:
        return Settings(), str(data_directory() / 'output')
    value = json.loads(row[0])
    settings = validate_settings(value['settings'])
    directory = value['directory']
    if not isinstance(directory, str) or not directory.strip():
        raise ValueError('保存先の設定が不正です。')
    return settings, directory


def save_preferences(settings, directory):
    validate_settings(asdict(settings))
    if not directory.strip():
        raise ValueError('保存先フォルダーを入力してください。')
    payload = json.dumps({'settings': asdict(settings), 'directory': directory}, ensure_ascii=False)
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO preferences VALUES (1, ?)', (payload,))


def save_batch(batch_id, settings, results, state):
    if state not in ('running', 'complete', 'failure'):
        raise ValueError('不正な処理状態です。')
    payload = json.dumps({'settings': asdict(settings), 'results': [asdict(r) for r in results]}, ensure_ascii=False)
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO batches VALUES (?, ?, ?, ?)',
                   (batch_id, datetime.now(timezone.utc).isoformat(), state, payload))


def list_batches():
    with connection() as db:
        return db.execute('SELECT id, updated, state FROM batches ORDER BY updated DESC LIMIT 20').fetchall()


def load_batch(batch_id):
    with connection() as db:
        row = db.execute('SELECT state, payload FROM batches WHERE id=?', (batch_id,)).fetchone()
    if row is None:
        raise ValueError('履歴が見つかりません。')
    value = json.loads(row[1])
    settings = validate_settings(value['settings'])
    results = [Result(**r) for r in value['results']]
    if any(r.status not in ('success', 'partial_success', 'failure')
           or not all(isinstance(v, str) for v in (r.name, r.markdown, r.error))
           or type(r.pages) is not int or r.pages < 0
           or type(r.seconds) not in (int, float) or not math.isfinite(r.seconds) or r.seconds < 0
           for r in results):
        raise ValueError('履歴に不正な結果が含まれています。')
    return settings, results, row[0]


def delete_batch(batch_id):
    with connection() as db:
        db.execute('DELETE FROM batches WHERE id=?', (batch_id,))
