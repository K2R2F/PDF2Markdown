"""Background supervisor for bounded Windows conversion workers."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import uuid

from core.models import Result
from core.pdf_validation import MAX_FILE, MAX_FILES, MAX_TOTAL
from environment.locks import OPERATION_LOCK
from execution.lease import OperationLease
from execution.process import ManagedProcess
from storage.paths import data_directory
from storage import state

ROOT = Path(__file__).resolve().parents[1]
_lock = threading.Lock()
_job = {}


def snapshot():
    with _lock:
        return {k: v for k, v in _job.items() if k not in ('cancel', '_resources')}


def cancel(batch_id):
    with _lock:
        if _job.get('id') == batch_id and _job.get('state') == 'running':
            _job['cancel'].set()


def start(settings, mode, files, urls, timeout_seconds=1800):
    if not 1 <= timeout_seconds <= 7200:
        raise ValueError('処理全体の上限は1〜7200秒です。')
    if len(files) > MAX_FILES or sum(len(data) for _, data in files) > MAX_TOTAL:
        raise ValueError('一度に30件・合計300 MBまでです。')
    if any(len(data) > MAX_FILE for _, data in files):
        raise ValueError('1ファイル100 MBまでです。')
    if len(urls) > MAX_FILES or sum(len(u) for u in urls) > 128000:
        raise ValueError('URLの件数または長さが上限を超えています。')
    if not OPERATION_LOCK.acquire(blocking=False):
        raise RuntimeError('変換または環境設定を実行中です。')
    lease = None
    folder = None
    batch_id = None
    try:
        lease = OperationLease()
        cleanup_stale_inputs()
        batch_id = uuid.uuid4().hex
        folder = data_directory() / 'jobs' / batch_id
        folder.mkdir(parents=True, exist_ok=False)
        entries = []
        for index, (name, data) in enumerate(files):
            filename = f'{index}.input'
            (folder / filename).write_bytes(data)
            entries.append({'name': name, 'file': filename})
        request = dict(id=batch_id, settings=asdict(settings), mode=mode, files=entries, urls=urls)
        (folder / 'request.json').write_text(json.dumps(request, ensure_ascii=False), encoding='utf-8')
        state.save_batch(batch_id, settings, [], 'running')
        event = threading.Event()
        with _lock:
            _job.clear()
            _job.update(id=batch_id, state='running', cancel=event, label='起動中', error='')
        thread = threading.Thread(target=_supervise, args=(batch_id, settings, folder, lease, event, timeout_seconds), daemon=True)
        thread.start()
        return batch_id
    except BaseException:
        if batch_id:
            try:
                state.save_batch(batch_id, settings,
                    [Result('バッチ処理', 'failure', error='変換の監視処理を起動できませんでした。')], 'failure')
            except Exception:
                pass  # Preserve the original startup exception; never report success.
        if folder:
            try:
                _cleanup(folder)
            except OSError:
                pass
        if lease:
            lease.close()
        with _lock:
            if _job.get('state') == 'running':
                _job.update(state='failure', error='監視処理を起動できませんでした。')
        OPERATION_LOCK.release()
        raise


def _cleanup(folder):
    # Remove only our newly created UUID directory, never user input paths.
    root = (data_directory() / 'jobs').resolve()
    target = folder.resolve()
    if target.parent != root or len(target.name) != 32 or any(c not in '0123456789abcdef' for c in target.name):
        raise ValueError('一時ファイルの削除先が不正です。')
    shutil.rmtree(target)


def cleanup_stale_inputs():
    """Caller must hold the OS lease, so no managed worker can still use these files."""
    root = data_directory() / 'jobs'
    if not root.exists():
        return
    for folder in root.iterdir():
        if not folder.is_dir() or len(folder.name) != 32 or any(c not in '0123456789abcdef' for c in folder.name):
            continue
        try:
            settings, results, status = state.load_batch(folder.name)
        except ValueError:
            # Preserve unknown/corrupt records for diagnosis; do not erase their input.
            continue
        if status == 'running':
            results.append(Result('バッチ処理', 'failure', error='前回の処理は完了を確認できませんでした。'))
            state.save_batch(folder.name, settings, results, 'interrupted')
        _cleanup(folder)


def _supervise(batch_id, settings, folder, lease, event, timeout_seconds):
    process = None
    stopped = True
    terminal = 'failure'
    message = ''
    try:
        # stdout/stderr can contain document text; do not persist raw worker output.
        process = ManagedProcess([sys.executable, '-u', '-m', 'execution.worker', str(folder)],
            cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        stopped = False
        deadline = time.monotonic() + timeout_seconds
        while process.poll() is None:
            if event.is_set():
                terminal, message = 'cancelled', '利用者がキャンセルしました。未完了のPDFは再度追加してください。'
                break
            if time.monotonic() >= deadline:
                terminal, message = 'timed_out', '処理全体の時間制限に達したため停止しました。'
                break
            try:
                label = (folder / 'progress.txt').read_text(encoding='utf-8')
                with _lock:
                    _job['label'] = label
            except OSError:
                pass
            event.wait(0.1)
        code = process.poll()
        process.close()  # Always terminate and confirm the entire tree before releasing exclusion.
        stopped = True
        if not message:
            _, _, saved_status = state.load_batch(batch_id)
            if code == 0 and saved_status in ('complete', 'failure'):
                terminal = saved_status
            else:
                message = '変換プロセスが正常完了しませんでした。保存済みの結果だけを表示します。'
    except Exception as exc:
        message = f'変換の起動・監視に失敗しました（{type(exc).__name__}）。'
        if process and not stopped:
            try:
                process.close()
                stopped = True
            except Exception:
                message += ' プロセスツリーの停止を確認できないため、追加処理を停止しています。'
    finally:
        if stopped:
            try:
                if message:
                    _, results, _ = state.load_batch(batch_id)
                    results.append(Result('バッチ処理', 'failure', error=message))
                    state.save_batch(batch_id, settings, results, terminal)
            except Exception:
                terminal = 'failure'
                message += ' 終了状態を履歴に保存できませんでした。'
            try:
                _cleanup(folder)
            except Exception:
                message += ' 一時入力を削除できませんでした。設定データ内のjobsフォルダーを確認してください。'
            lease.close()
            OPERATION_LOCK.release()
        with _lock:
            _job.update(state=terminal, error=message, blocked=not stopped)
            if not stopped:
                _job['_resources'] = (process, lease)  # Keep OS handles/lease alive until confirmed shutdown.
