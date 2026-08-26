#!/usr/bin/env python3
"""File viewer — generates HTML pages showing all tagged files + single-file reader."""
import os
import re
from pathlib import Path
from typing import Dict, List

from ..config import PROJECT_ROOT, DATA_DIR
from .. import db
from ..file_io import read_text_file
from .generator import CSS_BASE

DASHBOARD_DIR = DATA_DIR / "dashboard"


def generate() -> str:
    """Generate the file viewer HTML AND all individual reader pages."""
    output_dir = DATA_DIR / "dashboard"
    output_dir.mkdir(parents=True, exist_ok=True)
    all_files = db.get_all_files()
    html = _build_html(all_files)
    output_path = output_dir / "files.html"
    output_path.write_text(html, encoding="utf-8")
    # Generate reader pages for each file
    for f in all_files:
        fp = f.get("path")
        if fp:
            try:
                generate_single_file_reader(fp)
            except Exception:
                pass
    return str(output_path)


def generate_single_file_reader(file_path: str) -> str:
    """Generate an HTML reader for a single file — shows full text content."""
    import html as html_module
    output_dir = DATA_DIR / "dashboard"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = Path(file_path)
    file_meta = db.get_file(str(path.resolve()))
    try:
        content = read_text_file(path)
    except Exception as e:
        content = f"[Error reading file: {e}]"

    body_text = content
    if body_text.startswith("---"):
        end = body_text.find("---", 3)
        if end != -1:
            body_text = body_text[end + 3:].strip()
    ai_summary = ""
    summary_match = re.search(r'<!-- SCRIBBLER SUMMARY\n([\s\S]*?)\n-->', body_text)
    if summary_match:
        ai_summary = summary_match.group(1).strip()
        body_text = re.sub(r'<!-- SCRIBBLER SUMMARY\n[\s\S]*?\n-->', '', body_text).strip()

    body_html = html_module.escape(body_text).replace('\n\n', '</p><p>').replace('\n', '<br>')
    body_html = f'<p>{body_html}</p>'

    name = path.name
    status = (file_meta or {}).get("status", "seedling")
    word_count = (file_meta or {}).get("word_count", 0) or len(body_text.split())
    era = (file_meta or {}).get("era", "—")
    voice = (file_meta or {}).get("voice", "—")
    emotional = (file_meta or {}).get("emotional_register", "—")
    characters = (file_meta or {}).get("characters") or []
    places = (file_meta or {}).get("places") or []
    themes = (file_meta or {}).get("themes") or []
    sensory = (file_meta or {}).get("sensory") or []

    char_tags = "".join(f'<span style="display:inline-block;padding:3px 10px;border-radius:6px;background:#EDF5F0;border:1px solid #5B8C6E;font-size:12px;margin:3px">{c}</span>' for c in characters[:10])
    place_tags = "".join(f'<span style="display:inline-block;padding:3px 10px;border-radius:6px;background:#EDF1F5;border:1px solid #4A6FA5;font-size:12px;margin:3px">{p}</span>' for p in places[:8])
    theme_tags = "".join(f'<span style="display:inline-block;padding:3px 10px;border-radius:6px;background:#F5F0E8;border:1px solid #B8956A;font-size:12px;margin:3px">{t}</span>' for t in themes[:8])

    summary_html = f'<div style="background:var(--surface);border-left:3px solid var(--accent);padding:12px 16px;margin:12px 0;font-size:14px;border-radius:0 6px 6px 0"><div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--accent);font-weight:600;margin-bottom:8px">AI Summary</div>{ai_summary}</div>' if ai_summary else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} — The Audhd Scribbler</title>
<style>{CSS_BASE}
.reader-body {{ background: var(--card-bg); border: 1px solid var(--border-light); border-radius: 12px; padding: 32px 40px; line-height: 1.8; font-size: 16px; font-family: Georgia, serif; }}
.reader-body p {{ margin-bottom: 18px; }}
</style>
</head>
<body>
<div class="container" style="max-width:800px">
    <a href="files.html" style="color:var(--accent);text-decoration:none;font-size:14px">← Back to All Files</a>
    <div class="header">
        <div>
            <h1>{name}</h1>
            <p class="subtitle">{word_count:,} words · era: {era} · voice: {voice} · mood: {emotional}</p>
        </div>
    </div>
    {char_tags and '<div style="margin:10px 0">' + char_tags + '</div>' or ''}
    {place_tags and '<div style="margin:10px 0">' + place_tags + '</div>' or ''}
    {theme_tags and '<div style="margin:10px 0">' + theme_tags + '</div>' or ''}
    {summary_html}
    <div class="reader-body">{body_html}</div>
    <div style="font-family:monospace;font-size:11px;color:var(--text-muted);margin-top:16px">{path}</div>
</div>
</body>
</html>"""
    output_path = output_dir / f"read_{path.stem}.html"
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)


def _build_html(all_files: List[Dict]) -> str:
    if not all_files:
        files_html = '<div class="empty"><h2>No tagged files yet</h2><p>Drop text files into <code>raw-dumps/</code> and run "Tag all my dumps".</p></div>'
    else:
        files_html = ""
        for f in all_files:
            name = f.get("filename", "unknown")
            status = f.get("status", "seedling")
            word_count = f.get("word_count", 0)
            era = f.get("era", "—")
            themes = f.get("themes") or []
            summary = f.get("summary", "")
            theme_tags = "".join(f'<span style="display:inline-block;padding:3px 10px;border-radius:6px;background:#F5F0E8;border:1px solid #B8956A;font-size:12px;margin:2px">{t}</span>' for t in themes[:6])
            read_link = f'<a href="read_{Path(f.get("path","x")).stem}.html" style="display:inline-block;margin-top:12px;padding:8px 16px;background:var(--accent);color:white;text-decoration:none;border-radius:6px;font-size:13px">Read this file →</a>'
            summary_html = f'<div style="background:var(--surface);border-left:3px solid var(--accent);padding:12px 16px;margin:12px 0;font-size:14px;border-radius:0 6px 6px 0">{summary}</div>' if summary else ""
            files_html += f"""
            <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
                    <div><h3 style="font-size:17px;font-weight:600">{name}</h3><div style="font-size:12px;color:var(--text-muted)">{word_count:,} words · {era}</div></div>
                    <span style="padding:3px 10px;border-radius:12px;background:var(--accent);color:white;font-size:11px;text-transform:uppercase">{status}</span>
                </div>
                {summary_html}
                {theme_tags and '<div style="margin:10px 0">' + theme_tags + '</div>' or ''}
                {read_link}
            </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Audhd Scribbler — My Files</title>
<style>{CSS_BASE}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div><h1>My Files</h1><p class="subtitle">{len(all_files)} file(s) tagged</p></div>
        <a href="dashboard.html" style="color:var(--accent);text-decoration:none;font-size:14px">← Back to Dashboard</a>
    </div>
    {files_html}
</div>
</body>
</html>"""
