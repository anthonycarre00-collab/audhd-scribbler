#!/usr/bin/env python3
"""Theme & emotional arc analyzer.

Maps thematic density and emotional valence across chapters and the whole book.
"""
import re
import math
from collections import Counter, defaultdict
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag
from .. import tagger
from ..config import AUDHD_THEMES


# Simple sentiment lexicon (built-in for offline use)
POSITIVE_WORDS = {
    "good", "great", "wonderful", "beautiful", "love", "loved", "happy", "joy", "joyful",
    "warm", "bright", "hope", "hopeful", "kind", "gentle", "soft", "sweet", "calm",
    "peace", "peaceful", "free", "freedom", "alive", "light", "laughter", "smile",
    "smiled", "grateful", "thankful", "blessed", "lucky", "lucky", "best", "better",
    "comfort", "comfortable", "safe", "safety", "home", "belong", "belonged",
}

NEGATIVE_WORDS = {
    "bad", "terrible", "awful", "hate", "hated", "sad", "sadness", "angry", "anger",
    "fear", "afraid", "scared", "scary", "dark", "cold", "lonely", "alone", "lost",
    "broken", "hurt", "pain", "painful", "suffering", "cry", "cried", "tears",
    "death", "died", "gone", "empty", "numb", "wrong", "wrong", "fail", "failed",
    "failure", "stupid", "lazy", "ashamed", "embarrassed", "guilt", "guilty",
    "anxious", "anxiety", "panic", "dread", "worry", "worried", "stress", "stressed",
    "exhausted", "tired", "drained", "depleted", "overwhelmed", "flooded",
}

# Vonnegut's six shapes (simplified detection)
SHAPES = {
    "rags_to_riches": "steady rise from low to high",
    "riches_to_rags": "steady fall from high to low",
    "man_in_a_hole": "fall then rise",
    "icarus": "rise then fall",
    "cinderella": "rise, fall, rise",
    "oedipus": "fall, rise, fall",
    "flat": "no significant emotional movement",
}


def analyze(text: str) -> Dict:
    """Run theme and emotional arc analysis."""
    sentences = tagger.split_sentences(text)
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 10:
        return {"error": "Text too short", "word_count": word_count}

    theme_density = _theme_density(text, word_count)
    emotional_arc = _emotional_arc(sentences)
    shape = _classify_arc_shape(emotional_arc)
    motif_candidates = _motif_detection(text)

    observations = _generate_observations(theme_density, emotional_arc, shape)

    return {
        "word_count": word_count,
        "theme_density": theme_density,
        "emotional_arc": emotional_arc,
        "arc_shape": shape,
        "motif_candidates": motif_candidates,
        "observations": observations,
        "summary": _generate_summary(word_count, theme_density, shape),
    }


def _theme_density(text: str, word_count: int) -> Dict:
    """Compute theme density using AUDHD lexicon."""
    text_lower = text.lower()
    theme_scores = {}

    for theme, keywords in AUDHD_THEMES.items():
        score = sum(text_lower.count(kw.lower()) for kw in keywords)
        if score > 0:
            per_1000 = score / word_count * 1000
            theme_scores[theme] = {
                "count": score,
                "per_1000": round(per_1000, 2),
            }

    # Sort by density
    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1]["per_1000"], reverse=True)

    return {
        "themes_found": dict(sorted_themes),
        "dominant_theme": sorted_themes[0][0] if sorted_themes else None,
        "theme_count": len(sorted_themes),
    }


