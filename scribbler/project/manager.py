#!/usr/bin/env python3
"""Project manager — create, open, list, and manage writing projects.

A project is a folder on disk containing:
  <project-folder>/
    project.scribbler      ← SQLite database (the index)
    manuscript/            ← Markdown files (the source of truth)
      <part-slug>/
        <chapter-slug>.md
    brain-dumps/           ← Inbox dumps as .md files
    characters/            ← Character notes (optional, .md)
    places/                ← Place notes (optional, .md)
    themes/                ← Theme notes (optional, .md)
    backups/               ← Version snapshots

The DB is the index; the .md files are the source of truth. If the DB is
corrupted, the .md files can be re-imported.
"""
import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Where projects live by default
PROJECTS_ROOT = Path.home() / "Documents" / "Audhd Scribbler Projects"

# Registry of recent projects (stored in a single JSON file in the app data dir)
REGISTRY_PATH = Path.home() / ".audhd-scribbler" / "projects.json"


def _slugify(name: str) -> str:
    """Convert a name to a filesystem-safe slug."""
    slug = re.sub(r'[^A-Za-z0-9._ -]+', '_', name).strip(' .')
    slug = re.sub(r'\s+', '-', slug)
    return slug or 'untitled'


def _ensure_registry():
    """Ensure the registry file and parent dir exist."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        REGISTRY_PATH.write_text('{"recent": []}', encoding='utf-8')


def _read_registry() -> Dict:
    _ensure_registry()
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return {"recent": []}


def _write_registry(data: Dict):
    _ensure_registry()
    REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _add_to_recent(project_path: str, project_name: str):
    """Add a project to the recent projects list (most recent first, max 10)."""
    data = _read_registry()
    recent = data.get("recent", [])
    # Remove if already present (by path)
    recent = [r for r in recent if r.get("path") != project_path]
    recent.insert(0, {
        "path": project_path,
        "name": project_name,
        "opened_at": datetime.now().isoformat(),
    })
    recent = recent[:10]  # keep last 10
    data["recent"] = recent
    _write_registry(data)


def create_project(name: str, parent_folder: Optional[str] = None) -> Dict:
    """Create a new writing project.

    Args:
        name: Human-readable project name (e.g. "My Memoir").
        parent_folder: Where to create the project folder. Defaults to PROJECTS_ROOT.

    Returns:
        {ok, path, name, message} or {ok: False, error}
    """
    try:
        slug = _slugify(name)
        parent = Path(parent_folder) if parent_folder else PROJECTS_ROOT
        parent.mkdir(parents=True, exist_ok=True)
        project_folder = parent / slug
        if project_folder.exists() and any(project_folder.iterdir()):
            return {"ok": False, "error": f"A project already exists at {project_folder}"}
        project_folder.mkdir(parents=True, exist_ok=True)

        # Create subfolders
        for sub in ("manuscript", "brain-dumps", "characters", "places", "themes", "backups"):
            (project_folder / sub).mkdir(exist_ok=True)

        # Create the SQLite DB
        db_path = project_folder / "project.scribbler"
        _init_project_db(db_path, name, str(project_folder))

        _add_to_recent(str(project_folder), name)
        return {
            "ok": True,
            "path": str(project_folder),
            "name": name,
            "message": f"Project '{name}' created at {project_folder}",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def open_project(path: str) -> Dict:
    """Open an existing project.

    Args:
        path: Path to the project folder.

    Returns:
        {ok, path, name, info} or {ok: False, error}
    """
    try:
        project_folder = Path(path)
        if not project_folder.exists():
            return {"ok": False, "error": f"Project folder not found: {path}"}
        db_path = project_folder / "project.scribbler"
        if not db_path.exists():
            return {"ok": False, "error": f"Not a Scribbler project (no project.scribbler): {path}"}

        info = _read_project_info(db_path)
        if not info:
            return {"ok": False, "error": "Could not read project info from DB"}
        # Update last_opened_at
        _touch_project(db_path)
        _add_to_recent(str(project_folder), info.get("name", project_folder.name))
        return {
            "ok": True,
            "path": str(project_folder),
            "name": info.get("name", project_folder.name),
            "info": info,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_recent_projects() -> Dict:
    """List recently opened projects."""
    data = _read_registry()
    recent = data.get("recent", [])
    # Filter to only those that still exist
    existing = []
    for r in recent:
        if Path(r.get("path", "")).exists():
            existing.append(r)
    if len(existing) != len(recent):
        data["recent"] = existing
        _write_registry(data)
    return {"ok": True, "recent": existing}


def get_active_project() -> Optional[Dict]:
    """Return the most recently opened project that still exists, or None."""
    data = _read_registry()
    recent = data.get("recent", [])
    for r in recent:
        if Path(r.get("path", "")).exists():
            return r
    return None


def get_project_db_path(project_folder: str) -> Path:
    """Return the DB path for a project folder."""
    return Path(project_folder) / "project.scribbler"


# === DB helpers (project-local DB, separate from the legacy scribbler.db) ===

def _get_project_conn(db_path: Path):
    """Open a connection to a project DB, creating v12 tables if needed."""
    import sqlite3
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_v12_tables(conn)
    return conn


def _init_project_db(db_path: Path, name: str, folder_path: str):
    """Create a fresh project DB with the v12 schema and a project row."""
    conn = _get_project_conn(db_path)
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO v12_project (id, name, folder_path, created_at, last_opened_at, theme, schema_version)
        VALUES (1, ?, ?, ?, ?, 'dark', 12)
    """, (name, folder_path, now, now))
    conn.commit()
    conn.close()


