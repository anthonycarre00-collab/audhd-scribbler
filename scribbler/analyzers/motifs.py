#!/usr/bin/env python3
"""Motifs & Echoes analyzer.

Manuscript-level: detects recurring concrete nouns, phrase echoes, and
sensory motif clusters ACROSS chapters. Distinct from repetition.py
(which surfaces noise within a single text) — motifs finds meaningful
recurrence across the whole manuscript.
"""
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag
from .. import tagger
from ..config import SENSORY_CATEGORIES


def analyze(chapters: List[Dict] = None, text: str = None) -> Dict:
    """Run motif analysis. Either pass chapters (manuscript-level) or text (single chapter).

    Args:
        chapters: List of dicts with 'filename' and 'text' keys (manuscript-level)
        text: Single text string (chapter-level fallback)
    """
    if chapters:
        return _analyze_manuscript(chapters)
    elif text:
        return _analyze_single(text)
    else:
        return {"error": "No text or chapters provided"}


def _analyze_manuscript(chapters: List[Dict]) -> Dict:
    """Analyze motifs across multiple chapters."""
    total_words = sum(len(re.findall(r'\b\w+\b', ch.get("text", ""))) for ch in chapters)

    if total_words < 50:
        return {"error": "Not enough text for motif analysis", "total_words": total_words}

    # Collect concrete nouns recurring across chapters
    cross_chapter_nouns = _cross_chapter_recurring_nouns(chapters)
    phrase_echoes = _cross_chapter_phrase_echoes(chapters)
    sensory_clusters = _sensory_motif_clusters(chapters)
    orphan_motifs = _orphan_motifs(chapters, cross_chapter_nouns)

    observations = _generate_observations(cross_chapter_nouns, phrase_echoes,
                                           sensory_clusters, orphan_motifs, len(chapters))

    return {
        "scope": "manuscript",
        "chapter_count": len(chapters),
        "total_words": total_words,
        "candidate_motifs": cross_chapter_nouns[:15],
        "phrase_echoes": phrase_echoes[:10],
        "sensory_motif_clusters": sensory_clusters[:8],
        "orphan_motifs": orphan_motifs[:5],
        "observations": observations,
        "summary": _generate_summary(len(chapters), total_words, cross_chapter_nouns,
                                      phrase_echoes, sensory_clusters),
    }


def _analyze_single(text: str) -> Dict:
    """Analyze motifs within a single chapter (limited but useful)."""
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 50:
        return {"error": "Text too short for motif analysis", "word_count": word_count}

    # Find recurring concrete nouns
    content_words = [w.lower() for w in words if len(w) > 4 and w.lower() not in _STOPWORDS]
    word_freq = Counter(content_words)
    recurring = [{"word": w, "count": c} for w, c in word_freq.most_common(20) if c >= 3]

    # Find phrase echoes (3-5 word phrases)
    phrases = _find_phrase_echoes_single(text)

    # Sensory motifs
    sensory = _sensory_in_single(text)

    return {
        "scope": "chapter",
        "word_count": word_count,
        "candidate_motifs": recurring,
        "phrase_echoes": phrases,
        "sensory_motifs": sensory,
        "note": "Single-chapter motif analysis. Run manuscript-level analysis for cross-chapter motifs.",
        "summary": _generate_summary(1, word_count, recurring, phrases, sensory),
    }


_STOPWORDS = set("the a an and or but if then than so because as of to in on at for from by with about into through during before after above below is are was were be been being have has had do does did this that these those it its i me my mine we us our you your he him his she her they their what which who when where why how not no very just only more most some any all each every both other same can could will would should may might must one two three first second third".split())


def _cross_chapter_recurring_nouns(chapters: List[Dict]) -> List[Dict]:
    """Find concrete nouns that recur across multiple chapters."""
    chapter_nouns = {}
    for ch in chapters:
        text = ch.get("text", "")
        words = re.findall(r'\b\w+\b', text.lower())
        content = set(w for w in words if len(w) > 4 and w not in _STOPWORDS)
        chapter_nouns[ch.get("filename", "?")] = content

    # Find words appearing in 2+ chapters
    word_chapters = defaultdict(list)
    for filename, nouns in chapter_nouns.items():
        for noun in nouns:
            word_chapters[noun].append(filename)

    candidates = []
    for word, files in word_chapters.items():
        if len(files) >= 2:
            candidates.append({
                "image": word,
                "chapters": files,
                "chapter_count": len(files),
                "total_occurrences": sum(1 for ch in chapters if word in ch.get("text", "").lower()),
            })

    return sorted(candidates, key=lambda x: x["chapter_count"], reverse=True)


def _cross_chapter_phrase_echoes(chapters: List[Dict]) -> List[Dict]:
    """Find 3-5 word phrases that echo across chapters."""
    phrase_chapters = defaultdict(list)

    for ch in chapters:
        text = ch.get("text", "")
        words = [w.lower() for w in re.findall(r'\b\w+\b', text)]
        content_words = [w for w in words if w not in _STOPWORDS and len(w) > 3]

        # 4-grams
        for i in range(len(content_words) - 3):
            phrase = " ".join(content_words[i:i+4])
            if len(phrase) > 15:
                phrase_chapters[phrase].append(ch.get("filename", "?"))

    echoes = []
    for phrase, files in phrase_chapters.items():
        unique_files = list(set(files))
        if len(unique_files) >= 2:
            echoes.append({
                "phrase": phrase,
                "chapters": unique_files,
                "chapter_count": len(unique_files),
            })

    return sorted(echoes, key=lambda x: x["chapter_count"], reverse=True)