def _emotional_arc(sentences: List[str]) -> Dict:
    """Compute emotional valence per sentence to trace the arc."""
    valences = []
    for s in sentences:
        valence = _sentence_valence(s)
        valences.append(valence)

    # Smooth with a rolling average (window = 5 sentences or 10% of total, whichever is smaller)
    window = max(3, min(5, len(valences) // 10))
    smoothed = []
    for i in range(len(valences)):
        start = max(0, i - window // 2)
        end = min(len(valences), i + window // 2 + 1)
        avg = sum(valences[start:end]) / (end - start)
        smoothed.append(round(avg, 2))

    return {
        "per_sentence": valences,
        "smoothed": smoothed,
        "average": round(sum(valences) / len(valences), 2) if valences else 0,
        "min": min(valences) if valences else 0,
        "max": max(valences) if valences else 0,
        "range": max(valences) - min(valences) if valences else 0,
    }


def _sentence_valence(sentence: str) -> float:
    """Compute sentiment valence of a sentence. Range: -1 (very negative) to +1 (very positive)."""
    words = re.findall(r'\b\w+\b', sentence.lower())
    if not words:
        return 0

    pos = sum(1 for w in words if w in POSITIVE_WORDS)
    neg = sum(1 for w in words if w in NEGATIVE_WORDS)

    # Negation handling (simple)
    negation_words = {"not", "no", "never", "didn't", "don't", "doesn't", "wasn't", "weren't", "isn't", "aren't"}
    has_negation = any(neg in words for neg in negation_words)
    if has_negation:
        pos, neg = neg, pos  # Flip

    total = pos + neg
    if total == 0:
        return 0
    return (pos - neg) / total


def _classify_arc_shape(arc: Dict) -> Dict:
    """Classify the emotional arc into one of Vonnegut's six shapes."""
    smoothed = arc.get("smoothed", [])
    if len(smoothed) < 5:
        return {"shape": "insufficient_data", "description": "not enough sentences to classify"}

    # Divide into thirds
    third = len(smoothed) // 3
    first_third = sum(smoothed[:third]) / third
    middle_third = sum(smoothed[third:2*third]) / third
    last_third = sum(smoothed[2*third:]) / (len(smoothed) - 2*third)

    # Classify based on the pattern
    threshold = 0.1  # Minimum difference to count as a rise/fall

    r1 = first_third
    r2 = middle_third
    r3 = last_third

    if abs(r1 - r2) < threshold and abs(r2 - r3) < threshold:
        shape = "flat"
    elif r1 < r2 < r3:
        shape = "rags_to_riches"
    elif r1 > r2 > r3:
        shape = "riches_to_rags"
    elif r1 > r2 and r2 < r3:
        shape = "man_in_a_hole"
    elif r1 < r2 and r2 > r3:
        shape = "icarus"
    elif r1 < r2 > r3 and r3 > r1:
        shape = "cinderella"
    elif r1 > r2 < r3 and r3 < r1:
        shape = "oedipus"
    else:
        shape = "mixed"

    return {
        "shape": shape,
        "description": SHAPES.get(shape, "complex pattern"),
        "first_third_valence": round(r1, 2),
        "middle_third_valence": round(r2, 2),
        "last_third_valence": round(r3, 2),
        "note": "Vonnegut's six shapes are descriptive archetypes, not targets. A chapter need not match any of them. This is for seeing the arc, not enforcing one.",
    }


def _motif_detection(text: str) -> List[Dict]:
    """Detect recurring objects or images that might be motifs."""
    # Look for concrete nouns that appear multiple times
    words = re.findall(r'\b[a-z]{4,}\b', text.lower())

    # Filter to likely concrete nouns (not stopwords, not abstract)
    stopwords = {'that', 'this', 'with', 'from', 'have', 'they', 'were', 'been', 'their', 'what', 'about', 'which', 'would', 'there', 'could', 'other', 'more', 'some', 'these', 'such', 'only', 'into', 'after', 'before', 'then', 'than', 'very', 'just', 'also', 'like', 'well', 'even', 'back', 'much', 'most', 'make', 'made', 'going', 'being', 'time', 'year', 'years', 'day', 'days', 'first', 'last', 'next', 'thing', 'things', 'something', 'anything', 'everything', 'nothing'}

    word_freq = Counter(words)
    # Words that appear 3+ times and aren't stopwords
    candidates = {w: c for w, c in word_freq.items() if c >= 3 and w not in stopwords and len(w) > 4}

    # Return top candidates
    top = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:10]
    return [{"word": w, "count": c} for w, c in top]


def _generate_observations(theme_density: Dict, arc: Dict, shape: Dict) -> List[Dict]:
    observations = []

    # Flat arc
    if shape.get("shape") == "flat":
        observations.append(format_flag(
            "emotional_arc",
            "whole chapter",
            "the emotional arc is relatively flat — valence doesn't shift much across the chapter",
            "readers may not feel emotional movement, which can make the chapter feel static",
            [
                "check if the flatness is intentional (reflective, contemplative chapters can be flat)",
                "consider adding a moment of emotional contrast",
                "keep as-is if the stillness is the point",
            ]
        ))

    # Low theme density
    if theme_density.get("theme_count", 0) == 0:
        observations.append(format_flag(
            "themes",
            "whole chapter",
            "no AUDHD-specific themes were detected by the lexicon",
            "this may mean the chapter doesn't engage with neurodiversity themes, or that it uses different vocabulary",
            [
                "check if this chapter belongs in the research-braid or memoir-braid portion",
                "add custom theme keywords to the lexicon if you use different vocabulary",
                "keep as-is if this chapter intentionally doesn't engage with themes",
            ]
        ))

    # Arc shape description
    shape_name = shape.get("shape", "unknown")
    if shape_name not in ["flat", "insufficient_data", "mixed"]:
        observations.append(format_flag(
            "arc_shape",
            "whole chapter",
            f"the chapter's emotional arc resembles '{shape_name}' ({shape.get('description', '')})",
            "this is a recognizable narrative shape — readers may intuitively feel the pattern",
            [
                f"use this shape intentionally — '{shape_name}' carries specific emotional expectations",
                "consider if a different shape would serve the chapter better",
                "keep as-is if the shape feels right",
            ]
        ))

    return observations


def _generate_summary(word_count: int, theme_density: Dict, shape: Dict) -> str:
    dominant = theme_density.get("dominant_theme", "none detected")
    shape_name = shape.get("shape", "unknown")
    return plain_summary(
        what=f"Theme and emotional arc analysis of {word_count} words",
        found=f"Dominant theme: {dominant}. Arc shape: {shape_name} ({shape.get('description', '')}).",
        next_step="The arc shape is descriptive, not prescriptive — use it to see the chapter's emotional movement, not to enforce a pattern"
    )
