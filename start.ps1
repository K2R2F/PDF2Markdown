$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $bootstrapPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $bootstrapPython) {
        Write-Error 'Python 3.12をインストールしてから、もう一度起動してください。'
    }
    & $bootstrapPython.Source -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw '仮想環境の作成に失敗しました。' }
}
& $pythonPath -c 'import importlib.util; raise SystemExit(importlib.util.find_spec("streamlit") is None)'
if ($LASTEXITCODE -ne 0) {
    & $pythonPath -m pip install 'streamlit==1.63.0'
    if ($LASTEXITCODE -ne 0) { throw '画面起動用パッケージの導入に失敗しました。通信環境を確認してください。' }
}
& $pythonPath -m streamlit run app.py
exit $LASTEXITCODE
