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


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    clear_screen()
    print()
    print("  " + "=" * 54)
    print("  " + " " * 12 + "THE AUDHD SCRIBBLER")
    print("  " + " " * 8 + "Your memoir's calm companion")
    print("  " + "=" * 54)
    print()


def print_menu():
    print("  What would you like to do?")
    print()
    print("    1.  Tag all my dumps  (organize raw text files)")
    print("    2.  Open the dashboard  (see everything at a glance)")
    print("    3.  What should I do next?  (3 suggested actions)")
    print("    4.  Analyze a chapter  (run the full analysis suite)")
    print("    5.  Analyze ALL chapters  (batch analysis)")
    print("    6.  Show project stats  (word count, file count)")
    print("    7.  Export a file  (to Word, markdown, or plain text)")
    print("    8.  Market research  (find comparable titles)")
    print("    9.  Find links between files  (what connects to what)")
    print("    10. Open the raw-dumps folder  (drop new files here)")
    print("    11. Quit")
    print()


def get_choice(prompt="  Pick a number: "):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return "11"


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


def find_text_files():
    """Find all text files in the writing folders."""
    files = []
    for folder in ["raw-dumps", "triage", "chapters", "drafts", "final"]:
        folder_path = PROJECT_ROOT / folder
        if folder_path.exists():
            for ext in ["*.txt", "*.md"]:
                files.extend(folder_path.glob(ext))
    return files


def pick_file(prompt="  Pick a file:"):
    """Let the user pick a file from a numbered list."""
    files = find_text_files()

    if not files:
        print("\n  No text files found.")
        print("  Drop .txt or .md files into the 'raw-dumps' folder first.")
        return None

    print(prompt)
    print()
    for i, f in enumerate(files, 1):
        rel = f.relative_to(PROJECT_ROOT)
        size = f.stat().st_size
        size_str = f"{size//1024}KB" if size >= 1024 else f"{size}B"
        print(f"    {i:2d}. {rel}  ({size_str})")
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
        print("    1. Open the 'raw-dumps' folder")
        print("    2. Drop your .txt or .md files in there")
        print("    3. Come back and run this again")
        print()
        pause()
        return

    print(f"  Found {len(files)} file(s) to tag.")
    print()
    input("  Press Enter to start tagging...")

    run_cli("label-all")


def action_dashboard():
    print_header()
    print("  OPENING DASHBOARD")
    print("  " + "-" * 52)
    print()
    print("  Generating your dashboard...")
    print()

    # Generate dashboard without auto-opening (we'll open it ourselves)
    from scribbler.dashboard.generator import generate
    html_path = generate()

    print(f"  Dashboard generated: {html_path}")
    print()
    print("  Opening in your browser...")

    # Open in browser
    webbrowser.open(f"file://{os.path.abspath(html_path)}")

    print()
    print("  The dashboard should now be open in your browser.")
    print("  You can close this window, or pick another option.")
    pause()


def action_next():
    print_header()
    run_cli("next")


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
    print("    1. Word document (.docx)")
    print("    2. Markdown (.md)")
    print("    3. Plain text (.txt)")
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


def main():
    while True:
        print_header()
        print_menu()

        choice = get_choice()

        if choice == "1":
            action_label_all()
        elif choice == "2":
            action_dashboard()
        elif choice == "3":
            action_next()
        elif choice == "4":
            action_analyze()
        elif choice == "5":
            action_analyze_all()
        elif choice == "6":
            action_stats()
        elif choice == "7":
            action_export()
        elif choice == "8":
            action_market()
        elif choice == "9":
            action_links()
        elif choice == "10":
            action_open_folder()
        elif choice == "11":
            print_header()
            print("  Happy scribbling.")
            print()
            print("  Your writing stays on your machine. Nothing leaves unless")
            print("  you use the LLM-assisted tagging (which uses Z.ai).")
            print()
            break
        else:
            print("\n  Pick a number from 1 to 11.")
            pause()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Happy scribbling.\n")
    except Exception as e:
        print(f"\n  Something went wrong: {e}")
        print()
        pause()
