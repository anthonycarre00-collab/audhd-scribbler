#!/usr/bin/env python3
"""Place profiles — structured development cards for each place."""
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


def list_places() -> List[Dict]:
    conn = _conn()
    rows = conn.execute("SELECT id, name, type, provenance, created_at, updated_at FROM places_v12 ORDER BY name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["appearance_count"] = _count_appearances(d["name"])
        out.append(d)
    return out


def get_place(place_id: int) -> Optional[Dict]:
    conn = _conn()
    row = conn.execute("SELECT * FROM places_v12 WHERE id = ?", (place_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for field in ("sensory_signature",):
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


def create_place(data: Dict) -> Dict:
    conn = _conn()
    now = datetime.now().isoformat()
    name = data.get("name", "").strip()
    if not name:
        return {"error": "Name is required"}
    existing = conn.execute("SELECT id FROM places_v12 WHERE name = ?", (name,)).fetchone()
    if existing:
        return {"error": f"A place named '{name}' already exists"}
    sensory = json.dumps(data.get("sensory_signature", []), ensure_ascii=False) if data.get("sensory_signature") else None
    conn.execute("""
        INSERT INTO places_v12 (name, type, location, description, atmosphere, sensory_signature, history, significance, notes, provenance, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, data.get("type"), data.get("location"), data.get("description"),
          data.get("atmosphere"), sensory, data.get("history"), data.get("significance"),
          data.get("notes"), data.get("provenance", "author_confirmed"), now, now))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return get_place(new_id)


def update_place(place_id: int, data: Dict) -> Optional[Dict]:
    conn = _conn()
    now = datetime.now().isoformat()
    updates = []
    params = []
    field_map = {"name": "name", "type": "type", "location": "location", "description": "description",
                 "atmosphere": "atmosphere", "history": "history", "significance": "significance", "notes": "notes"}
    for key, col in field_map.items():
        if key in data:
            updates.append(f"{col} = ?")
            params.append(data[key])
    if "sensory_signature" in data:
        updates.append("sensory_signature = ?")
        params.append(json.dumps(data["sensory_signature"], ensure_ascii=False) if data["sensory_signature"] else None)
    if not updates:
        return get_place(place_id)
    updates.append("updated_at = ?")
    params.append(now)
    params.append(place_id)
    conn.execute(f"UPDATE places_v12 SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    return get_place(place_id)


def delete_place(place_id: int) -> bool:
    conn = _conn()
    conn.execute("DELETE FROM places_v12 WHERE id = ?", (place_id,))
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
