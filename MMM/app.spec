# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Collect all requirements
requirements = ['reportlab', 'ttkbootstrap', 'pandas', 'matplotlib', 'PIL']
binaries = []
hiddenimports = []
datas = [
    ('requirements.txt', '.'),
    ('assets/logo.ico', 'assets'),
    ('assets/logo.png', 'assets'),
    ('main.py', '.'),
    ('users.json', '.'),  # Include users database
    ('customers.json', '.'),  # Include customers database
    ('invoice_tracker.json', '.'),  # Include invoice tracker
    ('invoice_log.json', '.'),  # Include invoice logs
]

# Add output_invoices directory if it exists
if not os.path.exists('output_invoices'):
    os.makedirs('output_invoices')
datas.append(('output_invoices', 'output_invoices'))

for req in requirements:
    if req == 'PIL':
        req = 'Pillow'
    bins, dats, hids = collect_all(req)
    binaries.extend(bins)
    datas.extend(dats)
    hiddenimports.extend(hids)

# Add additional hidden imports
hiddenimports.extend([
    'tkinter',
    'json',
    'datetime',
    'smtplib',
    'email',
    'csv',
    'zipfile',
    'matplotlib.backends.backend_tkagg',
])

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pkg_resources'],  # Exclude pkg_resources to avoid deprecation warnings
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TFN Billing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',
) 