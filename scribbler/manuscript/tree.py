#!/usr/bin/env python3
"""Manuscript tree — CRUD for the hierarchical manuscript structure.

Items are stored in the `manuscript_items` table of the active project DB.
Types: book (root), part (folder), chapter (leaf with content), scene (leaf within chapter).

The tree is parent_id-based. sort_order determines ordering within a parent.
"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..project import manager


def _slugify(name: str) -> str:
    slug = re.sub(r'[^A-Za-z0-9._ -]+', '_', name).strip(' .')
    slug = re.sub(r'\s+', '-', slug)
    return slug.lower() or 'untitled'


def _conn():
    """Get the active project DB connection, or raise."""
    conn = manager.get_active_conn()
    if conn is None:
        raise RuntimeError("No active project — open or create one first")
    return conn


def get_tree() -> Dict:
    """Return the full manuscript tree as a nested dict.

    Structure:
      {
        "id": 1,
        "type": "book",
        "title": "Manuscript",
        "children": [
          {"id": 2, "type": "part", "title": "Part One", "children": [...]},
          ...
        ]
      }
    """
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM manuscript_items ORDER BY parent_id IS NULL DESC, parent_id, sort_order, id"
    ).fetchall()
    if not rows:
        return {"id": None, "type": "empty", "title": "No manuscript yet", "children": []}
    # Build a lookup
    by_id = {row["id"]: {**dict(row), "children": []} for row in rows}
    roots = []
    for row in rows:
        node = by_id[row["id"]]
        parent_id = row["parent_id"]
        if parent_id is None:
            roots.append(node)
        elif parent_id in by_id:
            by_id[parent_id]["children"].append(node)
    # Return the first root (there should be only one book)
    if len(roots) == 1:
        return roots[0]
    return {"id": None, "type": "forest", "title": "Manuscript", "children": roots}


def get_flat_list() -> List[Dict]:
    """Return a flat list of all manuscript items (no nesting)."""
    conn = _conn()
    rows = conn.execute(
        "SELECT id, parent_id, type, title, slug, sort_order, word_count, status, updated_at "
        "FROM manuscript_items ORDER BY parent_id IS NULL DESC, parent_id, sort_order"
    ).fetchall()
    return [dict(r) for r in rows]


def get_item(item_id: int) -> Optional[Dict]:
    """Return a single manuscript item by ID."""
    conn = _conn()
    row = conn.execute("SELECT * FROM manuscript_items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None


def create_book(title: str = "Manuscript") -> Dict:
    """Create the top-level book item (if it doesn't exist)."""
    conn = _conn()
    existing = conn.execute("SELECT * FROM manuscript_items WHERE type = 'book' LIMIT 1").fetchone()
    if existing:
        return dict(existing)
    now = datetime.now().isoformat()
    conn.execute("""
        INSERT INTO manuscript_items (parent_id, type, title, slug, sort_order, created_at)
        VALUES (NULL, 'book', ?, ?, 0, ?)
    """, (title, _slugify(title), now))
    conn.commit()
    return dict(conn.execute("SELECT * FROM manuscript_items WHERE id = last_insert_rowid()").fetchone())


def create_part(title: str, parent_id: Optional[int] = None) -> Dict:
    """Create a part (folder) under the book or another part."""
    conn = _conn()
    # If no parent_id, find the book
    if parent_id is None:
        book = conn.execute("SELECT id FROM manuscript_items WHERE type = 'book' LIMIT 1").fetchone()
        if not book:
            create_book()
            book = conn.execute("SELECT id FROM manuscript_items WHERE type = 'book' LIMIT 1").fetchone()
        parent_id = book["id"]
    now = datetime.now().isoformat()
    # Get next sort_order
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) as m FROM manuscript_items WHERE parent_id = ?", (parent_id,)
    ).fetchone()["m"]
    conn.execute("""
        INSERT INTO manuscript_items (parent_id, type, title, slug, sort_order, created_at)
        VALUES (?, 'part', ?, ?, ?, ?)
    """, (parent_id, title, _slugify(title), max_order + 1, now))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return dict(conn.execute("SELECT * FROM manuscript_items WHERE id = ?", (new_id,)).fetchone())


