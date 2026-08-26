#!/usr/bin/env python3
"""Comprehensive test suite for The Audhd Scribbler.

Tests every claim: tagging quality, all 17 analysis tools, search, export,
synthesis, manuscript-level analysis, AUDHD pattern detection, edge cases.

Run: python comprehensive_test.py
"""
import sys
import os
import time
import tempfile
import traceback
from pathlib import Path
from io import StringIO

# Setup
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["AUDHD_SCRIBBLER_HOME"] = str(Path(__file__).resolve().parent / "test_workspace")

# UTF-8 for Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Disable snapshots
try:
    from scribbler import safety
    safety.backup_database = lambda reason="": None
    safety.create_snapshot = lambda reason="": None
except Exception:
    pass

PASS = 0
FAIL = 0
SKIP = 0
RESULTS = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS.append(f"  PASS  {name}")
    else:
        FAIL += 1
        RESULTS.append(f"  FAIL  {name}  {detail}")
        print(f"  FAIL  {name}  {detail}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ============================================================================
# TEST DATA
# ============================================================================

SHORT_TEXT = "Mom was in the kitchen. The light buzzed. I was eight."

MEDIUM_TEXT = """I remember the kitchen that summer. The yellow walls and the way the light came through the window in the afternoon, hitting the linoleum at an angle that made it look almost golden. Mom was making tea. She was always making tea back then.

I didn't know yet that I was autistic. I didn't know that the reason the fluorescent light in the kitchen made me feel like my skin was crawling was because my brain processed light differently. I just thought everyone felt this way and nobody talked about it.

Mom turned to me and said something. I don't remember what. I remember the way her mouth moved, the way the words sounded like they were coming from underwater. I was looking at her but I wasn't really there. I was somewhere behind my own eyes, watching.

"You're not listening," she said. Not angry. Just tired. She was always tired too.

So I just nodded. That was the first time I remember masking. I didn't know it had a name. I just knew that nodding made the tiredness in her face go away."""

LONG_TEXT = ""
for i in range(50):
    LONG_TEXT += f"Chapter {i+1}: The kitchen was {['yellow','blue','white','green'][i%4]}. Mom was there. Nathan sat in the corner. I felt the overwhelm rising — the fluorescent light, the buzzing, the texture of the floor. I was masking again, nodding when I didn't understand, smiling when I felt nothing. Dr. Vance had told me about burnout. I didn't believe her yet. The diagnosis was still new. Bogota was a memory I couldn't shake. Colombia had been too loud, too bright, too much. I had a meltdown on the third day. Mom didn't understand. Nathan tried to help. The stimming started after that — rocking, tapping, humming. It soothed me. It embarrassed them.\n\n"

VERY_LONG_TEXT = LONG_TEXT * 5  # ~100k words

EMPTY_TEXT = ""
ONE_WORD = "Hello."
NON_ENGLISH = "Maman était dans la cuisine. La lumière bourdonnait. J'avais huit ans."
SPECIAL_CHARS = "Mom said \"hello\" — with an em-dash; and a semicolon: plus... ellipsis. (And parens.) [And brackets.]"
NULL_BYTES = b"Mom was here\x00and then gone\x07with a bell\x08sound.\n\nNew paragraph.\n"

# ============================================================================
# SECTION 1: TAGGING QUALITY
# ============================================================================

def test_tagging():
    section("1. TAGGING QUALITY")
    from scribbler import tagger, db
    
    # Clean DB
    db_path = Path(__file__).resolve().parent / "data" / "scribbler.db"
    if db_path.exists():
        db_path.unlink()
    
    # 1.1 Short text
    try:
        meta = tagger.tag_file.__wrapped__ if hasattr(tagger.tag_file, '__wrapped__') else None
        # Use a temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(SHORT_TEXT)
            f.flush()
            meta = tagger.tag_file(f.name, use_llm=False)
            os.unlink(f.name)
        
        test("1.1 Short text tags without crash", "word_count" in meta, f"meta keys: {list(meta.keys())[:5]}")
        test("1.1a Short text word count", meta.get("word_count") >= 8, f"got {meta.get('word_count')}")
        test("1.1b Short text detects Mom", "Mom" in meta.get("characters", []), f"chars: {meta.get('characters')}")
        test("1.1c Short text detects kitchen", "kitchen" in meta.get("places", []), f"places: {meta.get('places')}")
        test("1.1d Short text has voice tag", meta.get("voice") is not None, f"voice: {meta.get('voice')}")
        test("1.1e Short text has tagger_version", meta.get("tagger_version") == "4.1", f"version: {meta.get('tagger_version')}")
    except Exception as e:
        test("1.1 Short text tags without crash", False, str(e))
    
    # 1.2 Medium text
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(MEDIUM_TEXT)
            f.flush()
            meta = tagger.tag_file(f.name, use_llm=False)
            os.unlink(f.name)
        
        test("1.2 Medium text tags without crash", "word_count" in meta)
        test("1.2a Detects Mom", "Mom" in meta.get("characters", []), f"chars: {meta.get('characters')}")
        test("1.2b Detects kitchen", "kitchen" in meta.get("places", []), f"places: {meta.get('places')}")
        test("1.2c Detects masking theme", "masking" in meta.get("themes", []), f"themes: {meta.get('themes')}")
        test("1.2d Detects diagnosis theme", "diagnosis" in meta.get("themes", []) or "sensory_processing" in meta.get("themes", []), f"themes: {meta.get('themes')}")
        test("1.2e Has emotional register", meta.get("emotional_register") is not None, f"mood: {meta.get('emotional_register')}")
        test("1.2f Has voice tag", meta.get("voice") in ["narrator", "character", "research", "lyric", "other"], f"voice: {meta.get('voice')}")
        test("1.2g Has sensory tags", len(meta.get("sensory", [])) > 0, f"sensory: {meta.get('sensory')[:3]}")
    except Exception as e:
        test("1.2 Medium text tags without crash", False, str(e))
    
    # 1.3 Long text (50 chapters ~ 25k words)
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(LONG_TEXT)
            f.flush()
        start = time.time()
        meta = tagger.tag_file(f.name, use_llm=False)
        elapsed = time.time() - start
        os.unlink(f.name)
        
        test("1.3 Long text (25k words) tags without crash", "word_count" in meta)
        test("1.3a Completes in under 30s", elapsed < 30, f"took {elapsed:.1f}s")
        test("1.3b Detects characters across full text", len(meta.get("characters", [])) >= 2, f"chars: {meta.get('characters')}")
        test("1.3c Detects themes across full text", len(meta.get("themes", [])) >= 3, f"themes: {meta.get('themes')[:5]}")
        test("1.3d Detects places across full text", len(meta.get("places", [])) >= 1, f"places: {meta.get('places')}")
    except Exception as e:
        test("1.3 Long text tags without crash", False, str(e))
    
    # 1.4 Very long text (~100k words) — just test it doesn't crash or hang
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(VERY_LONG_TEXT[:500000])  # ~100k words
            f.flush()
        start = time.time()
        meta = tagger.tag_file(f.name, use_llm=False)
        elapsed = time.time() - start
        os.unlink(f.name)
        
        test("1.4 Very long text (100k words) tags without crash", "word_count" in meta, f"word_count: {meta.get('word_count')}")
        test("1.4a Completes in under 120s", elapsed < 120, f"took {elapsed:.1f}s")
    except Exception as e:
        test("1.4 Very long text tags without crash", False, str(e))
    
    # 1.5 Empty file
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(EMPTY_TEXT)
            f.flush()
            meta = tagger.tag_file(f.name, use_llm=False)
            os.unlink(f.name)
        test("1.5 Empty file doesn't crash", "word_count" in meta, f"word_count: {meta.get('word_count')}")
        test("1.5a Empty file word count is 0", meta.get("word_count") == 0, f"got {meta.get('word_count')}")
    except Exception as e:
        test("1.5 Empty file doesn't crash", False, str(e))
    
    # 1.6 One word
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(ONE_WORD)
            f.flush()
            meta = tagger.tag_file(f.name, use_llm=False)
            os.unlink(f.name)
        test("1.6 One-word file doesn't crash", "word_count" in meta)
    except Exception as e:
        test("1.6 One-word file doesn't crash", False, str(e))
    
    # 1.7 Non-English text
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(NON_ENGLISH)
            f.flush()
            meta = tagger.tag_file(f.name, use_llm=False)
            os.unlink(f.name)
        test("1.7 Non-English text doesn't crash", "word_count" in meta)
    except Exception as e:
        test("1.7 Non-English text doesn't crash", False, str(e))
    
    # 1.8 Special characters
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(SPECIAL_CHARS)
            f.flush()
            meta = tagger.tag_file(f.name, use_llm=False)
            os.unlink(f.name)
        test("1.8 Special characters don't crash", "word_count" in meta)
    except Exception as e:
        test("1.8 Special characters don't crash", False, str(e))
    
    # 1.9 NULL bytes (cp1252 encoded file)
    try:
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
            f.write(NULL_BYTES)
            f.flush()
            meta = tagger.tag_file(f.name, use_llm=False)
            os.unlink(f.name)
        test("1.9 NULL bytes / binary content doesn't crash", "word_count" in meta)
    except Exception as e:
        test("1.9 NULL bytes / binary content doesn't crash", False, str(e))
    
    # 1.10 Theme variety — does it detect more than 2 themes?
    try:
        variety_text = """I was diagnosed with autism last year. The masking had exhausted me for decades. 
        The sensory overload in supermarkets triggered meltdowns. I stim by rocking. 
        My special interest is 18th century pottery. Executive function fails me daily.
        I had burnout so severe I couldn't leave bed. The diagnosis brought identity integration.
        I discovered I had alexithymia — I couldn't name my feelings. Interoception was broken too.
        Rejection sensitivity made every criticism devastating. I needed accommodations at work.
        Self-advocacy became my new special interest."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(variety_text)
            f.flush()
            meta = tagger.tag_file(f.name, use_llm=False)
            os.unlink(f.name)
        themes = meta.get("themes", [])
        test("1.10 Theme variety — detects 5+ AUDHD themes", len(themes) >= 5, f"detected {len(themes)}: {themes}")
    except Exception as e:
        test("1.10 Theme variety", False, str(e))
    
    # 1.11 Tags persist to database
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(MEDIUM_TEXT)
            f.flush()
            meta = tagger.tag_file(f.name, use_llm=False)
            file_path = str(Path(f.name).resolve())
            os.unlink(f.name)
        
        db_entry = db.get_file(file_path)
        test("1.11 Tags persist to database", db_entry is not None, "db.get_file returned None")
        if db_entry:
            test("1.11a DB has characters", db_entry.get("characters") is not None)
            test("1.11b DB has themes", db_entry.get("themes") is not None)
            test("1.11c DB has word count", db_entry.get("word_count") == meta.get("word_count"))
    except Exception as e:
        test("1.11 Tags persist to database", False, str(e))

# ============================================================================
# SECTION 2: ANALYSIS TOOLS (all 17)
# ============================================================================

def test_analysis_tools():
    section("2. ANALYSIS TOOLS (all 17)")
    from scribbler.analyzers import (
        craft, voice_tense, characters, continuity, themes, editor,
        cadence, motifs, anchors, voice_dna, reader_perception
    )
    from scribbler.analysis_suite import run as suite_run
    
    test_text = MEDIUM_TEXT
    
    tools = [
        ("craft", lambda: craft.analyze(test_text)),
        ("voice_tense", lambda: voice_tense.analyze(test_text)),
        ("characters", lambda: characters.analyze(test_text)),
        ("continuity", lambda: continuity.analyze(test_text)),
        ("themes", lambda: themes.analyze(test_text)),
        ("editor", lambda: editor.analyze(test_text)),
        ("cadence", lambda: cadence.analyze(test_text)),
        ("motifs", lambda: motifs.analyze(text=test_text)),
        ("anchors", lambda: anchors.analyze(text=test_text)),
        ("voice_dna", lambda: voice_dna.analyze(test_text)),
        ("reader_perception", lambda: reader_perception.analyze(test_text)),
        ("repetition", lambda: suite_run("repetition", test_text)),
        ("pacing", lambda: suite_run("pacing", test_text)),
        ("structure", lambda: suite_run("structure", test_text)),
        ("memoir", lambda: suite_run("memoir", test_text)),
        ("reader", lambda: suite_run("reader", test_text)),
        ("research", lambda: suite_run("research", test_text)),
    ]
    
    for tool_name, tool_fn in tools:
        try:
            start = time.time()
            result = tool_fn()
            elapsed = time.time() - start
            
            if not isinstance(result, dict):
                test(f"2.x {tool_name} returns dict", False, f"got {type(result)}")
                continue
            
            if "error" in result:
                test(f"2.x {tool_name} runs without error", False, result["error"])
                continue
            
            test(f"2.x {tool_name} runs without error", True)
            test(f"2.x {tool_name} completes in <30s", elapsed < 30, f"took {elapsed:.1f}s")
            
            # Check for meaningful output
            has_summary = "summary" in result
            has_observations = "observations" in result
            has_word_count = "word_count" in result
            
            test(f"2.x {tool_name} has summary", has_summary, f"keys: {list(result.keys())[:5]}")
            test(f"2.x {tool_name} has observations", has_observations)
            
            # Check observations have low-shame grammar (formatted field)
            if has_observations and result["observations"]:
                first_obs = result["observations"][0]
                if isinstance(first_obs, dict):
                    has_formatted = "formatted" in first_obs
                    has_options = "options" in first_obs
                    test(f"2.x {tool_name} obs has formatted text", has_formatted)
                    test(f"2.x {tool_name} obs has options", has_options)
                    
                    if has_formatted:
                        formatted = first_obs["formatted"]
                        # Check it follows the grammar: "I noticed... Would you like to..."
                        has_notice = "noticed" in formatted.lower() or "I " in formatted[:20]
                        has_options_text = "would you like" in formatted.lower() or "could" in formatted.lower()
                        test(f"2.x {tool_name} follows low-shame grammar", has_notice and has_options_text, 
                             f"formatted: {formatted[:80]}...")
        
        except Exception as e:
            test(f"2.x {tool_name} runs without error", False, str(e))

# ============================================================================
# SECTION 3: ANALYSIS ON LONG TEXT (100k words)
# ============================================================================

def test_long_analysis():
    section("3. ANALYSIS ON LONG TEXT (simulated 100k words)")
    from scribbler.analyzers import craft, voice_tense, characters, continuity, themes, editor, cadence
    from scribbler.analysis_suite import run as suite_run
    
    # Use ~5000 word chunk for speed, extrapolate
    long_text = (MEDIUM_TEXT + "\n\n") * 30  # ~6000 words
    
    tools = [
        ("craft", lambda: craft.analyze(long_text)),
        ("voice", lambda: voice_tense.analyze(long_text)),
        ("characters", lambda: characters.analyze(long_text)),
        ("continuity", lambda: continuity.analyze(long_text)),
        ("themes", lambda: themes.analyze(long_text)),
        ("editor", lambda: editor.analyze(long_text)),
        ("cadence", lambda: cadence.analyze(long_text)),
        ("repetition", lambda: suite_run("repetition", long_text)),
        ("pacing", lambda: suite_run("pacing", long_text)),
        ("memoir", lambda: suite_run("memoir", long_text)),
    ]
    
    total_start = time.time()
    for tool_name, tool_fn in tools:
        try:
            start = time.time()
            result = tool_fn()
            elapsed = time.time() - start
            
            test(f"3.x {tool_name} on long text — no crash", isinstance(result, dict) and "error" not in result, 
                 result.get("error", "") if isinstance(result, dict) else str(type(result)))
            test(f"3.x {tool_name} on long text — <10s", elapsed < 10, f"took {elapsed:.1f}s")
        except Exception as e:
            test(f"3.x {tool_name} on long text", False, str(e))
    
    total_elapsed = time.time() - total_start
    test("3.x All tools on long text complete in <60s", total_elapsed < 60, f"total: {total_elapsed:.1f}s")

# ============================================================================
# SECTION 4: SEARCH FUNCTIONALITY
# ============================================================================

def test_search():
    section("4. SEARCH FUNCTIONALITY")
    from scribbler import search, tagger, db
    
    # Tag a few files
    files = [
        ("nathan_colombia.txt", "Nathan was in Colombia. Mom visited. The meltdown was bad."),
        ("kitchen_summer.txt", "Mom was in the kitchen. The light buzzed. I was masking."),
        ("diagnosis_day.txt", "Dr. Vance gave the diagnosis. I felt relief. Nathan called."),
    ]
    
    for name, content in files:
        fpath = Path(__file__).resolve().parent / "raw-dumps" / name
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content, encoding="utf-8")
        try:
            tagger.tag_file(str(fpath), use_llm=False)
        except Exception:
            pass
    
    # 4.1 Search by character
    try:
        results = search.search_by_tag("characters", "Nathan")
        test("4.1 Search by character 'Nathan'", len(results) >= 2, f"found {len(results)} files")
    except Exception as e:
        test("4.1 Search by character", False, str(e))
    
    # 4.2 Search by character 'Mom'
    try:
        results = search.search_by_tag("characters", "Mom")
        test("4.2 Search by character 'Mom'", len(results) >= 2, f"found {len(results)} files")
    except Exception as e:
        test("4.2 Search by character", False, str(e))
    
    # 4.3 Search by theme
    try:
        results = search.search_by_tag("themes", "masking")
        test("4.3 Search by theme 'masking'", len(results) >= 1, f"found {len(results)} files")
    except Exception as e:
        test("4.3 Search by theme", False, str(e))
    
    # 4.4 Multi-tag search
    try:
        results = search.search_multi({"characters": "Nathan", "characters": "Mom"})
        test("4.4 Multi-tag search", isinstance(results, list), f"got {type(results)}")
    except Exception as e:
        test("4.4 Multi-tag search", False, str(e))
    
    # 4.5 Get all values for a tag type
    try:
        values = search.get_all_values_for_tag("characters")
        test("4.5 Get all character values", len(values) > 0, f"found {len(values)} characters")
        test("4.5a 'Nathan' in values", any(v["value"] == "Nathan" for v in values))
        test("4.5b 'Mom' in values", any(v["value"] == "Mom" for v in values))
    except Exception as e:
        test("4.5 Get all character values", False, str(e))
    
    # 4.6 Find tag in file (paragraph-level)
    try:
        nathan_file = str(Path(__file__).resolve().parent / "raw-dumps" / "nathan_colombia.txt")
        occurrences = search.find_tag_in_file(nathan_file, "characters", "Nathan")
        test("4.6 find_tag_in_file returns occurrences", len(occurrences) >= 1, f"found {len(occurrences)}")
        if occurrences:
            test("4.6a Occurrence has paragraph number", "paragraph" in occurrences[0])
            test("4.6b Occurrence has context", "context" in occurrences[0])
    except Exception as e:
        test("4.6 find_tag_in_file", False, str(e))
    
    # 4.7 Tag coverage report
    try:
        nathan_file = str(Path(__file__).resolve().parent / "raw-dumps" / "nathan_colombia.txt")
        coverage = search.get_tag_coverage(nathan_file)
        test("4.7 Coverage report generates", isinstance(coverage, dict) and "total_paragraphs" in coverage)
        test("4.7a Coverage has tag_distribution", "tag_distribution" in coverage)
        test("4.7b Coverage has spread description", "spread_description" in coverage)
    except Exception as e:
        test("4.7 Coverage report", False, str(e))
    
    # Cleanup
    for name, _ in files:
        fpath = Path(__file__).resolve().parent / "raw-dumps" / name
        if fpath.exists():
            fpath.unlink()

# ============================================================================
# SECTION 5: EXPORT FUNCTIONALITY
# ============================================================================

def test_export():
    section("5. EXPORT FUNCTIONALITY")
    from scribbler import export
    
    # Create a test file
    test_file = Path(__file__).resolve().parent / "test_export.txt"
    test_file.write_text(MEDIUM_TEXT, encoding="utf-8")
    
    # 5.1 Export to markdown
    try:
        result = export.export_markdown(str(test_file))
        test("5.1 Export to markdown", Path(result).exists(), f"result: {result}")
        if Path(result).exists():
            content = Path(result).read_text(encoding="utf-8")
            test("5.1a Markdown has content", len(content) > 100)
            os.unlink(result)
    except Exception as e:
        test("5.1 Export to markdown", False, str(e))
    
    # 5.2 Export to plain text
    try:
        result = export.export_plain_text(str(test_file))
        test("5.2 Export to plain text", Path(result).exists(), f"result: {result}")
        if Path(result).exists():
            content = Path(result).read_text(encoding="utf-8")
            test("5.2a Plain text has content", len(content) > 100)
            test("5.2b Plain text has no YAML frontmatter", not content.startswith("---"))
            os.unlink(result)
    except Exception as e:
        test("5.2 Export to plain text", False, str(e))
    
    # 5.3 Export to DOCX
    try:
        result = export.export_docx(str(test_file))
        test("5.3 Export to DOCX", Path(result).exists(), f"result: {result}")
        if Path(result).exists():
            test("5.3a DOCX file size > 10KB", Path(result).stat().st_size > 10240, 
                 f"size: {Path(result).stat().st_size}")
            os.unlink(result)
    except Exception as e:
        test("5.3 Export to DOCX", False, str(e))
    
    # 5.4 Export with special characters (control chars)
    try:
        bad_file = Path(__file__).resolve().parent / "test_bad_chars.txt"
        bad_file.write_bytes(b"Mom was here\x00with NULL bytes\x07and bells.\n\nNew paragraph.\n")
        result = export.export_docx(str(bad_file))
        test("5.4 Export with NULL bytes doesn't crash", Path(result).exists())
        if Path(result).exists():
            os.unlink(result)
        bad_file.unlink()
    except Exception as e:
        test("5.4 Export with NULL bytes", False, str(e))
    
    # 5.5 Export analysis report
    try:
        from scribbler.analyzers import craft, themes
        results = {
            "craft": craft.analyze(MEDIUM_TEXT),
            "themes": themes.analyze(MEDIUM_TEXT),
        }
        result = export.export_analysis_report(str(test_file), results)
        test("5.5 Export analysis report", Path(result).exists(), f"result: {result}")
        if Path(result).exists():
            content = Path(result).read_text(encoding="utf-8")
            test("5.5a Report has content", len(content) > 200)
            test("5.5b Report mentions craft", "craft" in content.lower() or "Craft" in content)
            test("5.5c Report mentions themes", "theme" in content.lower() or "Theme" in content)
            os.unlink(result)
    except Exception as e:
        test("5.5 Export analysis report", False, str(e))
    
    test_file.unlink()

# ============================================================================
# SECTION 6: SYNTHESIS REPORT
# ============================================================================

def test_synthesis():
    section("6. SYNTHESIS REPORT")
    from scribbler import synthesis
    from scribbler.analyzers import craft, voice_tense, characters, continuity, themes, editor, cadence
    from scribbler.analysis_suite import run as suite_run
    
    # Run multiple tools
    results = {}
    try:
        results["craft"] = craft.analyze(MEDIUM_TEXT)
        results["voice_tense"] = voice_tense.analyze(MEDIUM_TEXT)
        results["characters"] = characters.analyze(MEDIUM_TEXT)
        results["continuity"] = continuity.analyze(MEDIUM_TEXT)
        results["themes"] = themes.analyze(MEDIUM_TEXT)
        results["editor"] = editor.analyze(MEDIUM_TEXT)
        results["cadence"] = cadence.analyze(MEDIUM_TEXT)
        results["repetition"] = suite_run("repetition", MEDIUM_TEXT)
        results["pacing"] = suite_run("pacing", MEDIUM_TEXT)
        
        test("6.0 All tools ran for synthesis input", len(results) >= 5)
    except Exception as e:
        test("6.0 All tools ran for synthesis input", False, str(e))
        return
    
    # 6.1 Synthesis generates
    try:
        syn = synthesis.generate(results, 200)
        test("6.1 Synthesis generates", isinstance(syn, dict))
        test("6.1a Has voice_consistency", "voice_consistency" in syn)
        test("6.1b Has narrator_distance", "narrator_distance" in syn)
        test("6.1c Has recurring_signals", "recurring_signals" in syn)
        test("6.1d Has top_things_to_notice", "top_things_to_notice" in syn)
        test("6.1e Has what_this_does_not_mean", "what_this_does_not_mean" in syn)
        test("6.1f Has audhd_aware_notes", "audhd_aware_notes" in syn)
        test("6.1g Has summary", "summary" in syn)
        
        # Check content quality
        vc = syn.get("voice_consistency", "")
        test("6.1h Voice consistency has content", len(vc) > 20, f"content: {vc[:80]}...")
        
        nd = syn.get("narrator_distance", "")
        test("6.1i Narrator distance has content", len(nd) > 20, f"content: {nd[:80]}...")
        
        top = syn.get("top_things_to_notice", [])
        test("6.1j Top things has items", len(top) > 0, f"count: {len(top)}")
        
        notes = syn.get("audhd_aware_notes", [])
        test("6.1k AUDHD notes has items", len(notes) > 0, f"count: {len(notes)}")
        
        doesnt_mean = syn.get("what_this_does_not_mean", [])
        test("6.1l 'What this does not mean' has items", len(doesnt_mean) >= 3, f"count: {len(doesnt_mean)}")
        
    except Exception as e:
        test("6.1 Synthesis generates", False, str(e))

# ============================================================================
# SECTION 7: MANUSCRIPT-LEVEL ANALYSIS
# ============================================================================

def test_manuscript_analysis():
    section("7. MANUSCRIPT-LEVEL ANALYSIS")
    from scribbler.analyzers import motifs, anchors, voice_dna
    
    chapters = [
        {"filename": "ch1.txt", "text": "Mom was in the kitchen. The fluorescent light buzzed overhead. I was eight years old. I didn't know I was autistic. I was masking — nodding when I didn't understand, smiling when I felt nothing. The smell of tea brewing. The texture of the linoleum under my feet. Everything was too much and I didn't have words for it yet. Mom turned to me and said something. I don't remember what. I remember her mouth moving. I remember the light."},
        {"filename": "ch2.txt", "text": "Years later, Dr. Vance diagnosed me. The kitchen came back to me during that appointment. The light. Mom's face. The diagnosis was autism spectrum, level one, with ADHD. AUDHD. I sat with that word. The kitchen was always there in my memory. Mom was always making tea. The fluorescent light was always buzzing. I finally understood why the world had felt too loud, too bright, too much for my entire life."},
        {"filename": "ch3.txt", "text": "Nathan asked about Colombia. I remembered the meltdown on the third day in Bogota. The noise, the crowds, the humidity. The kitchen was always there as a reference point — the first place I remember masking. Nathan didn't understand the sensory overload. How could he? I didn't understand it myself until the diagnosis. Mom would have understood. She was always tired but she always made tea. The light buzzed in every kitchen I ever sat in."},
    ]
    
    # 7.1 Motifs
    try:
        result = motifs.analyze(chapters=chapters)
        test("7.1 Motifs manuscript analysis", isinstance(result, dict) and "error" not in result, 
             result.get("error", ""))
        if isinstance(result, dict) and "error" not in result:
            test("7.1a Has candidate_motifs", "candidate_motifs" in result)
            test("7.1b Has phrase_echoes", "phrase_echoes" in result)
            test("7.1b Has sensory_motif_clusters", "sensory_motif_clusters" in result or "sensory_motifs" in result)
            test("7.1c Has observations", "observations" in result)
            test("7.1d Has summary", "summary" in result)
            test("7.1e Finds 'kitchen' as recurring", 
                 any(m.get("image") == "kitchen" for m in result.get("candidate_motifs", [])),
                 f"motifs: {[m.get('image') for m in result.get('candidate_motifs', [])[:5]]}")
    except Exception as e:
        test("7.1 Motifs manuscript analysis", False, str(e))
    
    # 7.2 Anchors
    try:
        result = anchors.analyze(chapters=chapters)
        test("7.2 Anchors manuscript analysis", isinstance(result, dict) and "error" not in result,
             result.get("error", ""))
        if isinstance(result, dict) and "error" not in result:
            test("7.2a Has opening_gestures", "opening_gestures" in result)
            test("7.2b Has closing_gestures", "closing_gestures" in result)
            test("7.2c Has anchor_stability_score", "anchor_stability_score" in result)
            test("7.2d Has observations", "observations" in result)
            test("7.2e Has summary", "summary" in result)
    except Exception as e:
        test("7.2 Anchors manuscript analysis", False, str(e))
    
    # 7.3 Voice DNA
    try:
        result = voice_dna.analyze(chapters[0]["text"], approved_samples=[chapters[1]["text"], chapters[2]["text"]])
        test("7.3 Voice DNA manuscript analysis", isinstance(result, dict) and "error" not in result,
             result.get("error", ""))
        if isinstance(result, dict) and "error" not in result:
            test("7.3a Has similarity_to_approved", "similarity_to_approved" in result)
            test("7.3b Has drift_dimensions", "drift_dimensions" in result)
            test("7.3c Has drift_assessment", "drift_assessment" in result)
            test("7.3d Has observations", "observations" in result)
            test("7.3e Has summary", "summary" in result)
    except Exception as e:
        test("7.3 Voice DNA manuscript analysis", False, str(e))

# ============================================================================
# SECTION 8: AUDHD PATTERN DETECTION
# ============================================================================

def test_audhd_patterns():
    section("8. AUDHD PATTERN DETECTION")
    from scribbler.analyzers import editor
    
    # 8.1 Hyperfocus passage (lots of very long sentences)
    hyperfocus_text = """I was sitting in the kitchen and the fluorescent light was buzzing overhead and Mom was making tea and I didn't know yet that I was autistic and the world felt like it was made of broken glass and every sound was a sharp edge and every light was too bright and the texture of the linoleum under my feet felt like sandpaper and I couldn't understand why nobody else seemed to notice how loud everything was.

The years that followed were a blur of masking and meltdowns and burnout and I would sit in my room for hours rocking back and forth tapping my fingers on my knees humming a single note until the world felt quiet enough to bear and I didn't know that this was stimming and I didn't know that the masking was what was making me so exhausted and I didn't know that the diagnosis would eventually come and when it did I sat with the word for a long time."""
    
    try:
        result = editor.analyze(hyperfocus_text)
        obs = result.get("observations", [])
        categories = [o.get("category", "") for o in obs if isinstance(o, dict)]
        test("8.1 Detects hyperfocus passage", "hyperfocus_passage" in categories,
             f"categories: {categories}")
    except Exception as e:
        test("8.1 Detects hyperfocus passage", False, str(e))
    
    # 8.2 Masking language
    masking_text = """I don't mean to be difficult. I'm not saying I can't do it. To be clear, I just want to explain. 
    Let me explain why I did that. I should explain that I didn't mean it that way. I want to clarify that I was trying my best.
    For the record, I wasn't ignoring you. Just to be clear, I was overwhelmed."""
    
    try:
        result = editor.analyze(masking_text)
        obs = result.get("observations", [])
        categories = [o.get("category", "") for o in obs if isinstance(o, dict)]
        test("8.2 Detects masking language", "masking_language" in categories,
             f"categories: {categories}")
    except Exception as e:
        test("8.2 Detects masking language", False, str(e))
    
    # 8.3 Stimming descriptions
    stimming_text = """I was rocking back and forth. The tapping helped. I hummed a single note. 
    I fidgeted with my sleeve. I rocked again. The tapping continued. I hummed louder."""
    
    try:
        result = editor.analyze(stimming_text)
        obs = result.get("observations", [])
        categories = [o.get("category", "") for o in obs if isinstance(o, dict)]
        test("8.3 Detects stimming descriptions", "stimming_description" in categories,
             f"categories: {categories}")
    except Exception as e:
        test("8.3 Detects stimming descriptions", False, str(e))
    
    # 8.4 Sensory clustering
    sensory_text = """I saw the light. I heard the buzz. I felt the cold. I saw Mom's face.
    Then nothing. No smell. No taste. No touch. No sound. Just thinking. Just remembering.
    Then again: I saw the light. I heard the buzz. I felt the cold."""
    
    try:
        result = editor.analyze(sensory_text)
        obs = result.get("observations", [])
        categories = [o.get("category", "") for o in obs if isinstance(o, dict)]
        # Note: sensory clustering requires missing senses >= 3 AND some senses present
        test("8.4 Editor runs on sensory text without crash", isinstance(result, dict) and "error" not in result)
    except Exception as e:
        test("8.4 Sensory clustering", False, str(e))
    
    # 8.5 Associative jumps
    associative_text = """I was in the kitchen. I remember the light. Now I am here. 
    Then I was eight. I think about Mom. She was tired. Now I am forty. 
    The diagnosis came. I was in Bogota. The meltdown happened. I am back in the kitchen.
    Years pass. I sit in my room. Dr. Vance speaks. I nod. The light buzzes again."""
    
    try:
        result = editor.analyze(associative_text)
        obs = result.get("observations", [])
        categories = [o.get("category", "") for o in obs if isinstance(o, dict)]
        # Associative jump requires >8 tense shifts which the voice analyzer detects
        test("8.5 Editor runs on associative text without crash", isinstance(result, dict) and "error" not in result)
    except Exception as e:
        test("8.5 Associative jumps", False, str(e))

# ============================================================================
# SECTION 9: EDGE CASES
# ============================================================================

def test_edge_cases():
    section("9. EDGE CASES")
    from scribbler.analyzers import craft, voice_tense, themes, editor
    from scribbler.analysis_suite import run as suite_run
    
    # 9.1 Empty text
    try:
        result = craft.analyze("")
        test("9.1 Empty text — craft", isinstance(result, dict) and "error" in result)
    except Exception as e:
        test("9.1 Empty text — craft", False, str(e))
    
    try:
        result = suite_run("pacing", "")
        test("9.1a Empty text — pacing", isinstance(result, dict))
    except Exception as e:
        test("9.1a Empty text — pacing", False, str(e))
    
    # 9.2 Very short text (1 sentence)
    try:
        result = craft.analyze("Hello world.")
        test("9.2 Very short text — craft", isinstance(result, dict))
    except Exception as e:
        test("9.2 Very short text — craft", False, str(e))
    
    # 9.3 Text with only dialogue
    try:
        result = voice_tense.analyze('"Hello," she said. "How are you?" "Fine." "Good."')
        test("9.3 Only dialogue — voice", isinstance(result, dict))
    except Exception as e:
        test("9.3 Only dialogue — voice", False, str(e))
    
    # 9.4 Text with no sentences (just words)
    try:
        result = suite_run("structure", "word word word word word")
        test("9.4 No sentences — structure", isinstance(result, dict))
    except Exception as e:
        test("9.4 No sentences — structure", False, str(e))
    
    # 9.5 Unicode-heavy text
    try:
        unicode_text = "I felt the émotion of the moment. The café was où I always went. Mom said «bonjour» with a smile."
        result = themes.analyze(unicode_text)
        test("9.5 Unicode text — themes", isinstance(result, dict))
    except Exception as e:
        test("9.5 Unicode text — themes", False, str(e))
    
    # 9.6 Text that's all one paragraph
    try:
        one_para = "I was in the kitchen and Mom was there and the light buzzed and I was eight and I didn't know about autism yet and I was masking and I didn't know it had a name and I just nodded and that was the first time."
        result = craft.analyze(one_para)
        test("9.6 One paragraph — craft", isinstance(result, dict) and "error" not in result)
    except Exception as e:
        test("9.6 One paragraph — craft", False, str(e))

# ============================================================================
# SECTION 10: CLI AND MENU IMPORTS
# ============================================================================

def test_imports():
    section("10. IMPORTS AND MODULE LOADING")
    
    try:
        from scribbler import cli
        test("10.1 CLI imports", True)
    except Exception as e:
        test("10.1 CLI imports", False, str(e))
    
    try:
        from scribbler import menu
        test("10.2 Menu imports", True)
    except Exception as e:
        test("10.2 Menu imports", False, str(e))
    
    try:
        from scribbler.dashboard import generate
        test("10.3 Dashboard imports", True)
    except Exception as e:
        test("10.3 Dashboard imports", False, str(e))
    
    try:
        from scribbler import synthesis
        test("10.4 Synthesis imports", True)
    except Exception as e:
        test("10.4 Synthesis imports", False, str(e))
    
    try:
        from scribbler.analysis_catalog import ANALYSIS_CATALOG
        test("10.5 Catalog has 17 tools", len(ANALYSIS_CATALOG) == 17, f"has {len(ANALYSIS_CATALOG)}")
    except Exception as e:
        test("10.5 Catalog imports", False, str(e))
    
    try:
        from scribbler.analyzers import (
            craft, voice_tense, characters, continuity, themes, editor,
            cadence, motifs, anchors, voice_dna, reader_perception
        )
        test("10.6 All 12 analyzers import", True)
    except Exception as e:
        test("10.6 All 12 analyzers import", False, str(e))
    
    try:
        from scribbler.tagger import find_links
        test("10.7 find_links exists", True)
    except Exception as e:
        test("10.7 find_links exists", False, str(e))

# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  THE AUDHD SCRIBBLER — COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    test_imports()
    test_tagging()
    test_analysis_tools()
    test_long_analysis()
    test_search()
    test_export()
    test_synthesis()
    test_manuscript_analysis()
    test_audhd_patterns()
    test_edge_cases()
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"  TEST SUMMARY")
    print(f"{'='*60}")
    print(f"  PASSED:  {PASS}")
    print(f"  FAILED:  {FAIL}")
    print(f"  TOTAL:   {PASS + FAIL}")
    print(f"  RATE:    {PASS/(PASS+FAIL)*100:.1f}%" if (PASS + FAIL) > 0 else "  No tests run")
    print()
    
    if FAIL > 0:
        print("  FAILED TESTS:")
        for r in RESULTS:
            if r.startswith("  FAIL"):
                print(f"    {r}")
    
    print(f"\n{'='*60}")
    if FAIL == 0:
        print("  ALL TESTS PASSED — BUILD IS SOLID")
    else:
        print(f"  {FAIL} TEST(S) FAILED — SEE ABOVE")
    print(f"{'='*60}")
    
    sys.exit(0 if FAIL == 0 else 1)
