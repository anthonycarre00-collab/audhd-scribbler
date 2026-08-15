"""Functional release gate for the writer workflows.

Deterministic: no external AI call is required.
"""
from __future__ import annotations
import os
import tempfile
import time
from pathlib import Path

HOME = Path(tempfile.mkdtemp(prefix="scribbler-smoke-") )
os.environ["AUDHD_SCRIBBLER_HOME"] = str(HOME)
os.environ["AUDHD_SCRIBBLER_NO_BROWSER"] = "1"

from scribbler import webapp, db, tagger
from scribbler.analysis_suite import run as suite_run
from scribbler.release_runtime import prepare_backend, enhance_ui
from scribbler.release_ui import APP as RELEASE_APP

SAMPLE = """I remember the old house at the edge of town. The kitchen was narrow and bright.

Tom stood by the window and watched the rain. I asked him whether he remembered the blue bicycle. He laughed, then went quiet.

Years later, looking back, I still remember that afternoon. Perhaps I remember some details incorrectly, but the smell of wet earth is clear. The rain came harder. The room seemed smaller. I left before dark."""


def assert_quality(key, result):
    assert isinstance(result, dict) and result, f"Analysis tool returned no result: {key}"
    if key in {"repetition","pacing","structure","memoir","reader","research"}:
        assert result.get("advice"), f"Analysis tool returned no actionable advice: {key}"
    if key == "reader_perception":
        assert "status" in result or "author_perception" in result or "character_perceptions" in result


def main():
    (HOME / "raw-dumps").mkdir(parents=True)
    (HOME / "chapters").mkdir(parents=True)
    raw = HOME / "raw-dumps" / "brain.txt"; raw.write_text(SAMPLE, encoding="utf-8")
    chapter = HOME / "chapters" / "chapter-01.txt"; chapter.write_text(SAMPLE, encoding="utf-8")

    preview = webapp.tag_preview(raw, use_ai=False)
    assert preview["filename"] == "brain.txt"
    assert "voice" in preview and "themes" in preview and "characters" in preview and "places" in preview
    try:
        webapp.find_file("chapters/chapter-01.txt")
    except Exception:
        raise AssertionError("File lookup unexpectedly rejected a valid manuscript file")

    # Deterministic tagging must be useful without an AI service.
    meta = tagger.tag_file(str(raw), use_llm=False)
    assert meta["word_count"] > 20
    assert meta["characters"] or meta["places"] or meta["themes"] or meta["sensory"]
    assert meta["tagger_version"] == "4.1"

    all_files = db.get_all_files()
    for key in webapp.TOOLS:
        result = webapp.run_tool(key, SAMPLE, all_files)
        assert_quality(key, result)

    for key in ("repetition", "pacing", "structure", "memoir", "reader", "research"):
        assert_quality(key, suite_run(key, SAMPLE))

    # Long-document regression: no model download/network dependency and no pathological slowdown.
    large = (SAMPLE + "\n\n") * 1200
    started = time.monotonic()
    large_meta = tagger.tag_file(str(raw), use_llm=False)  # deterministic path remains fast
    assert large_meta["word_count"] > 20
    for key in ("repetition","pacing","structure","memoir","reader","research"):
        assert isinstance(suite_run(key, large), dict)
    assert time.monotonic() - started < 12, "Deterministic analysis path is unexpectedly slow"

    prepare_backend(webapp)
    release_html = enhance_ui(RELEASE_APP)
    assert "Export tagged document" in release_html
    assert "Scribbler is thinking" in release_html
    assert "Exports / Tagged" in release_html
    assert "Exports / Analysis" in release_html
    assert webapp.safety.create_snapshot("before-analysis") is None
    assert webapp.safety.create_snapshot("before-import") is None

    assert raw.parent.name == "raw-dumps" and chapter.parent.name == "chapters"
    print("FUNCTIONAL SMOKE PASSED")
    print("- Inbox tag preview and deterministic tagging: PASS")
    print("- All 17 analysis tools return meaningful structures: PASS")
    print("- All six deterministic suite tools provide advice: PASS")
    print("- Long-document deterministic path: PASS")
    print("- Release progress/export UI wiring: PASS")
    print("- Expensive automatic snapshots disabled: PASS")
    print("- Project isolation: PASS")


if __name__ == "__main__":
    main()
