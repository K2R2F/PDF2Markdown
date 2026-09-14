from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from environment.catalog import ROOT, RUNTIME, LABELS
from environment.locks import OPERATION_LOCK

JOB_LOCK = threading.Lock()
JOB: dict = {}

def job_snapshot() -> dict:
    with JOB_LOCK:
        result = {key: value for key, value in JOB.items() if key != 'process'}
    if path := result.get('log'):
        try:
            with Path(path).open('rb') as stream:
                stream.seek(max(0, Path(path).stat().st_size - 20000))
                result['output'] = stream.read().decode('utf-8', errors='replace')
        except OSError:
            result['output'] = ''
    return result



def start_setup(component: str) -> None:
    if component not in (*LABELS, 'all'):
        raise ValueError('未対応のコンポーネントです。')
    if not OPERATION_LOCK.acquire(blocking=False):
        raise RuntimeError('変換または環境設定を実行中です。終了後に再実行してください。')
    try:
        RUNTIME.mkdir(parents=True, exist_ok=True)
        log_path = RUNTIME / f'setup-{time.time_ns()}.log'
        with log_path.open('wb') as log:
            child = subprocess.Popen([sys.executable, '-u', str(ROOT / 'environment_support.py'), component],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        with JOB_LOCK:
            JOB.clear()
            JOB.update(state='running', component=component, log=str(log_path), process=child)
        def finish():
            try:
                code = child.wait()
                with JOB_LOCK:
                    JOB.update(state='success' if code == 0 else 'failure', returncode=code)
            finally:
                OPERATION_LOCK.release()
        threading.Thread(target=finish, daemon=True).start()
    except BaseException:
        OPERATION_LOCK.release()
        raise
