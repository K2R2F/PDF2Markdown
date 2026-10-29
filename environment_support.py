"""Stable setup CLI and compatibility imports."""
from environment.catalog import LABELS
from environment.detection import inspect_environment, tesseract_configuration
from environment.locks import OPERATION_LOCK
from environment.jobs import job_snapshot, start_setup
from environment.worker import main

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--managed':
        if sys.stdin.buffer.readline() != b'GO\n':
            raise SystemExit(2)
        sys.argv.pop(1)
    main()
