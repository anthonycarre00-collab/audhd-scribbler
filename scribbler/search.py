#!/usr/bin/env python3
"""Search module for The Audhd Scribbler.

The core feature: query files by tags.
- By character (e.g., "Nathan")
- By place (e.g., "Colombia")
- By theme (e.g., "masking")
- By era
- By emotional register
- By status
- Multi-tag (combine filters)

This is what makes the tool actually useful for the writer's workflow:
they dump text here, tag it, then search to find relevant sections.
"""
from typing import Dict, List, Optional, Any
from collections import Counter, defaultdict

from . import db
from .config import PROJECT_ROOT
from .file_io import read_text_file
from pathlib import Path
import re


def get_all_values_for_tag(tag_type: str) -> List[Dict]:
    """Get all unique values for a tag type across all files.

    Args:
        tag_type: One of 'characters', 'places', 'themes', 'era',
                  'emotional_register', 'voice', 'status'

    Returns:
        List of {value, count} dicts, sorted by count (most frequent first)
    """
    all_files = db.get_all_files()
    value_counts = Counter()
    value_files = defaultdict(list)  # value -> list of filenames

    for f in all_files:
        if tag_type in ["characters", "places", "themes", "sensory", "continuity", "motifs"]:
            values = f.get(tag_type) or []
            for v in values:
                value_counts[v] += 1
                value_files[v].append(f.get("filename", ""))
        else:
            # Single-value tags (era, emotional_register, voice, status)
            val = f.get(tag_type)
            if val:
                value_counts[val] += 1
                value_files[val].append(f.get("filename", ""))

    return [
        {"value": v, "count": c, "files": value_files[v]}
        for v, c in value_counts.most_common()
    ]


def search_by_tag(tag_type: str, value: str) -> List[Dict]:
    """Find all files that have a specific tag value.

    Args:
        tag_type: 'characters', 'places', 'themes', etc.
        value: The specific value to search for (e.g., "Nathan")

    Returns:
        List of matching file dicts with metadata
    """
    all_files = db.get_all_files()
    matches = []

    for f in all_files:
        if tag_type in ["characters", "places", "themes", "sensory", "continuity", "motifs"]:
            values = f.get(tag_type) or []
            # Case-insensitive match
            if any(value.lower() in v.lower() for v in values):
                matches.append(f)
        else:
            # Single-value tags
            val = f.get(tag_type, "")
            if val and value.lower() in val.lower():
                matches.append(f)

    return matches


def search_multi(filters: Dict[str, str]) -> List[Dict]:
    """Search with multiple tag filters (AND logic).

    Args:
        filters: Dict of {tag_type: value} pairs. All must match.

    Returns:
        List of files matching ALL filters
    """
    all_files = db.get_all_files()
    matches = []

    for f in all_files:
        match = True
        for tag_type, value in filters.items():
            if tag_type in ["characters", "places", "themes", "sensory"]:
                values = f.get(tag_type) or []
                if not any(value.lower() in v.lower() for v in values):
                    match = False
                    break
            else:
                val = f.get(tag_type, "")
                if not val or value.lower() not in val.lower():
                    match = False
                    break
        if match:
            matches.append(f)

    return matches


def find_tag_in_file(file_path: str, tag_type: str, value: str) -> List[Dict]:
    """Find where in a file a tag value appears (which paragraphs).

    Uses word-boundary regex so 'mom' doesn't match 'moment'.
    Uses the passage indexer (Phase 2) for accurate paragraph numbers.

    Args:
        file_path: Path to the file
        tag_type: 'characters', 'places', 'themes'
        value: The value to find

    Returns:
        List of {paragraph, context, char_start, char_end} dicts
    """
    path = Path(file_path)
    if not path.exists():
        return []

    try:
        content = read_text_file(path)
    except Exception:
        return []

    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].strip()

    # Strip summary comments
    content = re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->', '', content).strip()

    from .passage import build_index, find_paragraphs_containing
    idx = build_index(content)
    matches = find_paragraphs_containing(idx, value, case_sensitive=False)

    occurrences = []
    for m in matches:
        para_num = m["paragraph"]
        # Find the actual offset within the paragraph for char_start
        para_text = next((p["text"] for p in idx["paragraphs"] if p["index"] == para_num), "")
        # Get the full paragraph text as context
        # Use ±120 chars around the first match
        if m.get("char_offsets_in_paragraph"):
            offset = m["char_offsets_in_paragraph"][0]
            start = max(0, offset - 80)
            end = min(len(para_text), offset + len(value) + 80)
            context = para_text[start:end].strip()
            if start > 0:
                context = "…" + context
            if end < len(para_text):
                context = context + "…"
        else:
            context = para_text[:200]

        occurrences.append({
            "paragraph": para_num,
            "context": context,
            "char_start": offset if m.get("char_offsets_in_paragraph") else 0,
            "char_end": (offset + len(value)) if m.get("char_offsets_in_paragraph") else len(value),
            "snippet": m.get("snippet", ""),
        })

    return occurrences


