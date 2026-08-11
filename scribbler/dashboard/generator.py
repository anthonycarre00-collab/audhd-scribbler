#!/usr/bin/env python3
"""Dashboard generator for The Audhd Scribbler.

Generates a single interactive HTML file that opens in any browser.
No server needed — just open the file.
"""
import json
import os
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ..config import PROJECT_ROOT, DATA_DIR, DASHBOARD_DIR, PALETTE, STATUSES
from .. import db


def generate() -> str:
    """Generate the dashboard HTML and return the file path."""
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    stats = db.get_stats()
    all_files = db.get_all_files()
    recent_activity = db.get_recent_activity(15)

    # Build the HTML
    html = _build_html(stats, all_files, recent_activity)

    output_path = DASHBOARD_DIR / "dashboard.html"
    output_path.write_text(html, encoding="utf-8")

    return str(output_path)


def _build_html(stats: Dict, all_files: List[Dict], recent_activity: List[Dict]) -> str:
    """Build the full dashboard HTML."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Audhd Scribbler — Dashboard</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="dashboard">
  <header class="header">
    <div class="header-left">
      <h1>The Audhd Scribbler</h1>
      <p class="subtitle">Your memoir, at a glance</p>
    </div>
    <div class="header-right">
      <div class="stat-block">
        <span class="stat-number">{stats['total_files']}</span>
        <span class="stat-label">files</span>
      </div>
      <div class="stat-block">
        <span class="stat-number">{stats['total_words']:,}</span>
        <span class="stat-label">words</span>
      </div>
      <div class="stat-block">
        <span class="stat-number">{len(stats.get('stale_drafts', []))}</span>
        <span class="stat-label">resting</span>
      </div>
    </div>
  </header>

  <nav class="nav">
    <button class="nav-btn active" onclick="showTab('overview')">Overview</button>
    <button class="nav-btn" onclick="showTab('chapters')">Chapters</button>
    <button class="nav-btn" onclick="showTab('characters')">Characters</button>
    <button class="nav-btn" onclick="showTab('themes')">Themes</button>
    <button class="nav-btn" onclick="showTab('map')">Relationship Map</button>
    <button class="nav-btn" onclick="showTab('activity')">Activity</button>
  </nav>

  <main class="content">
    {_render_overview(stats)}
    {_render_chapters(all_files)}
    {_render_characters(all_files)}
    {_render_themes(all_files)}
    {_render_map(all_files)}
    {_render_activity(recent_activity)}
  </main>

  <footer class="footer">
    <p>The Audhd Scribbler · Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
  </footer>
</div>

<script>
{JS}
</script>
</body>
</html>"""


def _render_overview(stats: Dict) -> str:
    status_counts = stats.get("status_counts", {})
    folder_counts = stats.get("folder_counts", {})
    stale = stats.get("stale_drafts", [])

    status_badges = ""
    for status in STATUSES:
        count = status_counts.get(status, 0)
        if count > 0:
            status_badges += f'<span class="status-badge status-{status}">{status}: {count}</span>'

    folder_rows = ""
    for folder, count in sorted(folder_counts.items()):
        folder_rows += f"<tr><td>{folder}</td><td>{count}</td></tr>"

    stale_rows = ""
    if stale:
        for s in stale[:5]:
            stale_rows += f"<tr><td>{s.get('filename', 'unknown')}</td><td>{s.get('last_modified', 'unknown')[:10]}</td><td>{s.get('word_count', 0)}</td></tr>"
    else:
        stale_rows = "<tr><td colspan='3' class='empty'>Nothing resting — all chapters have been touched recently.</td></tr>"

    return f"""
    <section id="overview" class="tab active">
      <div class="card">
        <h2>Status at a glance</h2>
        <div class="status-badges">{status_badges}</div>
      </div>

      <div class="card">
        <h2>Files by folder</h2>
        <table class="table">
          <thead><tr><th>Folder</th><th>Files</th></tr></thead>
          <tbody>{folder_rows}</tbody>
        </table>
      </div>

      <div class="card">
        <h2>Resting chapters</h2>
        <p class="note">Chapters not touched in 7+ days. "Resting" is a valid status, not a nudge.</p>
        <table class="table">
          <thead><tr><th>File</th><th>Last touched</th><th>Words</th></tr></thead>
          <tbody>{stale_rows}</tbody>
        </table>
      </div>
    </section>"""


