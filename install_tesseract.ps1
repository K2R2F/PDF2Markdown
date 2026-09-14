param([Parameter(Mandatory=$true)][string]$Installer,
      [Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference = 'Stop'
try {
    # NSIS requires /D to be last, with the destination unquoted even when it contains spaces.
    $installArgs = '/S /CURRENTUSER /D=' + $Destination
    $process = Start-Process -FilePath $Installer -ArgumentList $installArgs -WindowStyle Hidden -Wait -PassThru
    exit $process.ExitCode
} catch {
    Write-Error "Tesseractの導入に失敗しました。Windowsの確認・権限とインストーラーログを確認してください。 $_"
    exit 1
}
