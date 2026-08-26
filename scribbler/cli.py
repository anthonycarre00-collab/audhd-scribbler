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

# Fix Windows Unicode crashes — set stdout/stderr to UTF-8 before anything else
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, Exception):
    pass

# Disable per-file full-project snapshots — they cause "database is locked" and massive slowdowns
# (safety.backup_database is called on every tag/analysis write, copying ALL writer folders)
try:
    from . import safety
    safety.backup_database = lambda reason="": None
    safety.create_snapshot = lambda reason="": None
except Exception:
    pass
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
from . import search as search_module
from .file_io import read_text_file
from .analyzers import craft, voice_tense, characters, continuity, themes, editor, market as market_analyzer
from .analyzers import cadence, motifs, anchors, voice_dna, reader_perception
from .analysis_suite import run as suite_run
from .analysis_catalog import ANALYSIS_CATALOG
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

    # Find all text files (skip README.md and other meta files)
    files = []
    for ext in ["*.txt", "*.md", "*.text"]:
        for f in folder_path.glob(ext):
            if f.name.upper() == "README.MD":
                continue  # Skip README files — they're folder descriptions, not writing
            files.append(f)

    if not files:
        click.echo(f"  No text files found in {folder}/")
        click.echo(f"  Drop .txt or .md files into {folder}/ and try again.")
        return

    click.echo(f"\n  Tagging {len(files)} file(s) in {folder}/...")

    use_llm = not no_llm
    if use_llm and not llm.llm_available():
        click.echo("  Note: LLM not available, using rule-based tagging only.")
        use_llm = False

    # Try to use rich for progress display
    try:
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False

    success = 0
    errors = 0
    total = len(files)

    if use_rich:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            main_task = progress.add_task(f"Tagging {total} files...", total=total)
            for i, f in enumerate(files, 1):
                try:
                    progress.update(main_task, description=f"[{i}/{total}] {f.name}")
                    meta = tagger.tag_file(str(f), use_llm=use_llm)
                    progress.console.print(f"  ✓ [{i}/{total}] {f.name} — {meta['word_count']} words, {len(meta.get('characters', []))} characters detected")
                    success += 1
                except KeyboardInterrupt:
                    progress.console.print(f"\n  [yellow]Interrupted by user. {success} of {total} files completed and saved.[/yellow]")
                    progress.console.print(f"  Re-run to continue from where you left off.")
                    break
                except Exception as e:
                    progress.console.print(f"  [red]✗ [{i}/{total}] {f.name} — ERROR: {e}[/red]")
                    errors += 1
                progress.advance(main_task)
    else:
        # Fallback: simple text output
        for i, f in enumerate(files, 1):
            try:
                click.echo(f"  [{i}/{total}] Tagging: {f.name}...", nl=False)
                meta = tagger.tag_file(str(f), use_llm=use_llm)
                click.echo(f" {meta['word_count']} words, {len(meta.get('characters', []))} characters detected")
                success += 1
            except KeyboardInterrupt:
                click.echo(f"\n  Interrupted. {success} of {total} files completed and saved.")
                click.echo(f"  Re-run to continue.")
                break
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
    content = read_text_file(path)
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

    # All 17 tools from the catalog; default = the 6 core + 6 suite = 12 implemented tools
    suite_tools = ["repetition", "pacing", "structure", "memoir", "reader", "research"]
    if tool:
        tools_to_run = list(tool)
    else:
        # Default: run all implemented tools (12 of 17; 5 are not yet implemented)
        tools_to_run = ["craft", "voice", "characters", "continuity", "themes", "editor"] + suite_tools
    total_tools = len(tools_to_run)

    # Validate tools against the catalog
    valid_tools = set(ANALYSIS_CATALOG.keys())
    invalid = [t for t in tools_to_run if t not in valid_tools]
    if invalid:
        click.echo(f"  Unknown tool(s): {invalid}")
        click.echo(f"  Valid tools: {', '.join(sorted(valid_tools))}")
        return

    # Try rich for progress
    try:
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False

    results = {}

    def run_tool(t, text):
        """Run a single analysis tool and return its result dict."""
        # Core analyzers (6)
        if t == "craft": return craft.analyze(text)
        elif t == "voice": return voice_tense.analyze(text)
        elif t in ["characters", "character"]: return characters.analyze(text)
        elif t == "continuity": return continuity.analyze(text)
        elif t == "themes": return themes.analyze(text)
        elif t == "editor":
            # Pass pre-computed results to editor to avoid re-running sub-analyzers
            precomputed = {k: v for k, v in results.items() if k != "editor" and not isinstance(v, dict) or "error" not in (v or {})}
            try:
                return editor.analyze(text, precomputed=precomputed)
            except TypeError:
                return editor.analyze(text)
        # Suite tools (6)
        elif t in suite_tools:
            return suite_run(t, text)
        # New analyzers (5)
        elif t == "cadence":
            return cadence.analyze(text)
        elif t == "motifs":
            return motifs.analyze(text=text)
        elif t == "anchors":
            return anchors.analyze(text=text)
        elif t == "voice_dna":
            return voice_dna.analyze(text)
        elif t == "reader_perception":
            return reader_perception.analyze(text)
        else:
            return {"error": f"Unknown tool '{t}'"}

    if use_rich:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn(), console=console) as progress:
            task = progress.add_task(f"Analyzing {total_tools} tools...", total=total_tools)
            for i, t in enumerate(tools_to_run, 1):
                progress.update(task, description=f"[{i}/{total_tools}] Running {t}...")
                try:
                    result = run_tool(t, text)
                    if result:
                        results[t] = result
                        progress.console.print(f"  ✓ [{i}/{total_tools}] {t} — done")
                    else:
                        progress.console.print(f"  [yellow]✗ [{i}/{total_tools}] {t} — no result[/yellow]")
                except KeyboardInterrupt:
                    progress.console.print(f"\n  [yellow]Interrupted. {i-1} of {total_tools} tools completed and saved.[/yellow]")
                    break
                except Exception as e:
                    progress.console.print(f"  [red]✗ [{i}/{total_tools}] {t} — error: {e}[/red]")
                    results[t] = {"error": str(e)}
                progress.advance(task)
    else:
        for i, t in enumerate(tools_to_run, 1):
            click.echo(f"  [{i}/{total_tools}] Running {t}...", nl=False)
            try:
                result = run_tool(t, text)
                if result:
                    results[t] = result
                    click.echo(" done")
                else:
                    click.echo(" no result")
            except KeyboardInterrupt:
                click.echo(f"\n  Interrupted. {i-1} of {total_tools} tools completed.")
                break
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

    # Cross-tool synthesis report
    if len(results) >= 2:
        try:
            from . import synthesis
            click.echo(f"\n{'='*60}")
            click.echo(f"  SYNTHESIS — {path.name}")
            click.echo(f"{'='*60}\n")

            syn = synthesis.generate(results, len(text.split()))

            click.echo(f"  {syn['summary']}\n")

            click.echo(f"  VOICE CONSISTENCY")
            click.echo(f"    {syn['voice_consistency']}\n")

            click.echo(f"  NARRATOR DISTANCE")
            click.echo(f"    {syn['narrator_distance']}\n")

            if syn["recurring_signals"]:
                click.echo(f"  RECURRING SIGNALS ACROSS TOOLS")
                for sig in syn["recurring_signals"]:
                    click.echo(f"    • {sig}")
                click.echo()

            click.echo(f"  TOP THINGS TO NOTICE")
            for i, item in enumerate(syn["top_things_to_notice"], 1):
                click.echo(f"    {i}. {item[:120]}")
            click.echo()

            click.echo(f"  AUDHD-AWARE NOTES")
            for note in syn["audhd_aware_notes"]:
                click.echo(f"    • {note}")
            click.echo()

            click.echo(f"  WHAT THIS DOES NOT MEAN")
            for note in syn["what_this_does_not_mean"]:
                click.echo(f"    • {note}")
            click.echo()
        except Exception as e:
            click.echo(f"\n  [Synthesis skipped: {e}]")

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
        content = read_text_file(ch)
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