def create_chapter(title: str, parent_id: Optional[int] = None, content: str = "") -> Dict:
    """Create a chapter under a part (or the book if no parts exist)."""
    conn = _conn()
    # If no parent_id, find or create a default part
    if parent_id is None:
        book = conn.execute("SELECT id FROM manuscript_items WHERE type = 'book' LIMIT 1").fetchone()
        if not book:
            create_book()
            book = conn.execute("SELECT id FROM manuscript_items WHERE type = 'book' LIMIT 1").fetchone()
        # Use the first part under the book, or create one
        part = conn.execute(
            "SELECT id FROM manuscript_items WHERE type = 'part' AND parent_id = ? ORDER BY sort_order LIMIT 1",
            (book["id"],)
        ).fetchone()
        if part:
            parent_id = part["id"]
        else:
            # Create a default part
            new_part = create_part("Part One", book["id"])
            parent_id = new_part["id"]
    now = datetime.now().isoformat()
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) as m FROM manuscript_items WHERE parent_id = ?", (parent_id,)
    ).fetchone()["m"]
    wc = len(content.split()) if content else 0
    conn.execute("""
        INSERT INTO manuscript_items (parent_id, type, title, slug, sort_order, content, word_count, status, created_at, updated_at)
        VALUES (?, 'chapter', ?, ?, ?, ?, ?, 'seedling', ?, ?)
    """, (parent_id, title, _slugify(title), max_order + 1, content, wc, now, now))
    conn.commit()
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    return dict(conn.execute("SELECT * FROM manuscript_items WHERE id = ?", (new_id,)).fetchone())


