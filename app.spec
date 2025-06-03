# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Create required directories
if not os.path.exists('output_invoices'):
    os.makedirs('output_invoices')
if not os.path.exists('logs'):
    os.makedirs('logs')

# Collect all requirements
requirements = ['reportlab', 'ttkbootstrap', 'pandas', 'matplotlib', 'PIL']
binaries = []
hiddenimports = []
datas = []

# Add all required files and directories
datas = [
    ('requirements.txt', '.'),
    ('assets/*', 'assets'),  # Include all files in assets
    ('main.py', '.'),
    ('users.json', '.'),
    ('customers.json', '.'),
    ('invoice_tracker.json', '.'),
    ('invoice_log.json', '.'),
    ('output_invoices', 'output_invoices'),
    ('logs', 'logs'),  # Include logs directory
]

# Get the base directory
basedir = os.path.abspath(os.path.dirname('__file__'))

# Collect matplotlib data files
matplotlib_data = collect_data_files('matplotlib')

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
    ['main.py'],
    pathex=[basedir],
    binaries=[],
    datas=[
        ('assets/*', 'assets/'),
        *matplotlib_data,  # Include matplotlib data files
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'ttkbootstrap',
        'babel.numbers',
        'matplotlib',
        'reportlab',
        'reportlab.graphics.barcode',
        'reportlab.graphics.barcode.code39',
        'reportlab.graphics.barcode.code93',
        'reportlab.graphics.barcode.code128',
        'reportlab.graphics.barcode.usps',
        'reportlab.graphics.barcode.usps4s',
        'reportlab.graphics.barcode.qr',
        'reportlab.lib.units',
        'reportlab.pdfgen',
        'reportlab.pdfbase',
        'reportlab.pdfbase.ttfonts',
        'reportlab.pdfbase.pdfmetrics',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Exclude unnecessary matplotlib data to reduce size
a.datas = [d for d in a.datas if not (
    d[0].startswith('matplotlib/mpl-data/sample_data') or
    d[0].startswith('matplotlib/mpl-data/fonts/afm') or
    '.git' in d[0] or
    '__pycache__' in d[0] or
    'tests' in d[0]
)]

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TFN Billing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False to hide console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',  # Add application icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TFN Billing',
) 