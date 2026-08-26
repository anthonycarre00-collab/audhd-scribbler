#!/usr/bin/env python3
"""Structural Anchors analyzer.

Manuscript-level: detects recurring opening/closing gestures across
chapters — whether the writer unconsciously returns to the same
opening or closing patterns (time-anchored, place-anchored, sensory,
memory-anchored, declarative, question, dialogue).
"""
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag
from .. import tagger


def analyze(chapters: List[Dict] = None, text: str = None) -> Dict:
    """Run structural anchors analysis. Pass chapters for manuscript-level."""
    if chapters:
        return _analyze_manuscript(chapters)
    elif text:
        return _analyze_single(text)
    else:
        return {"error": "No text or chapters provided"}


def _analyze_manuscript(chapters: List[Dict]) -> Dict:
    """Analyze opening/closing gestures across chapters."""
    total_words = sum(len(re.findall(r'\b\w+\b', ch.get("text", ""))) for ch in chapters)

    if total_words < 50 or len(chapters) < 2:
        return {"error": "Need at least 2 chapters for anchor analysis", "chapter_count": len(chapters)}

    opening_gestures = []
    closing_gestures = []
    opening_words = []
    closing_words = []

    for ch in chapters:
        text = ch.get("text", "")
        sentences = tagger.split_sentences(text)
        if not sentences:
            continue

        first_sentence = sentences[0]
        last_sentence = sentences[-1] if len(sentences) > 1 else sentences[0]

        opening_type = _classify_gesture(first_sentence)
        closing_type = _classify_gesture(last_sentence)

        opening_gestures.append({
            "chapter": ch.get("filename", "?"),
            "type": opening_type,
            "preview": first_sentence[:80] + ("..." if len(first_sentence) > 80 else ""),
        })
        closing_gestures.append({
            "chapter": ch.get("filename", "?"),
            "type": closing_type,
            "preview": last_sentence[:80] + ("..." if len(last_sentence) > 80 else ""),
        })

        # First 1-3 words
        words = re.findall(r'\b\w+\b', first_sentence)
        if words:
            opening_words.append(" ".join(words[:2]))
        words = re.findall(r'\b\w+\b', last_sentence)
        if words:
            closing_words.append(" ".join(words[-2:]))

    opening_type_counts = Counter(g["type"] for g in opening_gestures)
    closing_type_counts = Counter(g["type"] for g in closing_gestures)

    recurring_openers = _find_recurring_patterns(opening_words, chapters)
    recurring_closers = _find_recurring_patterns(closing_words, chapters)

    anchor_stability = _anchor_stability_score(opening_type_counts, closing_type_counts, len(chapters))

    observations = _generate_observations(opening_type_counts, closing_type_counts,
                                            recurring_openers, recurring_closers, anchor_stability)

    return {
        "scope": "manuscript",
        "chapter_count": len(chapters),
        "total_words": total_words,
        "opening_gestures": opening_gestures,
        "closing_gestures": closing_gestures,
        "opening_gesture_counts": dict(opening_type_counts),
        "closing_gesture_counts": dict(closing_type_counts),
        "recurring_openers": recurring_openers[:5],
        "recurring_closers": recurring_closers[:5],
        "anchor_stability_score": anchor_stability,
        "observations": observations,
        "summary": _generate_summary(len(chapters), total_words, opening_type_counts,
                                      closing_type_counts, anchor_stability),
    }


def _analyze_single(text: str) -> Dict:
    """Analyze opening/closing gestures of a single chapter."""
    sentences = tagger.split_sentences(text)
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 20 or not sentences:
        return {"error": "Text too short", "word_count": word_count}

    first = sentences[0]
    last = sentences[-1] if len(sentences) > 1 else sentences[0]

    opening_type = _classify_gesture(first)
    closing_type = _classify_gesture(last)

    # Generate simple observations for single-chapter
    observations = []
    observations.append(format_flag(
        "opening_gesture",
        "first sentence",
        f"the chapter opens with a {opening_type} gesture",
        "the opening gesture sets the reader's expectation for the chapter's mode",
        [
            "check if this gesture type serves the chapter's purpose",
            "try opening with a different gesture type to compare",
            "keep as-is if the opening gesture is intentional",
        ]
    ))
    observations.append(format_flag(
        "closing_gesture",
        "last sentence",
        f"the chapter closes with a {closing_type} gesture",
        "the closing gesture determines how the reader feels at the chapter's end",
        [
            "check if the closing gesture lands the emotional beat you want",
            "try a different closing gesture to compare effects",
            "keep as-is if the closing gesture is intentional",
        ]
    ))

    return {
        "scope": "chapter",
        "word_count": word_count,
        "sentence_count": len(sentences),
        "opening_gesture": opening_type,
        "opening_preview": first[:100] + ("..." if len(first) > 100 else ""),
        "closing_gesture": closing_type,
        "closing_preview": last[:100] + ("..." if len(last) > 100 else ""),
        "observations": observations,
        "note": "Single-chapter analysis. Run manuscript-level for cross-chapter patterns.",
        "summary": plain_summary(
            what=f"Structural anchor analysis of 1 chapter ({word_count} words)",
            found=f"Opening: {opening_type}. Closing: {closing_type}.",
            next_step="Run manuscript-level analysis to see if these gestures recur across chapters"
        ),
    }


