#!/usr/bin/env python3
"""Dashboard generator — generates an interactive HTML dashboard.

This module provides the `generate()` function that creates an HTML dashboard
showing the project overview, chapter grid, themes, characters, and activity.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from collections import Counter, defaultdict

from ..config import PROJECT_ROOT, DATA_DIR, STATUSES
from .. import db

DASHBOARD_DIR = DATA_DIR / "dashboard"

# Shared CSS — calm blue, beautiful typography, generous spacing
CSS_BASE = """
:root {
    --bg: #F7F8FA;
    --surface: #EEF1F5;
    --card-bg: #FFFFFF;
    --text: #1A2332;
    --text-muted: #5C6878;
    --text-light: #8A95A8;
    --accent: #4A6FA5;
    --accent-dark: #365680;
    --accent-light: #7B9BC8;
    --accent-soft: #E8EDF5;
    --border: #D1D9E3;
    --border-light: #E5EAF0;
    --success: #5B8C6E;
    --warning: #B8956A;
    --shadow: 0 1px 3px rgba(26, 35, 50, 0.04), 0 1px 2px rgba(26, 35, 50, 0.06);
    --radius: 10px;
    --radius-sm: 6px;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}
.container { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 2px solid var(--accent);
}
.header h1 { font-size: 28px; font-weight: 700; color: var(--accent-dark); }
.subtitle { font-size: 14px; color: var(--text-muted); margin-top: 4px; }
.card {
    background: var(--card-bg);
    border: 1px solid var(--border-light);
    border-radius: var(--radius);
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
}
.card h2 { font-size: 18px; color: var(--accent-dark); margin-bottom: 16px; }
.note { font-size: 13px; color: var(--text-muted); margin-bottom: 16px; }
.empty { color: var(--text-light); font-style: italic; padding: 24px 0; text-align: center; }
code {
    background: var(--surface);
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
    font-size: 12px;
    color: var(--accent-dark);
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 10px 12px; background: var(--surface); color: var(--accent-dark); border-bottom: 2px solid var(--border); }
td { padding: 10px 12px; border-bottom: 1px solid var(--border-light); }
tr:hover { background: var(--surface); }
.footer { text-align: center; padding: 24px 0; font-size: 12px; color: var(--text-light); border-top: 1px solid var(--border-light); margin-top: 32px; }
"""


def generate() -> str:
    """Generate the dashboard HTML and return the file path."""
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    stats = db.get_stats()
    all_files = db.get_all_files()
    recent_activity = db.get_recent_activity(15)
    html = _build_html(stats, all_files, recent_activity)
    output_path = DASHBOARD_DIR / "dashboard.html"
    output_path.write_text(html, encoding="utf-8")
    return str(output_path)


def _build_html(stats: Dict, all_files: List[Dict], recent_activity: List[Dict]) -> str:
    status_badges = "".join(
        f'<span style="display:inline-block;padding:4px 12px;border-radius:16px;background:var(--accent);color:white;font-size:12px;margin:4px">{s}: {c}</span>'
        for s, c in stats.get("status_counts", {}).items()
    )

    chapter_rows = ""
    for f in [f for f in all_files if f.get("folder") in ("chapters", "drafts", "final")]:
        chapter_rows += f"<tr><td>{f.get('filename','')}</td><td>{f.get('word_count',0):,}</td><td>{f.get('era','—')}</td><td>{', '.join((f.get('themes') or [])[:3])}</td><td>{f.get('emotional_register','—')}</td></tr>"

    char_map = {}
    for f in all_files:
        for c in (f.get("characters") or []):
            char_map[c] = char_map.get(c, 0) + 1
    char_rows = "".join(f"<tr><td>{c}</td><td>{n}</td></tr>" for c, n in sorted(char_map.items(), key=lambda x: -x[1])[:20])

    theme_map = {}
    for f in all_files:
        for t in (f.get("themes") or []):
            theme_map[t] = theme_map.get(t, 0) + 1
    theme_bars = "".join(
        f'<div style="display:flex;align-items:center;gap:12px;margin:8px 0"><span style="min-width:120px;font-size:13px">{t}</span><div style="flex:1;height:20px;background:var(--surface);border-radius:4px;overflow:hidden"><div style="height:100%;width:{n/max(list(theme_map.values()))*100 if theme_map else 0}%;background:var(--accent)"></div></div><span style="min-width:30px;text-align:right">{n}</span></div>'
        for t, n in sorted(theme_map.items(), key=lambda x: -x[1])[:15]
    )

    activity_rows = "".join(
        f"<tr><td>{a.get('timestamp','')[:19]}</td><td>{a.get('action','')}</td><td>{a.get('details','')}</td></tr>"
        for a in recent_activity
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Audhd Scribbler — Dashboard</title>
<style>{CSS_BASE}</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1>The Audhd Scribbler</h1>
            <p class="subtitle">Your memoir, at a glance · {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        <a href="files.html" style="color:var(--accent);text-decoration:none;font-size:14px">View My Files →</a>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-bottom:32px">
        <div class="card" style="text-align:center"><div style="font-size:32px;font-weight:700;color:var(--accent)">{stats['total_files']}</div><div style="font-size:11px;color:var(--text-muted);text-transform:uppercase">Files</div></div>
        <div class="card" style="text-align:center"><div style="font-size:32px;font-weight:700;color:var(--accent)">{stats['total_words']:,}</div><div style="font-size:11px;color:var(--text-muted);text-transform:uppercase">Words</div></div>
        <div class="card" style="text-align:center"><div style="font-size:32px;font-weight:700;color:var(--accent)">{len(stats.get('stale_drafts',[]))}</div><div style="font-size:11px;color:var(--text-muted);text-transform:uppercase">Resting</div></div>
    </div>
    <div class="card">
        <h2>Overview</h2>
        <div style="margin-bottom:20px">{status_badges}</div>
    </div>
    <div class="card">
        <h2>Chapter Grid</h2>
        {'<table><thead><tr><th>File</th><th>Words</th><th>Era</th><th>Themes</th><th>Mood</th></tr></thead><tbody>' + chapter_rows + '</tbody></table>' if chapter_rows else '<p class="empty">No chapters yet.</p>'}
    </div>
    <div class="card">
        <h2>Themes</h2>
        {theme_bars if theme_bars else '<p class="empty">No themes detected.</p>'}
    </div>
    <div class="card">
        <h2>Characters</h2>
        {'<table><thead><tr><th>Character</th><th>Appearances</th></tr></thead><tbody>' + char_rows + '</tbody></table>' if char_rows else '<p class="empty">No characters detected.</p>'}
    </div>
    <div class="card">
        <h2>Recent Activity</h2>
        {'<table><thead><tr><th>When</th><th>Action</th><th>Details</th></tr></thead><tbody>' + activity_rows + '</tbody></table>' if activity_rows else '<p class="empty">No activity yet.</p>'}
    </div>
    <div class="footer">The Audhd Scribbler · Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</div>
</body>
</html>"""
