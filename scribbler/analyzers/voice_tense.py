#!/usr/bin/env python3
"""Voice & tense tracker — the dedicated tool for the user's answer #8.

Memoir is inherently first-person. This tool tracks:
- Tense distribution per chapter (past, present, future-in-past, pluperfect)
- Tense shifts within the chapter (and where they occur)
- First-person pronoun density
- Narrator distance signals (experiencing self vs. narrating self)
- Grammar pattern distribution (declarative, interrogative, conditional, imperative)
- Voice consistency across the manuscript
"""
import re
from collections import Counter
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag
from .. import tagger


def analyze(text: str) -> Dict:
    """Run voice and tense analysis on a text."""
    sentences = tagger.split_sentences(text)
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 10:
        return {"error": "Text too short", "word_count": word_count}

    tense_dist = _tense_distribution(sentences)
    tense_shifts = _detect_tense_shifts(sentences)
    pronoun_density = _pronoun_density(text, word_count)
    narrator_distance = _narrator_distance(text, word_count)
    grammar_patterns = _grammar_patterns(sentences)
    observations = _generate_observations(tense_dist, tense_shifts, pronoun_density, narrator_distance)

    return {
        "word_count": word_count,
        "sentence_count": len(sentences),
        "tense_distribution": tense_dist,
        "tense_shifts": tense_shifts,
        "pronoun_density": pronoun_density,
        "narrator_distance": narrator_distance,
        "grammar_patterns": grammar_patterns,
        "observations": observations,
        "summary": _generate_summary(word_count, tense_dist, narrator_distance),
    }


def _tense_distribution(sentences: List[str]) -> Dict:
    """Detect tense of each sentence and report distribution."""
    tense_labels = []
    for s in sentences:
        tense = _detect_sentence_tense(s)
        tense_labels.append(tense)

    counts = Counter(tense_labels)
    total = len(tense_labels)

    return {
        "labels": tense_labels,  # Per-sentence labels for shift detection
        "counts": dict(counts),
        "percentages": {k: round(v / total * 100, 1) for k, v in counts.items()},
        "dominant_tense": counts.most_common(1)[0][0] if counts else "unknown",
        "total_sentences": total,
    }


def _detect_sentence_tense(sentence: str) -> str:
    """Detect the primary tense of a sentence."""
    s_lower = sentence.lower()

    # Pluperfect (past perfect): "had walked", "had been walking"
    if re.search(r'\b(?:had|hadn\'t)\s+(?:been\s+)?\w+(?:ed|en|t)\b', s_lower):
        return "pluperfect"

    # Future in past: "would walk", "was going to walk", "would later learn"
    if re.search(r'\b(?:would|was going to|were going to)\s+\w+', s_lower):
        return "future_in_past"

    # Present continuous: "is walking", "are walking"
    if re.search(r'\b(?:is|are|am)\s+\w+ing\b', s_lower):
        return "present_continuous"

    # Present simple: "walks", "walk", "says", "thinks" (not "walked")
    # Check for present-tense verbs (simplified)
    present_markers = re.search(r'\b(?:i|we|you|they)\s+(?:walk|talk|say|think|feel|know|see|hear|remember|understand|wonder|notice)\b', s_lower)
    present_s_markers = re.search(r'\b(?:he|she|it)\s+(?:walks|talks|says|thinks|feels|knows|sees|hears|remembers|understands|wonders|notices)\b', s_lower)
    is_present = re.search(r'\b(?:is|are|am|do|does)\b', s_lower)

    # Past markers
    past_markers = re.search(r'\b(?:was|were|had|did|went|said|thought|felt|knew|saw|heard|remembered|walked|talked)\b', s_lower)

    # Decision logic
    if present_markers or present_s_markers:
        return "present"
    if is_present and not past_markers:
        return "present"
    if past_markers:
        return "past"

    # Default: check for -ed verbs
    if re.search(r'\b\w+ed\b', s_lower):
        return "past"

    return "ambiguous"


def _detect_tense_shifts(sentences: List[str]) -> List[Dict]:
    """Detect where tense shifts occur within the text."""
    shifts = []
    labels = [_detect_sentence_tense(s) for s in sentences]

    for i in range(1, len(labels)):
        if labels[i] != labels[i-1] and labels[i] != "ambiguous" and labels[i-1] != "ambiguous":
            shifts.append({
                "sentence_number": i + 1,
                "from_tense": labels[i-1],
                "to_tense": labels[i],
                "sentence_preview": sentences[i][:100] + ("..." if len(sentences[i]) > 100 else ""),
            })

    return shifts


