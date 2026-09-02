# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for The Audhd Scribbler v2.

Builds a --onedir desktop app (not --onefile, to avoid extracting
the 12MB spaCy model on every launch).
"""

import os
import sys
import spacy
from pathlib import Path

block_cipher = None

ROOT = Path(os.path.abspath(SPECPATH)).parent

# Find the spaCy model path
try:
    import en_core_web_sm
    model_path = str(Path(en_core_web_sm.__file__).parent)
except Exception:
    # Fallback: try to find it in site-packages
    import site
    model_path = None
    for sp in site.getsitepackages():
        candidate = Path(sp) / "en_core_web_sm"
        if candidate.exists():
            model_path = str(candidate)
            break

# Collect all data
datas = [
    (str(ROOT / 'assets' / 'ui'), 'assets/ui'),
    (str(ROOT / 'assets' / 'fonts'), 'assets/fonts'),
    (str(ROOT / 'assets' / 'icons'), 'assets/icons'),
]

# Add spaCy model if found
if model_path and os.path.exists(model_path):
    datas.append((model_path, 'en_core_web_sm'))
    print(f" Including spaCy model from: {model_path}")
else:
    print(" WARNING: en_core_web_sm not found — tagger will use regex fallback")

# Add spacy data files
spacy_path = str(Path(spacy.__file__).parent)
datas.append((spacy_path, 'spacy'))

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'pywebview',
        'pywebview.platforms.edgechromium',
        'pywebview.platforms.winforms',
        'spacy',
        'spacy.lang.en',
        'en_core_web_sm',
        'docx',
        'openai',
        'pypdf',
        'clr_loader',
        'pythonnet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'notebook',
        'IPython',
        'pytest',
        'sphinx',
    ],
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
    name='AudhdScribbler',
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
    upx_exclude=[],
    name='AudhdScribbler',
)
