# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtMultimedia",
]

a = Analysis(
    ["../src/textgrid_transcriber/main.py"],
    pathex=[".."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=["pyinstaller/hooks"],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="textgrid-transcriber",
    icon="../assets/icons/app.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="textgrid-transcriber",
)

app = BUNDLE(
    coll,
    name="textgrid-transcriber.app",
    icon="../assets/icons/app.icns",
)
