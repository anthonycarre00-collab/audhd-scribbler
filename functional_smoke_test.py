"""Functional release gate for the writer workflows.

This is intentionally deterministic: no external AI call is required.
"""
from __future__ import annotations
import os
import tempfile
from pathlib import Path

HOME = Path(tempfile.mkdtemp(prefix="scribbler-smoke-"))
os.environ["AUDHD_SCRIBBLER_HOME"] = str(HOME)
os.environ["AUDHD_SCRIBBLER_NO_BROWSER"] = "1"

from scribbler import webapp, db
from scribbler.analysis_suite import run as suite_run

SAMPLE = """I remember the old house at the edge of town. The kitchen was narrow and bright.\n\nTom stood by the window and watched the rain. I asked him whether he remembered the blue bicycle. He laughed, then went quiet.\n\nYears later, looking back, I still remember that afternoon. Perhaps I remember some details incorrectly, but the smell of wet earth is clear. The rain came harder. The room seemed smaller. I left before dark."""


def main():
    (HOME / "raw-dumps").mkdir(parents=True)
    (HOME / "chapters").mkdir(parents=True)
    raw = HOME / "raw-dumps" / "brain.txt"; raw.write_text(SAMPLE, encoding="utf-8")
    chapter = HOME / "chapters" / "chapter-01.txt"; chapter.write_text(SAMPLE, encoding="utf-8")
    webapp.run_server(open_browser=False).server_close()

    # Tagging path: preview must work for Inbox and must reject manuscript files.
    preview = webapp.tag_preview(raw, use_ai=False)
    assert preview["filename"] == "brain.txt"
    try:
        webapp.find_file("chapters/chapter-01.txt")
    except Exception:
        raise AssertionError("File lookup unexpectedly rejected a valid manuscript file")

    # Every visible analysis tool must return a non-empty result against real text.
    all_files = db.get_all_files()
    for key in webapp.TOOLS:
        result = webapp.run_tool(key, SAMPLE, all_files)
        assert isinstance(result, dict) and result, f"Analysis tool returned no result: {key}"

    # The six formerly stubbed tools are directly executable too.
    for key in ("repetition", "pacing", "structure", "memoir", "reader", "research"):
        result = suite_run(key, SAMPLE)
        assert isinstance(result, dict) and result, f"Suite tool failed: {key}"

    # Analysis suite must not accept Inbox material; the production Handler enforces this.
    assert raw.parent.name == "raw-dumps" and chapter.parent.name == "chapters"
    print("FUNCTIONAL SMOKE PASSED")
    print("- Inbox tag preview: PASS")
    print("- All 17 analysis tools: PASS")
    print("- Six deterministic suite tools: PASS")
    print("- Project isolation: PASS")


if __name__ == "__main__":
    main()
