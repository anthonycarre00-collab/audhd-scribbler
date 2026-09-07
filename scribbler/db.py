#!/usr/bin/env python3
"""SQLite database for indexing tagged files and analysis results."""
import sqlite3
import re
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
        last_analyzed TEXT,
        relationships TEXT,
        emotional_beats TEXT,
        time_markers TEXT,
        objects TEXT
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

    CREATE TABLE IF NOT EXISTS tag_occurrences (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path   TEXT NOT NULL,
        tag_type    TEXT NOT NULL,
        tag_value   TEXT NOT NULL,
        paragraph   INTEGER,
        char_start  INTEGER,
        char_end    INTEGER,
        snippet     TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_occ_file ON tag_occurrences(file_path);
    CREATE INDEX IF NOT EXISTS idx_occ_tag  ON tag_occurrences(tag_type, tag_value);
    """)
    # Phase 13: add new columns to existing files table (migration for old DBs)
    try:
        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(files)").fetchall()}
        for new_col in ("relationships", "emotional_beats", "time_markers", "objects"):
            if new_col not in existing_cols:
                conn.execute(f"ALTER TABLE files ADD COLUMN {new_col} TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists or table doesn't exist yet
    # FTS5 virtual table — wrapped in try/except because some SQLite builds lack FTS5
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS file_content_fts USING fts5(
                file_path UNINDEXED,
                filename  UNINDEXED,
                body,
                tokenize='porter unicode61'
            )
        """)
    except sqlite3.OperationalError as e:
        # FTS5 not available — full-text search will fall back to Python loop
        pass
    conn.commit()


def clear_tag_occurrences(file_path: str):
    """Remove all tag occurrences for a file (called before re-indexing)."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM tag_occurrences WHERE file_path = ?", (file_path,))
        conn.execute("DELETE FROM file_content_fts WHERE file_path = ?", (file_path,))
        conn.commit()
    except sqlite3.OperationalError:
        # FTS table may not exist
        conn.execute("DELETE FROM tag_occurrences WHERE file_path = ?", (file_path,))
        conn.commit()
    finally:
        conn.close()


def add_tag_occurrence(file_path: str, tag_type: str, tag_value: str,
                       paragraph: int, char_start: int, char_end: int, snippet: str):
    """Insert a single tag occurrence."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO tag_occurrences (file_path, tag_type, tag_value, paragraph, char_start, char_end, snippet) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (file_path, tag_type, tag_value, paragraph, char_start, char_end, snippet)
        )
        conn.commit()
    finally:
        conn.close()


def index_file_content(file_path: str, filename: str, body: str):
    """Add or replace a file's body in the FTS5 index."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM file_content_fts WHERE file_path = ?", (file_path,))
        conn.execute("INSERT INTO file_content_fts (file_path, filename, body) VALUES (?, ?, ?)",
                     (file_path, filename, body))
        conn.commit()
    except sqlite3.OperationalError:
        # FTS5 unavailable
        pass
    finally:
        conn.close()


def search_fts(query: str, limit: int = 200) -> List[Dict]:
    """Full-text search via FTS5. Returns matches with paragraph numbers + snippets.

    Each match dict:
      { file_path, filename, paragraph, char_start, char_end, snippet }

    Paragraph is computed from the offset using a simple newline-count heuristic.
    If FTS5 is unavailable, returns an empty list (caller should fall back).
    """
    conn = get_db()
    try:
        # FTS5 MATCH returns the body; we then need to find the match position
        # Use snippet() and offsets() functions
        rows = conn.execute("""
            SELECT file_path, filename, body,
                   snippet(file_content_fts, 2, '<<', '>>', '…', 32) as snip
            FROM file_content_fts
            WHERE body MATCH ?
            LIMIT ?
        """, (query, limit)).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # For each row, locate the match within the body to compute paragraph number
    results = []
    for r in rows:
        body = r["body"]
        # Compute paragraph number from offset of <<marker
        offset = body.find("<<")
        if offset == -1:
            offset = 0
        # Paragraph = 1 + number of blank-line-paragraph-separators before offset
        upto = body[:offset]
        para = 1 + len(re.findall(r'\n\s*\n', upto))
        # Strip the markers from the snippet for display
        snip = r["snip"].replace("<<", "").replace(">>", "") if r["snip"] else body[max(0,offset-80):offset+120]
        results.append({
            "file_path": r["file_path"],
            "filename": r["filename"],
            "paragraph": para,
            "char_start": offset,
            "char_end": offset + len(query),
            "snippet": snip,
        })
    return results


def get_tag_occurrences(tag_type: str = None, tag_value: str = None,
                        file_path: str = None, limit: int = 500) -> List[Dict]:
    """Query tag occurrences by any combination of filters."""
    conn = get_db()
    clauses = []
    params = []
    if tag_type:
        clauses.append("tag_type = ?")
        params.append(tag_type)
    if tag_value:
        clauses.append("tag_value = ?")
        params.append(tag_value)
    if file_path:
        clauses.append("file_path = ?")
        params.append(file_path)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    rows = conn.execute(
        f"SELECT * FROM tag_occurrences{where} ORDER BY file_path, paragraph LIMIT ?",
        params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_character(name: str, aliases: List[str] = None, description: str = "",
                     first_appearance: str = "", mention_count: int = 0):
    """Insert or update a character."""
    conn = get_db()
    aliases_json = json.dumps(aliases or [], ensure_ascii=False)
    try:
        conn.execute("""
            INSERT INTO characters (name, aliases, description, first_appearance, mention_count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                aliases=excluded.aliases,
                description=excluded.description,
                last_appearance=excluded.first_appearance,
                mention_count=excluded.mention_count
        """, (name, aliases_json, description, first_appearance, mention_count))
        conn.commit()
    finally:
        conn.close()


def upsert_place(name: str, aliases: List[str] = None, description: str = "",
                 first_appearance: str = "", mention_count: int = 0):
    """Insert or update a place."""
    conn = get_db()
    aliases_json = json.dumps(aliases or [], ensure_ascii=False)
    try:
        conn.execute("""
            INSERT INTO places (name, aliases, description, first_appearance, mention_count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                aliases=excluded.aliases,
                description=excluded.description,
                mention_count=excluded.mention_count
        """, (name, aliases_json, description, first_appearance, mention_count))
        conn.commit()
    finally:
        conn.close()


def upsert_file(meta: Dict[str, Any]):
    """Insert or update a file's metadata."""
    import copy
    conn = get_db()
    db_meta = copy.deepcopy(meta)
    # Strip keys that aren't DB columns (prevents OperationalError)
    valid_columns = {"path","filename","folder","word_count","status","chapter_no","characters","places","era","beats","themes","voice","sensory","continuity","emotional_register","motifs","research_claims","citations","comp_titles","strength_signal","summary","dump_date","last_modified","last_analyzed","relationships","emotional_beats","time_markers","objects"}
    db_meta = {k: v for k, v in db_meta.items() if k in valid_columns}
    for key in ["characters", "places", "beats", "themes", "sensory", "continuity", "motifs", "relationships", "emotional_beats", "time_markers", "objects"]:
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
    for key in ["characters", "places", "beats", "themes", "sensory", "continuity", "motifs", "relationships", "emotional_beats", "time_markers", "objects"]:
        if d.get(key) and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except json.JSONDecodeError:
                d[key] = []
        elif d.get(key) is None:
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
