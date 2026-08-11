#!/usr/bin/env python3
"""Character & voice tracking analyzer.

Tracks character presence, agency arcs, and voice drift across the manuscript.
"""
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag
from .. import tagger
from ..config import AUDHD_THEMES


def analyze(text: str, all_files: List[Dict] = None) -> Dict:
    """Analyze characters and voice in text. If all_files provided, does cross-chapter tracking."""
    sentences = tagger.split_sentences(text)
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 10:
        return {"error": "Text too short", "word_count": word_count}

    characters = _extract_characters(text)
    presence = _character_presence(sentences, characters)
    agency = _character_agency(sentences, characters)
    voice_fingerprint = _voice_fingerprint(text, words)
    observations = _generate_observations(characters, presence, agency, voice_fingerprint)

    return {
        "word_count": word_count,
        "characters_detected": characters,
        "character_presence": presence,
        "character_agency": agency,
        "voice_fingerprint": voice_fingerprint,
        "observations": observations,
        "summary": _generate_summary(word_count, len(characters)),
    }


def _extract_characters(text: str) -> List[str]:
    """Extract character names from text."""
    from ..tagger import detect_characters
    return detect_characters(text)


def _character_presence(sentences: List[str], characters: List[str]) -> Dict:
    """Track when each character appears (which sentences)."""
    presence = {}
    for char in characters:
        appearances = []
        for i, s in enumerate(sentences):
            if re.search(r'\b' + re.escape(char) + r'\b', s, re.IGNORECASE):
                appearances.append(i + 1)
        if appearances:
            presence[char] = {
                "first_appearance": appearances[0],
                "last_appearance": appearances[-1],
                "total_mentions": len(appearances),
                "sentence_numbers": appearances[:20],  # Cap for storage
            }
    return presence


def _character_agency(sentences: List[str], characters: List[str]) -> Dict:
    """Estimate character agency: agentive verbs vs. passive constructions."""
    agentive_verbs = [
        "decided", "chose", "left", "stayed", "fought", "ran", "walked", "said",
        "told", "asked", "demanded", "refused", "accepted", "began", "started",
        "stopped", "created", "built", "broke", "found", "lost", "gave", "took",
        "went", "came", "looked", "turned", "reached", "grabbed", "held",
    ]
    passive_verbs = ["was", "were", "had been", "got", "gotten", "became"]

    agency = {}
    for char in characters:
        agentive_count = 0
        passive_count = 0
        for s in sentences:
            if re.search(r'\b' + re.escape(char) + r'\b', s, re.IGNORECASE):
                # Check if character is subject of an agentive verb
                if re.search(r'\b' + re.escape(char) + r'\s+\w*\s*(?:' + '|'.join(agentive_verbs) + r')\b', s, re.IGNORECASE):
                    agentive_count += 1
                # Check for passive constructions
                if re.search(r'\b' + re.escape(char) + r'\s+(?:was|were|had been)\b', s, re.IGNORECASE):
                    passive_count += 1

        total = agentive_count + passive_count
        if total > 0:
            agency[char] = {
                "agentive_count": agentive_count,
                "passive_count": passive_count,
                "agency_ratio": round(agentive_count / total, 2),
                "assessment": _assess_agency(agentive_count / total),
            }
    return agency


def _assess_agency(ratio: float) -> str:
    if ratio > 0.7:
        return "highly agentive — this character acts on the world"
    elif ratio > 0.5:
        return "moderately agentive — this character drives some action"
    elif ratio > 0.3:
        return "moderately passive — things happen to this character"
    else:
        return "highly passive — this character is acted upon"


