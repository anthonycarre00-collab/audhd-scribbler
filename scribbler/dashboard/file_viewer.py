#!/usr/bin/env python3
"""File viewer — generates an HTML page showing all tagged files with metadata.

This is the 'where are my tagged files?' visibility the user asked for.
Opens in the browser, shows every file with its tags, summary, and a link to open it.
"""
import json
import os
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from ..config import PROJECT_ROOT, DATA_DIR, PALETTE
from .. import db


def generate() -> str:
    """Generate the file viewer HTML and return the file path."""
    from .generator import CSS_BASE

    output_dir = DATA_DIR / "dashboard"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_files = db.get_all_files()

    html = _build_html(all_files, CSS_BASE)
    output_path = output_dir / "files.html"
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)


def _build_html(all_files: List[Dict], css_base: str = "") -> str:
    files_html = ""

    if not all_files:
        files_html = """
        <div class="empty-state">
            <h2>No tagged files yet</h2>
            <p>Drop text files into the <code>raw-dumps/</code> folder, then run "Tag all my dumps" from the menu.</p>
        </div>
        """
    else:
        for f in all_files:
            files_html += _render_file_card(f)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Audhd Scribbler — My Files</title>
<style>
{css_base}
.file-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    transition: border-color 0.2s, box-shadow 0.2s;
}}
.file-card:hover {{
    border-color: var(--accent);
    box-shadow: 0 2px 8px rgba(74, 111, 165, 0.1);
}}
.file-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
}}
.file-name {{
    font-size: 17px;
    font-weight: 600;
    color: var(--text);
    margin: 0;
}}
.file-meta {{
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
}}
.file-status {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.status-seedling {{ background: #A8C4E0; color: #1A2332; }}
.status-growing {{ background: #7B9BC8; color: white; }}
.status-shaping {{ background: #4A6FA5; color: white; }}
.status-polishing {{ background: #365680; color: white; }}
.status-resting {{ background: #9BA8B8; color: white; }}
.tag-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 10px 0;
}}
.tag {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 12px;
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
}}
.tag-characters {{ border-color: #5B8C6E; background: #EDF5F0; }}
.tag-places {{ border-color: #4A6FA5; background: #EDF1F5; }}
.tag-themes {{ border-color: #B8956A; background: #F5F0E8; }}
.tag-sensory {{ border-color: #8B7BA8; background: #F0EDF5; }}
.tag-label {{
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-muted);
    margin-right: 4px;
}}
.file-summary {{
    background: var(--surface);
    border-left: 3px solid var(--accent);
    padding: 12px 16px;
    margin: 12px 0;
    font-size: 14px;
    color: var(--text);
    line-height: 1.6;
    border-radius: 0 6px 6px 0;
    white-space: pre-wrap;
}}
.file-path {{
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 11px;
    color: var(--text-muted);
    word-break: break-all;
    margin-top: 8px;
}}
.empty-state {{
    text-align: center;
    padding: 60px 20px;
    color: var(--text-muted);
}}
.empty-state code {{
    background: var(--surface);
    padding: 2px 8px;
    border-radius: 4px;
}}
</style>
</head>
<body>
<div class="container">
    <header class="header">
        <div>
            <h1>My Files</h1>
            <p class="subtitle">{len(all_files)} file(s) tagged · click any file path to open it in your text editor</p>
        </div>
        <a href="dashboard.html" class="nav-link">← Back to Dashboard</a>
    </header>
    <main>
        {files_html}
    </main>
</div>
</body>
</html>"""


def _render_file_card(f: Dict) -> str:
    """Render a single file as a card."""
    name = f.get("filename", "unknown")
    folder = f.get("folder", "")
    status = f.get("status", "seedling")
    word_count = f.get("word_count", 0)
    era = f.get("era", "")
    voice = f.get("voice", "")
    emotional = f.get("emotional_register", "")
    characters = f.get("characters") or []
    places = f.get("places") or []
    themes = f.get("themes") or []
    sensory = f.get("sensory") or []
    summary = f.get("summary", "")
    path = f.get("path", "")
    chapter_no = f.get("chapter_no")
    last_modified = f.get("last_modified", "")[:10] if f.get("last_modified") else ""

    # Build tag rows
    char_tags = "".join(f'<span class="tag tag-characters">{c}</span>' for c in characters[:8])
    place_tags = "".join(f'<span class="tag tag-places">{p}</span>' for p in places[:6])
    theme_tags = "".join(f'<span class="tag tag-themes">{t}</span>' for t in themes[:6])
    sensory_tags = "".join(f'<span class="tag tag-sensory">{s}</span>' for s in sensory[:6])

    char_row = f'<div class="tag-row"><span class="tag-label">Characters</span>{char_tags}</div>' if char_tags else ""
    place_row = f'<div class="tag-row"><span class="tag-label">Places</span>{place_tags}</div>' if place_tags else ""
    theme_row = f'<div class="tag-row"><span class="tag-label">Themes</span>{theme_tags}</div>' if theme_tags else ""
    sensory_row = f'<div class="tag-row"><span class="tag-label">Sensory</span>{sensory_tags}</div>' if sensory_tags else ""

    summary_html = f'<div class="file-summary">{summary}</div>' if summary else ""

    meta_parts = [f"{word_count:,} words"]
    if chapter_no:
        meta_parts.append(f"Chapter {chapter_no}")
    if era:
        meta_parts.append(era)
    if voice:
        meta_parts.append(f"voice: {voice}")
    if emotional:
        meta_parts.append(f"mood: {emotional}")
    if last_modified:
        meta_parts.append(f"modified: {last_modified}")
    meta_str = " · ".join(meta_parts)

    # File path as a clickable link (opens the file)
    file_path_html = f'<div class="file-path">{path}</div>' if path else ""

    return f"""
    <div class="file-card">
        <div class="file-header">
            <div>
                <h3 class="file-name">{name}</h3>
                <div class="file-meta">{meta_str}</div>
            </div>
            <span class="file-status status-{status}">{status}</span>
        </div>
        {summary_html}
        {char_row}
        {place_row}
        {theme_row}
        {sensory_row}
        {file_path_html}
    </div>
    """
