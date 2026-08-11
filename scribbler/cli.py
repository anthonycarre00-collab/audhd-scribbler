#!/usr/bin/env python3
"""The Audhd Scribbler — CLI entry point.

Usage:
  scribbler init                          Create folder structure
  scribbler label <file>                  Tag a single file
  scribbler label-all [folder]            Tag all files in a folder (default: raw-dumps)
  scribbler analyze <file>                Run full analysis suite on a file
  scribbler analyze-all                   Run analysis on all final/draft chapters
  scribbler dashboard                     Generate and open the dashboard
  scribbler market [--description TEXT]   Run comp-title research
  scribbler next                          Get 3 suggested next actions
  scribbler export <file> [--format F]    Export to md/txt/docx
  scribbler stats                         Show project statistics
  scribbler links <file>                  Show files that share characters/themes
"""
import sys
import os
import json
import webbrowser
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import click

from .config import PROJECT_ROOT, FOLDERS, STATUSES
from . import tagger
from . import db
from . import export
from . import llm
from .analyzers import craft, voice_tense, characters, continuity, themes, editor, market as market_analyzer
from .dashboard import generate as generate_dashboard


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """The Audhd Scribbler — your memoir's calm companion."""
    pass


@cli.command()
def init():
    """Create the folder structure for your memoir project."""
    click.echo("\n  Creating folder structure...")

    for folder, desc in FOLDERS.items():
        folder_path = PROJECT_ROOT / folder
        folder_path.mkdir(exist_ok=True)
        # Create or update README
        readme = folder_path / "README.md"
        readme.write_text(f"# {folder}/\n\n{desc}\n", encoding="utf-8")
        click.echo(f"  ✓ {folder}/")

    # Create data directory (gitignored)
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "exports").mkdir(exist_ok=True)
    (data_dir / "reports").mkdir(exist_ok=True)
    (data_dir / "dashboard").mkdir(exist_ok=True)

    # Initialize database
    conn = db.get_db()
    conn.close()

    click.echo(f"\n  Project initialized at: {PROJECT_ROOT}")
    click.echo("\n  Next steps:")
    click.echo("  1. Drop text files into raw-dumps/")
    click.echo("  2. Run: scribbler label-all")
    click.echo("  3. Run: scribbler dashboard")
    click.echo()


@cli.command()
@click.argument("file_path")
@click.option("--no-llm", is_flag=True, help="Skip LLM-assisted tagging (rule-based only)")
def label(file_path: str, no_llm: bool):
    """Tag a single file with suggested metadata."""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / file_path

    if not path.exists():
        click.echo(f"  File not found: {path}", err=True)
        sys.exit(1)

    click.echo(f"\n  Tagging: {path.name}")

    use_llm = not no_llm
    if use_llm and not llm.llm_available():
        click.echo("  Note: LLM not available, using rule-based tagging only.")
        click.echo("  (Install z-ai CLI or set SCRIBBLER_LLM_API_KEY for LLM-assisted tagging)")
        use_llm = False

    try:
        meta = tagger.tag_file(str(path), use_llm=use_llm)

        click.echo(f"\n  ✓ Tagged: {path.name}")
        click.echo(f"    Words: {meta['word_count']}")
        click.echo(f"    Status: {meta['status']}")
        if meta.get("era"):
            click.echo(f"    Era: {meta['era']}")
        if meta.get("characters"):
            click.echo(f"    Characters: {', '.join(meta['characters'][:5])}")
        if meta.get("places"):
            click.echo(f"    Places: {', '.join(meta['places'][:5])}")
        if meta.get("themes"):
            click.echo(f"    Themes: {', '.join(meta['themes'][:5])}")
        if meta.get("voice"):
            click.echo(f"    Voice: {meta['voice']}")
        if meta.get("emotional_register"):
            click.echo(f"    Emotional register: {meta['emotional_register']}")
        if meta.get("beats"):
            click.echo(f"    Beats: {len(meta['beats'])} detected")
        if meta.get("summary"):
            click.echo(f"\n    Summary:")
            for line in meta["summary"].split("\n"):
                click.echo(f"      {line}")
        click.echo()
    except Exception as e:
        click.echo(f"  Error tagging file: {e}", err=True)
        sys.exit(1)


