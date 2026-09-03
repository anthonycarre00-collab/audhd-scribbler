# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for The Audhd Scribbler v2."""

import os
import sys
from pathlib import Path

block_cipher = None
ROOT = Path(os.path.abspath(SPECPATH)).parent

# Find the spaCy model path
model_path = None
try:
    import en_core_web_sm
    model_path = str(Path(en_core_web_sm.__file__).parent)
except Exception:
    import site
    for sp in site.getsitepackages():
        candidate = Path(sp) / "en_core_web_sm"
        if candidate.exists():
            model_path = str(candidate)
            break

# Build datas list — include the HTML file explicitly
datas = []

# The single self-contained index.html (all CSS+JS inlined)
html_path = ROOT / 'assets' / 'ui' / 'index.html'
if html_path.exists():
    datas.append((str(html_path), 'assets/ui'))
    print(f" Including index.html ({html_path.stat().st_size} bytes)")

# Add any other asset dirs that exist and have files
for asset_dir, dest in [('assets/fonts', 'assets/fonts'), ('assets/icons', 'assets/icons')]:
    full_path = ROOT / asset_dir
    if full_path.exists() and any(full_path.iterdir()):
        datas.append((str(full_path), dest))

# Add spaCy model if found
if model_path and os.path.exists(model_path):
    datas.append((model_path, 'en_core_web_sm'))
    print(f" Including spaCy model from: {model_path}")

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
    excludes=['tkinter', 'matplotlib', 'notebook', 'IPython', 'pytest', 'sphinx'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True, name='AudhdScribbler',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[], name='AudhdScribbler',
)
