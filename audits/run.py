"""Run one verification command and preserve each attempt without overwriting it."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('command required')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    folder = ROOT / 'audits' / 'evidence' / run_id
    folder.mkdir(parents=True, exist_ok=False)
    git = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    sources = {}
    for pattern in ('*.py', 'core/*.py', 'environment/*.py', 'ui/*.py', 'storage/*.py', 'tests/*.py', 'audits/*.py'):
        for path in ROOT.glob(pattern):
            sources[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    def record(name, value):
        with (folder / name).open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
    record('started.json', {'label': args.label, 'utc': datetime.now(timezone.utc).isoformat(),
        'command': command, 'timeout_seconds': args.timeout, 'git_head': git.stdout.strip(),
        'source_sha256': sources, 'python': sys.version})
    status, code = 'error', None
    # Started without finished means interrupted/unknown, never a successful run.
    with (folder / 'output.txt').open('xb') as output:
        try:
            child = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
            try:
                code = child.wait(timeout=args.timeout)
                status = 'passed' if code == 0 else 'failed'
            except subprocess.TimeoutExpired:
                status = 'timed_out'
                child.kill()
                code = child.wait()
            except KeyboardInterrupt:
                status = 'interrupted'
                child.kill()
                code = child.wait()
        except OSError as exc:
            output.write(str(exc).encode('utf-8'))
    record('finished.json', {'status': status, 'returncode': code,
        'utc': datetime.now(timezone.utc).isoformat(),
        'output_sha256': hashlib.sha256((folder / 'output.txt').read_bytes()).hexdigest()})
    print(json.dumps({'evidence': folder.relative_to(ROOT).as_posix(), 'status': status, 'returncode': code}))
    print((folder / 'output.txt').read_text(encoding='utf-8', errors='replace'))
    return 0 if status == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