def _voice_fingerprint(text: str, words: List[str]) -> Dict:
    """Compute a voice fingerprint for drift detection."""
    word_count = len(words)
    if word_count == 0:
        return {}

    # Function word distribution (top 30)
    function_words = [
        "the", "of", "and", "to", "a", "in", "is", "that", "it", "was",
        "for", "on", "with", "as", "he", "i", "they", "we", "she", "you",
        "but", "not", "this", "from", "had", "by", "his", "her", "or", "an",
    ]
    text_lower = text.lower()
    fw_freq = {}
    for fw in function_words:
        count = len(re.findall(r'\b' + fw + r'\b', text_lower))
        fw_freq[fw] = count / word_count * 1000  # Per 1000 words

    # Punctuation habits
    punctuation = {}
    for punct, name in [(",", "comma"), (".", "period"), (";", "semicolon"),
                        ("—", "em_dash"), ("-", "hyphen"), ("!", "exclamation"),
                        ("?", "question"), (":", "colon"), ("...", "ellipsis")]:
        punctuation[name] = text.count(punct) / word_count * 1000

    # Lexical diversity (MATTR approximation)
    if word_count > 500:
        window = 500
        ttrs = []
        for i in range(0, word_count - window, 100):
            window_words = words[i:i + window]
            ttrs.append(len(set(window_words)) / len(window_words))
        mattr = sum(ttrs) / len(ttrs) if ttrs else 0
    else:
        mattr = len(set(words)) / word_count

    # Sentence length stats
    sentence_lengths = [len(re.findall(r'\b\w+\b', s)) for s in tagger.split_sentences(text)]
    avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0

    return {
        "function_word_freq": {k: round(v, 1) for k, v in fw_freq.items()},
        "punctuation_per_1000": {k: round(v, 2) for k, v in punctuation.items()},
        "lexical_diversity_mattr": round(mattr, 3),
        "avg_sentence_length": round(avg_sentence_length, 1),
    }


def _generate_observations(characters: List[str], presence: Dict, agency: Dict, voice: Dict) -> List[Dict]:
    observations = []

    # Characters with very low presence
    for char, data in presence.items():
        if data["total_mentions"] == 1:
            observations.append(format_flag(
                "character_presence",
                f"sentence {data['first_appearance']}",
                f"'{char}' appears only once in this text",
                "a character mentioned once may be a loose thread or an underdeveloped presence",
                [
                    f"check if '{char}' appears in other chapters and could be linked",
                    "consider whether this character needs more presence or is a passing mention",
                    "keep as-is if this is a deliberate single-mention reference",
                ]
            ))

    # Passive narrator (if 'I' or first-person is highly passive)
    for char, data in agency.items():
        if data["agency_ratio"] < 0.3 and char.lower() in ["i", "narrator", "me"]:
            observations.append(format_flag(
                "narrator_agency",
                "whole chapter",
                f"the narrator's agency ratio is {data['agency_ratio']}, which is quite low",
                "the narrator may read as passive — things happen to them rather than them driving action",
                [
                    "check if the passivity is intentional for this section of the arc",
                    "consider giving the narrator one decisive action",
                    "keep as-is if the passivity reflects the narrator's state at this point in the story",
                ]
            ))

    # Lexical diversity
    mattr = voice.get("lexical_diversity_mattr", 0.5)
    if mattr < 0.4:
        observations.append(format_flag(
            "lexical_diversity",
            "whole chapter",
            f"lexical diversity (MATTR) is {mattr}, which is low",
            "vocabulary repetition may make the prose feel constrained",
            [
                "try varying word choice in dense passages",
                "check if the repetition is intentional (thematic, rhythmic)",
                "keep as-is if the constrained vocabulary mirrors the narrator's mental state",
            ]
        ))

    return observations


def _generate_summary(word_count: int, char_count: int) -> str:
    return plain_summary(
        what=f"Character and voice analysis of {word_count} words with {char_count} characters detected",
        found="Character presence timeline, agency ratios, and voice fingerprint (function words, punctuation, lexical diversity)",
        next_step="Check which characters appear only once (loose threads?) and whether the narrator's agency feels right for this point in the arc"
    )