def _render_chapters(all_files: List[Dict]) -> str:
    chapter_files = [f for f in all_files if f.get("folder") in ("chapters", "drafts", "final")]

    if not chapter_files:
        return """
        <section id="chapters" class="tab">
          <div class="card">
            <h2>Chapters</h2>
            <p class="empty">No chapters yet. Drop text files into the <code>raw-dumps/</code> folder and run <code>scribbler label-all</code>.</p>
          </div>
        </section>"""

    rows = ""
    for f in chapter_files:
        status = f.get("status", "seedling")
        rows += f"""
        <tr>
          <td><span class="status-dot status-{status}"></span>{f.get('filename', 'unknown')}</td>
          <td>{f.get('chapter_no', '—')}</td>
          <td>{f.get('word_count', 0):,}</td>
          <td>{f.get('era', '—')}</td>
          <td>{', '.join((f.get('themes') or [])[:3]) or '—'}</td>
          <td>{f.get('emotional_register', '—')}</td>
          <td>{f.get('last_modified', '—')[:10]}</td>
        </tr>"""

    return f"""
    <section id="chapters" class="tab">
      <div class="card">
        <h2>Chapter grid</h2>
        <table class="table">
          <thead>
            <tr><th>File</th><th>Ch.</th><th>Words</th><th>Era</th><th>Themes</th><th>Mood</th><th>Modified</th></tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>"""


def _render_characters(all_files: List[Dict]) -> str:
    """Aggregate character appearances across all files."""
    char_map = {}
    for f in all_files:
        for char in (f.get("characters") or []):
            if char not in char_map:
                char_map[char] = {"count": 0, "files": []}
            char_map[char]["count"] += 1
            char_map[char]["files"].append(f.get("filename", ""))

    if not char_map:
        return """
        <section id="characters" class="tab">
          <div class="card">
            <h2>Characters</h2>
            <p class="empty">No characters detected yet. Run <code>scribbler label-all</code> to detect characters.</p>
          </div>
        </section>"""

    sorted_chars = sorted(char_map.items(), key=lambda x: x[1]["count"], reverse=True)
    rows = ""
    for char, data in sorted_chars[:30]:
        files_str = ", ".join(data["files"][:3])
        if len(data["files"]) > 3:
            files_str += f" (+{len(data['files']) - 3} more)"
        rows += f"<tr><td>{char}</td><td>{data['count']}</td><td>{files_str}</td></tr>"

    return f"""
    <section id="characters" class="tab">
      <div class="card">
        <h2>Characters</h2>
        <p class="note">{len(sorted_chars)} characters detected across all files.</p>
        <table class="table">
          <thead><tr><th>Character</th><th>Appearances</th><th>In files</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>"""


def _render_themes(all_files: List[Dict]) -> str:
    """Aggregate theme appearances."""
    theme_map = {}
    for f in all_files:
        for theme in (f.get("themes") or []):
            theme_map[theme] = theme_map.get(theme, 0) + 1

    if not theme_map:
        return """
        <section id="themes" class="tab">
          <div class="card">
            <h2>Themes</h2>
            <p class="empty">No themes detected yet.</p>
          </div>
        </section>"""

    sorted_themes = sorted(theme_map.items(), key=lambda x: x[1], reverse=True)
    bars = ""
    max_count = max(theme_map.values())
    for theme, count in sorted_themes:
        width = count / max_count * 100
        bars += f"""
        <div class="theme-bar">
          <span class="theme-label">{theme}</span>
          <div class="theme-bar-track"><div class="theme-bar-fill" style="width: {width}%"></div></div>
          <span class="theme-count">{count}</span>
        </div>"""

    return f"""
    <section id="themes" class="tab">
      <div class="card">
        <h2>Themes</h2>
        <p class="note">Theme frequency across all tagged files.</p>
        <div class="theme-bars">{bars}</div>
      </div>
    </section>"""


