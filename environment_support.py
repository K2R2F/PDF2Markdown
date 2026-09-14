"""Stable setup CLI and compatibility imports."""
from environment.catalog import LABELS
from environment.detection import inspect_environment, tesseract_configuration
from environment.locks import OPERATION_LOCK
from environment.jobs import job_snapshot, start_setup
from environment.worker import main

if __name__ == "__main__":
    main()
