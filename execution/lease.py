"""Per-user operation lease, shared across independent app processes."""
import os
from storage.paths import data_directory


class OperationLease:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Windowsで実行してください。')
        import msvcrt
        folder = data_directory()
        folder.mkdir(parents=True, exist_ok=True)
        self.stream = (folder / 'operation.lock').open('a+b')
        try:
            if self.stream.seek(0, 2) == 0:
                self.stream.write(b'0')
                self.stream.flush()
            self.stream.seek(0)
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
        except BaseException:
            self.stream.close()
            raise RuntimeError('別の画面またはアプリで変換・環境設定を実行中です。') from None

    def close(self):
        self.stream.close()  # OS releases byte-range locks on close/process exit.
