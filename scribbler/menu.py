#!/usr/bin/env python3
"""The Audhd Scribbler — Menu interface.

Double-click SCRIBBLER-Windows.bat or SCRIBBLER-Mac.command to open this menu.
No console commands needed. Just pick a number.
"""
import os
import sys
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime

# Make sure we can import the scribbler package
SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from scribbler.config import PROJECT_ROOT, FOLDERS
from scribbler import db
from scribbler import settings
from scribbler import llm


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    clear_screen()
    print()
    print("  " + "=" * 54)
    print("  " + " " * 12 + "THE AUDHD SCRIBBLER")
    print("  " + " " * 8 + "Your memoir's calm companion")
    print("  " + "=" * 54)
    # Show LLM status
    status = llm.llm_status()
    print(f"  AI: {status}")
    print()


def print_menu():
    print("  What would you like to do?")
    print()
    print("  ── WRITING ──────────────────────────────────")
    print("    1.  Tag all my dumps  (organize raw text files)")
    print("    2.  View my files  (browse all files with metadata)")
    print("    3.  Read a file  (see the actual writing)")
    print("    4.  What should I do next?  (3 suggested actions)")
    print("    5.  Open the raw-dumps folder  (drop new files here)")
    print()
    print("  ── ANALYSIS ─────────────────────────────────")
    print("    6.  Analyze a chapter  (run the full analysis suite)")
    print("    7.  Analyze ALL chapters  (batch analysis)")
    print("    8.  Market research  (find comparable titles)")
    print("    9.  Find links between files  (what connects to what)")
    print()
    print("  ── VIEW ─────────────────────────────────────")
    print("    10. Open the dashboard  (visual overview)")
    print("    11. Show project stats  (word count, file count)")
    print()
    print("  ── EXPORT & MANAGE ──────────────────────────")
    print("    12. Export a file  (to Word, markdown, or plain text)")
    print("    13. Export all tagged files  (batch export)")
    print("    14. Delete a file  (remove from project)")
    print()
    print("  ── SETTINGS ─────────────────────────────────")
    print("    15. Settings  (Z.ai API key, theme, etc.)")
    print("    16. Quit")
    print()


def get_choice(prompt="  Pick a number: "):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "16"


def pause():
    try:
        input("\n  Press Enter to go back to the menu...")
    except (EOFError, KeyboardInterrupt):
        pass


def run_cli(*args):
    """Run a scribbler CLI command."""
    python = sys.executable
    cmd = [python, "-m", "scribbler.cli"] + list(args)
    subprocess.run(cmd, cwd=str(PROJECT_ROOT))


def find_text_files(include_readme: bool = False):
    """Find all text files in the writing folders.

    Args:
        include_readme: If False (default), skip README.md files — they're folder descriptions, not writing.
    """
    files = []
    for folder in ["raw-dumps", "triage", "chapters", "drafts", "final"]:
        folder_path = PROJECT_ROOT / folder
        if folder_path.exists():
            for ext in ["*.txt", "*.md"]:
                for f in folder_path.glob(ext):
                    if not include_readme and f.name.upper() == "README.MD":
                        continue
                    files.append(f)
    # Sort by folder then name for predictable ordering
    files.sort(key=lambda f: (str(f.parent), f.name))
    return files


def pick_file(prompt="  Pick a file:"):
    """Let the user pick a file from a numbered list."""
    files = find_text_files()

    if not files:
        print("\n  No text files found.")
        print("  Drop .txt or .md files into the 'raw-dumps' folder first.")
        print("  (Menu option 4 opens that folder for you)")
        return None

    print(prompt)
    print()
    for i, f in enumerate(files, 1):
        rel = f.relative_to(PROJECT_ROOT)
        size = f.stat().st_size
        size_str = f"{size//1024}KB" if size >= 1024 else f"{size}B"

        # Try to get word count and status from DB
        from scribbler import db
        db_entry = db.get_file(str(f.resolve()))
        if db_entry:
            word_count = db_entry.get("word_count", 0)
            status = db_entry.get("status", "")
            extra = f"  ·  {word_count} words  ·  {status}" if status else f"  ·  {word_count} words"
        else:
            extra = ""

        print(f"    {i:2d}. {rel}  ({size_str}){extra}")
    print()

    choice = get_choice("  Number: ")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(files):
            return str(files[idx])
    except ValueError:
        pass

    print("\n  Invalid choice.")
    return None