def _classify_gesture(sentence: str) -> str:
    """Classify a sentence's gesture type."""
    s_lower = sentence.lower().strip()
    words = re.findall(r'\b\w+\b', s_lower)

    if not words:
        return "unknown"

    # Time-anchored
    if re.search(r'\b(in|during|that|the) (summer|winter|spring|fall|autumn)\b', s_lower):
        return "time_anchored"
    if re.search(r'\b(19[8-9]\d|20[0-2]\d)\b', s_lower):
        return "time_anchored"
    if re.search(r'\b(when i was|at age|aged)\b', s_lower):
        return "time_anchored"

    # Place-anchored
    if re.search(r'\b(the kitchen|the house|the room|the garden|the school|the hospital)\b', s_lower):
        return "place_anchored"

    # Memory-anchored
    if re.search(r'\b(i remember|i recall|looking back|memory|that day)\b', s_lower):
        return "memory_anchored"

    # Sensory
    if re.search(r'\b(the smell|the sound|the light|the taste|the feel)\b', s_lower):
        return "sensory_anchored"

    # Question
    if sentence.strip().endswith('?'):
        return "question"

    # Dialogue
    if sentence.strip().startswith('"') or sentence.strip().startswith('"'):
        return "dialogue"

    # Declarative (default)
    return "declarative"


def _find_recurring_patterns(openers: List[str], chapters: List[Dict]) -> List[Dict]:
    """Find opening/closing word patterns that recur across chapters."""
    pattern_counts = Counter(openers)
    recurring = []
    for pattern, count in pattern_counts.most_common(10):
        if count >= 2:
            chapters_with = [ch.get("filename", "?") for i, ch in enumerate(chapters)
                             if i < len(openers) and openers[i] == pattern]
            recurring.append({
                "pattern": pattern,
                "count": count,
                "chapters": chapters_with,
            })
    return recurring


def _anchor_stability_score(opening_counts, closing_counts, chapter_count) -> float:
    """How stable are the anchors? 0.0 = completely varied, 1.0 = all same."""
    if chapter_count == 0:
        return 0.0

    # Most common opening type as % of total
    if opening_counts:
        top_open = max(opening_counts.values()) / chapter_count
    else:
        top_open = 0

    if closing_counts:
        top_close = max(closing_counts.values()) / chapter_count
    else:
        top_close = 0

    return round((top_open + top_close) / 2, 2)


def _generate_observations(opening_counts, closing_counts, recurring_openers,
                            recurring_closers, stability) -> List[Dict]:
    observations = []

    if stability > 0.6:
        dominant_open = opening_counts.most_common(1)[0][0] if opening_counts else "unknown"
        observations.append(format_flag(
            "anchor_stability",
            "whole manuscript",
            f"anchor stability score is {stability} — chapters tend to open/close with the same gesture type ({dominant_open})",
            "high anchor stability creates consistency; readers know what kind of chapter to expect",
            [
                "check if the consistency is intentional (a deliberate structural choice)",
                "try varying one chapter's opening to see if it creates useful contrast",
                "keep as-is if the consistency is the manuscript's structural voice",
            ]
        ))
    elif stability < 0.3 and len(opening_counts) > 2:
        observations.append(format_flag(
            "anchor_variety",
            "whole manuscript",
            f"anchor stability score is {stability} — chapters open/close with varied gestures",
            "high variety keeps the reader alert; no two chapters feel structurally identical",
            [
                "check if the variety is intentional or if some chapters feel unfocused",
                "notice which gesture types work best for which kinds of content",
                "keep as-is — variety is a strength in most memoir structures",
            ]
        ))

    if recurring_openers:
        top = recurring_openers[0]
        observations.append(format_flag(
            "recurring_opener",
            f"{top['count']} chapter(s)",
            f"'{top['pattern']}' opens {top['count']} chapter(s) — a recurring structural opener",
            "recurring openers can be a deliberate refrain (powerful) or an unconscious habit (worth varying)",
            [
                "check if the recurrence is intentional (refrain, callback, structural motif)",
                "if unintentional, try opening one chapter differently",
                "keep as-is if the recurring opener is part of the manuscript's voice",
            ]
        ))

    if recurring_closers:
        top = recurring_closers[0]
        observations.append(format_flag(
            "recurring_closer",
            f"{top['count']} chapter(s)",
            f"'{top['pattern']}' closes {top['count']} chapter(s) — a recurring structural closer",
            "recurring closers create a sense of return; readers feel the chapter land in a familiar place",
            [
                "check if the recurring closer is doing deliberate thematic work",
                "notice if the closer shifts meaning across chapters (same words, different weight)",
                "keep as-is if the closer is an intentional structural anchor",
            ]
        ))

    return observations


def _generate_summary(chapter_count, total_words, opening_counts, closing_counts, stability) -> str:
    top_open = opening_counts.most_common(1)[0] if opening_counts else ("unknown", 0)
    top_close = closing_counts.most_common(1)[0] if closing_counts else ("unknown", 0)
    return plain_summary(
        what=f"Structural anchor analysis across {chapter_count} chapters ({total_words} words)",
        found=f"Dominant opening: {top_open[0]} ({top_open[1]}x). Dominant closing: {top_close[0]} ({top_close[1]}x). Stability: {stability}.",
        next_step="Review whether recurring gestures are intentional refrain or unconscious habit"
    )
