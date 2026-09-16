"""One-click local saves for the local desktop app."""
from pathlib import Path

from inputs import safe_name
from storage.paths import data_directory

DEFAULT_SAVE_DIR = data_directory() / 'output'


def save_file(directory: str, filename: str, data: str | bytes) -> Path:
    if not directory.strip():
        raise ValueError('保存先フォルダーを入力してください。')
    folder = Path(directory.strip()).expanduser()
    if not folder.is_absolute():
        folder = DEFAULT_SAVE_DIR.parent / folder
    folder = folder.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    name = Path(safe_name(filename))
    payload = data.encode('utf-8') if isinstance(data, str) else data
    for number in range(1, 10001):
        target = folder / (name.name if number == 1 else f'{name.stem}_{number}{name.suffix}')
        try:
            stream = target.open('xb')
        except FileExistsError:
            continue
        try:
            with stream:
                stream.write(payload)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return target
    raise OSError('同名ファイルが多すぎます。保存先を変更してください。')