def search_tags_with_excerpts(tag_type: str, value: str) -> List[Dict]:
    """Combined search + excerpts in one call. Returns files with their matching paragraphs.

    Each result dict:
      {
        filename, path, word_count, status, era, voice, emotional_register,
        characters, places, themes,
        excerpts: [{ paragraph, context, char_start, char_end, snippet }]
      }
    """
    files = search_by_tag(tag_type, value)
    out = []
    for f in files:
        path = f.get("path")
        excerpts = []
        if path:
            # First try the tag_occurrences table (fast, indexed)
            from . import db
            occs = db.get_tag_occurrences(tag_type=tag_type, tag_value=value, file_path=path)
            if occs:
                # Deduplicate by paragraph (multiple LLM-tagged values may match the same string)
                seen_paras = set()
                for o in occs:
                    if o["paragraph"] not in seen_paras:
                        seen_paras.add(o["paragraph"])
                        excerpts.append({
                            "paragraph": o["paragraph"],
                            "context": o.get("snippet", "")[:300],
                            "char_start": o.get("char_start", 0),
                            "char_end": o.get("char_end", 0),
                            "snippet": o.get("snippet", "")[:200],
                        })
                excerpts.sort(key=lambda x: x["paragraph"])
            else:
                # Fallback: scan the file directly
                excerpts = find_tag_in_file(path, tag_type, value)
        out.append({
            "filename": f.get("filename", ""),
            "path": path,
            "word_count": f.get("word_count", 0),
            "status": f.get("status", ""),
            "era": f.get("era", ""),
            "voice": f.get("voice", ""),
            "emotional_register": f.get("emotional_register", ""),
            "characters": f.get("characters", []),
            "places": f.get("places", []),
            "themes": f.get("themes", []),
            "excerpts": excerpts,
            "excerpt_count": len(excerpts),
        })
    return out


def search_text_in_all_files(query: str, limit: int = 200) -> List[Dict]:
    """Free-text search across all indexed files. Uses FTS5 if available, falls back to Python loop.

    Returns matches grouped by file:
      [{ file_path, filename, matches: [{ paragraph, char_start, char_end, snippet }] }]
    """
    if not query or len(query.strip()) < 2:
        return []

    from . import db
    # Try FTS5 first
    try:
        fts_results = db.search_fts(query, limit=limit)
        if fts_results:
            # Group by file
            by_file = {}
            for r in fts_results:
                fp = r["file_path"]
                if fp not in by_file:
                    by_file[fp] = {
                        "file_path": fp,
                        "filename": r["filename"],
                        "matches": [],
                    }
                by_file[fp]["matches"].append({
                    "paragraph": r["paragraph"],
                    "char_start": r["char_start"],
                    "char_end": r["char_end"],
                    "snippet": r["snippet"],
                })
            return list(by_file.values())
    except Exception:
        pass

    # Fallback: Python loop over all files
    all_files = db.get_all_files()
    results = []
    pattern = re.compile(r'\b' + re.escape(query) + r'\b', re.IGNORECASE)
    from .passage import build_index, find_paragraphs_containing
    for f in all_files:
        path = f.get("path")
        if not path:
            continue
        p = Path(path)
        if not p.exists():
            continue
        try:
            content = read_text_file(p)
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    content = content[end + 3:].strip()
            content = re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->', '', content).strip()
            idx = build_index(content)
            matches = find_paragraphs_containing(idx, query, case_sensitive=False)
            if matches:
                results.append({
                    "file_path": path,
                    "filename": f.get("filename", p.name),
                    "matches": [{
                        "paragraph": m["paragraph"],
                        "char_start": m.get("char_offsets_in_paragraph", [0])[0],
                        "char_end": m.get("char_offsets_in_paragraph", [0])[0] + len(query),
                        "snippet": m.get("snippet", ""),
                    } for m in matches],
                })
        except Exception:
            continue
        if len(results) >= limit:
            break
    return results


