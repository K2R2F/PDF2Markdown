from __future__ import annotations

import os
import subprocess

def run(command: list[str], timeout: int = 120, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, timeout=timeout, check=True,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, **kwargs)