@cli.command(name="label-all")
@click.argument("folder", default="raw-dumps")
@click.option("--no-llm", is_flag=True, help="Skip LLM-assisted tagging")
def label_all(folder: str, no_llm: bool):
    """Tag all files in a folder."""
    folder_path = PROJECT_ROOT / folder
    if not folder_path.exists():
        click.echo(f"  Folder not found: {folder_path}", err=True)
        sys.exit(1)

    # Find all text files
    files = []
    for ext in ["*.txt", "*.md", "*.text"]:
        files.extend(folder_path.glob(ext))

    if not files:
        click.echo(f"  No text files found in {folder}/")
        click.echo(f"  Drop .txt or .md files into {folder}/ and try again.")
        return

    click.echo(f"\n  Tagging {len(files)} file(s) in {folder}/...")

    use_llm = not no_llm
    if use_llm and not llm.llm_available():
        click.echo("  Note: LLM not available, using rule-based tagging only.")
        use_llm = False

    success = 0
    errors = 0
    for f in files:
        try:
            click.echo(f"  → {f.name}...", nl=False)
            meta = tagger.tag_file(str(f), use_llm=use_llm)
            click.echo(f" {meta['word_count']} words, {len(meta.get('characters', []))} chars")
            success += 1
        except Exception as e:
            click.echo(f" ERROR: {e}")
            errors += 1

    click.echo(f"\n  ✓ Tagged {success} file(s), {errors} error(s)")
    click.echo(f"  Run 'scribbler dashboard' to see the overview.")
    click.echo()


@cli.command()
@click.argument("file_path")
@click.option("--tool", "-t", multiple=True,
              help="Specific tool(s) to run: craft, voice, characters, continuity, themes, editor")
def analyze(file_path: str, tool):
    """Run analysis suite on a file."""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / file_path

    if not path.exists():
        click.echo(f"  File not found: {path}", err=True)
        sys.exit(1)

    # Read text (strip frontmatter)
    content = path.read_text(encoding="utf-8")
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            text = content[end + 3:].strip()
        else:
            text = content
    else:
        text = content

    import re
    # Strip summary comments
    text = re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->', '', text).strip()

    click.echo(f"\n  Analyzing: {path.name} ({len(text.split())} words)")

    tools_to_run = tool if tool else ["craft", "voice", "characters", "continuity", "themes", "editor"]

    results = {}
    for t in tools_to_run:
        click.echo(f"  → Running {t}...", nl=False)
        try:
            if t == "craft":
                results["craft"] = craft.analyze(text)
            elif t == "voice":
                results["voice_tense"] = voice_tense.analyze(text)
            elif t in ["characters", "character"]:
                results["characters"] = characters.analyze(text)
            elif t == "continuity":
                results["continuity"] = continuity.analyze(text)
            elif t == "themes":
                results["themes"] = themes.analyze(text)
            elif t == "editor":
                results["editor"] = editor.analyze(text)
            else:
                click.echo(f" unknown tool '{t}'")
                continue
            click.echo(" done")
        except Exception as e:
            click.echo(f" error: {e}")
            results[t] = {"error": str(e)}

    # Save to database
    for t, result in results.items():
        db.save_analysis(str(path.resolve()), t, result)

    # Output results
    click.echo(f"\n{'='*60}")
    click.echo(f"  ANALYSIS REPORT: {path.name}")
    click.echo(f"{'='*60}\n")

    for t, result in results.items():
        if "error" in result:
            click.echo(f"\n  [{t.upper()}] Error: {result['error']}")
            continue

        click.echo(f"\n  [{'='*50}]")
        click.echo(f"  [{t.upper()}]")
        click.echo(f"  [{'='*50}]")

        if "summary" in result:
            click.echo(f"\n  {result['summary']}")

        if "strengths" in result:
            click.echo(f"\n  STRENGTHS:")
            for s in result["strengths"]:
                click.echo(f"    • {s}")

        if "observations" in result:
            click.echo(f"\n  OBSERVATIONS ({len(result['observations'])}):")
            for obs in result["observations"]:
                if isinstance(obs, dict):
                    click.echo(f"\n    [{obs.get('category', '').replace('_', ' ').upper()}]")
                    click.echo(f"    {obs.get('formatted', '')}")
                else:
                    click.echo(f"    • {obs}")

        # Print key metrics
        _print_key_metrics(t, result)

    # Export report
    report_path = export.export_analysis_report(str(path), results)
    click.echo(f"\n  Report saved to: {report_path}")
    click.echo()


