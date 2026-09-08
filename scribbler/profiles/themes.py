#!/usr/bin/env python3
"""Theme profiles — structured development cards for each theme."""
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..project import manager


def _conn():
    conn = manager.get_active_conn()
    if conn is None:
        raise RuntimeError("No active project")
    return conn


def list_themes() -> List[Dict]:
    conn = _conn()
    rows = conn.execute("SELECT id, name, category, provenance, created_at, updated_at FROM themes_v12 ORDER BY name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["appearance_count"] = _count_appearances(d["name"])
        out.append(d)
    return out


def get_theme(theme_id: int) -> Optional[Dict]:
    conn = _conn()
    row = conn.execute("SELECT * FROM themes_v12 WHERE id = ?", (theme_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for field in ("related_ideas", "symbols", "motifs"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = []
        else:
            d[field] = []
    d["appearances"] = get_appearances(d["name"])
    d["appearance_count"] = len(d["appearances"])
    return d


def create_theme(data: Dict) -> Dict:
    conn = _conn()
    now = datetime.now().isoformat()
    name = data.get("name", "").strip()
    if not name:
        return {"error": "Name is required"}
    existing = conn.execute("SELECT id FROM themes_v12 WHERE name = ?", (name,)).fetchone()
    if existing:
        return {"error": f"A theme named '{name}' already exists"}
    json_fields = {"related_ideas": "related_ideas", "symbols": "symbols", "motifs": "motifs"}
    params = {}
    for key, col in json_fields.items():
        if key in data:
            params[col] = json.dumps(data[key], ensure_ascii=False) if data[key] else None
        else:
            params[col] = None
    conn.execute("""
        INSERT INTO themes_v12 (name, category, definition, related_ideas, symbols, motifs, evolution, notes, provenance, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, data.get("category"), data.get("definition"), params["related_ideas"],
          params["symbols"], params["motifs"], data.get("evolution"), data.get("notes"),
          data.get("provenance", "author_confirmed"), now, now))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return get_theme(new_id)


def update_theme(theme_id: int, data: Dict) -> Optional[Dict]:
    conn = _conn()
    now = datetime.now().isoformat()
    updates = []
    params = []
    field_map = {"name": "name", "category": "category", "definition": "definition", "evolution": "evolution", "notes": "notes"}
    for key, col in field_map.items():
        if key in data:
            updates.append(f"{col} = ?")
            params.append(data[key])
    for key in ("related_ideas", "symbols", "motifs"):
        if key in data:
            updates.append(f"{key} = ?")
            params.append(json.dumps(data[key], ensure_ascii=False) if data[key] else None)
    if not updates:
        return get_theme(theme_id)
    updates.append("updated_at = ?")
    params.append(now)
    params.append(theme_id)
    conn.execute(f"UPDATE themes_v12 SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    return get_theme(theme_id)


def delete_theme(theme_id: int) -> bool:
    conn = _conn()
    conn.execute("DELETE FROM themes_v12 WHERE id = ?", (theme_id,))
    conn.commit()
    return True


def get_appearances(name: str) -> List[Dict]:
    conn = _conn()
    appearances = []
    chapters = conn.execute("SELECT id, title, content FROM manuscript_items WHERE type = 'chapter'").fetchall()
    for ch in chapters:
        if not ch["content"]:
            continue
        paras = re.split(r'\n\s*\n', ch["content"])
        for i, para in enumerate(paras):
            if re.search(r'\b' + re.escape(name) + r'\b', para, re.IGNORECASE):
                snippet = para[:150].strip()
                if len(para) > 150:
                    snippet += "…"
                appearances.append({"chapter_id": ch["id"], "chapter_title": ch["title"], "paragraph": i + 1, "snippet": snippet})
                break
    return appearances


def _count_appearances(name: str) -> int:
    return len(get_appearances(name))
