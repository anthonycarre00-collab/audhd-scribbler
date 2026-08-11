#!/usr/bin/env python3
"""Dashboard generator for The Audhd Scribbler.

Generates a beautiful, calm, feature-rich HTML dashboard.
Opens in any browser. No server needed.
"""
import json
import os
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from collections import Counter, defaultdict

from ..config import PROJECT_ROOT, DATA_DIR, DASHBOARD_DIR, PALETTE, STATUSES
from .. import db


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
    --shadow-hover: 0 4px 12px rgba(26, 35, 50, 0.08), 0 2px 4px rgba(26, 35, 50, 0.06);
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
    -moz-osx-font-smoothing: grayscale;
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
.header h1 {
    font-size: 28px;
    font-weight: 700;
    color: var(--accent-dark);
    letter-spacing: -0.5px;
    margin: 0;
}
.subtitle {
    font-size: 14px;
    color: var(--text-muted);
    margin-top: 4px;
}
.nav-link {
    color: var(--accent);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    padding: 8px 16px;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    transition: all 0.15s;
}
.nav-link:hover {
    background: var(--accent-soft);
    border-color: var(--accent);
}
.stats-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
}
.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--border-light);
    border-radius: var(--radius);
    padding: 20px;
    text-align: center;
    box-shadow: var(--shadow);
}
.stat-number {
    font-size: 32px;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
    margin-bottom: 4px;
}
.stat-label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 500;
}
.card {
    background: var(--card-bg);
    border: 1px solid var(--border-light);
    border-radius: var(--radius);
    padding: 24px;
    margin-bottom: 24px;
    box-shadow: var(--shadow);
}
.card h2 {
    font-size: 18px;
    color: var(--accent-dark);
    margin-bottom: 16px;
    font-weight: 600;
}
.card h3 {
    font-size: 14px;
    color: var(--text-muted);
    margin-bottom: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.note {
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: 16px;
    line-height: 1.5;
}
.empty {
    color: var(--text-light);
    font-style: italic;
    padding: 24px 0;
    text-align: center;
    font-size: 14px;
}
code {
    background: var(--surface);
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
    font-size: 12px;
    color: var(--accent-dark);
}
/* Status badges */
.status-badges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.status-badge {
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    color: white;
}
.status-seedling { background: #A8C4E0; color: #1A2332; }
.status-growing { background: #7B9BC8; }
.status-shaping { background: #4A6FA5; }
.status-polishing { background: #365680; }
.status-resting { background: #9BA8B8; }
/* Tables */
.table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.table th {
    text-align: left;
    padding: 10px 12px;
    background: var(--surface);
    color: var(--accent-dark);
    font-weight: 600;
    border-bottom: 2px solid var(--border);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.table td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border-light);
    vertical-align: top;
}
.table tr:hover { background: var(--surface); }
.table tr:last-child td { border-bottom: none; }
/* Status dot */
.status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 8px;
    vertical-align: middle;
}
/* Theme bars */
.theme-bars { display: flex; flex-direction: column; gap: 10px; }
.theme-bar {
    display: flex;
    align-items: center;
    gap: 12px;
}
.theme-label {
    min-width: 120px;
    font-size: 13px;
    font-weight: 500;
    color: var(--text);
}
.theme-bar-track {
    flex: 1;
    height: 24px;
    background: var(--surface);
    border-radius: var(--radius-sm);
    overflow: hidden;
}
.theme-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent-light), var(--accent));
    border-radius: var(--radius-sm);
    transition: width 0.3s ease;
}
.theme-count {
    min-width: 30px;
    text-align: right;
    font-size: 13px;
    color: var(--text-muted);
    font-weight: 500;
}
/* Orphan tray */
.orphan-tray {
    background: #FFF9F0;
    border: 1px solid #E8D9B8;
    border-radius: var(--radius);
    padding: 16px 20px;
}
.orphan-item {
    padding: 8px 0;
    border-bottom: 1px solid #F0E5C8;
    font-size: 13px;
}
.orphan-item:last-child { border-bottom: none; }
.orphan-name {
    font-weight: 500;
    color: var(--text);
}
.orphan-meta {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
}
/* Constellation heatmap */
.heatmap {
    display: grid;
    gap: 2px;
    font-size: 11px;
    overflow-x: auto;
}
.heatmap-cell {
    padding: 6px 8px;
    text-align: center;
    border-radius: 3px;
    min-width: 40px;
}
.heatmap-header {
    background: var(--accent-dark);
    color: white;
    font-weight: 600;
    font-size: 10px;
}
.heatmap-row-label {
    background: var(--surface);
    font-weight: 500;
    color: var(--accent-dark);
    text-align: right;
    padding-right: 10px;
}
.heatmap-0 { background: var(--surface); }
.heatmap-1 { background: #D4E1F0; }
.heatmap-2 { background: #A8C4E0; }
.heatmap-3 { background: #7B9BC8; color: white; }
.heatmap-4 { background: #4A6FA5; color: white; }
.heatmap-5 { background: #365680; color: white; }
/* Timeline */
.timeline {
    position: relative;
    padding-left: 24px;
}
.timeline::before {
    content: '';
    position: absolute;
    left: 8px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: var(--border);
}
.timeline-item {
    position: relative;
    padding-bottom: 20px;
}
.timeline-item::before {
    content: '';
    position: absolute;
    left: -20px;
    top: 4px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--accent);
    border: 2px solid var(--card-bg);
}
.timeline-date {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 500;
}
.timeline-title {
    font-size: 14px;
    color: var(--text);
    margin-top: 2px;
}
/* Footer */
.footer {
    text-align: center;
    padding: 24px 0;
    font-size: 12px;
    color: var(--text-light);
    border-top: 1px solid var(--border-light);
    margin-top: 32px;
}
/* Graph */
#graph-container {
    width: 100%;
    height: 500px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius);
    background: var(--card-bg);
    overflow: hidden;
}
/* Responsive */
@media (max-width: 768px) {
    .container { padding: 20px 16px; }
    .header { flex-direction: column; gap: 16px; align-items: flex-start; }
    .stats-row { grid-template-columns: repeat(2, 1fr); }
}
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
    <header class="header">
        <div>
            <h1>The Audhd Scribbler</h1>
            <p class="subtitle">Your memoir, at a glance · {datetime.now().strftime('%B %d, %Y')}</p>
        </div>
        <a href="files.html" class="nav-link">View My Files →</a>
    </header>

    {_render_stats_row(stats)}

    {_render_overview(stats, all_files)}
    {_render_chapter_grid(all_files)}
    {_render_constellation(all_files)}
    {_render_timeline(all_files)}
    {_render_relationship_map(all_files)}
    {_render_orphan_tray(all_files)}
    {_render_themes(all_files)}
    {_render_characters(all_files)}
    {_render_activity(recent_activity)}

    <footer class="footer">
        <p>The Audhd Scribbler · Your writing stays on your machine · Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </footer>
</div>

<script>
{_build_graph_js(all_files)}
</script>
</body>
</html>"""


def _render_stats_row(stats: Dict) -> str:
    return f"""
    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-number">{stats['total_files']}</div>
            <div class="stat-label">Files</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{stats['total_words']:,}</div>
            <div class="stat-label">Words</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{len(stats.get('stale_drafts', []))}</div>
            <div class="stat-label">Resting</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{sum(len(f.get('characters', [])) for f in db.get_all_files())}</div>
            <div class="stat-label">Characters</div>
        </div>
    </div>"""


def _render_overview(stats: Dict, all_files: List[Dict]) -> str:
    status_counts = stats.get("status_counts", {})
    folder_counts = stats.get("folder_counts", {})

    status_badges = ""
    for status in STATUSES:
        count = status_counts.get(status, 0)
        if count > 0:
            status_badges += f'<span class="status-badge status-{status}">{status}: {count}</span>'

    folder_rows = ""
    for folder, count in sorted(folder_counts.items()):
        folder_rows += f"<tr><td>{folder}/</td><td>{count}</td></tr>"

    return f"""
    <div class="card">
        <h2>Overview</h2>
        <div class="status-badges" style="margin-bottom: 20px;">{status_badges}</div>
        <table class="table">
            <thead><tr><th>Folder</th><th>Files</th></tr></thead>
            <tbody>{folder_rows}</tbody>
        </table>
    </div>"""


def _render_chapter_grid(all_files: List[Dict]) -> str:
    chapter_files = [f for f in all_files if f.get("folder") in ("chapters", "drafts", "final")]

    if not chapter_files:
        return """
        <div class="card">
            <h2>Chapters</h2>
            <p class="empty">No chapters yet. Drop text files into <code>raw-dumps/</code> and run "Tag all my dumps" from the menu.</p>
        </div>"""

    rows = ""
    for f in sorted(chapter_files, key=lambda x: (x.get("chapter_no") or 999, x.get("filename", ""))):
        status = f.get("status", "seedling")
        themes_str = ", ".join((f.get("themes") or [])[:3]) or "—"
        rows += f"""
        <tr>
            <td><span class="status-dot status-{status}"></span>{f.get('filename', '')}</td>
            <td>{f.get('chapter_no', '—')}</td>
            <td>{f.get('word_count', 0):,}</td>
            <td>{f.get('era', '—')}</td>
            <td>{themes_str}</td>
            <td>{f.get('emotional_register', '—')}</td>
        </tr>"""

    return f"""
    <div class="card">
        <h2>Chapter Grid</h2>
        <p class="note">Status at a glance — click the colored dots to learn what each status means.</p>
        <table class="table">
            <thead><tr><th>File</th><th>Ch.</th><th>Words</th><th>Era</th><th>Themes</th><th>Mood</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""


def _render_constellation(all_files: List[Dict]) -> str:
    """Chapter × theme constellation heatmap."""
    chapter_files = [f for f in all_files if f.get("folder") in ("chapters", "drafts", "final", "raw-dumps")]
    chapter_files = [f for f in chapter_files if f.get("themes")]

    if not chapter_files:
        return """
        <div class="card">
            <h2>Theme Constellation</h2>
            <p class="empty">No themed chapters yet. Tag some files to see which themes appear where.</p>
        </div>"""

    # Collect all themes
    all_themes = set()
    for f in chapter_files:
        all_themes.update(f.get("themes") or [])
    all_themes = sorted(all_themes)[:12]  # Cap at 12 themes for display

    if not all_themes:
        return '<div class="card"><h2>Theme Constellation</h2><p class="empty">No themes detected.</p></div>'

    # Build the matrix
    header_cells = '<div class="heatmap-cell heatmap-header"></div>'
    for theme in all_themes:
        header_cells += f'<div class="heatmap-cell heatmap-header">{theme[:10]}</div>'

    rows = ""
    for f in chapter_files[:15]:  # Cap at 15 chapters
        name = f.get("filename", "")[:15]
        rows += f'<div class="heatmap-cell heatmap-row-label">{name}</div>'
        file_themes = set(f.get("themes") or [])
        for theme in all_themes:
            if theme in file_themes:
                count = (f.get("themes") or []).count(theme)
                rows += f'<div class="heatmap-cell heatmap-{min(count, 5)}" title="{theme}: {count}">{count}</div>'
            else:
                rows += '<div class="heatmap-cell heatmap-0"></div>'

    return f"""
    <div class="card">
        <h2>Theme Constellation</h2>
        <p class="note">Which themes appear in which chapters. Darker = more dense. Shows whether themes are braided (interleaved) or blocky (segregated).</p>
        <div class="heatmap" style="grid-template-columns: 140px repeat({len(all_themes)}, 1fr);">
            {header_cells}
            {rows}
        </div>
    </div>"""


def _render_timeline(all_files: List[Dict]) -> str:
    """Timeline view — files ordered by era/date."""
    # Sort by dump_date or last_modified
    def get_date(f):
        return f.get("dump_date") or f.get("last_modified", "")[:10] or ""

    dated = [f for f in all_files if get_date(f)]
    dated.sort(key=get_date, reverse=True)

    if not dated:
        return """
        <div class="card">
            <h2>Timeline</h2>
            <p class="empty">No dated files yet.</p>
        </div>"""

    items = ""
    for f in dated[:12]:
        date_str = get_date(f)[:10]
        name = f.get("filename", "")
        era = f.get("era", "")
        word_count = f.get("word_count", 0)
        title = f"{name} · {word_count} words"
        if era:
            title += f" · {era}"
        items += f"""
        <div class="timeline-item">
            <div class="timeline-date">{date_str}</div>
            <div class="timeline-title">{title}</div>
        </div>"""

    return f"""
    <div class="card">
        <h2>Recent Activity Timeline</h2>
        <p class="note">Your most recently touched files, newest first.</p>
        <div class="timeline">
            {items}
        </div>
    </div>"""


def _render_relationship_map(all_files: List[Dict]) -> str:
    """Force-directed graph of files ↔ characters ↔ themes."""
    nodes = []
    edges = []
    node_set = set()

    def add_node(label, ntype):
        if label not in node_set:
            node_set.add(label)
            nodes.append({"id": label, "type": ntype})

    for f in all_files:
        fname = f.get("filename", "")
        if not fname:
            continue
        add_node(fname, "file")
        for char in (f.get("characters") or [])[:5]:
            add_node(char, "character")
            edges.append({"source": fname, "target": char})
        for theme in (f.get("themes") or [])[:3]:
            add_node(theme, "theme")
            edges.append({"source": fname, "target": theme})

    if not nodes:
        return """
        <div class="card">
            <h2>Relationship Map</h2>
            <p class="empty">No relationships to map yet. Tag some files first.</p>
        </div>"""

    return f"""
    <div class="card">
        <h2>Relationship Map</h2>
        <p class="note">How files, characters, and themes connect. Drag nodes to rearrange. Blue = files, green = characters, gold = themes.</p>
        <div id="graph-container">
            <svg id="graph-svg" width="100%" height="100%"></svg>
        </div>
    </div>"""


def _build_graph_js(all_files: List[Dict]) -> str:
    """Build the JavaScript for the force-directed graph."""
    nodes = []
    edges = []
    node_set = set()

    def add_node(label, ntype):
        if label not in node_set:
            node_set.add(label)
            nodes.append({"id": label, "type": ntype})

    for f in all_files:
        fname = f.get("filename", "")
        if not fname:
            continue
        add_node(fname, "file")
        for char in (f.get("characters") or [])[:5]:
            add_node(char, "character")
            edges.append({"source": fname, "target": char})
        for theme in (f.get("themes") or [])[:3]:
            add_node(theme, "theme")
            edges.append({"source": fname, "target": theme})

    graph_json = json.dumps({"nodes": nodes, "edges": edges})

    return f"""
    var graphData = {graph_json};
    drawGraph(graphData);

    function drawGraph(data) {{
        if (!data || !data.nodes || data.nodes.length === 0) return;

        var svg = document.getElementById('graph-svg');
        if (!svg) return;

        var width = svg.clientWidth || 800;
        var height = svg.clientHeight || 500;

        svg.innerHTML = '';

        // Add zoom/pan support
        var g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        svg.appendChild(g);

        var viewBox = {{x: 0, y: 0, w: width, h: height}};
        var scale = 1;
        var isDragging = false;
        var dragStart = {{x: 0, y: 0}};

        svg.addEventListener('mousedown', function(e) {{
            isDragging = true;
            dragStart = {{x: e.clientX, y: e.clientY}};
        }});
        svg.addEventListener('mousemove', function(e) {{
            if (!isDragging) return;
            var dx = (e.clientX - dragStart.x) / scale;
            var dy = (e.clientY - dragStart.y) / scale;
            viewBox.x -= dx;
            viewBox.y -= dy;
            dragStart = {{x: e.clientX, y: e.clientY}};
            g.setAttribute('transform', 'translate(' + (-viewBox.x * scale) + ',' + (-viewBox.y * scale) + ') scale(' + scale + ')');
        }});
        svg.addEventListener('mouseup', function() {{ isDragging = false; }});
        svg.addEventListener('mouseleave', function() {{ isDragging = false; }});
        svg.addEventListener('wheel', function(e) {{
            e.preventDefault();
            scale = e.deltaY < 0 ? scale * 1.1 : scale / 1.1;
            scale = Math.max(0.3, Math.min(3, scale));
            g.setAttribute('transform', 'translate(' + (-viewBox.x * scale) + ',' + (-viewBox.y * scale) + ') scale(' + scale + ')');
        }});

        var nodes = data.nodes.map(function(n, i) {{
            return {{
                id: n.id,
                type: n.type,
                x: width / 2 + (Math.random() - 0.5) * 300,
                y: height / 2 + (Math.random() - 0.5) * 300,
                vx: 0,
                vy: 0
            }};
        }});

        var nodeMap = {{}};
        nodes.forEach(function(n) {{ nodeMap[n.id] = n; }});

        var edges = data.edges.map(function(e) {{
            return {{ source: nodeMap[e.source], target: nodeMap[e.target] }};
        }}).filter(function(e) {{ return e.source && e.target; }});

        // Simulation
        var iterations = 150;
        for (var iter = 0; iter < iterations; iter++) {{
            for (var i = 0; i < nodes.length; i++) {{
                for (var j = i + 1; j < nodes.length; j++) {{
                    var dx = nodes[j].x - nodes[i].x;
                    var dy = nodes[j].y - nodes[i].y;
                    var dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    var force = 800 / (dist * dist);
                    nodes[i].vx -= force * dx / dist;
                    nodes[i].vy -= force * dy / dist;
                    nodes[j].vx += force * dx / dist;
                    nodes[j].vy += force * dy / dist;
                }}
            }}
            edges.forEach(function(e) {{
                var dx = e.target.x - e.source.x;
                var dy = e.target.y - e.source.y;
                var dist = Math.sqrt(dx * dx + dy * dy) || 1;
                var force = dist * 0.005;
                e.source.vx += force * dx / dist;
                e.source.vy += force * dy / dist;
                e.target.vx -= force * dx / dist;
                e.target.vy -= force * dy / dist;
            }});
            nodes.forEach(function(n) {{
                n.vx += (width / 2 - n.x) * 0.002;
                n.vy += (height / 2 - n.y) * 0.002;
                n.x += n.vx;
                n.y += n.vy;
                n.vx *= 0.85;
                n.vy *= 0.85;
            }});
        }}

        var colors = {{
            file: '#4A6FA5',
            character: '#5B8C6E',
            theme: '#B8956A'
        }};
        var sizes = {{
            file: 8,
            character: 5,
            theme: 5
        }};

        // Draw edges
        edges.forEach(function(e) {{
            var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', e.source.x);
            line.setAttribute('y1', e.source.y);
            line.setAttribute('x2', e.target.x);
            line.setAttribute('y2', e.target.y);
            line.setAttribute('stroke', '#D1D9E3');
            line.setAttribute('stroke-width', '1');
            g.appendChild(line);
        }});

        // Draw nodes
        nodes.forEach(function(n) {{
            var circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', n.x);
            circle.setAttribute('cy', n.y);
            circle.setAttribute('r', sizes[n.type] || 5);
            circle.setAttribute('fill', colors[n.type] || '#4A6FA5');
            circle.setAttribute('opacity', '0.85');
            circle.setAttribute('stroke', 'white');
            circle.setAttribute('stroke-width', '1.5');
            g.appendChild(circle);

            var text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', n.x + 10);
            text.setAttribute('y', n.y + 4);
            text.setAttribute('font-size', '10');
            text.setAttribute('font-family', 'sans-serif');
            text.setAttribute('fill', '#1A2332');
            text.textContent = n.id.length > 25 ? n.id.substring(0, 22) + '...' : n.id;
            g.appendChild(text);
        }});
    }}
    """


def _render_orphan_tray(all_files: List[Dict]) -> str:
    """Orphan tray — files with no chapter assignment."""
    orphans = [f for f in all_files if f.get("folder") == "raw-dumps" and not f.get("chapter_no")]

    if not orphans:
        return """
        <div class="card">
            <h2>Orphan Tray</h2>
            <p class="empty">No orphans — everything is filed.</p>
        </div>"""

    items = ""
    for o in orphans[:10]:
        name = o.get("filename", "")
        word_count = o.get("word_count", 0)
        themes = ", ".join((o.get("themes") or [])[:3])
        items += f"""
        <div class="orphan-item">
            <div class="orphan-name">{name} <span style="color: var(--text-muted); font-weight: 400;">· {word_count} words</span></div>
            <div class="orphan-meta">{themes or "No themes detected yet"}</div>
        </div>"""

    return f"""
    <div class="card">
        <h2>Orphan Tray</h2>
        <p class="note">Dumps that haven't been assigned to a chapter yet. They may link together later — keep them visible.</p>
        <div class="orphan-tray">
            {items}
        </div>
    </div>"""


def _render_themes(all_files: List[Dict]) -> str:
    """Theme frequency bars."""
    theme_map = {}
    for f in all_files:
        for theme in (f.get("themes") or []):
            theme_map[theme] = theme_map.get(theme, 0) + 1

    if not theme_map:
        return """
        <div class="card">
            <h2>Themes</h2>
            <p class="empty">No themes detected yet.</p>
        </div>"""

    sorted_themes = sorted(theme_map.items(), key=lambda x: x[1], reverse=True)
    max_count = max(theme_map.values())
    bars = ""
    for theme, count in sorted_themes:
        width = count / max_count * 100
        bars += f"""
        <div class="theme-bar">
            <span class="theme-label">{theme}</span>
            <div class="theme-bar-track"><div class="theme-bar-fill" style="width: {width}%"></div></div>
            <span class="theme-count">{count}</span>
        </div>"""

    return f"""
    <div class="card">
        <h2>Themes</h2>
        <p class="note">Theme frequency across all tagged files.</p>
        <div class="theme-bars">{bars}</div>
    </div>"""


def _render_characters(all_files: List[Dict]) -> str:
    """Character appearances."""
    char_map = {}
    for f in all_files:
        for char in (f.get("characters") or []):
            if char not in char_map:
                char_map[char] = {"count": 0, "files": []}
            char_map[char]["count"] += 1
            char_map[char]["files"].append(f.get("filename", ""))

    if not char_map:
        return """
        <div class="card">
            <h2>Characters</h2>
            <p class="empty">No characters detected yet. Run "Tag all my dumps" from the menu.</p>
        </div>"""

    sorted_chars = sorted(char_map.items(), key=lambda x: x[1]["count"], reverse=True)
    rows = ""
    for char, data in sorted_chars[:25]:
        files_str = ", ".join(data["files"][:3])
        if len(data["files"]) > 3:
            files_str += f" (+{len(data['files']) - 3} more)"
        rows += f"<tr><td><strong>{char}</strong></td><td>{data['count']}</td><td style='color: var(--text-muted);'>{files_str}</td></tr>"

    return f"""
    <div class="card">
        <h2>Characters</h2>
        <p class="note">{len(sorted_chars)} characters detected across all files.</p>
        <table class="table">
            <thead><tr><th>Character</th><th>Appearances</th><th>In files</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""


def _render_activity(recent_activity: List[Dict]) -> str:
    """Recent activity log."""
    if not recent_activity:
        return """
        <div class="card">
            <h2>Recent Activity</h2>
            <p class="empty">No activity yet. Run "Tag all my dumps" from the menu.</p>
        </div>"""

    rows = ""
    for a in recent_activity:
        ts = a.get("timestamp", "")[:19]
        action = a.get("action", "")
        details = a.get("details", "")
        rows += f"<tr><td style='color: var(--text-muted);'>{ts}</td><td><strong>{action}</strong></td><td>{details}</td></tr>"

    return f"""
    <div class="card">
        <h2>Recent Activity</h2>
        <table class="table">
            <thead><tr><th>When</th><th>Action</th><th>Details</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>"""