def _pronoun_density(text: str, word_count: int) -> Dict:
    """Compute first-person pronoun density and distribution."""
    first_person = len(re.findall(r'\b(I|me|my|mine|myself)\b', text, re.IGNORECASE))
    first_plural = len(re.findall(r'\b(we|us|our|ours|ourselves)\b', text, re.IGNORECASE))
    second_person = len(re.findall(r'\b(you|your|yours|yourself)\b', text, re.IGNORECASE))
    third_person = len(re.findall(r'\b(he|him|his|she|her|hers|they|them|their|theirs)\b', text, re.IGNORECASE))

    per_1000 = lambda n: round(n / word_count * 1000, 1) if word_count > 0 else 0

    return {
        "first_person_singular": {
            "count": first_person,
            "per_1000": per_1000(first_person),
        },
        "first_person_plural": {
            "count": first_plural,
            "per_1000": per_1000(first_plural),
        },
        "second_person": {
            "count": second_person,
            "per_1000": per_1000(second_person),
        },
        "third_person": {
            "count": third_person,
            "per_1000": per_1000(third_person),
        },
        "first_person_total_per_1000": per_1000(first_person + first_plural),
        "note": "Memoir is inherently first-person. The density tells you how present the 'I' is vs. the world.",
    }


def _narrator_distance(text: str, word_count: int) -> Dict:
    """Detect signals of narrator distance: experiencing self vs. narrating self.

    Experiencing self: immersive, in-scene, present-tense or simple past
    Narrating self: reflective, qualifying, "I would later learn", "I didn't yet know"
    """
    # Narrating-self signals
    reflective_cues = [
        r'\b(i would later|i didn\'?t yet|at the time|i hadn\'?t yet realized|i would come to|i didn\'?t know then)\b',
        r'\b(looking back|in retrospect|years later|now i know|now i understand|i see now)\b',
        r'\b(i remember|i recall|memory of|that day|that moment|that summer|that winter)\b',
    ]
    reflective_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in reflective_cues)

    # Experiencing-self signals
    immersive_cues = [
        r'\b(i hear|i see|i feel|i smell|i taste|right now|in this moment)\b',
        r'\b(here|now|today|this moment)\b',
    ]
    immersive_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in immersive_cues)

    # Hedging/modality (narrating self)
    hedge_count = len(re.findall(r'\b(maybe|perhaps|might have|could have|i think|i suppose|i imagine|i wonder if)\b', text, re.IGNORECASE))

    total_signals = reflective_count + immersive_count + hedge_count
    if total_signals == 0:
        ratio = 0.5
    else:
        ratio = reflective_count / total_signals

    return {
        "reflective_signals": reflective_count,
        "immersive_signals": immersive_count,
        "hedge_signals": hedge_count,
        "narrating_self_ratio": round(ratio, 2),
        "assessment": _assess_distance(ratio, reflective_count, immersive_count),
        "note": "Gornick's 'The Situation and the Story': memoir has two selves — the experiencing self and the retrospective narrating self. The ratio between them is itself an arc.",
    }


def _assess_distance(ratio: float, reflective: int, immersive: int) -> str:
    if ratio > 0.7:
        return "heavily reflective — the narrating self dominates; readers may feel distanced from the experience"
    elif ratio > 0.5:
        return "moderately reflective — a balance of retrospection and immersion, leaning reflective"
    elif ratio > 0.3:
        return "moderately immersive — readers are present in the scene with occasional reflective framing"
    else:
        return "heavily immersive — readers are inside the experience; the narrating self is largely absent"


def _grammar_patterns(sentences: List[str]) -> Dict:
    """Detect grammar pattern distribution: declarative, interrogative, imperative, conditional, fragment."""
    patterns = []
    for s in sentences:
        s_stripped = s.strip()
        if not s_stripped:
            continue

        # Interrogative (ends with ?)
        if s_stripped.endswith('?'):
            patterns.append("interrogative")
        # Imperative (starts with verb, no subject)
        elif re.match(r'^(go|come|look|listen|wait|stop|don\'t|do not|remember|imagine|consider|think|feel|see)\b', s_stripped, re.IGNORECASE):
            patterns.append("imperative")
        # Conditional (if...then, would, could, might)
        elif re.search(r'\b(if|would|could|might|unless|provided that)\b', s_stripped, re.IGNORECASE):
            patterns.append("conditional")
        # Fragment (no main verb or very short)
        elif len(re.findall(r'\b\w+\b', s_stripped)) < 4:
            patterns.append("fragment")
        # Exclamatory
        elif s_stripped.endswith('!'):
            patterns.append("exclamatory")
        else:
            patterns.append("declarative")

    counts = Counter(patterns)
    total = len(patterns)

    return {
        "counts": dict(counts),
        "percentages": {k: round(v / total * 100, 1) for k, v in counts.items()},
        "dominant_pattern": counts.most_common(1)[0][0] if counts else "declarative",
    }


