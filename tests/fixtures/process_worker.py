"""Real-process test fixture. Never imports Docling or accesses the network."""
import json
from pathlib import Path
import subprocess
import sys
import time

if sys.argv[1] == 'leaf':
    while True:
        time.sleep(1)

if sys.stdin.buffer.readline() != b'GO\n':
    raise SystemExit(2)
mode, folder = sys.argv[1], Path(sys.argv[2])
if mode == 'tree':
    child = subprocess.Popen([sys.executable, __file__, 'leaf'])
    (folder / 'leaf.pid').write_text(str(child.pid))
if mode == 'partial':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from core.models import Result
    from storage.state import save_batch, validate_settings
    request = json.loads((folder / 'request.json').read_text(encoding='utf-8'))
    save_batch(request['id'], validate_settings(request['settings']),
               [Result('done.pdf', 'success', '# completed')], 'running')
(folder / 'ready').write_text('ready')
while True:
    time.sleep(1)
