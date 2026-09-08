#!/usr/bin/env python3
"""Shared paragraph/sentence indexer.

Used by:
- The reader view (Phase 3) to wrap each paragraph in <div id="para-N">.
- The analyzers (Phase 7) to compute `loc.paragraphs` for click-to-jump observations.
- The search (Phase 5) to translate character offsets back into paragraph numbers.

Design:
- Paragraphs are split on blank lines (one or more newlines between non-empty text).
- Sentences are split on a simple regex (period/exclamation/question followed by space or end).
- All offsets are character offsets into the original text.
- Paragraph and sentence indices are 1-based (paragraph 1 = first paragraph).
"""
import re
from typing import List, Dict, Any, Optional, Tuple

# Match a sentence-ending punctuation followed by whitespace + capital/quote
_SENTENCE_END = re.compile(r'(?<=[.!?])\s+(?=["\'A-Z])')


def split_paragraphs(text: str) -> List[Dict[str, Any]]:
    """Split text into paragraphs with character offsets.

    Returns a list of dicts (1-based paragraph number stored as `index`):
        [
          {"index": 1, "start": 0,  "end": 412, "text": "..."},
          {"index": 2, "start": 414, "end": 921, "text": "..."},
          ...
        ]

    Blank lines and pure-whitespace separators are not emitted as paragraphs.
    """
    if not text:
        return []
    # Normalize: split on runs of 2+ newlines (with optional whitespace between)
    # But we want to preserve original character offsets, so we walk through.
    paragraphs = []
    # Find runs of non-blank text separated by blank lines
    pos = 0
    # Match a paragraph: non-blank chars up to a blank line or end
    para_re = re.compile(r'[ \t]*([^\n].*?)(?=\n[ \t]*\n|\Z)', re.DOTALL)
    for m in para_re.finditer(text):
        para_text = m.group(1)
        # Strip trailing whitespace from the paragraph text
        para_text_stripped = para_text.rstrip()
        # Find the actual start (skip leading whitespace on the line)
        start = m.start(1)
        # Advance past leading whitespace
        while start < len(text) and text[start] in ' \t':
            start += 1
        end = start + len(para_text_stripped)
        paragraphs.append({
            "index": len(paragraphs) + 1,
            "start": start,
            "end": end,
            "text": para_text_stripped,
        })
        pos = m.end()
    return paragraphs


def split_sentences(paragraph_text: str) -> List[Dict[str, Any]]:
    """Split a single paragraph into sentences with character offsets.

    Returns a list of dicts:
        [
          {"index": 1, "start": 0, "end": 87, "text": "..."},
          ...
        ]
    """
    if not paragraph_text:
        return []
    sentences = []
    pos = 0
    # Use finditer to walk through sentence boundaries
    last_end = 0
    for m in _SENTENCE_END.finditer(paragraph_text):
        end = m.start()
        sent_text = paragraph_text[last_end:end].strip()
        if sent_text:
            sentences.append({
                "index": len(sentences) + 1,
                "start": last_end,
                "end": end,
                "text": sent_text,
            })
        last_end = m.end()
    # Tail
    if last_end < len(paragraph_text):
        sent_text = paragraph_text[last_end:].strip()
        if sent_text:
            sentences.append({
                "index": len(sentences) + 1,
                "start": last_end,
                "end": len(paragraph_text),
                "text": sent_text,
            })
    return sentences


def build_index(text: str) -> Dict[str, Any]:
    """Build a complete paragraph + sentence index of `text`.

    Returns:
        {
          "paragraphs": [
            {"index": 1, "start": 0, "end": 412, "text": "...",
             "sentences": [{"index": 1, "start": 0, "end": 87, "text": "..."}, ...]},
            ...
          ],
          "word_count": N,
          "char_count": N,
        }
    """
    paragraphs = split_paragraphs(text)
    for p in paragraphs:
        p["sentences"] = split_sentences(p["text"])
    word_count = len(text.split())
    return {
        "paragraphs": paragraphs,
        "word_count": word_count,
        "char_count": len(text),
    }


def paragraph_at_offset(index: Dict[str, Any], offset: int) -> Optional[int]:
    """Return the 1-based paragraph number that contains `offset`, or None."""
    for p in index["paragraphs"]:
        if p["start"] <= offset < p["end"]:
            return p["index"]
    # If offset is exactly at the end of the last paragraph, return it
    if index["paragraphs"] and offset == index["paragraphs"][-1]["end"]:
        return index["paragraphs"][-1]["index"]
    return None


def paragraphs_in_range(index: Dict[str, Any], start_offset: int, end_offset: int) -> List[int]:
    """Return all paragraph numbers that overlap the [start, end) character range."""
    out = []
    for p in index["paragraphs"]:
        if p["end"] <= start_offset:
            continue
        if p["start"] >= end_offset:
            break
        out.append(p["index"])
    return out


def find_paragraphs_containing(index: Dict[str, Any], term: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
    """Return all paragraphs whose text contains `term`.

    Each entry includes the paragraph index, the paragraph text, and a list of
    in-paragraph character offsets where the term appears (relative to the paragraph
    text, NOT the whole document).
    """
    if not term:
        return []
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(r'\b' + re.escape(term) + r'\b', flags)
    out = []
    for p in index["paragraphs"]:
        matches = list(pattern.finditer(p["text"]))
        if matches:
            out.append({
                "paragraph": p["index"],
                "char_offsets_in_paragraph": [m.start() for m in matches],
                "snippet": p["text"][:200] + ("…" if len(p["text"]) > 200 else ""),
            })
    return out


def make_loc(paragraphs: List[int], evidence_quote: str = "", sentences: List[int] = None,
             kind: str = None) -> Dict[str, Any]:
    """Build a structured `loc` dict for an observation.

    Args:
        paragraphs: 1-based paragraph numbers, inclusive range.
        evidence_quote: 1-2 sentence excerpt showing the pattern in context.
        sentences: optional 1-based sentence numbers (within the paragraph range).
        kind: optional kind override; otherwise inferred from paragraph list shape.
    """
    if not paragraphs:
        return None
    if kind is None:
        if len(paragraphs) == 1:
            kind = "paragraph"
        else:
            # Check if range is contiguous
            sorted_p = sorted(paragraphs)
            if sorted_p == list(range(sorted_p[0], sorted_p[-1] + 1)):
                kind = "paragraph_range"
            else:
                kind = "paragraph_list"
    loc = {
        "kind": kind,
        "paragraphs": sorted(paragraphs) if kind != "paragraph_list" else paragraphs,
        "evidence_quote": evidence_quote,
    }
    if sentences:
        loc["sentences"] = sentences
    return loc


def excerpt_for_paragraph(index: Dict[str, Any], para_num: int, padding: int = 80) -> str:
    """Return a snippet around the given paragraph number."""
    for p in index["paragraphs"]:
        if p["index"] == para_num:
            text = p["text"]
            if len(text) <= padding * 2:
                return text
            return "…" + text[:padding] + " … " + text[-padding:] + "…"
    return ""


def offset_to_paragraph_snippet(text: str, offset: int, padding: int = 80) -> Tuple[int, str]:
    """Given a character offset into the whole text, return (paragraph_number, snippet)."""
    idx = build_index(text)
    p = paragraph_at_offset(idx, offset)
    if p is None:
        return 0, ""
    return p, excerpt_for_paragraph(idx, p, padding)