@cli.command(name="analyze-manuscript")
@click.option("--tool", "-t", multiple=True, help="Specific manuscript-level tool(s): motifs, anchors, voice_dna")
def analyze_manuscript(tool):
    """Run manuscript-level analysis across ALL chapters.

    Manuscript-level tools (motifs, anchors) need multiple chapters to work.
    They find cross-chapter patterns: recurring images, structural anchors, voice drift.
    """
    # Collect all chapters
    chapters = []
    for folder in ["chapters", "drafts", "final"]:
        folder_path = PROJECT_ROOT / folder
        if folder_path.exists():
            for ext in ["*.txt", "*.md"]:
                for f in folder_path.glob(ext):
                    if f.name.upper() == "README.MD":
                        continue
                    try:
                        content = read_text_file(f)
                        # Strip frontmatter
                        if content.startswith("---"):
                            end = content.find("---", 3)
                            if end != -1:
                                content = content[end + 3:].strip()
                        import re
                        content = re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->', '', content).strip()
                        chapters.append({"filename": f.name, "text": content, "path": str(f)})
                    except Exception as e:
                        click.echo(f"  Warning: could not read {f.name}: {e}")

    if not chapters:
        click.echo("  No chapters found in /chapters, /drafts, or /final.")
        click.echo("  Move tagged files to /chapters or /drafts first.")
        return

    click.echo(f"\n  Analyzing {len(chapters)} chapter(s) at manuscript level...")

    # Default tools for manuscript analysis
    if tool:
        tools_to_run = list(tool)
    else:
        tools_to_run = ["motifs", "anchors", "voice_dna"]
    total_tools = len(tools_to_run)

    # Try rich for progress
    try:
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False

    results = {}

    def run_ms_tool(t, chapters):
        if t == "motifs":
            return motifs.analyze(chapters=chapters)
        elif t == "anchors":
            return anchors.analyze(chapters=chapters)
        elif t == "voice_dna":
            # Voice DNA: analyze the first chapter against the rest as approved samples
            if len(chapters) >= 2:
                target = chapters[0]["text"]
                approved = [ch["text"] for ch in chapters[1:]]
                return voice_dna.analyze(target, approved_samples=approved)
            else:
                return voice_dna.analyze(chapters[0]["text"])
        else:
            return {"error": f"Unknown manuscript tool '{t}'"}

    if use_rich:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), TimeElapsedColumn(), console=console) as progress:
            task = progress.add_task(f"Manuscript analysis ({total_tools} tools)...", total=total_tools)
            for i, t in enumerate(tools_to_run, 1):
                progress.update(task, description=f"[{i}/{total_tools}] Running {t}...")
                try:
                    result = run_ms_tool(t, chapters)
                    if result:
                        results[t] = result
                        progress.console.print(f"  ✓ [{i}/{total_tools}] {t} — done")
                except KeyboardInterrupt:
                    progress.console.print(f"\n  [yellow]Interrupted. {i-1} of {total_tools} tools completed.[/yellow]")
                    break
                except Exception as e:
                    progress.console.print(f"  [red]✗ {t} — error: {e}[/red]")
                progress.advance(task)
    else:
        for i, t in enumerate(tools_to_run, 1):
            click.echo(f"  [{i}/{total_tools}] Running {t}...", nl=False)
            try:
                result = run_ms_tool(t, chapters)
                if result:
                    results[t] = result
                    click.echo(" done")
            except KeyboardInterrupt:
                click.echo(f"\n  Interrupted.")
                break
            except Exception as e:
                click.echo(f" error: {e}")

    # Output results
    click.echo(f"\n{'='*60}")
    click.echo(f"  MANUSCRIPT ANALYSIS REPORT ({len(chapters)} chapters)")
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

        if "observations" in result:
            click.echo(f"\n  OBSERVATIONS ({len(result['observations'])}):")
            for obs in result["observations"]:
                if isinstance(obs, dict):
                    click.echo(f"\n    [{obs.get('category', '').replace('_', ' ').upper()}]")
                    click.echo(f"    {obs.get('formatted', '')}")

        # Key metrics
        for key in ["candidate_motifs", "phrase_echoes", "opening_gesture_counts",
                     "closing_gesture_counts", "anchor_stability_score", "drift_assessment"]:
            if key in result:
                val = result[key]
                if isinstance(val, list):
                    click.echo(f"\n  {key.replace('_', ' ').title()} ({len(val)}):")
                    for item in val[:5]:
                        if isinstance(item, dict):
                            click.echo(f"    • {item.get('image', item.get('phrase', item.get('pattern', str(item)[:80])))}")
                elif isinstance(val, dict):
                    click.echo(f"\n  {key.replace('_', ' ').title()}:")
                    for k, v in list(val.items())[:5]:
                        click.echo(f"    • {k}: {v}")
                else:
                    click.echo(f"  {key.replace('_', ' ').title()}: {val}")

    click.echo()


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
                content = read_text_file(f)[:200]
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


