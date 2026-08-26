#!/usr/bin/env python3
"""Cadence & Rhythm analyzer.

Measures punctuation-driven movement, pauses, and contrast — distinct from
craft.py which measures sentence LENGTH distribution. Cadence measures HOW
the sentences move via punctuation, fragments, parallelism, and breath units.
"""
import re
import math
from collections import Counter
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag
from .. import tagger


def analyze(text: str) -> Dict:
    """Run cadence analysis on a text."""
    sentences = tagger.split_sentences(text)
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 10:
        return {"error": "Text too short", "word_count": word_count}

    pause_density = _pause_density(text, word_count)
    drop_beats = _detect_drop_beats(sentences)
    opener_variety = _opener_variety(sentences)
    fragment_density = _fragment_density(sentences)
    parallelism = _detect_parallelism(sentences)
    breath_units = _breath_units(text, sentences)

    observations = _generate_observations(pause_density, drop_beats, opener_variety,
                                           fragment_density, parallelism, breath_units, word_count)

    return {
        "word_count": word_count,
        "sentence_count": len(sentences),
        "pause_density": pause_density,
        "drop_beats": drop_beats[:10],
        "drop_beat_count": len(drop_beats),
        "opener_variety_score": opener_variety,
        "fragment_density_per_1000": round(fragment_density / word_count * 1000, 1) if word_count else 0,
        "parallelism_runs": parallelism[:5],
        "parallelism_run_count": len(parallelism),
        "breath_units": breath_units,
        "observations": observations,
        "summary": _generate_summary(word_count, len(sentences), pause_density, drop_beats),
    }


def _pause_density(text: str, word_count: int) -> Dict:
    """Compute punctuation pause density per 1000 words."""
    em_dashes = text.count('—') + text.count('--')
    semicolons = text.count(';')
    colons = text.count(':')
    ellipses = text.count('...')
    parens = text.count('(')
    brackets = text.count('[')

    per_1000 = lambda n: round(n / word_count * 1000, 1) if word_count else 0

    return {
        "em_dash_per_1000": per_1000(em_dashes),
        "semicolon_per_1000": per_1000(semicolons),
        "colon_per_1000": per_1000(colons),
        "ellipsis_per_1000": per_1000(ellipses),
        "parenthetical_per_1000": per_1000(parens),
        "bracket_per_1000": per_1000(brackets),
        "total_pause_density": per_1000(em_dashes + semicolons + colons + ellipses + parens),
    }


def _detect_drop_beats(sentences: List[str]) -> List[Dict]:
    """Detect 'drop beats' — a very short sentence after a run of long ones."""
    lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences]
    drops = []

    for i in range(2, len(lengths)):
        prev_two_avg = (lengths[i-2] + lengths[i-1]) / 2
        current = lengths[i]

        if prev_two_avg > 20 and current <= 6:
            drops.append({
                "after_sentence": i,
                "previous_lengths": [lengths[i-2], lengths[i-1]],
                "short_sentence_length": current,
                "short_sentence_preview": sentences[i][:100] + ("..." if len(sentences[i]) > 100 else ""),
            })

    return drops


def _opener_variety(sentences: List[str]) -> float:
    """Measure how varied sentence openers are. 0.0 = all same, 1.0 = all different."""
    if not sentences:
        return 0.0

    openers = []
    for s in sentences:
        words = re.findall(r'\b\w+\b', s)
        if words:
            openers.append(words[0].lower())

    unique = len(set(openers))
    total = len(openers)
    return round(unique / total, 2) if total else 0.0


def _fragment_density(sentences: List[str]) -> int:
    """Count sentence fragments (no main verb, <= 3 words)."""
    count = 0
    for s in sentences:
        words = re.findall(r'\b\w+\b', s)
        if len(words) <= 3:
            count += 1
    return count


def _detect_parallelism(sentences: List[str]) -> List[Dict]:
    """Detect parallelism runs — same sentence-opener pattern 3+ times."""
    if len(sentences) < 3:
        return []

    runs = []
    i = 0
    while i < len(sentences) - 2:
        openers = []
        for j in range(i, min(i + 6, len(sentences))):
            words = re.findall(r'\b\w+\b', sentences[j])
            if words:
                openers.append(words[0].lower())

        if len(openers) >= 3:
            first = openers[0]
            run_length = 1
            for k in range(1, len(openers)):
                if openers[k] == first:
                    run_length += 1
                else:
                    break

            if run_length >= 3:
                previews = [sentences[i + k][:60] + "..." if len(sentences[i + k]) > 60 else sentences[i + k]
                            for k in range(min(run_length, 5))]
                runs.append({
                    "opener": first,
                    "run_length": run_length,
                    "start_sentence": i + 1,
                    "previews": previews,
                })
                i += run_length
                continue
        i += 1

    return runs