def _sensory_motif_clusters(chapters: List[Dict]) -> List[Dict]:
    """Find sensory words that recur across chapters tied to specific objects."""
    clusters = []
    for sense, words in SENSORY_CATEGORIES.items():
        sense_chapters = defaultdict(list)
        for ch in chapters:
            text = ch.get("text", "").lower()
            for w in words:
                if w in text:
                    sense_chapters[w].append(ch.get("filename", "?"))

        for word, files in sense_chapters.items():
            if len(set(files)) >= 2:
                clusters.append({
                    "sense": sense,
                    "word": word,
                    "chapters": list(set(files)),
                    "chapter_count": len(set(files)),
                })

    return sorted(clusters, key=lambda x: x["chapter_count"], reverse=True)


def _orphan_motifs(chapters: List[Dict], recurring_nouns: List[Dict]) -> List[Dict]:
    """Find motifs introduced in one chapter but never returned to."""
    recurring_words = {n["image"] for n in recurring_nouns}
    orphans = []

    for ch in chapters:
        text = ch.get("text", "")
        words = set(w.lower() for w in re.findall(r'\b\w+\b', text) if len(w) > 5)
        introduced = words - recurring_words
        # Filter to likely concrete nouns (capitalized in original or appear 2+ times)
        for word in introduced:
            count = text.lower().count(word)
            if count >= 2 and word not in _STOPWORDS:
                orphans.append({
                    "word": word,
                    "introduced_in": ch.get("filename", "?"),
                    "occurrences_in_chapter": count,
                })

    return orphans[:10]


def _find_phrase_echoes_single(text: str) -> List[Dict]:
    """Find recurring 3-5 word phrases in a single text."""
    words = [w.lower() for w in re.findall(r'\b\w+\b', text) if w not in _STOPWORDS and len(w) > 3]
    phrase_freq = Counter()

    for n in [4, 5]:
        for i in range(len(words) - n + 1):
            phrase = " ".join(words[i:i+n])
            phrase_freq[phrase] += 1

    return [{"phrase": p, "count": c} for p, c in phrase_freq.most_common(10) if c >= 2]


def _sensory_in_single(text: str) -> List[Dict]:
    """Find sensory motifs in a single text."""
    text_lower = text.lower()
    found = []
    for sense, words in SENSORY_CATEGORIES.items():
        for w in words:
            count = text_lower.count(w)
            if count >= 2:
                found.append({"sense": sense, "word": w, "count": count})
    return sorted(found, key=lambda x: x["count"], reverse=True)[:10]


def _generate_observations(recurring, echoes, sensory, orphans, chapter_count) -> List[Dict]:
    observations = []

    if recurring:
        top = recurring[0]
        observations.append(format_flag(
            "recurring_motif",
            f"across {top['chapter_count']} chapters",
            f"'{top['image']}' recurs across {top['chapter_count']} chapter(s) — a candidate motif",
            "recurring images create thematic stitching; readers may not consciously notice but feel the coherence",
            [
                "notice whether this motif is doing deliberate symbolic work",
                "check if it evolves across chapters (same image, different meaning)",
                "keep as-is if the recurrence feels organic",
            ]
        ))

    if echoes:
        observations.append(format_flag(
            "phrase_echo",
            f"across {len(echoes)} phrases",
            f"{len(echoes)} phrase echo(es) detected across chapters",
            "echoing phrases create a musical quality — the manuscript returns to its own language",
            [
                "check if the echoes are intentional (refrain, callback) or accidental (crutch phrase)",
                "intentional echoes are a strength — they weave the manuscript together",
                "if accidental, try varying one of the echoed phrases",
            ]
        ))

    if sensory:
        top_sensory = sensory[0]
        observations.append(format_flag(
            "sensory_motif",
            f"'{top_sensory['word']}' ({top_sensory['sense']}) in {top_sensory['chapter_count']} chapters",
            f"sensory motif: '{top_sensory['word']}' ({top_sensory['sense']}) recurs across {top_sensory['chapter_count']} chapter(s)",
            "recurring sensory details are among the most powerful motif types — they ground the reader in the body",
            [
                "notice whether this sensory detail is doing thematic work",
                "check if it shifts meaning across chapters (e.g., 'cold' as isolation → 'cold' as clarity)",
                "keep as-is — sensory motifs are a hallmark of strong memoir",
            ]
        ))

    if orphans:
        observations.append(format_flag(
            "orphan_motif",
            f"{len(orphans)} orphan(s)",
            f"{len(orphans)} image(s) introduced but never returned to — potential loose threads",
            "orphan motifs may be: (a) intentionally introduced for a single chapter, (b) forgotten threads worth returning to, or (c) noise",
            [
                "review each orphan — could any be developed in a later chapter?",
                "if intentional, keep them — single-use images can be powerful",
                "if forgotten, consider whether the thread deserves closure",
            ]
        ))

    return observations


def _generate_summary(chapter_count, total_words, recurring, echoes, sensory) -> str:
    return plain_summary(
        what=f"Motif analysis across {chapter_count} chapter(s), {total_words} words",
        found=f"{len(recurring)} recurring motif(s), {len(echoes)} phrase echo(es), {len(sensory)} sensory cluster(s)",
        next_step="Review candidate motifs — recurring images are the manuscript's thematic stitching"
    )