@cli.command()
@click.option("--character", "-c", help="Search by character name")
@click.option("--place", "-p", help="Search by place name")
@click.option("--theme", "-t", help="Search by theme")
@click.option("--era", "-e", help="Search by era (childhood, adolescence, etc.)")
@click.option("--mood", "-m", help="Search by emotional register")
@click.option("--status", "-s", help="Search by status (seedling, growing, etc.)")
def search(character, place, theme, era, mood, status):
    """Search files by tags. Find all sections mentioning a character, set in a place, etc.

    Examples:
      scribbler search --character "Nathan"
      scribbler search --place "Colombia"
      scribbler search --theme "masking"
      scribbler search --character "Nathan" --place "Colombia"
    """
    # Build filters
    filters = {}
    if character:
        filters["characters"] = character
    if place:
        filters["places"] = place
    if theme:
        filters["themes"] = theme
    if era:
        filters["era"] = era
    if mood:
        filters["emotional_register"] = mood
    if status:
        filters["status"] = status

    if not filters:
        click.echo("\n  Search by tags — pick at least one filter:")
        click.echo("    --character NAME    e.g., --character \"Nathan\"")
        click.echo("    --place NAME        e.g., --place \"Colombia\"")
        click.echo("    --theme NAME        e.g., --theme \"masking\"")
        click.echo("    --era NAME          e.g., --era \"childhood\"")
        click.echo("    --mood NAME         e.g., --mood \"numb\"")
        click.echo("    --status NAME       e.g., --status \"resting\"")
        click.echo()
        click.echo("  Combine multiple filters (AND logic):")
        click.echo("    scribbler search --character \"Nathan\" --place \"Colombia\"")
        click.echo()
        return

    click.echo(f"\n  Searching for files matching: {filters}")
    click.echo()

    if len(filters) == 1:
        # Single tag search
        tag_type, value = next(iter(filters.items()))
        results = search_module.search_by_tag(tag_type, value)
    else:
        # Multi-tag search
        results = search_module.search_multi(filters)

    if not results:
        click.echo(f"  No files found matching your search.")
        click.echo()
        return

    click.echo(f"  Found {len(results)} file(s):\n")

    for i, f in enumerate(results, 1):
        name = f.get("filename", "unknown")
        word_count = f.get("word_count", 0)
        file_status = f.get("status", "")
        file_era = f.get("era", "")
        file_chars = f.get("characters") or []
        file_themes = f.get("themes") or []

        click.echo(f"  {i}. {name}")
        click.echo(f"     {word_count:,} words · status: {file_status} · era: {file_era or '—'}")
        if file_chars:
            click.echo(f"     Characters: {', '.join(file_chars[:6])}")
        if file_themes:
            click.echo(f"     Themes: {', '.join(file_themes[:5])}")

        # Show where the searched tag appears in this file
        for tag_type, value in filters.items():
            if tag_type in ["characters", "places", "themes"]:
                occurrences = search_module.find_tag_in_file(f.get("path", ""), tag_type, value)
                if occurrences:
                    click.echo(f"     '{value}' appears in {len(occurrences)} paragraph(s):")
                    for occ in occurrences[:3]:  # Show first 3
                        click.echo(f"       ¶{occ['paragraph']}: {occ['context']}")
                    if len(occurrences) > 3:
                        click.echo(f"       ... and {len(occurrences) - 3} more")
        click.echo()


