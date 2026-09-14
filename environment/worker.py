"""Setup subprocess entry point."""
import json
import sys
from environment.catalog import LABELS
from environment.detection import inspect_environment
from environment.installer import install_component

def main():
    selection = sys.argv[1]
    failed = False
    for name in LABELS if selection == 'all' else [selection]:
        try:
            install_component(name)
        except Exception as exc:
            failed = True
            print(f'失敗: {name}: {exc}', flush=True)
    print(json.dumps(inspect_environment(), ensure_ascii=False), flush=True)
    raise SystemExit(1 if failed else 0)