def get_tag_coverage(file_path: str) -> Dict:
    """Get tag coverage info for a file — proves the whole document was analyzed.

    Returns:
        Dict with:
        - total_paragraphs: how many paragraphs in the file
        - paragraphs_with_tags: how many paragraphs contain at least one tagged entity
        - tag_distribution: {tag_type: {value: [paragraph_numbers]}}
        - chunks_analyzed: how many chunks the LLM processed (estimated from word count)
    """
    from . import db
    path = Path(file_path)
    if not path.exists():
        return {}

    try:
        content = read_text_file(path)
    except Exception:
        return {}

    # Strip YAML frontmatter
    body = content
    if body.startswith("---"):
        end = body.find("---", 3)
        if end != -1:
            body = body[end + 3:].strip()
    body = re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->', '', body).strip()

    # Get file metadata from DB
    file_meta = db.get_file(str(path.resolve()))
    if not file_meta:
        return {"total_paragraphs": len(re.split(r'\n\s*\n', body))}

    paragraphs = re.split(r'\n\s*\n', body)
    total_paragraphs = len(paragraphs)

    # For each tag type, find which paragraphs contain which values
    tag_distribution = {}
    paragraphs_with_any_tag = set()

    for tag_type in ["characters", "places", "themes"]:
        values = file_meta.get(tag_type) or []
        if not values:
            continue

        tag_distribution[tag_type] = {}
        for value in values:
            para_numbers = []
            for i, para in enumerate(paragraphs):
                if value.lower() in para.lower():
                    para_numbers.append(i + 1)
                    paragraphs_with_any_tag.add(i + 1)
            if para_numbers:
                tag_distribution[tag_type][value] = para_numbers

    # Estimate chunks analyzed (10k char chunks)
    word_count = file_meta.get("word_count", 0)
    char_count = len(body)
    chunks_analyzed = max(1, (char_count + 9999) // 10000)

    # Check if tags appear in different parts of the document
    # (beginning, middle, end) — proves full coverage
    if paragraphs_with_any_tag:
        tagged_thirds = set()
        for para_num in paragraphs_with_any_tag:
            third = (para_num - 1) * 3 // max(total_paragraphs, 1)
            tagged_thirds.add(third)
        coverage_spread = len(tagged_thirds)
    else:
        coverage_spread = 0

    return {
        "total_paragraphs": total_paragraphs,
        "paragraphs_with_tags": len(paragraphs_with_any_tag),
        "tag_coverage_pct": round(len(paragraphs_with_any_tag) / max(total_paragraphs, 1) * 100, 1),
        "tag_distribution": tag_distribution,
        "chunks_analyzed": chunks_analyzed,
        "coverage_spread": coverage_spread,  # 1=only beginning, 3=beginning+middle+end
        "spread_description": _describe_spread(coverage_spread),
    }


def _describe_spread(spread: int) -> str:
    """Human-readable description of tag coverage spread."""
    if spread == 0:
        return "No tags found in body text (tags may be from AI analysis only)"
    elif spread == 1:
        return "Tags found only in one part of the document (beginning, middle, OR end)"
    elif spread == 2:
        return "Tags found in two parts of the document (e.g., beginning + middle)"
    else:
        return "Tags found across the entire document (beginning, middle, AND end) — full coverage confirmed"


def format_search_results(results: List[Dict], tag_type: str, value: str) -> str:
    """Format search results for display."""
    if not results:
        return f"\n  No files found with {tag_type} matching '{value}'.\n"

    output = f"\n  Found {len(results)} file(s) with {tag_type} matching '{value}':\n\n"
    for i, f in enumerate(results, 1):
        name = f.get("filename", "unknown")
        word_count = f.get("word_count", 0)
        status = f.get("status", "")
        era = f.get("era", "")
        other_chars = [c for c in (f.get("characters") or []) if c.lower() != value.lower()]
        other_themes = f.get("themes") or []

        output += f"    {i}. {name}\n"
        output += f"       {word_count:,} words · status: {status}"
        if era:
            output += f" · era: {era}"
        output += "\n"
        if other_chars:
            output += f"       Also features: {', '.join(other_chars[:5])}\n"
        if other_themes:
            output += f"       Themes: {', '.join(other_themes[:5])}\n"
        output += "\n"

    return output
