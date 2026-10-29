"""Private subprocess entry. Never execute work until the parent owns the tree."""
import sys


def main():
    if sys.stdin.buffer.readline() != b'GO\n':
        return 2
    import json
    from pathlib import Path
    from storage.state import save_batch, validate_settings
    from execution.pipeline import run_batch
    folder = Path(sys.argv[1])
    request = json.loads((folder / 'request.json').read_text(encoding='utf-8'))
    settings = validate_settings(request['settings'])
    files = [(row['name'], (folder / row['file']).read_bytes()) for row in request['files']]
    def emit(results, status):
        save_batch(request['id'], settings, results, status)
    def progress(label):
        temporary = folder / 'progress.tmp'
        temporary.write_text(label, encoding='utf-8')
        temporary.replace(folder / 'progress.txt')
    run_batch(settings, request['mode'], files, request['urls'], emit, progress)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
