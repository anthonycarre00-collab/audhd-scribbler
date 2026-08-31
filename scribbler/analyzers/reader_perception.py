#!/usr/bin/env python3
"""Reader Perception analyzer.

Evidence-first impression of narrator/author and named characters.
LLM-assisted when AI is configured; deterministic fallback using
memoir-pattern heuristics when not.
"""
import re
from typing import Dict, List, Any
import json

from ..feedback import plain_summary, format_flag
from .. import tagger, llm
from ..config import AUDHD_THEMES, FILTER_WORDS


def analyze(text: str) -> Dict:
    """Run reader perception analysis."""
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 50:
        return {"error": "Text too short", "word_count": word_count}

    # Try LLM-assisted analysis first
    if llm.llm_available():
        result = _llm_reader_perception(text)
        if result:
            result["fallback_used"] = False
            result["word_count"] = word_count
            result["observations"] = result.get("observations", [])
            result["summary"] = _generate_summary(word_count, result, False)
            return result

    # Deterministic fallback
    return _deterministic_fallback(text, word_count)


def _llm_reader_perception(text: str) -> Dict:
    """Use LLM to generate evidence-first reader perception."""
    # Extract characters for the prompt
    from .characters import _extract_characters
    characters = _extract_characters(text)

    system = """You are a perceptive reader providing evidence-first impressions of a memoir text.
Your job is to describe how the text FEELS to read, not to judge it.
Always anchor every impression to a quoted passage.
Never say the writing is bad. Describe effects, not quality.
You are gentle, observant, and never judgmental."""

    # Truncate very long texts
    sample = text[:8000] if len(text) > 8000 else text

    prompt = f"""Read this text and provide reader perception as JSON.

Text:
---
{sample}
---

Respond with this JSON structure:
{{
  "narrator_perception": {{
    "closeness": <1-10 scale, how close the reader feels to the narrator>,
    "reliability": "<one sentence: does the narrator hedge, deflect, or own? anchor to quoted evidence>",
    "evidence": ["3 quoted passages that support your impressions"]
  }},
  "character_perceptions": {{
    "<Character Name>": {{
      "warmth": <1-10>,
      "competence": <1-10>,
      "agency": <1-10>,
      "evidence": ["1-2 quoted passages"]
    }}
  }},
  "genre_register": "<one phrase: does this read as memoir, essay, research-braid, or something else?>",
  "emotional_register": "<one phrase: the dominant emotional tone>",
  "strength_signal": "<one sentence: what feels strong or alive in this text>"
}}

Respond with valid JSON only."""

    result = llm.llm_json(prompt, system)
    if not result:
        return None

    # Generate observations from the LLM's perceptions
    observations = _generate_observations_from_llm(result)
    result["observations"] = observations
    return result