def action_label_all():
    print_header()
    print("  TAG ALL DUMPS")
    print("  " + "-" * 52)
    print()
    print("  This will read all text files in 'raw-dumps/' and add")
    print("  metadata tags (characters, places, themes, etc.).")
    print("  Your original text is never changed — only metadata is added.")
    print()

    # Check if there are files to tag
    raw_path = PROJECT_ROOT / "raw-dumps"
    files = list(raw_path.glob("*.txt")) + list(raw_path.glob("*.md")) if raw_path.exists() else []
    if not files:
        print("  No text files found in 'raw-dumps/'.")
        print()
        print("  To add files:")
        print("    1. Open the 'raw-dumps' folder (menu option 4)")
        print("    2. Drop your .txt or .md files in there")
        print("    3. Come back and run this again")
        print()
        pause()
        return

    print(f"  Found {len(files)} file(s) to tag.")
    print()

    # Show LLM status
    if llm.llm_available():
        print(f"  AI: {llm.llm_status()}")
        print("  → Beats, themes, and summaries will be AI-assisted.")
    else:
        print("  AI: Not configured (rule-based only).")
        print("  → To enable AI-assisted tagging, set your Z.ai API key (menu option 13).")
    print()

    input("  Press Enter to start tagging...")
    run_cli("label-all")

    # After tagging, offer to view files
    print()
    print("  ────────────────────────────────────────────────")
    print("  Tagging complete! Want to see your tagged files?")
    print("  Pick option 2 from the menu to view them in your browser.")
    print("  ────────────────────────────────────────────────")
    pause()


def action_view_files():
    print_header()
    print("  VIEW MY FILES")
    print("  " + "-" * 52)
    print()
    print("  Generating a browsable view of all your tagged files...")
    print()

    from scribbler.dashboard.file_viewer import generate
    html_path = generate()

    print(f"  ✓ Generated: {html_path}")
    print()
    print("  Opening in your browser...")
    webbrowser.open(f"file://{os.path.abspath(html_path)}")

    print()
    print("  Each file shows:")
    print("    • Status (seedling/growing/shaping/polishing/resting)")
    print("    • Word count, era, voice, emotional register")
    print("    • Characters, places, themes, sensory details")
    print("    • AI-generated summary")
    print("    • Full text content of the file")
    print("    • File path (so you can open it in your editor)")
    pause()


def action_read_file():
    """Show the actual writing content of a file."""
    print_header()
    print("  READ A FILE")
    print("  " + "-" * 52)
    print()
    print("  Pick a file to read. The full text will open in your browser")
    print("  with the metadata at the top.")
    print()

    file_path = pick_file("  Which file do you want to read?")
    if not file_path:
        pause()
        return

    # Generate a single-file reader HTML and open it
    from scribbler.dashboard.file_viewer import generate_single_file_reader
    html_path = generate_single_file_reader(file_path)

    print()
    print(f"  ✓ Opening: {os.path.basename(file_path)}")
    webbrowser.open(f"file://{os.path.abspath(html_path)}")
    pause()


