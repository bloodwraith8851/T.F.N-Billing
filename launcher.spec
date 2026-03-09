# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Collect all data files
datas = [
    ('web', 'web'),
    ('assets', 'assets'),
    ('version.json', '.'),
]

# Specifically ensure dependencies that might have data files are included
datas += collect_data_files('eel')

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'eel', 
        'jinja2', 
        'reportlab', 
        'PIL', 
        'pandas', 
        'matplotlib', 
        'ttkbootstrap',
        'pkg_resources.py2_warn', # Often needed
        'pyautogui',
        'pyscreeze',
        'pymsgbox',
        'pygetwindow',
        'pyrect',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Thunderstorm Billing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico' if os.path.exists('assets/logo.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Thunderstorm Billing',
)
