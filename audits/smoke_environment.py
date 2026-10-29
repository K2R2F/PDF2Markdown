"""Verify the installed RapidOCR runtime through the gated setup worker."""
import os
import tempfile
import time
from environment.jobs import start_setup, job_snapshot
from environment.detection import inspect_environment

if __name__ == '__main__':
    assert inspect_environment()['rapidocr']['ready'], 'Install separately; this check must not install packages.'
    with tempfile.TemporaryDirectory() as folder:
        os.environ['PDF2MARKDOWN_DATA_DIR'] = folder
        start_setup('rapidocr')
        deadline = time.monotonic() + 60
        while job_snapshot().get('state') == 'running' and time.monotonic() < deadline:
            time.sleep(0.2)
        result = job_snapshot()
        print(result.get('state'))
        print(result.get('output'))
        assert result.get('state') == 'success', result