def _render_map(all_files: List[Dict]) -> str:
    """Generate a force-directed graph of files ↔ characters ↔ themes."""
    nodes = []
    edges = []
    node_set = set()

    def add_node(label, ntype):
        if label not in node_set:
            node_set.add(label)
            nodes.append({"id": label, "type": ntype})

    for f in all_files:
        fname = f.get("filename", "unknown")
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

    if not nodes:
        return """
        <section id="map" class="tab">
          <div class="card">
            <h2>Relationship Map</h2>
            <p class="empty">No relationships to map yet. Tag some files first.</p>
          </div>
        </section>"""

    return f"""
    <section id="map" class="tab">
      <div class="card">
        <h2>Relationship Map</h2>
        <p class="note">How files, characters, and themes connect. Drag nodes to rearrange.</p>
        <div id="graph-container" style="width: 100%; height: 500px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg);">
          <svg id="graph-svg" width="100%" height="100%"></svg>
        </div>
      </div>
    </section>
    <script>
    var graphData = {graph_json};
    drawGraph(graphData);
    </script>"""


def _render_activity(recent_activity: List[Dict]) -> str:
    if not recent_activity:
        return """
        <section id="activity" class="tab">
          <div class="card">
            <h2>Recent Activity</h2>
            <p class="empty">No activity yet. Run <code>scribbler label-all</code> or <code>scribbler analyze</code> to get started.</p>
          </div>
        </section>"""

    rows = ""
    for a in recent_activity:
        rows += f"<tr><td>{a.get('timestamp', '')[:19]}</td><td>{a.get('action', '')}</td><td>{a.get('details', '')}</td></tr>"

    return f"""
    <section id="activity" class="tab">
      <div class="card">
        <h2>Recent Activity</h2>
        <table class="table">
          <thead><tr><th>When</th><th>Action</th><th>Details</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>"""


# CSS for the dashboard — calm blue palette, low sensory load
CSS = """
:root {
  --bg: #F7F8FA;
  --surface: #EEF1F5;
  --card-bg: #FFFFFF;
  --text: #1A2332;
  --text-muted: #5C6878;
  --accent: #4A6FA5;
  --accent-dark: #365680;
  --accent-light: #7B9BC8;
  --border: #D1D9E3;
  --success: #5B8C6E;
  --warning: #B8956A;
  --status-seedling: #A8C4E0;
  --status-growing: #7B9BC8;
  --status-shaping: #4A6FA5;
  --status-polishing: #365680;
  --status-resting: #9BA8B8;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
.dashboard { max-width: 1100px; margin: 0 auto; padding: 24px; }
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
  border-bottom: 2px solid var(--accent);
  margin-bottom: 24px;
}
.header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--accent-dark);
  letter-spacing: -0.5px;
}
.subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin-top: 4px;
}
.header-right {
  display: flex;
  gap: 24px;
}
.stat-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 60px;
}
.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
}
.stat-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-top: 4px;
}
.nav {
  display: flex;
  gap: 4px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border);
}
.nav-btn {
  padding: 10px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}
.nav-btn:hover { color: var(--accent); }
.nav-btn.active {
  color: var(--accent-dark);
  border-bottom-color: var(--accent);
  font-weight: 600;
}
.content { min-height: 500px; }
.tab { display: none; }
.tab.active { display: block; }
.card {
  background: var(--card-bg);
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 20px;
  border: 1px solid var(--border);
}
.card h2 {
  font-size: 18px;
  color: var(--accent-dark);
  margin-bottom: 16px;
  font-weight: 600;
}
.note {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 12px;
  font-style: italic;
}
.empty {
  color: var(--text-muted);
  font-style: italic;
  padding: 24px 0;
  text-align: center;
}
code {
  background: var(--surface);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table th {
  text-align: left;
  padding: 8px 12px;
  background: var(--surface);
  color: var(--accent-dark);
  font-weight: 600;
  border-bottom: 1px solid var(--border);
}
.table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
.table tr:hover { background: var(--surface); }
.status-badges {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.status-badge {
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 12px;
  font-weight: 500;
  color: white;
}
.status-seedling { background: var(--status-seedling); color: var(--text); }
.status-growing { background: var(--status-growing); }
.status-shaping { background: var(--status-shaping); }
.status-polishing { background: var(--status-polishing); }
.status-resting { background: var(--status-resting); }
.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 8px;
}
.theme-bars { display: flex; flex-direction: column; gap: 8px; }
.theme-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.theme-label {
  min-width: 120px;
  font-size: 13px;
  font-weight: 500;
}
.theme-bar-track {
  flex: 1;
  height: 20px;
  background: var(--surface);
  border-radius: 4px;
  overflow: hidden;
}
.theme-bar-fill {
  height: 100%;
  background: var(--accent);
  transition: width 0.3s;
}
.theme-count {
  min-width: 30px;
  text-align: right;
  font-size: 13px;
  color: var(--text-muted);
}
.footer {
  text-align: center;
  padding: 20px 0;
  font-size: 12px;
  color: var(--text-muted);
  border-top: 1px solid var(--border);
  margin-top: 24px;
}
@media (max-width: 768px) {
  .header { flex-direction: column; gap: 16px; }
  .header-right { justify-content: center; }
  .nav { overflow-x: auto; }
}
"""