def _generate_observations(tense_dist: Dict, tense_shifts: List, pronoun_density: Dict, narrator_distance: Dict) -> List[Dict]:
    """Generate low-shame observations."""
    observations = []

    # Tense shifts
    if len(tense_shifts) > 5:
        observations.append(format_flag(
            "tense_consistency",
            f"throughout ({len(tense_shifts)} shifts detected)",
            f"the tense shifts {len(tense_shifts)} times across the chapter",
            "frequent tense shifts can disorient readers unless they're intentional mode switches",
            [
                "check if each shift marks a deliberate move between experiencing and narrating self",
                "consider adding a section break at major shifts to signal the change",
                "keep as-is if the shifts mirror the narrator's mental movement",
            ]
        ))

    # Dominant tense
    dominant = tense_dist.get("dominant_tense", "past")
    pct = tense_dist.get("percentages", {}).get(dominant, 0)
    if dominant == "present" and pct > 70:
        observations.append(format_flag(
            "tense",
            "whole chapter",
            f"the chapter is predominantly present tense ({pct:.0f}%)",
            "present tense creates immediacy but can feel exhausting over long stretches",
            [
                "try mixing in past tense for reflective passages",
                "keep as-is if the immediacy is the point",
                "consider whether the present tense serves the scene or has become a default",
            ]
        ))
    elif dominant == "past" and pct > 90:
        observations.append(format_flag(
            "tense",
            "whole chapter",
            f"the chapter is almost entirely past tense ({pct:.0f}%)",
            "consistent past tense is memoir's default; readers will feel settled",
            [
                "try a present-tense passage for a particularly vivid memory",
                "keep as-is if the steady past tense is your voice",
                "check if any flashback scenes need pluperfect ('had') markers",
            ]
        ))

    # Narrator distance
    dist_ratio = narrator_distance.get("narrating_self_ratio", 0.5)
    if dist_ratio > 0.7:
        observations.append(format_flag(
            "narrator_distance",
            "whole chapter",
            "the narrating self (reflective, retrospective) dominates over the experiencing self",
            "readers may feel they're being told about the experience rather than living it",
            [
                "try dropping into present-tense scene for a key moment",
                "convert one reflective passage into a sensory scene",
                "keep as-is if the reflective voice is the chapter's purpose",
            ]
        ))
    elif dist_ratio < 0.2 and narrator_distance.get("reflective_signals", 0) == 0:
        observations.append(format_flag(
            "narrator_distance",
            "whole chapter",
            "the experiencing self dominates; the narrating self is absent",
            "without any reflective framing, readers may not understand why this scene matters to you now",
            [
                "add a sentence or two of retrospective insight",
                "let the narrating self comment on what the experiencing self didn't yet know",
                "keep as-is if the chapter is intentionally immersive and the meaning emerges later",
            ]
        ))

    # First-person pronoun density
    fp_per_1000 = pronoun_density.get("first_person_total_per_1000", 0)
    if fp_per_1000 > 60:
        observations.append(format_flag(
            "pronoun_density",
            "whole chapter",
            f"first-person pronoun density is {fp_per_1000}/1000 words, which is high",
            "the narration may feel self-referential; 'I' appears very frequently",
            [
                "try replacing some 'I + verb' constructions with the action itself",
                "vary sentence openers to include sensory details or external observations",
                "keep as-is if the high 'I' density is the voice you want",
            ]
        ))

    return observations


def _generate_summary(word_count: int, tense_dist: Dict, narrator_distance: Dict) -> str:
    dominant_tense = tense_dist.get("dominant_tense", "unknown")
    dist_assessment = narrator_distance.get("assessment", "unknown")
    return plain_summary(
        what=f"Voice and tense analysis of {word_count} words",
        found=f"Dominant tense: {dominant_tense}. Narrator distance: {dist_assessment}.",
        next_step="Review tense shifts and narrator-distance observations — each offers paths to adjust or keep as-is"
    )
