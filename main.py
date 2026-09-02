#!/usr/bin/env python3
"""The Audhd Scribbler v2 — Desktop app entry point.

Creates a pywebview native window with the full UI. No web server, no browser.
"""
import sys
import os
import webview

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

from scribbler.api import Api


def main():
    # Resolve UI path (works in both dev and frozen exe)
    if getattr(sys, "frozen", False):
        ui_path = os.path.join(sys._MEIPASS, "assets", "ui", "index.html")
    else:
        ui_path = os.path.join(SCRIPT_DIR, "assets", "ui", "index.html")

    api = Api()

    window = webview.create_window(
        title="The Audhd Scribbler",
        url=ui_path,
        js_api=api,
        width=1200,
        height=800,
        min_size=(900, 600),
        text_select=True,
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
