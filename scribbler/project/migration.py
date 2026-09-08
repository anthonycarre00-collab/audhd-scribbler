#!/usr/bin/env python3
"""Migration: v11 → v12.

Imports existing v11 files (from the legacy `files` table in scribbler.db)
into the active v12 project as manuscript_items and brain_dumps.

Non-destructive: the v11 DB is preserved, only read from. The v12 project DB
is written to.
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import json
import shutil

from . import manager


def migrate_v11_to_active_project() -> Dict:
    """Migrate all v11 files into the currently active v12 project.

    Returns: {ok, migrated_count, skipped_count, errors: [...]}
    """
    info = manager.get_active_info()
    if not info:
        return {"ok": False, "error": "No active project — open or create one first"}

    conn = manager.get_active_conn()
    if conn is None:
        return {"ok": False, "error": "Could not connect to project DB"}

    # Read from the legacy v11 DB
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from scribbler import db as legacy_db
        from scribbler.file_io import read_text_file
    except Exception as e:
        return {"ok": False, "error": f"Could not import legacy DB: {e}"}

    legacy_files = legacy_db.get_all_files()
    if not legacy_files:
        return {"ok": True, "migrated_count": 0, "skipped_count": 0, "errors": [],
                "message": "No v11 files to migrate"}

    migrated = 0
    skipped = 0
    errors = []

    # Check if migration already happened (either manuscript_items or brain_dumps has data)
    existing_ms = conn.execute("SELECT COUNT(*) as c FROM manuscript_items").fetchone()["c"]
    existing_bd = conn.execute("SELECT COUNT(*) as c FROM brain_dumps").fetchone()["c"]
    if existing_ms > 0 or existing_bd > 0:
        return {"ok": True, "migrated_count": 0, "skipped_count": 0, "errors": [],
                "message": "Project already has items — migration skipped"}

    # Create default parts if needed
    now = datetime.now().isoformat()

    # Sort files: chapters/drafts/final → manuscript; raw-dumps/triage → brain_dumps
    manuscript_files = []
    brain_dump_files = []
    for f in legacy_files:
        folder = f.get("folder", "")
        if folder in ("chapters", "drafts", "final"):
            manuscript_files.append(f)
        elif folder in ("raw-dumps", "triage"):
            brain_dump_files.append(f)
        else:
            skipped += 1

    # Create a "Manuscript" top-level folder if we have chapters
    manuscript_root_id = None
    if manuscript_files:
        conn.execute("""
            INSERT INTO manuscript_items (parent_id, type, title, slug, sort_order, created_at)
            VALUES (NULL, 'book', 'Manuscript', 'manuscript', 0, ?)
        """, (now,))
        manuscript_root_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Create an "Inbox" pseudo-folder for brain dumps (they go in brain_dumps table)
    # Migrate manuscript files
    for i, f in enumerate(manuscript_files):
        try:
            path = Path(f["path"])
            content = ""
            if path.exists():
                try:
                    content = read_text_file(path)
                except Exception:
                    content = ""
                # Strip YAML frontmatter
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end != -1:
                        content = content[end + 3:].strip()

            import re
            slug = re.sub(r'[^A-Za-z0-9._ -]+', '_', f.get("filename", "untitled")).strip(' .')
            wc = len(content.split()) if content else 0
            status = f.get("status", "seedling")
            conn.execute("""
                INSERT INTO manuscript_items
                (parent_id, type, title, slug, sort_order, content, word_count, status, created_at, updated_at)
                VALUES (?, 'chapter', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (manuscript_root_id, f.get("filename", "untitled"), slug, i, content, wc, status, now, now))
            migrated += 1
        except Exception as e:
            errors.append(f"{f.get('filename', '?')}: {e}")

    # Migrate brain dumps
    for f in brain_dump_files:
        try:
            path = Path(f["path"])
            content = ""
            if path.exists():
                try:
                    content = read_text_file(path)
                except Exception:
                    content = ""
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end != -1:
                        content = content[end + 3:].strip()

            wc = len(content.split()) if content else 0
            tags = {
                "characters": f.get("characters", []),
                "places": f.get("places", []),
                "themes": f.get("themes", []),
                "era": f.get("era", ""),
                "voice": f.get("voice", ""),
                "emotional_register": f.get("emotional_register", ""),
            }
            conn.execute("""
                INSERT INTO brain_dumps (title, content, word_count, created_at, tagged_at, tags, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (f.get("filename", "untitled"), content, wc, now, now, json.dumps(tags, ensure_ascii=False), "tagged"))
            migrated += 1
        except Exception as e:
            errors.append(f"{f.get('filename', '?')}: {e}")

    conn.commit()
    return {
        "ok": True,
        "migrated_count": migrated,
        "skipped_count": skipped,
        "errors": errors,
        "message": f"Migrated {migrated} file(s) into the project",
    }
