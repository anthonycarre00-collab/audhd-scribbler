#!/usr/bin/env python3
"""Story/narrative arcs + scenes + relationships + timeline.

Consolidates Phase 5 (arcs/structure) into one module for efficiency.
"""
import json, re
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..project import manager


def _conn():
    conn = manager.get_active_conn()
    if conn is None:
        raise RuntimeError("No active project")
    return conn

# === ARCS ===

def list_arcs() -> List[Dict]:
    conn = _conn()
    rows = conn.execute("SELECT id, title, type, purpose, created_at FROM arcs ORDER BY title").fetchall()
    return [dict(r) for r in rows]

def get_arc(arc_id: int) -> Optional[Dict]:
    conn = _conn()
    row = conn.execute("SELECT * FROM arcs WHERE id = ?", (arc_id,)).fetchone()
    if not row: return None
    d = dict(row)
    for f in ("turning_points","major_beats"):
        if d.get(f):
            try: d[f] = json.loads(d[f])
            except: d[f] = []
        else: d[f] = []
    return d

def create_arc(data: Dict) -> Dict:
    conn = _conn()
    now = datetime.now().isoformat()
    name = data.get("title","").strip()
    if not name: return {"error":"Title required"}
    tp = json.dumps(data.get("turning_points",[]),ensure_ascii=False) if data.get("turning_points") else None
    mb = json.dumps(data.get("major_beats",[]),ensure_ascii=False) if data.get("major_beats") else None
    conn.execute("""INSERT INTO arcs (title,type,purpose,beginning,climax,resolution,turning_points,major_beats,notes,provenance,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",(name,data.get("type"),data.get("purpose"),data.get("beginning"),data.get("climax"),data.get("resolution"),tp,mb,data.get("notes"),data.get("provenance","author_confirmed"),now,now))
    conn.commit()
    return get_arc(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

def update_arc(arc_id: int, data: Dict) -> Optional[Dict]:
    conn = _conn()
    now = datetime.now().isoformat()
    updates=[]; params=[]
    for k in ("title","type","purpose","beginning","climax","resolution","notes"):
        if k in data: updates.append(f"{k}=?"); params.append(data[k])
    for k in ("turning_points","major_beats"):
        if k in data: updates.append(f"{k}=?"); params.append(json.dumps(data[k],ensure_ascii=False) if data[k] else None)
    if not updates: return get_arc(arc_id)
    updates.append("updated_at=?"); params.extend([now,arc_id])
    conn.execute(f"UPDATE arcs SET {','.join(updates)} WHERE id=?",params)
    conn.commit()
    return get_arc(arc_id)

def delete_arc(arc_id: int) -> bool:
    conn = _conn()
    conn.execute("DELETE FROM arcs WHERE id=?", (arc_id,)); conn.commit(); return True

# === RELATIONSHIPS ===

def list_relationships() -> List[Dict]:
    conn = _conn()
    rows = conn.execute("""SELECT r.*, a.name as char_a_name, b.name as char_b_name
        FROM relationships_v12 r
        JOIN characters_v12 a ON r.character_a_id=a.id
        JOIN characters_v12 b ON r.character_b_id=b.id
        ORDER BY a.name""").fetchall()
    return [dict(r) for r in rows]

def get_relationship(rel_id: int) -> Optional[Dict]:
    conn = _conn()
    row = conn.execute("""SELECT r.*, a.name as char_a_name, b.name as char_b_name
        FROM relationships_v12 r
        JOIN characters_v12 a ON r.character_a_id=a.id
        JOIN characters_v12 b ON r.character_b_id=b.id
        WHERE r.id=?""",(rel_id,)).fetchone()
    if not row: return None
    d = dict(row)
    for f in ("key_scenes",):
        if d.get(f):
            try: d[f] = json.loads(d[f])
            except: d[f] = []
        else: d[f] = []
    return d

def create_relationship(data: Dict) -> Dict:
    conn = _conn()
    now = datetime.now().isoformat()
    a_id = data.get("character_a_id"); b_id = data.get("character_b_id")
    if not a_id or not b_id: return {"error":"Both characters required"}
    if a_id == b_id: return {"error":"Cannot relate a character to themselves"}
    # Check for existing (either direction)
    existing = conn.execute("SELECT id FROM relationships_v12 WHERE (character_a_id=? AND character_b_id=?) OR (character_a_id=? AND character_b_id=?)",(a_id,b_id,b_id,a_id)).fetchone()
    if existing: return {"error":"Relationship already exists"}
    ks = json.dumps(data.get("key_scenes",[]),ensure_ascii=False) if data.get("key_scenes") else None
    conn.execute("""INSERT INTO relationships_v12 (character_a_id,character_b_id,relation_type,history,current_state,conflicts,key_scenes,notes,provenance,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",(a_id,b_id,data.get("relation_type"),data.get("history"),data.get("current_state"),data.get("conflicts"),ks,data.get("notes"),data.get("provenance","author_confirmed"),now,now))
    conn.commit()
    return get_relationship(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

def update_relationship(rel_id: int, data: Dict) -> Optional[Dict]:
    conn = _conn()
    now = datetime.now().isoformat()
    updates=[]; params=[]
    for k in ("relation_type","history","current_state","conflicts","notes"):
        if k in data: updates.append(f"{k}=?"); params.append(data[k])
    if "key_scenes" in data: updates.append("key_scenes=?"); params.append(json.dumps(data["key_scenes"],ensure_ascii=False) if data["key_scenes"] else None)
    if not updates: return get_relationship(rel_id)
    updates.append("updated_at=?"); params.extend([now,rel_id])
    conn.execute(f"UPDATE relationships_v12 SET {','.join(updates)} WHERE id=?",params)
    conn.commit()
    return get_relationship(rel_id)

def delete_relationship(rel_id: int) -> bool:
    conn = _conn()
    conn.execute("DELETE FROM relationships_v12 WHERE id=?", (rel_id,)); conn.commit(); return True

# === SCENES ===

def list_scenes(chapter_id: int) -> List[Dict]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM scenes WHERE chapter_id=? ORDER BY char_start",(chapter_id,)).fetchall()
    return [dict(r) for r in rows]

def create_scene(data: Dict) -> Dict:
    conn = _conn()
    chapter_id = data.get("chapter_id")
    if not chapter_id: return {"error":"Chapter ID required"}
    conn.execute("""INSERT INTO scenes (chapter_id,title,summary,place_id,time_marker,purpose,emotional_beat,arc_id,char_start,char_end,provenance)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",(chapter_id,data.get("title"),data.get("summary"),data.get("place_id"),data.get("time_marker"),data.get("purpose"),data.get("emotional_beat"),data.get("arc_id"),data.get("char_start",0),data.get("char_end",0),data.get("provenance","author_confirmed")))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return dict(conn.execute("SELECT * FROM scenes WHERE id=?", (new_id,)).fetchone())

def update_scene(scene_id: int, data: Dict) -> Optional[Dict]:
    conn = _conn()
    updates=[]; params=[]
    for k in ("title","summary","place_id","time_marker","purpose","emotional_beat","arc_id","char_start","char_end"):
        if k in data: updates.append(f"{k}=?"); params.append(data[k])
    if not updates: return None
    params.append(scene_id)
    conn.execute(f"UPDATE scenes SET {','.join(updates)} WHERE id=?",params)
    conn.commit()
    return dict(conn.execute("SELECT * FROM scenes WHERE id=?", (scene_id,)).fetchone())

def delete_scene(scene_id: int) -> bool:
    conn = _conn()
    conn.execute("DELETE FROM scenes WHERE id=?", (scene_id,)); conn.commit(); return True

# === TIMELINE ===

def get_timeline() -> Dict:
    """Build a lightweight timeline from chapter order + time_markers."""
    conn = _conn()
    chapters = conn.execute("SELECT id, title, content, sort_order FROM manuscript_items WHERE type='chapter' ORDER BY parent_id, sort_order").fetchall()
    entries = []
    for ch in chapters:
        content = ch["content"] or ""
        # Find time markers in this chapter
        markers = re.findall(r'\b(summer of \d{4}|spring of \d{4}|winter of \d{4}|fall of \d{4}|\d{4}|two weeks later|the day after|last week|next month|yesterday|tomorrow|in \d{4})\b', content, re.IGNORECASE)
        entries.append({
            "chapter_id": ch["id"],
            "chapter_title": ch["title"],
            "time_markers": list(set(markers)) if markers else [],
            "word_count": len(content.split()) if content else 0,
        })
    return {"entries": entries, "total": len(entries)}

# === NOTES ===

def list_notes(target_type: str = None, target_id: int = None) -> List[Dict]:
    conn = _conn()
    if target_type and target_id:
        rows = conn.execute("SELECT * FROM notes WHERE target_type=? AND target_id=? ORDER BY created_at DESC",(target_type,target_id)).fetchall()
    elif target_type:
        rows = conn.execute("SELECT * FROM notes WHERE target_type=? ORDER BY created_at DESC",(target_type,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notes ORDER BY created_at DESC LIMIT 100").fetchall()
    return [dict(r) for r in rows]

def create_note(data: Dict) -> Dict:
    conn = _conn()
    now = datetime.now().isoformat()
    target_type = data.get("target_type")
    content = data.get("content","").strip()
    if not target_type or not content: return {"error":"target_type and content required"}
    conn.execute("""INSERT INTO notes (target_type,target_id,target_chapter,target_paragraph,content,created_at,provenance)
        VALUES (?,?,?,?,?,?,?)""",(target_type,data.get("target_id"),data.get("target_chapter"),data.get("target_paragraph"),content,now,data.get("provenance","author_confirmed")))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return dict(conn.execute("SELECT * FROM notes WHERE id=?", (new_id,)).fetchone())

def delete_note(note_id: int) -> bool:
    conn = _conn()
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,)); conn.commit(); return True

# === FINDINGS (Phase 6) ===

def list_findings(status: str = None, source_type: str = None, source_id: int = None, limit: int = 100) -> List[Dict]:
    conn = _conn()
    clauses = []; params = []
    if status: clauses.append("status=?"); params.append(status)
    if source_type: clauses.append("source_type=?"); params.append(source_type)
    if source_id: clauses.append("source_id=?"); params.append(source_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    rows = conn.execute(f"SELECT * FROM analysis_findings{where} ORDER BY created_at DESC LIMIT ?", params).fetchall()
    return [dict(r) for r in rows]

def get_things_to_look_at(limit: int = 10) -> List[Dict]:
    """Return top N open findings across the project, prioritised."""
    conn = _conn()
    rows = conn.execute("""SELECT * FROM analysis_findings WHERE status='open'
        ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]

def update_finding_status(finding_id: int, status: str) -> Optional[Dict]:
    conn = _conn()
    now = datetime.now().isoformat()
    conn.execute("UPDATE analysis_findings SET status=?, resolved_at=? WHERE id=?", (status, now if status != "open" else None, finding_id))
    conn.commit()
    return dict(conn.execute("SELECT * FROM analysis_findings WHERE id=?", (finding_id,)).fetchone())

def create_finding(data: Dict) -> Dict:
    conn = _conn()
    now = datetime.now().isoformat()
    conn.execute("""INSERT INTO analysis_findings
        (source_type,source_id,source_chapter,source_paragraph,tool,category,observation,evidence,why_it_matters,suggested_improvement,status,provenance,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data.get("source_type"),data.get("source_id"),data.get("source_chapter"),data.get("source_paragraph"),
         data.get("tool"),data.get("category"),data.get("observation"),data.get("evidence"),data.get("why_it_matters"),
         data.get("suggested_improvement"),data.get("status","open"),data.get("provenance","suggested"),now))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return dict(conn.execute("SELECT * FROM analysis_findings WHERE id=?", (new_id,)).fetchone())

# === UNIFIED SEARCH (Phase 7) ===

def unified_search(query: str) -> Dict:
    """Search across manuscript, characters, places, themes, arcs, notes, findings."""
    if not query or len(query.strip()) < 2:
        return {"results": {}, "total": 0}
    conn = _conn()
    q = "%" + query.strip() + "%"
    results = {}

    # Manuscript chapters
    chapters = conn.execute("SELECT id, title, content FROM manuscript_items WHERE type='chapter' AND (title LIKE ? OR content LIKE ?)", (q, q)).fetchall()
    if chapters:
        results["manuscript"] = []
        for ch in chapters:
            # Find first matching paragraph
            content = ch["content"] or ""
            paras = re.split(r'\n\s*\n', content)
            for i, para in enumerate(paras):
                if query.lower() in para.lower():
                    snippet = para[:150].strip() + ("…" if len(para) > 150 else "")
                    results["manuscript"].append({"chapter_id": ch["id"], "chapter_title": ch["title"], "paragraph": i+1, "snippet": snippet})
                    break

    # Characters
    chars = conn.execute("SELECT id, name, role, background FROM characters_v12 WHERE name LIKE ? OR background LIKE ? OR notes LIKE ?", (q, q, q)).fetchall()
    if chars: results["characters"] = [{"id": r["id"], "name": r["name"], "role": r["role"]} for r in chars]

    # Places
    places = conn.execute("SELECT id, name, type FROM places_v12 WHERE name LIKE ? OR description LIKE ? OR notes LIKE ?", (q, q, q)).fetchall()
    if places: results["places"] = [{"id": r["id"], "name": r["name"], "type": r["type"]} for r in places]

    # Themes
    themes = conn.execute("SELECT id, name, category FROM themes_v12 WHERE name LIKE ? OR definition LIKE ? OR notes LIKE ?", (q, q, q)).fetchall()
    if themes: results["themes"] = [{"id": r["id"], "name": r["name"], "category": r["category"]} for r in themes]

    # Arcs
    arcs = conn.execute("SELECT id, title, type FROM arcs WHERE title LIKE ? OR purpose LIKE ? OR notes LIKE ?", (q, q, q)).fetchall()
    if arcs: results["arcs"] = [{"id": r["id"], "title": r["title"], "type": r["type"]} for r in arcs]

    # Notes
    notes = conn.execute("SELECT id, target_type, target_id, content FROM notes WHERE content LIKE ?", (q,)).fetchall()
    if notes: results["notes"] = [{"id": r["id"], "target_type": r["target_type"], "target_id": r["target_id"], "snippet": r["content"][:120]} for r in notes]

    # Findings
    findings = conn.execute("SELECT id, source_type, source_chapter, category, observation FROM analysis_findings WHERE observation LIKE ? OR evidence LIKE ? OR why_it_matters LIKE ?", (q, q, q)).fetchall()
    if findings: results["findings"] = [{"id": r["id"], "source_type": r["source_type"], "category": r["category"], "snippet": r["observation"][:120]} for r in findings]

    total = sum(len(v) for v in results.values())
    return {"results": results, "total": total, "query": query}
