Param(
    [string]$PyInstaller = "pyinstaller"
)

$RootDir = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $RootDir

& $PyInstaller `
    --clean `
    --noconfirm `
    pyinstaller\textgrid-transcriber.spec
