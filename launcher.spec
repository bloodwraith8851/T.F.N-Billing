# -*- mode: python ; coding: utf-8 -*-
# launcher.spec  —  T.F.N Billing v2.0
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

datas = [
    ('web',          'web'),          # Eel frontend (HTML/CSS/JS)
    ('assets',       'assets'),       # Logo + icon
    ('version.json', '.'),            # Version file
]

# Eel ships template files that must be bundled
datas += collect_data_files('eel')

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # Core Eel stack
        'eel',
        'bottle',
        'bottle_websocket',
        'geventwebsocket',
        'gevent',
        'whichcraft',
        # Jinja2 (used by Eel internals)
        'jinja2',
        # PDF generation
        'reportlab',
        'reportlab.lib.pagesizes',
        'reportlab.platypus',
        # Image handling
        'PIL',
        'PIL.Image',
        # Data export
        'pandas',
        # SQLite (stdlib, but explicit to be safe under PyInstaller)
        'sqlite3',
        '_sqlite3',
        # WhatsApp automation (optional, included so it doesn't crash if called)
        'pyautogui',
        'pyscreeze',
        'pymsgbox',
        'pygetwindow',
        'pyrect',
        # HTTP requests (update checker)
        'requests',
        'urllib3',
        'certifi',
        'charset_normalizer',
        'idna',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude heavy libs we do NOT use
    excludes=[
        'matplotlib',
        'ttkbootstrap',
        'scipy',
        'numpy',
        'tkinter.test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_icon = 'assets/logo.ico' if os.path.exists('assets/logo.ico') else None

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
    icon=_icon,
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