def _breath_units(text: str, sentences: List[str]) -> Dict:
    """Estimate breath units — average syllables between major punctuation."""
    # Approximate syllable count
    def count_syllables(word):
        word = word.lower()
        if len(word) <= 3:
            return 1
        word = re.sub(r'(?:[^laeiouy]es|ed|[^laeiouy]e)$', '', word)
        word = re.sub(r'^y', '', word)
        matches = re.findall(r'[aeiouy]{1,2}', word)
        return max(1, len(matches))

    words = re.findall(r'\b\w+\b', text)
    total_syllables = sum(count_syllables(w) for w in words)

    major_pauses = text.count('.') + text.count('?') + text.count('!') + text.count(';') + text.count('—')
    if major_pauses == 0:
        major_pauses = 1

    avg_syllables = round(total_syllables / major_pauses, 1)
    return {
        "avg_syllables_between_pauses": avg_syllables,
        "total_syllables": total_syllables,
        "total_major_pauses": major_pauses,
    }


def _generate_observations(pause_density, drop_beats, opener_variety, fragment_density,
                           parallelism, breath_units, word_count) -> List[Dict]:
    observations = []

    total_pause = pause_density.get("total_pause_density", 0)
    if total_pause > 40:
        observations.append(format_flag(
            "pause_density",
            "whole chapter",
            f"total punctuation pause density is {total_pause}/1000 words, which is high",
            "the prose may feel pausy — readers encounter many interruptions (em-dashes, semicolons, parentheticals)",
            [
                "check if each pause is doing genuine work (setting rhythm, inserting thought)",
                "try removing a few pauses in dense areas to see if the prose flows better",
                "keep as-is if the interrupted rhythm mirrors the narrator's mental state",
            ]
        ))

    if drop_beats:
        observations.append(format_flag(
            "drop_beats",
            f"sentence(s) {[d['after_sentence'] for d in drop_beats[:3]]}",
            f"{len(drop_beats)} 'drop beat(s)' detected — very short sentences after runs of long ones",
            "drop beats create emphasis and rhythm contrast — they're a strength when intentional",
            [
                "notice where these land — they're often the most quotable lines",
                "check if any drop beats feel accidental rather than deliberate",
                "keep as-is — drop beats are a hallmark of strong prose rhythm",
            ]
        ))

    if opener_variety < 0.4:
        observations.append(format_flag(
            "opener_variety",
            "whole chapter",
            f"opener variety score is {opener_variety} (low) — sentences tend to start with the same words",
            "the prose may feel chant-like or repetitive; this can be a deliberate stylistic choice (anaphora) or accidental monotony",
            [
                "check if the repetition is intentional anaphora (emphatic) or accidental monotony",
                "try varying 2-3 sentence openers to see the effect",
                "keep as-is if the chant-like quality is the voice you want",
            ]
        ))

    if parallelism:
        for run in parallelism[:2]:
            observations.append(format_flag(
                "parallelism",
                f"sentences {run['start_sentence']}-{run['start_sentence'] + run['run_length'] - 1}",
                f"a parallelism run of '{run['opener']}' repeats {run['run_length']} times",
                "parallelism creates rhythm and emphasis — a powerful technique when intentional",
                [
                    "notice the cumulative effect — parallelism builds emotional weight",
                    "check if the run is the right length (3-4 is punchy, 5+ may feel listy)",
                    "keep as-is if the parallelism is doing deliberate work",
                ]
            ))

    avg_breath = breath_units.get("avg_syllables_between_pauses", 12)
    if avg_breath > 25:
        observations.append(format_flag(
            "breath_units",
            "whole chapter",
            f"average breath unit is {avg_breath} syllables between pauses, which is long",
            "readers may feel they need to hold their breath — long units can feel exhausting or hypnotic depending on context",
            [
                "check if the long breath units create a meditative or overwhelming effect",
                "try breaking one long unit with a pause to give readers a breather",
                "keep as-is if the sustained flow is intentional (stream-of-consciousness, meditation)",
            ]
        ))
    elif avg_breath < 6:
        observations.append(format_flag(
            "breath_units",
            "whole chapter",
            f"average breath unit is {avg_breath} syllables between pauses, which is very short",
            "the prose may feel staccato — punchy but potentially choppy",
            [
                "check if the short units create useful tension or feel monotonous",
                "try combining 2-3 short units into one longer sentence",
                "keep as-is if the staccato rhythm matches the emotional content",
            ]
        ))

    return observations


def _generate_summary(word_count: int, sentence_count: int, pause_density: Dict, drop_beats: List) -> str:
    return plain_summary(
        what=f"Cadence and rhythm analysis of {word_count} words across {sentence_count} sentences",
        found=f"Pause density: {pause_density.get('total_pause_density', 0)}/1000. Drop beats: {len(drop_beats)}. Parallelism runs detected.",
        next_step="Review observations — each describes a rhythm pattern, not a flaw"
    )