def _print_key_metrics(tool: str, result: dict):
    """Print key metrics for a tool's results."""
    if tool == "craft":
        rhythm = result.get("sentence_length_rhythm", {})
        if rhythm:
            click.echo(f"\n  KEY METRICS:")
            click.echo(f"    Mean sentence length: {rhythm.get('mean_length', '—')} words")
            click.echo(f"    Rhythm: {rhythm.get('rhythm_assessment', '—')}")
            click.echo(f"    Short sentences: {rhythm.get('short_sentences_pct', '—')}%")
        readability = result.get("readability", {})
        if readability:
            click.echo(f"    Readability band: {readability.get('grade_band', '—')}")
        sensory = result.get("sensory_density", {})
        if sensory:
            click.echo(f"    Sensory density: {sensory.get('per_1000_words', '—')}/1000 words")

    elif tool == "voice_tense":
        tense = result.get("tense_distribution", {})
        if tense:
            click.echo(f"\n  KEY METRICS:")
            click.echo(f"    Dominant tense: {tense.get('dominant_tense', '—')}")
            click.echo(f"    Tense shifts: {len(result.get('tense_shifts', []))}")
        pronouns = result.get("pronoun_density", {})
        if pronouns:
            click.echo(f"    First-person pronouns: {pronouns.get('first_person_total_per_1000', '—')}/1000")
        distance = result.get("narrator_distance", {})
        if distance:
            click.echo(f"    Narrator distance: {distance.get('assessment', '—')}")

    elif tool == "themes":
        theme_d = result.get("theme_density", {})
        if theme_d:
            click.echo(f"\n  KEY METRICS:")
            click.echo(f"    Dominant theme: {theme_d.get('dominant_theme', '—')}")
            click.echo(f"    Themes detected: {theme_d.get('theme_count', 0)}")
        arc = result.get("arc_shape", {})
        if arc:
            click.echo(f"    Arc shape: {arc.get('shape', '—')} ({arc.get('description', '')})")

    elif tool == "continuity":
        timeline = result.get("timeline", {})
        if timeline:
            click.echo(f"\n  KEY METRICS:")
            click.echo(f"    Timeline: {timeline.get('assessment', '—')}")
        anach = result.get("anachronism_flags", [])
        click.echo(f"    Anachronism flags: {len(anach)}")
        claims = result.get("research_claims", [])
        uncited = [c for c in claims if c.get("needs_citation")]
        click.echo(f"    Research claims: {len(claims)} ({len(uncited)} uncited)")


@cli.command(name="analyze-all")
def analyze_all():
    """Run analysis on all chapters in /final and /drafts."""
    chapters = []
    for folder in ["final", "drafts", "chapters"]:
        folder_path = PROJECT_ROOT / folder
        if folder_path.exists():
            for ext in ["*.txt", "*.md"]:
                chapters.extend(folder_path.glob(ext))

    if not chapters:
        click.echo("  No chapters found in /final, /drafts, or /chapters.")
        click.echo("  Move tagged files to /chapters or /drafts first.")
        return

    click.echo(f"\n  Analyzing {len(chapters)} chapter(s)...")
    for ch in chapters:
        click.echo(f"\n  → {ch.name}")
        # Run analysis (simplified — just save, don't print full report)
        content = ch.read_text(encoding="utf-8")
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                text = content[end + 3:].strip()
            else:
                text = content
        else:
            text = content

        import re
        text = re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->', '', text).strip()

        for tool_name, analyzer in [("craft", craft), ("voice_tense", voice_tense),
                                     ("characters", characters), ("continuity", continuity),
                                     ("themes", themes), ("editor", editor)]:
            try:
                result = analyzer.analyze(text)
                db.save_analysis(str(ch.resolve()), tool_name, result)
                click.echo(f"    ✓ {tool_name}")
            except Exception as e:
                click.echo(f"    ✗ {tool_name}: {e}")

    click.echo(f"\n  ✓ All chapters analyzed.")
    click.echo(f"  Run 'scribbler dashboard' to see the overview.")


@cli.command()
@click.option("--open/--no-open", "open_browser", default=True, help="Open in browser")
def dashboard(open_browser: bool):
    """Generate and open the interactive dashboard."""
    click.echo("\n  Generating dashboard...")
    html_path = generate_dashboard()
    click.echo(f"  ✓ Dashboard generated: {html_path}")

    if open_browser:
        click.echo("  Opening in browser...")
        webbrowser.open(f"file://{html_path}")

    click.echo()


