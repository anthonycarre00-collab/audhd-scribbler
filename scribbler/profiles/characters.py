#!/usr/bin/env python3
"""Character profiles — structured development cards for each character.

Each character has:
  - Identity (name, aliases, role, age, occupation, background, physical)
  - Personality (traits, strengths, weaknesses, fears, desires)
  - Voice (speech style, vocabulary, mannerisms)
  - Motivation (wants, needs, fears, objectives)
  - Arc (beginning, pressure, change, end)
  - Notes (free-form)
  - Appearances (auto-populated from manuscript — which chapters/paragraphs mention them)
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..project import manager
from ..manuscript import tree as manuscript_tree


def _conn():
    conn = manager.get_active_conn()
    if conn is None:
        raise RuntimeError("No active project")
    return conn


def list_characters() -> List[Dict]:
    """Return all characters (summary only — name, role, mention_count)."""
    conn = _conn()
    rows = conn.execute("SELECT id, name, aliases, role, provenance, created_at, updated_at FROM characters_v12 ORDER BY name").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if d.get("aliases"):
            try:
                d["aliases"] = json.loads(d["aliases"])
            except (json.JSONDecodeError, TypeError):
                d["aliases"] = []
        else:
            d["aliases"] = []
        # Count appearances
        d["appearance_count"] = _count_appearances(d["name"], d["aliases"])
        out.append(d)
    return out


def get_character(character_id: int) -> Optional[Dict]:
    """Return a single character with all fields."""
    conn = _conn()
    row = conn.execute("SELECT * FROM characters_v12 WHERE id = ?", (character_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    # Parse JSON fields
    for field in ("aliases", "personality", "voice", "motivation", "arc_structure"):
        if d.get(field):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = [] if field != "arc_structure" else {}
        else:
            d[field] = [] if field != "arc_structure" else {}
    # Get appearances
    d["appearances"] = get_appearances(d["name"], d.get("aliases", []))
    d["appearance_count"] = len(d["appearances"])
    return d


def create_character(data: Dict) -> Dict:
    """Create a new character. Returns the created character."""
    conn = _conn()
    now = datetime.now().isoformat()
    name = data.get("name", "").strip()
    if not name:
        return {"error": "Name is required"}
    # Check for existing
    existing = conn.execute("SELECT id FROM characters_v12 WHERE name = ?", (name,)).fetchone()
    if existing:
        return {"error": f"A character named '{name}' already exists"}
    # Serialize list/dict fields
    aliases = json.dumps(data.get("aliases", []), ensure_ascii=False) if data.get("aliases") else None
    personality = json.dumps(data.get("personality", []), ensure_ascii=False) if data.get("personality") else None
    voice = json.dumps(data.get("voice", {}), ensure_ascii=False) if data.get("voice") else None
    motivation = json.dumps(data.get("motivation", {}), ensure_ascii=False) if data.get("motivation") else None
    arc_structure = json.dumps(data.get("arc_structure", {}), ensure_ascii=False) if data.get("arc_structure") else None

    conn.execute("""
        INSERT INTO characters_v12
        (name, aliases, role, age, occupation, background, physical, personality, voice,
         motivation, arc_summary, arc_structure, notes, provenance, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name, aliases, data.get("role"), data.get("age"), data.get("occupation"),
        data.get("background"), data.get("physical"), personality, voice, motivation,
        data.get("arc_summary"), arc_structure, data.get("notes"),
        data.get("provenance", "author_confirmed"), now, now
    ))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return get_character(new_id)


def update_character(character_id: int, data: Dict) -> Optional[Dict]:
    """Update an existing character. Returns the updated character."""
    conn = _conn()
    now = datetime.now().isoformat()
    # Build SET clause from provided fields
    updates = []
    params = []
    field_map = {
        "name": "name", "role": "role", "age": "age", "occupation": "occupation",
        "background": "background", "physical": "physical", "arc_summary": "arc_summary",
        "notes": "notes",
    }
    json_fields = {"aliases": "aliases", "personality": "personality", "voice": "voice",
                   "motivation": "motivation", "arc_structure": "arc_structure"}
    for key, col in field_map.items():
        if key in data:
            updates.append(f"{col} = ?")
            params.append(data[key])
    for key, col in json_fields.items():
        if key in data:
            updates.append(f"{col} = ?")
            params.append(json.dumps(data[key], ensure_ascii=False) if data[key] else None)
    if not updates:
        return get_character(character_id)
    updates.append("updated_at = ?")
    params.append(now)
    params.append(character_id)
    conn.execute(f"UPDATE characters_v12 SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    return get_character(character_id)


def delete_character(character_id: int) -> bool:
    """Delete a character."""
    conn = _conn()
    conn.execute("DELETE FROM characters_v12 WHERE id = ?", (character_id,))
    conn.commit()
    return True


def get_appearances(name: str, aliases: List[str] = None) -> List[Dict]:
    """Find all chapters/paragraphs where this character appears.

    Searches manuscript_items content for the name (and aliases).
    Returns [{chapter_id, chapter_title, paragraph, snippet}].
    """
    conn = _conn()
    search_terms = [name] + (aliases or [])
    appearances = []
    chapters = conn.execute("SELECT id, title, content FROM manuscript_items WHERE type = 'chapter'").fetchall()
    for ch in chapters:
        if not ch["content"]:
            continue
        # Split into paragraphs
        import re
        paras = re.split(r'\n\s*\n', ch["content"])
        for i, para in enumerate(paras):
            para_lower = para.lower()
            for term in search_terms:
                if not term:
                    continue
                if re.search(r'\b' + re.escape(term.lower()) + r'\b', para_lower):
                    snippet = para[:150].strip()
                    if len(para) > 150:
                        snippet += "…"
                    appearances.append({
                        "chapter_id": ch["id"],
                        "chapter_title": ch["title"],
                        "paragraph": i + 1,
                        "snippet": snippet,
                    })
                    break  # Only count once per paragraph
    return appearances


def _count_appearances(name: str, aliases: List[str] = None) -> int:
    """Quick count of appearances (for list view)."""
    return len(get_appearances(name, aliases))


def auto_create_from_tags(chapter_id: int, characters: List[str]):
    """When a chapter is tagged, auto-create stub profiles for detected characters.

    Called from the tagger. Creates stub profiles (name only, provenance='suggested')
    for characters that don't already exist.
    """
    conn = _conn()
    now = datetime.now().isoformat()
    for name in characters:
        if not name or not isinstance(name, str):
            continue
        name = name.strip()
        if not name:
            continue
        # Check if a character with this name or alias already exists
        existing = conn.execute("SELECT id FROM characters_v12 WHERE name = ?", (name,)).fetchone()
        if existing:
            continue
        # Check aliases
        all_chars = conn.execute("SELECT id, aliases FROM characters_v12").fetchall()
        found = False
        for c in all_chars:
            if c["aliases"]:
                try:
                    alias_list = json.loads(c["aliases"])
                    if name.lower() in [a.lower() for a in alias_list]:
                        found = True
                        break
                except (json.JSONDecodeError, TypeError):
                    pass
        if found:
            continue
        # Create stub
        conn.execute("""
            INSERT INTO characters_v12 (name, provenance, created_at, updated_at)
            VALUES (?, 'suggested', ?, ?)
        """, (name, now, now))
    conn.commit()