def action_delete_file():
    """Delete a file from the project."""
    print_header()
    print("  DELETE A FILE")
    print("  " + "-" * 52)
    print()
    print("  Pick a file to delete. The file will be moved to the")
    print("  'archive' folder (not permanently deleted — you can")
    print("  recover it from there if needed).")
    print()

    file_path = pick_file("  Which file do you want to delete?")
    if not file_path:
        pause()
        return

    path = Path(file_path)
    if not path.exists():
        print(f"\n  File not found: {path}")
        pause()
        return

    # Confirm
    print()
    print(f"  You want to delete: {path.name}")
    print(f"  Location: {path.parent}")
    print()
    confirm = input("  Type 'yes' to confirm (anything else cancels): ").strip().lower()

    if confirm != "yes":
        print("\n  Cancelled. File not deleted.")
        pause()
        return

    # Move to archive
    archive_dir = PROJECT_ROOT / "archive"
    archive_dir.mkdir(exist_ok=True)

    # Handle name collisions
    dest = archive_dir / path.name
    counter = 1
    while dest.exists():
        dest = archive_dir / f"{path.stem}_{counter}{path.suffix}"
        counter += 1

    try:
        path.rename(dest)
        print(f"\n  ✓ Moved to: archive/{dest.name}")
        print(f"  (Recoverable from the archive folder)")

        # Remove from database
        from scribbler import db
        conn = db.get_db()
        conn.execute("DELETE FROM files WHERE path = ?", (str(path.resolve()),))
        conn.execute("DELETE FROM analysis_results WHERE file_path = ?", (str(path.resolve()),))
        conn.execute(
            "INSERT INTO activity_log (timestamp, action, file_path, details) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), "delete", str(path.resolve()), f"Moved to archive/{dest.name}")
        )
        conn.commit()
        conn.close()
        print(f"  ✓ Removed from project database")
    except Exception as e:
        print(f"\n  Error: {e}")
    pause()


def action_dashboard():
    print_header()
    print("  OPENING DASHBOARD")
    print("  " + "-" * 52)
    print()
    print("  Generating your dashboard...")
    print()

    from scribbler.dashboard.generator import generate
    html_path = generate()

    print(f"  ✓ Generated: {html_path}")
    print()
    print("  Opening in your browser...")
    webbrowser.open(f"file://{os.path.abspath(html_path)}")

    print()
    print("  The dashboard includes:")
    print("    • Overview stats and status badges")
    print("    • Chapter grid with status dots")
    print("    • Theme constellation heatmap")
    print("    • Timeline of recent activity")
    print("    • Relationship map (files ↔ characters ↔ themes)")
    print("    • Orphan tray (unfiled dumps)")
    print("    • Theme frequency bars")
    print("    • Character appearances")
    pause()


def action_next():
    print_header()
    run_cli("next")
    pause()


def action_analyze():
    print_header()
    print("  ANALYZE A CHAPTER")
    print("  " + "-" * 52)
    print()
    print("  Pick a file to analyze. The analysis suite will run")
    print("  all 6 analyzers: craft, voice/tense, characters, continuity,")
    print("  themes, and editor-style suggestions.")
    print()

    file_path = pick_file("  Which file do you want to analyze?")
    if file_path:
        print()
        input("  Press Enter to start analysis...")
        run_cli("analyze", file_path)


def action_analyze_all():
    print_header()
    print("  ANALYZE ALL CHAPTERS")
    print("  " + "-" * 52)
    print()
    print("  This will run the full analysis suite on every chapter")
    print("  in /chapters, /drafts, and /final.")
    print()
    input("  Press Enter to start...")
    run_cli("analyze-all")


def action_stats():
    print_header()
    run_cli("stats")


def action_export():
    print_header()
    print("  EXPORT A FILE")
    print("  " + "-" * 52)
    print()
    print("  Pick a file to export, then choose a format.")
    print()

    file_path = pick_file("  Which file do you want to export?")
    if not file_path:
        pause()
        return

    print()
    print("  Choose a format:")
    print("    1. Word document (.docx) — for sharing or editing in Word")
    print("    2. Markdown (.md) — with YAML frontmatter metadata")
    print("    3. Plain text (.txt) — just the text, no metadata")
    print()
    fmt_choice = get_choice("  Format (1-3): ")

    fmt_map = {"1": "docx", "2": "md", "3": "txt"}
    fmt = fmt_map.get(fmt_choice)
    if not fmt:
        print("\n  Invalid choice.")
        pause()
        return

    print()
    run_cli("export", file_path, "-f", fmt)

    # Open the export folder
    export_dir = PROJECT_ROOT / "data" / "exports"
    print()
    print(f"  Opening the export folder: {export_dir}")
    if sys.platform == "win32":
        os.startfile(str(export_dir))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(export_dir)])
    else:
        subprocess.run(["xdg-open", str(export_dir)])