def rename_item(item_id: int, new_title: str) -> Dict:
    """Rename an item."""
    conn = _conn()
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE manuscript_items SET title = ?, slug = ?, updated_at = ? WHERE id = ?
    """, (new_title, _slugify(new_title), now, item_id))
    conn.commit()
    return dict(conn.execute("SELECT * FROM manuscript_items WHERE id = ?", (item_id,)).fetchone())


def move_item(item_id: int, new_parent_id: Optional[int], new_sort_order: int) -> bool:
    """Move an item to a new parent and/or position."""
    conn = _conn()
    now = datetime.now().isoformat()
    conn.execute("""
        UPDATE manuscript_items SET parent_id = ?, sort_order = ?, updated_at = ? WHERE id = ?
    """, (new_parent_id, new_sort_order, now, item_id))
    conn.commit()
    return True


def delete_item(item_id: int) -> bool:
    """Delete an item and all its children (cascade)."""
    conn = _conn()
    # Recursive delete (children first)
    def _delete_recursive(item_id):
        children = conn.execute("SELECT id FROM manuscript_items WHERE parent_id = ?", (item_id,)).fetchall()
        for child in children:
            _delete_recursive(child["id"])
        conn.execute("DELETE FROM manuscript_items WHERE id = ?", (item_id,))
    _delete_recursive(item_id)
    conn.commit()
    return True


def duplicate_item(item_id: int) -> Optional[Dict]:
    """Duplicate an item (and its children). Returns the new item."""
    conn = _conn()
    now = datetime.now().isoformat()
    src = conn.execute("SELECT * FROM manuscript_items WHERE id = ?", (item_id,)).fetchone()
    if not src:
        return None
    # Get next sort_order under the same parent
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) as m FROM manuscript_items WHERE parent_id IS ?",
        (src["parent_id"],)
    ).fetchone()["m"]
    new_title = f"{src['title']} (copy)"
    conn.execute("""
        INSERT INTO manuscript_items (parent_id, type, title, slug, sort_order, content, word_count, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (src["parent_id"], src["type"], new_title, _slugify(new_title), max_order + 1,
          src["content"], src["word_count"], src["status"], now, now))
    new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    # Duplicate children recursively
    def _dup_children(src_id, new_parent_id):
        children = conn.execute("SELECT * FROM manuscript_items WHERE parent_id = ? ORDER BY sort_order", (src_id,)).fetchall()
        for i, child in enumerate(children):
            conn.execute("""
                INSERT INTO manuscript_items (parent_id, type, title, slug, sort_order, content, word_count, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_parent_id, child["type"], child["title"], child["slug"], i,
                  child["content"], child["word_count"], child["status"], now, now))
            child_new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            _dup_children(child["id"], child_new_id)
    _dup_children(item_id, new_id)
    conn.commit()
    return dict(conn.execute("SELECT * FROM manuscript_items WHERE id = ?", (new_id,)).fetchone())


def get_chapter_content(chapter_id: int) -> Optional[str]:
    """Return the content of a chapter."""
    conn = _conn()
    row = conn.execute("SELECT content FROM manuscript_items WHERE id = ? AND type = 'chapter'", (chapter_id,)).fetchone()
    return row["content"] if row else None


def save_chapter_content(chapter_id: int, content: str) -> Dict:
    """Save chapter content (autosave). Also creates a version snapshot."""
    conn = _conn()
    now = datetime.now().isoformat()
    wc = len(content.split()) if content else 0
    conn.execute("""
        UPDATE manuscript_items SET content = ?, word_count = ?, updated_at = ? WHERE id = ?
    """, (content, wc, now, chapter_id))
    # Create a version snapshot
    conn.execute("""
        INSERT INTO version_history (chapter_id, content, word_count, saved_at, reason)
        VALUES (?, ?, ?, ?, 'autosave')
    """, (chapter_id, content, wc, now))
    # Prune old versions (keep last 20)
    conn.execute("""
        DELETE FROM version_history WHERE id NOT IN (
            SELECT id FROM version_history WHERE chapter_id = ? ORDER BY saved_at DESC LIMIT 20
        ) AND chapter_id = ?
    """, (chapter_id, chapter_id))
    conn.commit()
    return {"ok": True, "word_count": wc, "saved_at": now}


def touch_chapter(chapter_id: int):
    """Mark a chapter as last opened (for 'Continue writing')."""
    conn = _conn()
    now = datetime.now().isoformat()
    conn.execute("UPDATE manuscript_items SET last_opened_at = ? WHERE id = ?", (now, chapter_id))
    conn.execute("UPDATE v12_project SET last_chapter_id = ? WHERE id = 1", (chapter_id,))
    conn.commit()


def get_last_opened_chapter() -> Optional[Dict]:
    """Return the last-opened chapter, or None."""
    conn = _conn()
    proj = conn.execute("SELECT last_chapter_id FROM v12_project WHERE id = 1").fetchone()
    if not proj or not proj["last_chapter_id"]:
        # Fall back to most recently updated chapter
        row = conn.execute(
            "SELECT * FROM manuscript_items WHERE type = 'chapter' ORDER BY updated_at DESC LIMIT 1"
        ).fetchone()
    else:
        row = conn.execute("SELECT * FROM manuscript_items WHERE id = ?", (proj["last_chapter_id"],)).fetchone()
        if not row:
            row = conn.execute(
                "SELECT * FROM manuscript_items WHERE type = 'chapter' ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
    return dict(row) if row else None


def get_version_history(chapter_id: int, limit: int = 20) -> List[Dict]:
    """Return version history for a chapter."""
    conn = _conn()
    rows = conn.execute(
        "SELECT id, word_count, saved_at, reason FROM version_history WHERE chapter_id = ? ORDER BY saved_at DESC LIMIT ?",
        (chapter_id, limit)
    ).fetchall()
    return [dict(r) for r in rows]


def restore_version(version_id: int) -> Optional[Dict]:
    """Restore a chapter to a previous version. Creates a new snapshot first."""
    conn = _conn()
    version = conn.execute("SELECT * FROM version_history WHERE id = ?", (version_id,)).fetchone()
    if not version:
        return None
    chapter_id = version["chapter_id"]
    # Save current state as a snapshot first
    current = conn.execute("SELECT content, word_count FROM manuscript_items WHERE id = ?", (chapter_id,)).fetchone()
    if current:
        now = datetime.now().isoformat()
        conn.execute("""
            INSERT INTO version_history (chapter_id, content, word_count, saved_at, reason)
            VALUES (?, ?, ?, ?, 'pre_restore')
        """, (chapter_id, current["content"], current["word_count"], now))
    # Restore
    now = datetime.now().isoformat()
    wc = len(version["content"].split()) if version["content"] else 0
    conn.execute("""
        UPDATE manuscript_items SET content = ?, word_count = ?, updated_at = ? WHERE id = ?
    """, (version["content"], wc, now, chapter_id))
    conn.commit()
    return dict(conn.execute("SELECT * FROM manuscript_items WHERE id = ?", (chapter_id,)).fetchone())
