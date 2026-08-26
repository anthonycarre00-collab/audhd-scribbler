#!/usr/bin/env python3
"""Editor-style suggestions analyzer.

The signature tool. Generates a strengths inventory FIRST, then surfaces
memoir-specific patterns (distant narrator, defensive register, missing stakes,
early/late revelation, summary-where-scene, essay-vs-memoir drift) using
the low-shame feedback grammar.
"""
import re
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag, strengths_first
from .. import tagger
from ..config import AUDHD_THEMES, WEAK_WORDS, FILTER_WORDS
from . import craft, voice_tense, characters, continuity, themes


def analyze(text: str, precomputed: Dict = None) -> Dict:
    """Run editor-style analysis. Combines signals from other analyzers + memoir-specific patterns.

    Args:
        text: The text to analyze
        precomputed: Optional dict of already-computed analyzer results to avoid re-running.
                     Keys can be: 'craft', 'voice_tense', 'characters', 'continuity', 'themes'
    """
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 10:
        return {"error": "Text too short", "word_count": word_count}

    # Use pre-computed results if available, otherwise compute (avoids 2-3x redundant work)
    precomputed = precomputed or {}
    craft_result = precomputed.get("craft") or craft.analyze(text)
    voice_result = precomputed.get("voice_tense") or precomputed.get("voice") or voice_tense.analyze(text)
    char_result = precomputed.get("characters") or precomputed.get("character") or characters.analyze(text)
    cont_result = precomputed.get("continuity") or continuity.analyze(text)
    theme_result = precomputed.get("themes") or themes.analyze(text)

    # Generate strengths inventory FIRST
    strengths = _generate_strengths(text, craft_result, voice_result, theme_result, char_result)

    # Generate memoir-specific observations
    memoir_patterns = _detect_memoir_patterns(text, craft_result, voice_result, char_result, cont_result)

    # Combine all observations
    all_observations = []
    all_observations.extend(memoir_patterns)
    all_observations.extend(craft_result.get("observations", []))
    all_observations.extend(voice_result.get("observations", []))
    all_observations.extend(char_result.get("observations", []))
    all_observations.extend(cont_result.get("observations", []))
    all_observations.extend(theme_result.get("observations", []))

    # Deduplicate by category+location
    seen = set()
    deduped = []
    for obs in all_observations:
        key = (obs.get("category", ""), obs.get("location", ""))
        if key not in seen:
            seen.add(key)
            deduped.append(obs)

    output = strengths_first(strengths, [o["formatted"] for o in deduped])

    return {
        "word_count": word_count,
        "strengths": output["strengths"],
        "observations": deduped,
        "observation_count": len(deduped),
        "summary": _generate_summary(word_count, len(strengths), len(deduped)),
    }


def _generate_strengths(text: str, craft_result: Dict, voice_result: Dict, theme_result: Dict, char_result: Dict = None) -> List[str]:
    """Generate a genuine strengths inventory. This is the foundation of low-shame feedback."""
    strengths = []

    # Sensory detail
    sensory = craft_result.get("sensory_density", {})
    if sensory.get("per_1000_words", 0) > 8:
        senses_present = list(sensory.get("by_sense", {}).keys())
        strengths.append(f"Strong sensory grounding ({sensory['per_1000_words']}/1000 words) — particularly {', '.join(senses_present[:3])}. This puts the reader in the body of the scene.")

    # Sentence rhythm variation
    rhythm = craft_result.get("sentence_length_rhythm", {})
    cv = rhythm.get("coefficient_of_variation", 0)
    if 0.7 <= cv <= 1.2:
        strengths.append(f"Healthy sentence-length variation (CV={cv}). The prose rhythm has natural contrast between short and long sentences, which carries the reader forward.")

    # Theme presence
    theme_density = theme_result.get("theme_density", {})
    if theme_density.get("theme_count", 0) >= 3:
        dominant = theme_density.get("dominant_theme", "")
        strengths.append(f"Rich thematic texture — {theme_density['theme_count']} themes detected, with '{dominant}' as the dominant thread. The chapter is doing thematic work.")

    # Emotional arc movement
    arc = theme_result.get("emotional_arc", {})
    if arc.get("range", 0) > 0.3:
        strengths.append(f"The emotional arc has meaningful range ({arc.get('min', 0):.2f} to {arc.get('max', 0):.2f}), which gives the chapter emotional movement rather than flatness.")

    # Voice consistency
    voice = voice_result.get("tense_distribution", {})
    dominant_tense = voice.get("dominant_tense", "")
    tense_pct = voice.get("percentages", {}).get(dominant_tense, 0)
    if tense_pct > 80:
        strengths.append(f"Consistent {dominant_tense} tense ({tense_pct:.0f}%) — the voice feels settled and intentional rather than accidentally shifting.")

    # Dialogue presence
    dialogue = craft_result.get("dialogue_ratio", {})
    if 10 < dialogue.get("dialogue_pct", 0) < 50:
        strengths.append(f"Balanced dialogue presence ({dialogue['dialogue_pct']:.0f}%) — other voices are present without overwhelming the narrator's.")

    # Lexical diversity — use passed-in char_result instead of re-running characters.analyze
    if char_result is None:
        char_result = characters.analyze(text)
    voice_fp = char_result.get("voice_fingerprint", {})
    mattr = voice_fp.get("lexical_diversity_mattr", 0)
    if mattr > 0.6:
        strengths.append(f"Rich vocabulary (lexical diversity MATTR={mattr}) — the word choice is varied without being showy.")

    # Length / commitment
    if len(text.split()) > 1500:
        strengths.append(f"The chapter is substantial ({len(text.split())} words) — you've committed to developing this material rather than sketching it.")

    # Always include at least one strength
    if not strengths:
        strengths.append("The fact that this material exists and was shared for analysis is itself a strength. The hardest part of memoir is showing up to the page; you did that.")

    return strengths