def action_export_all():
    print_header()
    print("  EXPORT ALL TAGGED FILES")
    print("  " + "-" * 52)
    print()
    print("  This exports all your tagged files to Word documents")
    print("  in the data/exports/ folder.")
    print()

    files = find_text_files()
    if not files:
        print("  No files found to export.")
        pause()
        return

    print(f"  Found {len(files)} file(s) to export.")
    print()
    print("  Format:")
    print("    1. Word document (.docx)")
    print("    2. Plain text (.txt)")
    print()
    fmt_choice = get_choice("  Format (1-2): ")
    fmt = "docx" if fmt_choice == "1" else "txt" if fmt_choice == "2" else None

    if not fmt:
        print("\n  Invalid choice.")
        pause()
        return

    print()
    input(f"  Press Enter to export {len(files)} files as {fmt}...")

    export_dir = PROJECT_ROOT / "data" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    for f in files:
        try:
            run_cli("export", str(f), "-f", fmt)
            success += 1
        except Exception as e:
            print(f"  Error exporting {f.name}: {e}")

    print()
    print(f"  ✓ Exported {success}/{len(files)} files to: {export_dir}")

    # Open the export folder
    if sys.platform == "win32":
        os.startfile(str(export_dir))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(export_dir)])
    else:
        subprocess.run(["xdg-open", str(export_dir)])

    pause()


def action_market():
    print_header()
    print("  MARKET RESEARCH")
    print("  " + "-" * 52)
    print()
    print("  This finds comparable titles for your memoir.")
    print("  It helps you understand where your book fits in the market.")
    print()
    print("  You can provide a one-paragraph description of your book,")
    print("  or just press Enter to use the themes detected from your files.")
    print()

    desc = input("  Describe your book in one paragraph (or press Enter to skip): ").strip()
    print()

    if desc:
        run_cli("market", "-d", desc)
    else:
        run_cli("market")


def action_links():
    print_header()
    print("  FIND LINKS BETWEEN FILES")
    print("  " + "-" * 52)
    print()
    print("  Pick a file to see which other files share characters,")
    print("  places, or themes with it.")
    print()

    file_path = pick_file("  Which file do you want to find links for?")
    if file_path:
        print()
        run_cli("links", file_path)


def action_open_folder():
    print_header()
    print("  OPENING RAW-DUMPS FOLDER")
    print("  " + "-" * 52)
    print()

    raw_path = PROJECT_ROOT / "raw-dumps"
    raw_path.mkdir(exist_ok=True)

    # Create a README if it doesn't exist
    readme = raw_path / "README.md"
    if not readme.exists():
        readme.write_text("# raw-dumps/\n\nDrop your text files here (.txt or .md).\nBrain dumps, voice memos, freewrites — anything goes.\n", encoding="utf-8")

    print(f"  Opening: {raw_path}")
    print()

    # Open the folder in the file explorer
    if sys.platform == "win32":
        os.startfile(str(raw_path))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(raw_path)])
    else:
        subprocess.run(["xdg-open", str(raw_path)])

    print("  The folder should now be open in your file manager.")
    print("  Drop your text files in there, then come back and pick option 1.")
    print()
    pause()


