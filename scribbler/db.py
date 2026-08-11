#!/usr/bin/env python3
"""SQLite database for indexing tagged files and analysis results."""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from .config import DB_PATH, DATA_DIR


def get_db() -> sqlite3.Connection:
    """Get a database connection, creating tables if needed."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        folder TEXT NOT NULL,
        word_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'seedling',
        chapter_no INTEGER,
        characters TEXT,  -- JSON array
        places TEXT,      -- JSON array
        era TEXT,
        beats TEXT,       -- JSON array
        themes TEXT,      -- JSON array
        voice TEXT,
        sensory TEXT,     -- JSON array
        continuity TEXT,  -- JSON array
        emotional_register TEXT,
        motifs TEXT,      -- JSON array
        research_claims TEXT,
        citations TEXT,
        comp_titles TEXT,
        strength_signal INTEGER DEFAULT 0,
        summary TEXT,
        dump_date TEXT,
        last_modified TEXT,
        last_analyzed TEXT
    );

    CREATE TABLE IF NOT EXISTS analysis_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        analysis_type TEXT NOT NULL,
        result_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(file_path, analysis_type)
    );

    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        aliases TEXT,  -- JSON array
        description TEXT,
        first_appearance TEXT,
        last_appearance TEXT,
        mention_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS places (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        aliases TEXT,
        description TEXT,
        first_appearance TEXT,
        mention_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        action TEXT NOT NULL,
        file_path TEXT,
        details TEXT
    );
    """)
    conn.commit()


def upsert_file(meta: Dict[str, Any]):
    """Insert or update a file's metadata."""
    import copy
    conn = get_db()
    # Work on a copy so we don't mutate the caller's dict
    db_meta = copy.deepcopy(meta)
    # Convert lists to JSON strings for SQLite storage
    for key in ["characters", "places", "beats", "themes", "sensory", "continuity", "motifs"]:
        if key in db_meta and isinstance(db_meta[key], list):
            db_meta[key] = json.dumps(db_meta[key], ensure_ascii=False)

    db_meta["last_modified"] = datetime.now().isoformat()
    columns = list(db_meta.keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_names = ", ".join(columns)
    update_clause = ", ".join([f"{c}=excluded.{c}" for c in columns if c != "path"])

    try:
        conn.execute(
            f"INSERT INTO files ({column_names}) VALUES ({placeholders}) ON CONFLICT(path) DO UPDATE SET {update_clause}",
            [db_meta.get(c) for c in columns]
        )
        conn.execute(
            "INSERT INTO activity_log (timestamp, action, file_path, details) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), "label", db_meta.get("path"), f"Tagged {db_meta.get('filename', '')}")
        )
        conn.commit()
    finally:
        conn.close()


def get_file(path: str) -> Optional[Dict]:
    """Get a file's metadata by path."""
    conn = get_db()
    row = conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        # Parse JSON arrays
        for key in ["characters", "places", "beats", "themes", "sensory", "continuity", "motifs"]:
            if d.get(key) and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except json.JSONDecodeError:
                    d[key] = []
        return d
    return None


def get_all_files(folder: str = None) -> List[Dict]:
    """Get all files, optionally filtered by folder."""
    conn = get_db()
    if folder:
        rows = conn.execute("SELECT * FROM files WHERE folder = ? ORDER BY last_modified DESC", (folder,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM files ORDER BY last_modified DESC").fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        for key in ["characters", "places", "beats", "themes", "sensory", "continuity", "motifs"]:
            if d.get(key) and isinstance(d[key], str):
                try:
                    d[key] = json.loads(d[key])
                except json.JSONDecodeError:
                    d[key] = []
        results.append(d)
    return results


def save_analysis(file_path: str, analysis_type: str, result: dict):
    """Save an analysis result."""
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO analysis_results (file_path, analysis_type, result_json, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(file_path, analysis_type) DO UPDATE SET result_json=excluded.result_json, created_at=excluded.created_at""",
            (file_path, analysis_type, json.dumps(result, ensure_ascii=False), datetime.now().isoformat())
        )
        conn.execute(
            "UPDATE files SET last_analyzed = ? WHERE path = ?",
            (datetime.now().isoformat(), file_path)
        )
        conn.execute(
            "INSERT INTO activity_log (timestamp, action, file_path, details) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), "analyze", file_path, f"Ran {analysis_type}")
        )
        conn.commit()
    finally:
        conn.close()


def get_analysis(file_path: str, analysis_type: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute(
        "SELECT result_json FROM analysis_results WHERE file_path = ? AND analysis_type = ?",
        (file_path, analysis_type)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["result_json"])
    return None


def log_activity(action: str, file_path: str = None, details: str = None):
    conn = get_db()
    conn.execute(
        "INSERT INTO activity_log (timestamp, action, file_path, details) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), action, file_path, details)
    )
    conn.commit()
    conn.close()


def get_recent_activity(limit: int = 20) -> List[Dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> Dict:
    """Get project statistics for dashboard."""
    conn = get_db()
    total_files = conn.execute("SELECT COUNT(*) as c FROM files").fetchone()["c"]
    total_words = conn.execute("SELECT COALESCE(SUM(word_count), 0) as c FROM files").fetchone()["c"]

    status_counts = {}
    for row in conn.execute("SELECT status, COUNT(*) as c FROM files GROUP BY status").fetchall():
        status_counts[row["status"]] = row["c"]

    folder_counts = {}
    for row in conn.execute("SELECT folder, COUNT(*) as c FROM files GROUP BY folder").fetchall():
        folder_counts[row["folder"]] = row["c"]

    # Stale drafts (not modified in 7+ days)
    stale = conn.execute(
        """SELECT * FROM files WHERE last_modified < datetime('now', '-7 days')
           AND folder IN ('chapters', 'drafts', 'final') ORDER BY last_modified DESC"""
    ).fetchall()

    conn.close()
    return {
        "total_files": total_files,
        "total_words": total_words,
        "status_counts": status_counts,
        "folder_counts": folder_counts,
        "stale_drafts": [dict(r) for r in stale],
    }
