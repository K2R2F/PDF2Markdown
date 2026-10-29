"""Only launches gated workers; the gate opens after tree ownership is installed."""
import os
import subprocess


class ManagedProcess:
    def __init__(self, command, **kwargs):
        if os.name != 'nt':
            raise RuntimeError('この試用版のプロセス管理はWindows専用です。')
        from execution.windows_job import WindowsJob
        self.job = WindowsJob()
        self.child = None
        try:
            self.child = subprocess.Popen(command, stdin=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW, **kwargs)
            self.job.assign(self.child)
            self.child.stdin.write(b'GO\n')
            self.child.stdin.flush()
            self.child.stdin.close()
        except BaseException:
            # Before GO the worker cannot start imports, inference or subprocesses.
            if self.child:
                self.child.kill()
                self.child.wait(timeout=10)
                if self.child.stdin:
                    self.child.stdin.close()
            self.job.close()
            raise

    def poll(self):
        return self.child.poll()

    def wait(self, timeout=None):
        return self.child.wait(timeout=timeout)

    def stop(self):
        self.job.stop()
        self.child.wait(timeout=10)

    def close(self):
        # Also collect descendants of a worker which has already exited.
        self.stop()
        self.job.close()