def action_settings():
    while True:
        print_header()
        print("  SETTINGS")
        print("  " + "-" * 52)
        print()

        current = settings.load_settings()
        provider_id = current.get("provider", "zai_cli")
        provider_config = settings.get_provider_config(provider_id)

        # Show current status
        print("  Current AI provider:")
        print(f"    {provider_config.get('name', provider_id)}")
        print(f"    Status: {llm.llm_status()}")
        print()
        print("  ────────────────────────────────────────────────")
        print()
        print("  Pick an AI provider:")
        print()
        print("    1.  Z.ai CLI  (FREE — the AI you're chatting with, NO API KEY needed)")
        print("    2.  Google Gemini  (FREE — needs API key)")
        print("    3.  Groq           (FREE — very fast, needs API key)")
        print("    4.  Ollama         (LOCAL — completely free, runs on your machine)")
        print("    5.  Z.ai API       (requires credits — NOT recommended)")
        print()
        print("    6.  Test current connection")
        print("    7.  Clear API key")
        print("    8.  Back to menu")
        print()

        choice = get_choice("  Pick a number: ")

        if choice == "1":
            _setup_zai_cli()
        elif choice == "2":
            _setup_gemini()
        elif choice == "3":
            _setup_groq()
        elif choice == "4":
            _setup_ollama()
        elif choice == "5":
            _setup_zai()
        elif choice == "6":
            _test_connection()
        elif choice == "7":
            settings.set_setting("api_key", "")
            print()
            print("  ✓ API key cleared.")
            pause()
        elif choice == "8":
            break