@cli.command()
@click.option("--description", "-d", help="Manuscript description (one paragraph)")
def market(description: Optional[str]):
    """Run comp-title research and market positioning."""
    # Gather themes from all analyzed files
    all_files = db.get_all_files()
    all_themes = []
    for f in all_files:
        all_themes.extend(f.get("themes") or [])

    if not description and not all_themes:
        click.echo("  No themes detected yet. Run 'scribbler label-all' first.")
        click.echo("  Or provide a description: scribbler market --description \"your blurb\"")
        return

    click.echo("\n  Running market analysis...")

    result = market_analyzer.analyze(
        manuscript_description=description,
        chapter_themes=list(set(all_themes)),
    )

    click.echo(f"\n{'='*60}")
    click.echo(f"  MARKET & COMP ANALYSIS")
    click.echo(f"{'='*60}\n")

    if result.get("summary"):
        click.echo(f"  {result['summary']}\n")

    positioning = result.get("positioning", {})
    click.echo(f"  POSITIONING:")
    click.echo(f"    Shelf: {positioning.get('shelf', '—')}")
    click.echo(f"    BISAC Primary: {positioning.get('bisac_primary', '—')}")
    click.echo(f"    BISAC Secondary: {positioning.get('bisac_secondary', '—')}")

    if positioning.get("market_gaps"):
        click.echo(f"\n  MARKET OPPORTUNITIES:")
        for gap in positioning["market_gaps"]:
            click.echo(f"    • {gap}")

    comps = result.get("comp_suggestions", [])
    if comps:
        click.echo(f"\n  COMP SUGGESTIONS ({len(comps)} found):")
        for i, comp in enumerate(comps, 1):
            click.echo(f"\n    {i}. '{comp['title']}' by {comp['author']} ({comp['year']})")
            click.echo(f"       Form: {comp.get('form', '—')}")
            click.echo(f"       Themes: {', '.join(comp.get('themes', []))}")
            click.echo(f"       Match: {', '.join(comp.get('match_reasons', []))}")
            if comp.get("flags"):
                for flag in comp["flags"]:
                    click.echo(f"       ⚠ {flag}")

    if result.get("observations"):
        click.echo(f"\n  OBSERVATIONS ({len(result['observations'])}):")
        for obs in result["observations"]:
            if isinstance(obs, dict):
                click.echo(f"\n    [{obs.get('category', '').replace('_', ' ').upper()}]")
                click.echo(f"    {obs.get('formatted', '')}")

    click.echo()


@cli.command(name="next")
def next_action():
    """Get 3 suggested next actions (addresses decision paralysis)."""
    click.echo("\n  Here are 3 things you could do:\n")

    stats = db.get_stats()
    all_files = db.get_all_files()

    suggestions = []

    # Check for untagged raw dumps
    raw_dumps = PROJECT_ROOT / "raw-dumps"
    if raw_dumps.exists():
        untagged = []
        for ext in ["*.txt", "*.md"]:
            for f in raw_dumps.glob(ext):
                # Check if it has frontmatter
                content = f.read_text(encoding="utf-8")[:200]
                if not content.startswith("---"):
                    untagged.append(f)
        if untagged:
            suggestions.append({
                "action": f"Tag {len(untagged)} untagged dump(s) in raw-dumps/",
                "command": "scribbler label-all",
                "why": "You have raw material waiting to be organized. Tagging takes seconds and makes it searchable.",
            })

    # Check for stale drafts
    stale = stats.get("stale_drafts", [])
    if stale:
        suggestions.append({
            "action": f"Visit a resting chapter: {stale[0].get('filename', 'unknown')} (last touched {stale[0].get('last_modified', '')[:10]})",
            "command": f"scribbler analyze {stale[0].get('path', '')}",
            "why": "This chapter has been resting. A fresh look might spark something.",
        })

    # Check for unanalyzed final chapters
    final_files = [f for f in all_files if f.get("folder") == "final"]
    if final_files:
        unanalyzed = [f for f in final_files if not f.get("last_analyzed")]
        if unanalyzed:
            suggestions.append({
                "action": f"Analyze '{unanalyzed[0].get('filename', 'unknown')}' — it's in /final but hasn't been analyzed",
                "command": f"scribbler analyze {unanalyzed[0].get('path', '')}",
                "why": "Final chapters benefit most from the analysis suite.",
            })

    # Check for chapters that could be moved forward
    growing = [f for f in all_files if f.get("status") == "growing"]
    if growing:
        suggestions.append({
            "action": f"Move '{growing[0].get('filename', 'unknown')}' forward — it's been 'growing' for a while",
            "command": f"Edit the file and update its status to 'shaping'",
            "why": "Moving a chapter forward in status is progress, even small progress.",
        })

    # Default suggestions
    if not suggestions:
        suggestions = [
            {
                "action": "Drop a brain dump into raw-dumps/",
                "command": "echo 'your text' > raw-dumps/dump-$(date +%Y%m%d).txt",
                "why": "Start with raw material. The tagger will handle the rest.",
            },
            {
                "action": "Open the dashboard to see your project at a glance",
                "command": "scribbler dashboard",
                "why": "Seeing the whole project can spark direction.",
            },
            {
                "action": "Run comp-title research to see where your book fits",
                "command": "scribbler market --description \"your one-paragraph blurb\"",
                "why": "Knowing the shelf helps you write to it.",
            },
        ]

    # Pick top 3
    for i, s in enumerate(suggestions[:3], 1):
        click.echo(f"  {i}. {s['action']}")
        click.echo(f"     Run: {click.style(s['command'], fg='blue')}")
        click.echo(f"     Why: {s['why']}\n")