def _deterministic_fallback(text: str, word_count: int) -> Dict:
    """Fallback when LLM is not available — uses heuristic signals."""
    sentences = tagger.split_sentences(text)
    text_lower = text.lower()

    # Narrator closeness: based on first-person density + sensory density + interiority
    first_person = len(re.findall(r'\b(I|me|my)\b', text, re.IGNORECASE))
    first_person_ratio = first_person / word_count * 100
    sensory_words = sum(len(re.findall(r'\b' + re.escape(w) + r'\b', text_lower))
                        for sense_words in AUDHD_THEMES.values() for w in sense_words)
    interiority_verbs = len(re.findall(r'\b(thought|felt|realized|wondered|knew|remembered)\b', text, re.IGNORECASE))

    # Closeness heuristic: high first-person + high interiority = close
    closeness = min(10, int((first_person_ratio / 5 + interiority_verbs / max(len(sentences), 1) * 10) / 2))

    # Reliability: check for hedging/defensive language
    hedge_count = len(re.findall(r'\b(maybe|perhaps|might have|i think|i suppose|i imagine|as far as i)\b', text, re.IGNORECASE))
    defensive_count = len(re.findall(r'\b(because|had to|needed to|no choice|forced|justify|to be clear)\b', text, re.IGNORECASE))

    if hedge_count + defensive_count > 5:
        reliability = f"moderate — hedging/defensive language present in {hedge_count + defensive_count} places"
    elif hedge_count > 0:
        reliability = "generally reliable — some uncertainty language, but not excessive"
    else:
        reliability = "appears reliable — confident declarative voice"

    # Extract a few evidence passages
    evidence = []
    for s in sentences[:5]:
        if first_person and re.search(r'\b(I|me|my)\b', s, re.IGNORECASE):
            evidence.append(s[:150] + ("..." if len(s) > 150 else ""))
            if len(evidence) >= 3:
                break

    # Character perceptions (basic)
    from .characters import _extract_characters
    characters = _extract_characters(text)
    char_perceptions = {}
    for char in characters[:5]:
        char_lower = char.lower()
        char_sentences = [s for s in sentences if char.lower() in s.lower()]
        if char_sentences:
            # Agency heuristic
            agentive_count = len(re.findall(r'\b(decided|chose|left|said|told|asked|went|came|began)\b',
                                             ' '.join(char_sentences), re.IGNORECASE))
            passive_count = len(re.findall(r'\b(was|were|had been)\b', ' '.join(char_sentences), re.IGNORECASE))
            agency = min(10, 3 + agentive_count - passive_count // 2)
            agency = max(1, agency)

            char_evidence = [s[:100] + "..." for s in char_sentences[:2]]
            char_perceptions[char] = {
                "warmth": 5,  # Default — can't determine without LLM
                "competence": 5,
                "agency": agency,
                "evidence": char_evidence,
            }

    # Genre register
    citation_cues = len(re.findall(r'\b(according to|studies show|research|found that)\b', text, re.IGNORECASE))
    if citation_cues > 2:
        genre_register = "research-braid memoir"
    elif first_person_ratio > 3:
        genre_register = "personal memoir"
    else:
        genre_register = "memoir with reflective distance"

    # Emotional register
    emotional = tagger.detect_emotional_register(text) or "reflective"

    observations = _generate_observations_deterministic(closeness, reliability, hedge_count, defensive_count)

    return {
        "narrator_perception": {
            "closeness": closeness,
            "reliability": reliability,
            "evidence": evidence,
        },
        "character_perceptions": char_perceptions,
        "genre_register": genre_register,
        "emotional_register": emotional,
        "fallback_used": True,
        "word_count": word_count,
        "observations": observations,
        "summary": _generate_summary(word_count, {"fallback_used": True}, True),
    }


def _generate_observations_from_llm(result: Dict) -> List[Dict]:
    """Generate observations from LLM reader perception results."""
    observations = []

    narrator = result.get("narrator_perception", {})
    closeness = narrator.get("closeness", 5)

    if closeness <= 3:
        observations.append(format_flag(
            "narrator_closeness",
            "whole chapter",
            f"reader-perceived closeness to narrator is {closeness}/10 (distant)",
            "readers may feel they're observing the narrator rather than inhabiting their perspective",
            [
                "check if the distance is intentional (reflective, analytical voice)",
                "try adding one interior beat (a thought, a sensation) in a key scene",
                "keep as-is if the distance serves the chapter's purpose",
            ]
        ))
    elif closeness >= 8:
        observations.append(format_flag(
            "narrator_closeness",
            "whole chapter",
            f"reader-perceived closeness to narrator is {closeness}/10 (very close)",
            "readers are deeply inside the narrator's perspective — immersive but can feel claustrophobic over long stretches",
            [
                "check if the immersion is sustainable or if readers need a breathing space",
                "notice whether the closeness serves the emotional content",
                "keep as-is if the immersion is intentional",
            ]
        ))

    reliability = narrator.get("reliability", "")
    if "hedg" in reliability.lower() or "defensive" in reliability.lower():
        observations.append(format_flag(
            "narrator_reliability",
            "whole chapter",
            f"narrator reliability: {reliability}",
            "hedging or defensive language can create distance — readers may sense the narrator is protecting something",
            [
                "check if the defensiveness is masking (AUDHD trait) or situation-specific",
                "try one passage without the qualifier to see the effect",
                "keep as-is if the hedging is the narrator's authentic voice",
            ]
        ))

    return observations


def _generate_observations_deterministic(closeness, reliability, hedge_count, defensive_count) -> List[Dict]:
    """Generate observations for the deterministic fallback."""
    observations = []

    if closeness <= 3:
        observations.append(format_flag(
            "narrator_closeness",
            "whole chapter",
            f"narrator closeness is estimated at {closeness}/10 (distant) based on first-person density and interiority signals",
            "readers may feel they're observing rather than inhabiting the narrator's perspective",
            [
                "try adding one interior beat (a thought, a sensation) after key dialogue",
                "check if the distance is intentional (reflective voice) or accidental",
                "keep as-is if the distance serves the chapter",
            ]
        ))

    if defensive_count > 3:
        observations.append(format_flag(
            "defensive_register",
            "whole chapter",
            f"defensive language density is {defensive_count} instances",
            "defensive language can read as masking — explaining yourself before being asked",
            [
                "check if the defensiveness is masking (AUDHD trait) or situation-specific",
                "try one passage without the qualifier",
                "keep as-is if the defensiveness is the narrator's authentic voice",
            ]
        ))

    return observations


def _generate_summary(word_count: int, result: Dict, fallback: bool) -> str:
    mode = "deterministic fallback" if fallback else "AI-assisted"
    narrator = result.get("narrator_perception", {})
    closeness = narrator.get("closeness", "?")
    genre = result.get("genre_register", "?")
    return plain_summary(
        what=f"Reader perception analysis of {word_count} words ({mode})",
        found=f"Narrator closeness: {closeness}/10. Genre register: {genre}.",
        next_step="These are evidence-first impressions, not judgments — use them to notice effects on the reader"
    )