def _setup_zai_cli():
    """Set up the Z.ai CLI — free, no API key needed."""
    print_header()
    print("  Z.AI CLI SETUP (FREE — NO API KEY NEEDED)")
    print("  " + "-" * 52)
    print()
    print("  This uses the same AI you're chatting with right now.")
    print("  No API key. No credits. No payment. Ever.")
    print()
    print("  ────────────────────────────────────────────────")
    print()

    # Check if z-ai is already installed (handles Windows PATH issues)
    from scribbler.llm import _find_zai_cli
    zai_path = _find_zai_cli()
    if zai_path:
        print("  ✓ Z.ai CLI is already installed!")
        settings.set_setting("provider", "zai_cli")
        settings.set_setting("api_key", "")
        print()
        print("  Testing connection...")
        result = llm.llm_complete("Say 'hello' and nothing else.")
        if result:
            print(f"  ✓✓✓ SUCCESS! Z.ai responded: {result[:60]}")
            print()
            print("  You're all set. AI-assisted tagging and analysis now work.")
        else:
            print("  ⚠ Connection test failed, but the CLI is installed.")
            print("  Try tagging a file — it may still work.")
        pause()
        return

    # Need to install it
    print("  The Z.ai CLI is not installed yet. Let's install it.")
    print()
    print("  ────────────────────────────────────────────────")
    print("  STEP 1: Check if Node.js is installed")
    print("  ────────────────────────────────────────────────")
    print()

    # Check for node
    import shutil
    node_installed = shutil.which("node") is not None or shutil.which("npm") is not None

    if node_installed:
        print("  ✓ Node.js is installed. Good.")
    else:
        print("  ✗ Node.js is not installed.")
        print()
        print("  Node.js is required to run the Z.ai CLI.")
        print("  It's free and easy to install:")
        print()
        print("    1. Go to https://nodejs.org")
        print("    2. Download the 'LTS' version (left button)")
        print("    3. Run the installer (just click Next, Next, Finish)")
        print("    4. Come back here and run this option again")
        print()
        print("  ────────────────────────────────────────────────")
        print()
        pause()
        return

    print()
    print("  ────────────────────────────────────────────────")
    print("  STEP 2: Install the Z.ai CLI")
    print("  ────────────────────────────────────────────────")
    print()
    print("  This runs: npm install -g z-ai-web-dev-sdk")
    print("  (One-time install, takes about 30 seconds)")
    print()
    input("  Press Enter to install...")

    import subprocess
    print()
    print("  Installing... (this may take a minute)")
    try:
        # On Windows, npm is npm.cmd — subprocess.run needs shell=True to find it
        # On Mac/Linux, shell=True is also fine but not required
        is_windows = sys.platform == "win32"
        npm_cmd = "npm install -g z-ai-web-dev-sdk"

        if is_windows:
            result = subprocess.run(
                npm_cmd,
                shell=True,
                capture_output=True, text=True, timeout=120,
                encoding='utf-8', errors='replace'
            )
        else:
            result = subprocess.run(
                ["npm", "install", "-g", "z-ai-web-dev-sdk"],
                capture_output=True, text=True, timeout=120,
                encoding='utf-8', errors='replace'
            )

        if result.returncode == 0:
            print("  ✓ Installation complete!")
        else:
            print(f"  ⚠ Installation may have had issues.")
            if result.stderr:
                print(f"  Output: {result.stderr[:300]}")
            if result.stdout:
                print(f"  Log: {result.stdout[:300]}")
    except subprocess.TimeoutExpired:
        print("  ⚠ Installation timed out. Try running manually in a terminal:")
        print("    npm install -g z-ai-web-dev-sdk")
    except Exception as e:
        print(f"  ⚠ Error: {e}")
        print("  Try running manually in a terminal:")
        print("    npm install -g z-ai-web-dev-sdk")

    # Check if it worked (use _find_zai_cli to handle Windows PATH issues)
    from scribbler.llm import _find_zai_cli
    zai_path = _find_zai_cli()
    if zai_path:
        settings.set_setting("provider", "zai_cli")
        settings.set_setting("api_key", "")
        print()
        print("  ✓ Z.ai CLI is now available!")
        print(f"    Location: {zai_path}")
        print()
        print("  Testing connection...")
        result = llm.llm_complete("Say 'hello' and nothing else.")
        if result:
            print(f"  ✓✓✓ SUCCESS! Z.ai responded: {result[:60]}")
            print()
            print("  You're all set. AI-assisted tagging and analysis now work.")
        else:
            print("  ⚠ Connection test failed. The CLI is installed though.")
            print("  Try restarting this menu and running a tag.")
    else:
        print()
        print("  ⚠ The CLI doesn't seem to be in PATH yet.")
        print("  You may need to:")
        print("    1. Close this window")
        print("    2. Re-open it (so PATH refreshes)")
        print("    3. Come back to Settings and pick option 1 again")
        print()
        print("  Or the install may have failed. Check that Node.js is installed")
        print("  and try running this in a terminal manually:")
        print("    npm install -g z-ai-web-dev-sdk")

    pause()


def _setup_gemini():
    """Set up Google Gemini (free)."""
    print_header()
    print("  GOOGLE GEMINI SETUP (FREE)")
    print("  " + "-" * 52)
    print()
    print("  Gemini is Google's AI. The free tier is generous:")
    print("    • 15 requests per minute")
    print("    • 1,500 requests per day")
    print("    • No credit card needed")
    print()
    print("  ────────────────────────────────────────────────")
    print("  HOW TO GET YOUR FREE API KEY:")
    print("  ────────────────────────────────────────────────")
    print()
    print("    1. Open your browser and go to:")
    print("       https://aistudio.google.com/app/apikey")
    print()
    print("    2. Sign in with any Google account")
    print()
    print("    3. Click the blue 'Create API key' button")
    print()
    print("    4. Pick 'Create API key in new project' (the easy option)")
    print()
    print("    5. Copy the key (it starts with 'AIza...')")
    print()
    print("    6. Paste it below")
    print()
    print("  ────────────────────────────────────────────────")
    print()

    api_key = input("  Paste your Gemini API key: ").strip()
    if not api_key:
        print("\n  No key entered. Nothing changed.")
        pause()
        return

    # Save settings
    settings.set_setting("provider", "gemini")
    settings.set_setting("api_key", api_key)
    settings.set_setting("model", "gemini-2.0-flash")

    print()
    print("  ✓ Saved. Testing connection...")
    result = llm.llm_complete("Say 'hello' and nothing else.")
    if result:
        print(f"  ✓✓✓ SUCCESS! Gemini responded: {result[:60]}")
        print()
        print("  You're all set. AI-assisted tagging and analysis now work.")
    else:
        print()
        print("  ✗ Connection failed. Common causes:")
        print("    • Key was copied with extra spaces (try again)")
        print("    • Key is from a region that doesn't support Gemini")
        print("    • You're on a corporate network blocking Google APIs")
    pause()


