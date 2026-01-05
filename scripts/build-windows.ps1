Param(
    [string]$PyInstaller = "pyinstaller"
)

$RootDir = (Resolve-Path "$PSScriptRoot\..").Path
Set-Location $RootDir

& $PyInstaller `
    --clean `
    --noconfirm `
    --distpath dist `
    --workpath build `
    pyinstaller\textgrid-transcriber.spec