def _init_v12_tables(conn):
    """Create all v12 tables if they don't exist."""
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS v12_project (
        id              INTEGER PRIMARY KEY DEFAULT 1,
        name            TEXT NOT NULL,
        folder_path     TEXT NOT NULL,
        created_at      TEXT NOT NULL,
        last_opened_at  TEXT,
        last_chapter_id INTEGER,
        theme           TEXT DEFAULT 'dark',
        schema_version  INTEGER DEFAULT 12
    );

    CREATE TABLE IF NOT EXISTS manuscript_items (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id       INTEGER,
        type            TEXT NOT NULL,
        title           TEXT NOT NULL,
        slug            TEXT,
        sort_order      INTEGER DEFAULT 0,
        content         TEXT,
        word_count      INTEGER DEFAULT 0,
        status          TEXT DEFAULT 'seedling',
        created_at      TEXT NOT NULL,
        updated_at      TEXT,
        last_opened_at  TEXT,
        FOREIGN KEY (parent_id) REFERENCES manuscript_items(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_ms_parent ON manuscript_items(parent_id, sort_order);

    CREATE TABLE IF NOT EXISTS brain_dumps (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT,
        content         TEXT NOT NULL,
        word_count      INTEGER DEFAULT 0,
        created_at      TEXT NOT NULL,
        tagged_at       TEXT,
        tags            TEXT,
        status          TEXT DEFAULT 'unprocessed',
        promoted_to     INTEGER
    );

    CREATE TABLE IF NOT EXISTS characters_v12 (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL UNIQUE,
        aliases         TEXT,
        role            TEXT,
        age             TEXT,
        occupation      TEXT,
        background      TEXT,
        physical        TEXT,
        personality     TEXT,
        voice           TEXT,
        motivation      TEXT,
        arc_summary     TEXT,
        arc_structure   TEXT,
        notes           TEXT,
        provenance      TEXT DEFAULT 'author_confirmed',
        created_at      TEXT NOT NULL,
        updated_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS places_v12 (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL UNIQUE,
        type            TEXT,
        location        TEXT,
        description     TEXT,
        atmosphere      TEXT,
        sensory_signature TEXT,
        history         TEXT,
        significance    TEXT,
        notes           TEXT,
        provenance      TEXT DEFAULT 'author_confirmed',
        created_at      TEXT NOT NULL,
        updated_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS themes_v12 (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL UNIQUE,
        category        TEXT,
        definition      TEXT,
        related_ideas   TEXT,
        symbols         TEXT,
        motifs          TEXT,
        evolution       TEXT,
        notes           TEXT,
        provenance      TEXT DEFAULT 'author_confirmed',
        created_at      TEXT NOT NULL,
        updated_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS arcs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        title           TEXT NOT NULL,
        type            TEXT,
        purpose         TEXT,
        beginning       TEXT,
        climax          TEXT,
        resolution      TEXT,
        turning_points  TEXT,
        major_beats     TEXT,
        notes           TEXT,
        provenance      TEXT DEFAULT 'author_confirmed',
        created_at      TEXT NOT NULL,
        updated_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS relationships_v12 (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        character_a_id  INTEGER NOT NULL,
        character_b_id  INTEGER NOT NULL,
        relation_type   TEXT,
        history         TEXT,
        current_state   TEXT,
        conflicts       TEXT,
        key_scenes      TEXT,
        notes           TEXT,
        provenance      TEXT DEFAULT 'author_confirmed',
        created_at      TEXT NOT NULL,
        updated_at      TEXT
    );

    CREATE TABLE IF NOT EXISTS scenes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id      INTEGER NOT NULL,
        title           TEXT,
        summary         TEXT,
        place_id        INTEGER,
        time_marker     TEXT,
        purpose         TEXT,
        emotional_beat  TEXT,
        arc_id          INTEGER,
        char_start      INTEGER,
        char_end        INTEGER,
        provenance      TEXT DEFAULT 'author_confirmed'
    );

    CREATE TABLE IF NOT EXISTS notes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        target_type     TEXT NOT NULL,
        target_id       INTEGER,
        target_chapter  INTEGER,
        target_paragraph INTEGER,
        content         TEXT NOT NULL,
        created_at      TEXT NOT NULL,
        provenance      TEXT DEFAULT 'author_confirmed'
    );
    CREATE INDEX IF NOT EXISTS idx_notes_target ON notes(target_type, target_id);

    CREATE TABLE IF NOT EXISTS analysis_findings (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type     TEXT NOT NULL,
        source_id       INTEGER,
        source_chapter  INTEGER,
        source_paragraph INTEGER,
        tool            TEXT NOT NULL,
        category        TEXT NOT NULL,
        observation     TEXT NOT NULL,
        evidence        TEXT,
        why_it_matters  TEXT,
        suggested_improvement TEXT,
        status          TEXT DEFAULT 'open',
        provenance      TEXT DEFAULT 'suggested',
        created_at      TEXT NOT NULL,
        resolved_at     TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_findings_source ON analysis_findings(source_type, source_id);
    CREATE INDEX IF NOT EXISTS idx_findings_status ON analysis_findings(status);

    CREATE TABLE IF NOT EXISTS version_history (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id      INTEGER NOT NULL,
        content         TEXT NOT NULL,
        word_count      INTEGER,
        saved_at        TEXT NOT NULL,
        reason          TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_version_chapter ON version_history(chapter_id, saved_at);

    CREATE TABLE IF NOT EXISTS writing_sessions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        session_date    TEXT NOT NULL,
        chapter_id      INTEGER,
        words_written   INTEGER DEFAULT 0,
        duration_seconds INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS editor_prefs (
        key             TEXT PRIMARY KEY,
        value           TEXT
    );

    CREATE TABLE IF NOT EXISTS tag_occurrences (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        chapter_id  INTEGER,
        tag_type    TEXT NOT NULL,
        tag_value   TEXT NOT NULL,
        paragraph   INTEGER,
        char_start  INTEGER,
        char_end    INTEGER,
        snippet     TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_occ_chapter ON tag_occurrences(chapter_id);
    CREATE INDEX IF NOT EXISTS idx_occ_tag ON tag_occurrences(tag_type, tag_value);

    CREATE VIRTUAL TABLE IF NOT EXISTS chapter_content_fts USING fts5(
        chapter_id UNINDEXED,
        title UNINDEXED,
        body
    );
    """)
    conn.commit()


def _read_project_info(db_path: Path) -> Optional[Dict]:
    """Read the project row from the DB."""
    try:
        conn = _get_project_conn(db_path)
        row = conn.execute("SELECT * FROM v12_project WHERE id = 1").fetchone()
        conn.close()
        if not row:
            return None
        return dict(row)
    except Exception:
        return None


def _touch_project(db_path: Path):
    """Update last_opened_at."""
    conn = _get_project_conn(db_path)
    conn.execute("UPDATE v12_project SET last_opened_at = ? WHERE id = 1",
                 (datetime.now().isoformat(),))
    conn.commit()
    conn.close()


# === Active project (in-memory) ===

_ACTIVE_PROJECT: Optional[Dict] = None
_ACTIVE_CONN = None  # Open connection to the active project DB


def set_active_project(project_info: Optional[Dict]):
    """Set the in-memory active project. Pass None to close."""
    global _ACTIVE_PROJECT, _ACTIVE_CONN
    if _ACTIVE_CONN is not None:
        try:
            _ACTIVE_CONN.close()
        except Exception:
            pass
        _ACTIVE_CONN = None
    _ACTIVE_PROJECT = project_info
    if project_info:
        db_path = get_project_db_path(project_info["path"])
        _ACTIVE_CONN = _get_project_conn(db_path)


def get_active_conn():
    """Get a connection to the active project DB. Returns None if no active project."""
    global _ACTIVE_CONN
    if _ACTIVE_CONN is None:
        return None
    # Verify the connection is still alive
    try:
        _ACTIVE_CONN.execute("SELECT 1").fetchone()
    except Exception:
        # Reconnect
        if _ACTIVE_PROJECT:
            db_path = get_project_db_path(_ACTIVE_PROJECT["path"])
            _ACTIVE_CONN = _get_project_conn(db_path)
        else:
            return None
    return _ACTIVE_CONN


def get_active_info() -> Optional[Dict]:
    """Return info about the active project, or None."""
    return _ACTIVE_PROJECT
