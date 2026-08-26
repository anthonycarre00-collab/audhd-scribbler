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
        characters TEXT,
        places TEXT,
        era TEXT,
        beats TEXT,
        themes TEXT,
        voice TEXT,
        sensory TEXT,
        continuity TEXT,
        emotional_register TEXT,
        motifs TEXT,
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

    CREATE TABLE IF NOT EXISTS analysis_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT NOT NULL,
        analysis_type TEXT NOT NULL,
        result_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        aliases TEXT,
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
    db_meta = copy.deepcopy(meta)
    # Strip keys that aren't DB columns (prevents OperationalError)
    valid_columns = {"path","filename","folder","word_count","status","chapter_no","characters","places","era","beats","themes","voice","sensory","continuity","emotional_register","motifs","research_claims","citations","comp_titles","strength_signal","summary","dump_date","last_modified","last_analyzed"}
    db_meta = {k: v for k, v in db_meta.items() if k in valid_columns}
    for key in ["characters", "places", "beats", "themes", "sensory", "continuity", "motifs"]:
        if key in db_meta and isinstance(db_meta[key], list):
            db_meta[key] = json.dumps(db_meta[key], ensure_ascii=False)
    db_meta["last_modified"] = datetime.now().isoformat()
    columns = list(db_meta.keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_names = ", ".join(columns)
    update_clause = ", ".join([f"{c}=excluded.{c}" for c in columns if c != "path"])
    try:
        conn.execute(f"INSERT INTO files ({column_names}) VALUES ({placeholders}) ON CONFLICT(path) DO UPDATE SET {update_clause}", [db_meta.get(c) for c in columns])
        conn.execute("INSERT INTO activity_log (timestamp, action, file_path, details) VALUES (?, ?, ?, ?)", (datetime.now().isoformat(), "label", db_meta.get("path"), f"Tagged {db_meta.get('filename', '')}"))
        conn.commit()
    finally:
        conn.close()


def _decode_file_row(row):
    d = dict(row)
    for key in ["characters", "places", "beats", "themes", "sensory", "continuity", "motifs"]:
        if d.get(key) and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except json.JSONDecodeError:
                d[key] = []
    return d


def get_file(path: str) -> Optional[Dict]:
    conn = get_db()
    row = conn.execute("SELECT * FROM files WHERE path = ?", (path,)).fetchone()
    conn.close()
    return _decode_file_row(row) if row else None


def get_all_files(folder: str = None) -> List[Dict]:
    conn = get_db()
    if folder:
        rows = conn.execute("SELECT * FROM files WHERE folder = ? ORDER BY last_modified DESC", (folder,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM files ORDER BY last_modified DESC").fetchall()
    conn.close()
    return [_decode_file_row(row) for row in rows]


def save_analysis(file_path: str, analysis_type: str, result: dict):
    """Save analysis safely; retain the previous result in immutable history."""
    conn = get_db()
    now = datetime.now().isoformat()
    payload = json.dumps(result, ensure_ascii=False)
    try:
        previous = conn.execute("SELECT result_json, created_at FROM analysis_results WHERE file_path = ? AND analysis_type = ?", (file_path, analysis_type)).fetchone()
        if previous:
            conn.execute("INSERT INTO analysis_history (file_path, analysis_type, result_json, created_at) VALUES (?, ?, ?, ?)", (file_path, analysis_type, previous["result_json"], previous["created_at"]))
        conn.execute("""INSERT INTO analysis_results (file_path, analysis_type, result_json, created_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(file_path, analysis_type) DO UPDATE SET result_json=excluded.result_json, created_at=excluded.created_at""", (file_path, analysis_type, payload, now))
        conn.execute("UPDATE files SET last_analyzed = ? WHERE path = ?", (now, file_path))
        conn.execute("INSERT INTO activity_log (timestamp, action, file_path, details) VALUES (?, ?, ?, ?)", (now, "analyze", file_path, f"Ran {analysis_type}; previous result retained in history"))
        conn.commit()
    finally:
        conn.close()


def get_analysis(file_path: str, analysis_type: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT result_json FROM analysis_results WHERE file_path = ? AND analysis_type = ?", (file_path, analysis_type)).fetchone()
    conn.close()
    return json.loads(row["result_json"]) if row else None


def get_analysis_history(file_path: str, analysis_type: str) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT id, result_json, created_at FROM analysis_history WHERE file_path = ? AND analysis_type = ? ORDER BY created_at DESC", (file_path, analysis_type)).fetchall()
    conn.close()
    return [{"id": r["id"], "created_at": r["created_at"], "result": json.loads(r["result_json"])} for r in rows]


def log_activity(action: str, file_path: str = None, details: str = None):
    conn = get_db()
    conn.execute("INSERT INTO activity_log (timestamp, action, file_path, details) VALUES (?, ?, ?, ?)", (datetime.now().isoformat(), action, file_path, details))
    conn.commit()
    conn.close()


def get_recent_activity(limit: int = 20) -> List[Dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> Dict:
    conn = get_db()
    total_files = conn.execute("SELECT COUNT(*) as c FROM files").fetchone()["c"]
    total_words = conn.execute("SELECT COALESCE(SUM(word_count), 0) as c FROM files").fetchone()["c"]
    status_counts = {row["status"]: row["c"] for row in conn.execute("SELECT status, COUNT(*) as c FROM files GROUP BY status").fetchall()}
    folder_counts = {row["folder"]: row["c"] for row in conn.execute("SELECT folder, COUNT(*) as c FROM files GROUP BY folder").fetchall()}
    stale = conn.execute("SELECT * FROM files WHERE last_modified < datetime('now', '-7 days') AND folder IN ('chapters', 'drafts', 'final') ORDER BY last_modified DESC").fetchall()
    conn.close()
    return {"total_files": total_files, "total_words": total_words, "status_counts": status_counts, "folder_counts": folder_counts, "stale_drafts": [dict(r) for r in stale]}