def _detect_memoir_patterns(text: str, craft_result: Dict, voice_result: Dict, char_result: Dict, cont_result: Dict) -> List[Dict]:
    """Detect memoir-specific patterns: distant narrator, defensive register, missing stakes, etc."""
    patterns = []

    # Distant narrator (high filter words + low sensory)
    filter_words = craft_result.get("filter_words", {})
    sensory = craft_result.get("sensory_density", {})
    if filter_words.get("per_1000_words", 0) > 15 and sensory.get("per_1000_words", 0) < 5:
        patterns.append(format_flag(
            "distant_narrator",
            "whole chapter",
            "high filter-word density combined with low sensory detail",
            "the narrator feels like an observer reporting events rather than being present in them",
            [
                "add one interior beat (a thought, a sensation, a reaction) after a key piece of dialogue",
                "ground a scene with a specific sensory detail (smell and taste carry the most memory-weight)",
                "keep as-is if the distance is intentional for this section",
            ]
        ))

    # Defensive register
    defensive_cues = len(re.findall(r'\b(because|had to|needed to|no choice|forced|had no option|i\'m not saying|i don\'t mean|to be clear|just to be clear|for the record)\b', text, re.IGNORECASE))
    word_count = len(re.findall(r'\b\w+\b', text))
    if defensive_cues / max(word_count, 1) * 1000 > 3:
        patterns.append(format_flag(
            "defensive_register",
            "whole chapter",
            f"defensive-language density is {defensive_cues / max(word_count, 1) * 1000:.1f}/1000 words",
            "the prose may read as building a case rather than reliving the moment",
            [
                "convert one defensive statement into a scene that shows the reader what happened",
                "name the defensiveness as part of the narrator's voice ('I catch myself explaining again')",
                "keep as-is if the argumentative mode is the point",
            ]
        ))

    # Missing stakes (low emotional words + summary-heavy)
    summary_signals = len(re.findall(r'\b(years later|after that|eventually|over time|in the end|things changed|i grew up|time passed)\b', text, re.IGNORECASE))
    if summary_signals > 3 and voice_result.get("narrator_distance", {}).get("narrating_self_ratio", 0) > 0.6:
        patterns.append(format_flag(
            "missing_stakes",
            "whole chapter",
            "multiple summary passages without scene-level grounding",
            "readers may not feel why this matters to the narrator now",
            [
                "pick one summary passage and expand it into a scene with dialogue and sensory detail",
                "add a sentence naming what the narrator wants or fears in the moment",
                "keep as-is if this is intentionally a reflective, summary chapter",
            ]
        ))

    # Essay-vs-memoir drift (high citation cues + low first-person)
    citation_cues = len(re.findall(r'\b(according to|studies show|research|found that|evidence|data)\b', text, re.IGNORECASE))
    first_person = len(re.findall(r'\b(I|me|my)\b', text, re.IGNORECASE))
    if citation_cues > 5 and first_person / max(word_count, 1) * 100 < 2:
        patterns.append(format_flag(
            "essay_vs_memoir_drift",
            "whole chapter",
            "high citation density with low first-person presence",
            "this section may read as an essay rather than a memoir chapter — the 'I' has disappeared behind the research",
            [
                "anchor the research in a personal moment ('When I read this study, I thought of...')",
                "intersperse memoir scenes between research passages",
                "keep as-is if this is intentionally a research-braid chapter",
            ]
        ))

    # Summary where scene is needed
    long_paragraphs = [p for p in re.split(r'\n\s*\n', text) if len(re.findall(r'\b\w+\b', p)) > 200]
    if len(long_paragraphs) > 2:
        patterns.append(format_flag(
            "summary_where_scene",
            f"{len(long_paragraphs)} long paragraphs (>200 words)",
            "several very long paragraphs that may be summary rather than scene",
            "long summary paragraphs can lose the reader's sense of being present",
            [
                "break one long paragraph into a scene with dialogue and action",
                "add a section break to signal a shift from summary to scene",
                "keep as-is if the summary is doing necessary expository work",
            ]
        ))

    return patterns


def _generate_summary(word_count: int, strength_count: int, obs_count: int) -> str:
    return plain_summary(
        what=f"Editor-style analysis of {word_count} words",
        found=f"{strength_count} strengths identified, {obs_count} observations (each with 2-3 optional paths)",
        next_step="Read the strengths first — they're the foundation. Then scan observations; each offers options, never demands"
    )