@cli.command(name="export")
@click.argument("file_path")
@click.option("--format", "-f", type=click.Choice(["md", "txt", "docx"]), default="md")
@click.option("--output", "-o", help="Output file path")
def export_cmd(file_path: str, format: str, output: Optional[str]):
    """Export a file to a different format."""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / file_path

    if not path.exists():
        click.echo(f"  File not found: {path}", err=True)
        sys.exit(1)

    click.echo(f"\n  Exporting {path.name} as {format}...")

    try:
        if format == "md":
            result = export.export_markdown(str(path), output)
        elif format == "txt":
            result = export.export_plain_text(str(path), output)
        elif format == "docx":
            result = export.export_docx(str(path), output)
        click.echo(f"  ✓ Exported to: {result}")
    except Exception as e:
        click.echo(f"  Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def stats():
    """Show project statistics."""
    s = db.get_stats()
    all_files = db.get_all_files()

    click.echo(f"\n  PROJECT STATISTICS")
    click.echo(f"  {'='*40}")
    click.echo(f"  Total files: {s['total_files']}")
    click.echo(f"  Total words: {s['total_words']:,}")

    if s.get("status_counts"):
        click.echo(f"\n  By status:")
        for status, count in s["status_counts"].items():
            click.echo(f"    {status}: {count}")

    if s.get("folder_counts"):
        click.echo(f"\n  By folder:")
        for folder, count in s["folder_counts"].items():
            click.echo(f"    {folder}: {count}")

    if s.get("stale_drafts"):
        click.echo(f"\n  Resting chapters ({len(s['stale_drafts'])}):")
        for stale in s["stale_drafts"][:5]:
            click.echo(f"    {stale['filename']} (last touched {stale['last_modified'][:10]})")

    # Aggregate characters and themes
    all_chars = set()
    all_themes = set()
    for f in all_files:
        all_chars.update(f.get("characters") or [])
        all_themes.update(f.get("themes") or [])

    click.echo(f"\n  Unique characters detected: {len(all_chars)}")
    click.echo(f"  Unique themes detected: {len(all_themes)}")
    click.echo()


@cli.command()
@click.argument("file_path")
def links(file_path: str):
    """Show files that share characters, places, or themes with this file."""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / file_path

    if not path.exists():
        click.echo(f"  File not found: {path}", err=True)
        sys.exit(1)

    click.echo(f"\n  Finding links for: {path.name}")

    links = tagger.find_links(str(path.resolve()))

    if not links:
        click.echo("  No links found yet. Tag more files to discover connections.")
        return

    click.echo(f"\n  Found {len(links)} linked file(s):\n")
    for link in links:
        click.echo(f"  → {link['file']}")
        if link.get("shared_characters"):
            click.echo(f"    Shared characters: {', '.join(link['shared_characters'])}")
        if link.get("shared_places"):
            click.echo(f"    Shared places: {', '.join(link['shared_places'])}")
        if link.get("shared_themes"):
            click.echo(f"    Shared themes: {', '.join(link['shared_themes'])}")
        click.echo()


def main():
    cli()


if __name__ == "__main__":
    main()