# JavaScript for tab switching and graph rendering
JS = """
function showTab(tabId) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  event.target.classList.add('active');
}

function drawGraph(data) {
  if (!data || !data.nodes || data.nodes.length === 0) return;

  var svg = document.getElementById('graph-svg');
  if (!svg) return;

  var width = svg.clientWidth || 800;
  var height = svg.clientHeight || 500;

  // Clear
  svg.innerHTML = '';

  // Simple force-directed layout (basic implementation)
  var nodes = data.nodes.map(function(n, i) {
    return {
      id: n.id,
      type: n.type,
      x: width / 2 + (Math.random() - 0.5) * 200,
      y: height / 2 + (Math.random() - 0.5) * 200,
      vx: 0,
      vy: 0
    };
  });

  var nodeMap = {};
  nodes.forEach(function(n) { nodeMap[n.id] = n; });

  var edges = data.edges.map(function(e) {
    return { source: nodeMap[e.source], target: nodeMap[e.target] };
  }).filter(function(e) { return e.source && e.target; });

  // Simple simulation
  var iterations = 100;
  for (var iter = 0; iter < iterations; iter++) {
    // Repulsion
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var dx = nodes[j].x - nodes[i].x;
        var dy = nodes[j].y - nodes[i].y;
        var dist = Math.sqrt(dx * dx + dy * dy) || 1;
        var force = 500 / (dist * dist);
        nodes[i].vx -= force * dx / dist;
        nodes[i].vy -= force * dy / dist;
        nodes[j].vx += force * dx / dist;
        nodes[j].vy += force * dy / dist;
      }
    }
    // Attraction (edges)
    edges.forEach(function(e) {
      var dx = e.target.x - e.source.x;
      var dy = e.target.y - e.source.y;
      var dist = Math.sqrt(dx * dx + dy * dy) || 1;
      var force = dist * 0.01;
      e.source.vx += force * dx / dist;
      e.source.vy += force * dy / dist;
      e.target.vx -= force * dx / dist;
      e.target.vy -= force * dy / dist;
    });
    // Center gravity
    nodes.forEach(function(n) {
      n.vx += (width / 2 - n.x) * 0.001;
      n.vy += (height / 2 - n.y) * 0.001;
      n.x += n.vx;
      n.y += n.vy;
      n.vx *= 0.9;
      n.vy *= 0.9;
    });
  }

  // Colors by type
  var colors = {
    file: '#4A6FA5',
    character: '#5B8C6E',
    theme: '#B8956A'
  };

  // Draw edges
  edges.forEach(function(e) {
    var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', e.source.x);
    line.setAttribute('y1', e.source.y);
    line.setAttribute('x2', e.target.x);
    line.setAttribute('y2', e.target.y);
    line.setAttribute('stroke', '#D1D9E3');
    line.setAttribute('stroke-width', '1');
    svg.appendChild(line);
  });

  // Draw nodes
  nodes.forEach(function(n) {
    var circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', n.x);
    circle.setAttribute('cy', n.y);
    circle.setAttribute('r', n.type === 'file' ? 8 : 5);
    circle.setAttribute('fill', colors[n.type] || '#4A6FA5');
    circle.setAttribute('opacity', '0.8');
    svg.appendChild(circle);

    var text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', n.x + 10);
    text.setAttribute('y', n.y + 4);
    text.setAttribute('font-size', '10');
    text.setAttribute('fill', '#1A2332');
    text.textContent = n.id.length > 20 ? n.id.substring(0, 17) + '...' : n.id;
    svg.appendChild(text);
  });
}
"""
