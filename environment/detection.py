from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess
from environment.catalog import PACKAGES, TESS_EXE, TESSDATA, LANGUAGES
from environment.process import run

def tesseract_path() -> Path | None:
    candidates = [TESS_EXE]
    found = shutil.which('tesseract')
    if found:
        candidates.append(Path(found))
    if os.name == 'nt':
        for base in ('ProgramFiles', 'ProgramFiles(x86)', 'LOCALAPPDATA'):
            if value := os.environ.get(base):
                candidates.extend([Path(value) / 'Tesseract-OCR' / 'tesseract.exe',
                                   Path(value) / 'Programs' / 'Tesseract-OCR' / 'tesseract.exe'])
    return next((p for p in candidates if p.is_file()), None)



def tesseract_configuration() -> dict:
    config = {'tesseract_cmd': str(tesseract_path() or 'tesseract')}
    if all((TESSDATA / f'{lang}.traineddata').is_file() for lang in LANGUAGES):
        config['path'] = str(TESSDATA)
    return config



def inspect_environment() -> dict[str, dict]:
    report = {}
    for component, packages in PACKAGES.items():
        installed, missing, mismatched = {}, [], []
        for name, wanted in packages.items():
            try:
                installed[name] = importlib.metadata.version(name)
                if installed[name] != wanted:
                    mismatched.append(f'{name}: 検証済み版は{wanted}')
            except importlib.metadata.PackageNotFoundError:
                missing.append(name)
        report[component] = {'ready': not missing and not mismatched, 'detail': ', '.join(
            f'{name} {version}' for name, version in installed.items()),
            'missing': missing, 'notes': mismatched}
    executable = tesseract_path()
    tess = {'ready': False, 'detail': str(executable or '本体が見つかりません'), 'missing': [], 'notes': []}
    if executable:
        try:
            version = run([str(executable), '--version'], capture_output=True, text=True, errors='replace', timeout=15)
            command = [str(executable), '--list-langs']
            if path := tesseract_configuration().get('path'):
                command.extend(['--tessdata-dir', path])
            output = run(command, capture_output=True, text=True, errors='replace', timeout=15)
            available = set(output.stdout.splitlines())
            tess['missing'] = [lang for lang in LANGUAGES if lang not in available]
            tess['ready'] = not tess['missing']
            tess['detail'] = version.stdout.splitlines()[0] + ' / ' + str(executable)
        except (OSError, subprocess.SubprocessError, IndexError) as exc:
            tess['notes'].append(f'起動確認失敗: {exc}')
    else:
        tess['missing'] = ['Tesseract本体', *LANGUAGES]
    report['tesseract'] = tess
    return report