@cli.command()
@click.argument("file_path")
def coverage(file_path: str):
    """Show tag coverage for a file — proves the whole document was analyzed."""
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / file_path

    if not path.exists():
        click.echo(f"  File not found: {path}", err=True)
        sys.exit(1)

    coverage_info = search_module.get_tag_coverage(str(path.resolve()))

    if not coverage_info:
        click.echo(f"  No coverage data for {path.name}. Tag it first.")
        return

    click.echo(f"\n  TAG COVERAGE REPORT: {path.name}")
    click.echo(f"  {'='*50}\n")

    total_paras = coverage_info.get("total_paragraphs", 0)
    tagged_paras = coverage_info.get("paragraphs_with_tags", 0)
    coverage_pct = coverage_info.get("tag_coverage_pct", 0)
    chunks = coverage_info.get("chunks_analyzed", 1)
    spread = coverage_info.get("spread_description", "unknown")

    click.echo(f"  Document size: {total_paras} paragraphs")
    click.echo(f"  Chunks analyzed: {chunks} (the AI processed the whole document)")
    click.echo(f"  Paragraphs containing tags: {tagged_paras}/{total_paras} ({coverage_pct}%)")
    click.echo(f"  Coverage spread: {spread}")
    click.echo()

    tag_dist = coverage_info.get("tag_distribution", {})
    if tag_dist:
        click.echo(f"  WHERE TAGS APPEAR IN THE DOCUMENT:")
        click.echo()
        for tag_type, values in tag_dist.items():
            click.echo(f"  {tag_type.upper()}:")
            for value, para_nums in values.items():
                # Show which paragraphs contain this tag
                if len(para_nums) <= 10:
                    paras_str = ", ".join(str(p) for p in para_nums)
                else:
                    paras_str = ", ".join(str(p) for p in para_nums[:5]) + f" ... +{len(para_nums)-5} more"
                click.echo(f"    '{value}' → paragraph(s): {paras_str}")
            click.echo()
    else:
        click.echo("  No tags found in body text (tags may be from AI analysis only)")
        click.echo()

    # Verify full coverage
    spread_num = coverage_info.get("coverage_spread", 0)
    if spread_num == 3:
        click.echo("  ✓ FULL COVERAGE CONFIRMED — tags found in beginning, middle, AND end")
    elif spread_num == 2:
        click.echo("  ⚠ Partial coverage — tags found in 2 of 3 sections")
    elif spread_num == 1:
        click.echo("  ⚠ Limited coverage — tags found in only 1 section of the document")
    click.echo()


def main():
    cli()


if __name__ == "__main__":
    main()