def _setup_groq():
    """Set up Groq (free, very fast)."""
    print_header()
    print("  GROQ SETUP (FREE, VERY FAST)")
    print("  " + "-" * 52)
    print()
    print("  Groq runs Llama and Mixtral models on custom hardware.")
    print("  Stupidly fast. Generous free tier:")
    print("    • 30 requests per minute")
    print("    • 14,400 requests per day")
    print("    • No credit card needed")
    print()
    print("  ────────────────────────────────────────────────")
    print("  HOW TO GET YOUR FREE API KEY:")
    print("  ────────────────────────────────────────────────")
    print()
    print("    1. Open your browser and go to:")
    print("       https://console.groq.com/keys")
    print()
    print("    2. Sign up (Google or GitHub login — one click)")
    print()
    print("    3. Click 'Create API Key'")
    print()
    print("    4. Give it any name (e.g. 'scribbler')")
    print()
    print("    5. Copy the key (starts with 'gsk_...')")
    print()
    print("    6. Paste it below")
    print()
    print("  ────────────────────────────────────────────────")
    print()

    api_key = input("  Paste your Groq API key: ").strip()
    if not api_key:
        print("\n  No key entered. Nothing changed.")
        pause()
        return

    settings.set_setting("provider", "groq")
    settings.set_setting("api_key", api_key)
    settings.set_setting("model", "llama-3.3-70b-versatile")

    print()
    print("  ✓ Saved. Testing connection...")
    result = llm.llm_complete("Say 'hello' and nothing else.")
    if result:
        print(f"  ✓✓✓ SUCCESS! Groq responded: {result[:60]}")
        print()
        print("  You're all set. AI-assisted tagging and analysis now work.")
    else:
        print()
        print("  ✗ Connection failed. Check the key was copied correctly.")
    pause()


def _setup_ollama():
    """Set up Ollama (local, completely free)."""
    print_header()
    print("  OLLAMA SETUP (LOCAL, COMPLETELY FREE)")
    print("  " + "-" * 52)
    print()
    print("  Ollama runs an AI model on YOUR machine.")
    print("  Pros: completely free, no limits, your text never leaves your computer.")
    print("  Cons: you need to install it and download a model (~2GB).")
    print()
    print("  ────────────────────────────────────────────────")
    print("  HOW TO SET UP OLLAMA:")
    print("  ────────────────────────────────────────────────")
    print()
    print("    1. Go to https://ollama.com")
    print()
    print("    2. Download Ollama for your system (Windows/Mac/Linux)")
    print()
    print("    3. Install it (double-click the downloaded file)")
    print()
    print("    4. Open a terminal/command prompt and run:")
    print("         ollama pull llama3.2")
    print("       (This downloads the model — about 2GB, takes a few minutes)")
    print()
    print("    5. Ollama runs in the background. No API key needed!")
    print()
    print("    6. Select Ollama below and you're done.")
    print()
    print("  ────────────────────────────────────────────────")
    print()

    confirm = input("  Have you installed Ollama and pulled llama3.2? (y/n): ").strip().lower()
    if confirm != "y":
        print()
        print("  Install Ollama first, then come back.")
        print("  URL: https://ollama.com")
        pause()
        return

    settings.set_setting("provider", "ollama")
    settings.set_setting("api_key", "")  # Ollama doesn't need a key
    settings.set_setting("model", "llama3.2")

    print()
    print("  ✓ Saved. Testing connection (make sure Ollama is running)...")
    result = llm.llm_complete("Say 'hello' and nothing else.")
    if result:
        print(f"  ✓✓✓ SUCCESS! Ollama responded: {result[:60]}")
        print()
        print("  You're all set. AI runs locally on your machine.")
    else:
        print()
        print("  ✗ Connection failed. Make sure:")
        print("    • Ollama is installed (https://ollama.com)")
        print("    • You ran 'ollama pull llama3.2'")
        print("    • Ollama is running (it usually auto-starts)")
        print("    • Try running 'ollama serve' in a terminal")
    pause()


