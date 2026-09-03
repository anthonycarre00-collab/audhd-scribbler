#!/usr/bin/env python3
"""The Audhd Scribbler v2 — Desktop app entry point.

Creates a pywebview native window with the full UI. No web server, no browser.
Uses html= parameter (not url=) to serve the UI in-memory, bypassing
all file:// security restrictions in WebView2.
"""
import sys
import os

# Ensure the scribbler package is importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Fix Windows Unicode crashes
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, Exception):
    pass

# Disable per-file snapshots (causes "database is locked" and slowdowns)
try:
    from scribbler import safety
    safety.backup_database = lambda reason="": None
    safety.create_snapshot = lambda reason="": None
except Exception:
    pass

import webview
from scribbler.api import Api


def load_html():
    """Load the UI HTML as a string. Works in both dev and frozen exe."""
    if getattr(sys, "frozen", False):
        ui_path = os.path.join(sys._MEIPASS, "assets", "ui", "index.html")
    else:
        ui_path = os.path.join(SCRIPT_DIR, "assets", "ui", "index.html")
    with open(ui_path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    html_string = load_html()
    api = Api()

    window = webview.create_window(
        title="The Audhd Scribbler",
        html=html_string,
        js_api=api,
        width=1200,
        height=800,
        min_size=(900, 600),
        text_select=True,
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
