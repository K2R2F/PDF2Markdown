from __future__ import annotations

import os
import platform
import sys
from environment.catalog import LABELS, PACKAGES, ROOT, RUNTIME, TESS_EXE, TESSDATA, LANGUAGES, INSTALLER_URL, INSTALLER_SHA256
from environment.process import run
from environment.detection import inspect_environment, tesseract_path
from environment.downloads import download

def install_component(component: str) -> None:
    if component not in LABELS:
        raise ValueError('未対応のコンポーネントです。')
    print(f'準備: {LABELS[component]}', flush=True)
    if component in PACKAGES:
        if sys.prefix == sys.base_prefix:
            raise RuntimeError('グローバルPythonへの変更を防ぐため、.venvから起動してください。')
        report = inspect_environment()[component]
        if report['ready']:
            print('導入済み。パッケージの変更をスキップします。', flush=True)
        else:
            specs = [f'{name}=={version}' for name, version in PACKAGES[component].items()]
            run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check', *specs], timeout=3600)
            run([sys.executable, '-m', 'pip', 'check'], timeout=120)
        imports = {'docling': 'from docling.document_converter import DocumentConverter',
                   'easyocr': 'import easyocr; import torch',
                   'rapidocr': 'import rapidocr; import onnxruntime'}
        print('別プロセスでインポートとDLLを確認します。', flush=True)
        run([sys.executable, '-c', imports[component]], timeout=180)
    else:
        if not tesseract_path():
            if os.name != 'nt' or platform.machine().lower() not in ('amd64', 'x86_64'):
                raise RuntimeError('Tesseract本体の自動導入はWindows x64用です。他のOSでは本体を導入後に再実行してください。')
            installer = RUNTIME / 'downloads' / 'tesseract-setup.exe'
            print('UB Mannheim配布のインストーラーを取得・SHA-256照合します。', flush=True)
            download(INSTALLER_URL, installer, INSTALLER_SHA256)
            print('Tesseract本体を導入中。Windowsの確認が出た場合は画面で操作してください。', flush=True)
            # A checked-in script handles quoting, UAC, and waiting for installer completion.
            run(['powershell.exe', '-NoProfile', '-File', str(ROOT / 'install_tesseract.ps1'),
                 '-Installer', str(installer), '-Destination', str(TESS_EXE.parent)], timeout=1800)
            if not tesseract_path():
                raise RuntimeError('インストール後にtesseract.exeが見つかりません。ログを確認してください。')
        for lang in LANGUAGES:
            target = TESSDATA / f'{lang}.traineddata'
            if not target.is_file():
                print(f'公式の言語データを取得: {lang}', flush=True)
                download(f'https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/main/{lang}.traineddata', target)
        check = inspect_environment()['tesseract']
        if not check['ready']:
            raise RuntimeError(f'Tesseractの設定確認に失敗: {check}')
    print(f'完了: {LABELS[component]}', flush=True)