def _setup_zai():
    """Set up Z.ai (requires credits)."""
    print_header()
    print("  Z.AI SETUP (REQUIRES CREDITS)")
    print("  " + "-" * 52)
    print()
    print("  ⚠  Z.ai requires payment/credits. The free tier is limited.")
    print("  Consider Gemini (option 1) or Groq (option 2) instead — both free.")
    print()
    print("  ────────────────────────────────────────────────")
    print()

    api_key = input("  Paste your Z.ai API key (or press Enter to cancel): ").strip()
    if not api_key:
        print("\n  No key entered. Nothing changed.")
        pause()
        return

    settings.set_setting("provider", "zai")
    settings.set_setting("api_key", api_key)
    settings.set_setting("model", "glm-4-plus")

    print()
    print("  ✓ Saved. Testing connection...")
    result = llm.llm_complete("Say 'hello' and nothing else.")
    if result:
        print(f"  ✓✓✓ SUCCESS! Z.ai responded: {result[:60]}")
    else:
        print()
        print("  ✗ Connection failed. Z.ai requires credits.")
        print("  Try Gemini (option 1) or Groq (option 2) — both are free.")
    pause()


def _test_connection():
    """Test the current AI connection."""
    print()
    print("  Testing connection...")
    print(f"  Provider: {settings.get_provider()}")
    print(f"  Model: {settings.get_model()}")
    print()

    if not llm.llm_available():
        print("  ✗ No AI configured.")
        print("  Pick a provider (1-4) and set it up first.")
        pause()
        return

    result = llm.llm_complete("Say 'hello' and nothing else.")
    if result:
        print(f"  ✓✓✓ SUCCESS! AI responded: {result[:80]}")
    else:
        print()
        print("  ✗ Connection failed.")
        print()
        print("  Troubleshooting:")
        print("    • Check the API key is correct (no extra spaces)")
        print("    • Make sure you have credits (Z.ai) or are within free limits (Gemini/Groq)")
        print("    • For Ollama, make sure it's running: 'ollama serve'")
    pause()


def main():
    while True:
        print_header()
        print_menu()

        choice = get_choice()

        if choice == "1":
            action_label_all()
        elif choice == "2":
            action_view_files()
        elif choice == "3":
            action_read_file()
        elif choice == "4":
            action_next()
        elif choice == "5":
            action_open_folder()
        elif choice == "6":
            action_analyze()
        elif choice == "7":
            action_analyze_all()
        elif choice == "8":
            action_market()
        elif choice == "9":
            action_links()
        elif choice == "10":
            action_dashboard()
        elif choice == "11":
            action_stats()
        elif choice == "12":
            action_export()
        elif choice == "13":
            action_export_all()
        elif choice == "14":
            action_delete_file()
        elif choice == "15":
            action_settings()
        elif choice == "16":
            print_header()
            print("  Happy scribbling.")
            print()
            print("  Your writing stays on your machine. Nothing leaves unless")
            print("  you use AI-assisted tagging (which calls Z.ai).")
            print()
            break
        else:
            print("\n  Pick a number from 1 to 16.")
            pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Happy scribbling.\n")
    except Exception as e:
        print(f"\n  Something went wrong: {e}")
        import traceback
        traceback.print_exc()
        print()
        pause()
