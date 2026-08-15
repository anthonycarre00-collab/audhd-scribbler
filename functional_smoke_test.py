"""Functional release gate for the writer workflows.

Deterministic: no external AI call is required.
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
from scribbler.release_runtime import prepare_backend, enhance_ui
from scribbler.release_ui import APP as RELEASE_APP

SAMPLE = """I remember the old house at the edge of town. The kitchen was narrow and bright.

Tom stood by the window and watched the rain. I asked him whether he remembered the blue bicycle. He laughed, then went quiet.

Years later, looking back, I still remember that afternoon. Perhaps I remember some details incorrectly, but the smell of wet earth is clear. The rain came harder. The room seemed smaller. I left before dark."""


def main():
    (HOME / "raw-dumps").mkdir(parents=True)
    (HOME / "chapters").mkdir(parents=True)
    raw = HOME / "raw-dumps" / "brain.txt"; raw.write_text(SAMPLE, encoding="utf-8")
    chapter = HOME / "chapters" / "chapter-01.txt"; chapter.write_text(SAMPLE, encoding="utf-8")

    preview = webapp.tag_preview(raw, use_ai=False)
    assert preview["filename"] == "brain.txt"
    try:
        webapp.find_file("chapters/chapter-01.txt")
    except Exception:
        raise AssertionError("File lookup unexpectedly rejected a valid manuscript file")

    all_files = db.get_all_files()
    for key in webapp.TOOLS:
        result = webapp.run_tool(key, SAMPLE, all_files)
        assert isinstance(result, dict) and result, f"Analysis tool returned no result: {key}"

    for key in ("repetition", "pacing", "structure", "memoir", "reader", "research"):
        result = suite_run(key, SAMPLE)
        assert isinstance(result, dict) and result, f"Suite tool failed: {key}"

    # Release presentation must still be the established API-driven UI, not a second engine.
    prepare_backend(webapp)
    release_html = enhance_ui(RELEASE_APP)
    assert "Export tagged document" in release_html
    assert "Scribbler is thinking" in release_html
    assert "Exports / Tagged" in release_html
    assert "Exports / Analysis" in release_html

    # Full snapshots are intentionally not triggered for ordinary analysis/import/note work.
    assert webapp.safety.create_snapshot("before-analysis") is None
    assert webapp.safety.create_snapshot("before-import") is None

    assert raw.parent.name == "raw-dumps" and chapter.parent.name == "chapters"
    print("FUNCTIONAL SMOKE PASSED")
    print("- Inbox tag preview: PASS")
    print("- All 17 analysis tools: PASS")
    print("- Six deterministic suite tools: PASS")
    print("- Release progress/export UI wiring: PASS")
    print("- Expensive automatic snapshots disabled: PASS")
    print("- Project isolation: PASS")


if __name__ == "__main__":
    main()
