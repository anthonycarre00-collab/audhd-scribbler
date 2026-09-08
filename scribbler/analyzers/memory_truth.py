#!/usr/bin/env python3
"""Memory-truth analyzer.

Detects:
- Memory-uncertainty language ("I think", "as far as I remember", "if I recall")
- Absolute claims ("always", "never", "everyone", "no one")
- Unverifiable internal states attributed to others ("she must have been angry",
  "he probably knew")

Memoir-specific: flags places where the narrator is over-claiming certainty
or under-claiming memory. Neither is wrong — but they're craft choices worth
noticing.
"""
import re
from typing import Dict, List
from collections import Counter

from ..feedback import format_flag, plain_summary
from ..passage import build_index as build_passage_index, make_loc


# Memory-uncertainty phrases (narrator hedging on memory)
MEMORY_UNCERTAINTY_PATTERNS = [
    (r'\b(i think|i believe|i guess|i suppose|i imagine)\b', 'hedge'),
    (r'\b(as far as i (can )?remember|if i recall|if i remember|my memory serves)\b', 'memory_hedge'),
    (r'\b(i don\'t remember|i can\'t remember|i don\'t recall|i have no memory)\b', 'memory_loss'),
    (r'\b(maybe|perhaps|probably|possibly|i think maybe)\b', 'general_hedge'),
    (r'\b(i must have|i must\'ve|i would have|i would\'ve)\b', 'reconstruction'),
    (r'\b(i don\'t know if|i\'m not sure if|i can\'t say whether)\b', 'explicit_doubt'),
]

# Absolute claims (over-claiming certainty)
ABSOLUTE_PATTERNS = [
    (r'\b(always|never|everyone|no one|nobody|everybody|all|none)\b', 'absolute'),
    (r'\b(certain|definitely|absolutely|undoubtedly|without question)\b', 'certainty'),
    (r'\b(obviously|clearly|of course|naturally)\b', 'assumed_obvious'),
]

# Unverifiable internal states attributed to others
OTHER_MIND_PATTERNS = [
    (r'\b(he|she|they|mom|dad|mother|father)\s+(must have|must\'ve|probably|likely)\b', 'other_mind_guess'),
    (r'\b(he|she|they)\s+(was|were)\s+(probably|likely|surely)\b', 'other_mind_assumption'),
    (r'\b(i knew (he|she|they) (was|were))\b', 'claimed_knowledge'),
]


def analyze(text: str) -> Dict:
    """Run memory-truth analysis on the text."""
    if len(text.split()) < 10:
        return {"error": "Text too short for meaningful analysis"}

    try:
        passage_idx = build_passage_index(text)
    except Exception:
        passage_idx = {"paragraphs": []}

    # Find all matches with paragraph numbers
    uncertainty_matches = _find_pattern_matches(text, passage_idx, MEMORY_UNCERTAINTY_PATTERNS)
    absolute_matches = _find_pattern_matches(text, passage_idx, ABSOLUTE_PATTERNS)
    other_mind_matches = _find_pattern_matches(text, passage_idx, OTHER_MIND_PATTERNS)

    # Build observations
    observations = []

    # Memory uncertainty — usually not a problem, but worth noticing
    if len(uncertainty_matches) >= 3:
        # Find the paragraphs with the most hedges
        para_counts = Counter(m["paragraph"] for m in uncertainty_matches)
        dense_paras = [p for p, _ in para_counts.most_common(5)]
        evidence = _excerpt_for_paragraphs(passage_idx, dense_paras[:3])
        loc = make_loc(dense_paras[:5], evidence_quote=evidence)
        observations.append(format_flag(
            "memory_uncertainty",
            f"{len(uncertainty_matches)} instances across {len(para_counts)} paragraph(s)",
            f"memory-uncertainty language appears {len(uncertainty_matches)} times "
            f"(phrases like 'I think', 'as far as I remember', 'I must have')",
            "the narrator is signaling the fragility of memory — this is honest memoir craft, "
            "but clusters of hedges can slow the reader's trust in the scene",
            [
                "let one or two hedges stand (they're authentic) and convert others to specific detail",
                "if a memory is genuinely uncertain, name the uncertainty ('I don't remember what she wore, only the smell of her coat')",
                "keep as-is if the chapter is intentionally about the unreliability of memory",
            ],
            loc=loc,
            evidence_quote=evidence,
            why_it_matters="Memoir readers don't need certainty — they need specificity. 'I think she was wearing blue' is less powerful than 'I can't see her face, but I remember her hands were cold.'"
        ))

    # Absolute claims
    if len(absolute_matches) >= 5:
        para_counts = Counter(m["paragraph"] for m in absolute_matches)
        dense_paras = [p for p, _ in para_counts.most_common(5)]
        evidence = _excerpt_for_paragraphs(passage_idx, dense_paras[:3])
        loc = make_loc(dense_paras[:5], evidence_quote=evidence)
        # Find the most common absolute word
        word_counts = Counter(m["match"].lower() for m in absolute_matches)
        top_word = word_counts.most_common(1)[0][0] if word_counts else "always"
        observations.append(format_flag(
            "absolute_claims",
            f"{len(absolute_matches)} instances across {len(para_counts)} paragraph(s)",
            f"absolute-language density is high ({len(absolute_matches)} instances; "
            f"most frequent: '{top_word}')",
            "absolutes ('always', 'never', 'everyone') can read as over-claiming — "
            "they invite the reader to find the exception that breaks the absolute",
            [
                f"replace one '{top_word}' with a specific instance ('every Tuesday' instead of 'always')",
                "soften one absolute into a tendency ('usually', 'often') where the specific isn't available",
                "keep as-is if the absolute is the point ('She never came back' as a chapter-ending line)",
            ],
            loc=loc,
            evidence_quote=evidence,
            why_it_matters="Memoir lives in specifics. 'My mother never hugged me' is a thesis; 'I cannot remember my mother ever hugging me before I was twelve' is a memoir."
        ))

    # Unverifiable internal states attributed to others
    if len(other_mind_matches) >= 2:
        para_counts = Counter(m["paragraph"] for m in other_mind_matches)
        dense_paras = [p for p, _ in para_counts.most_common(5)]
        evidence = _excerpt_for_paragraphs(passage_idx, dense_paras[:3])
        loc = make_loc(dense_paras[:5], evidence_quote=evidence)
        observations.append(format_flag(
            "other_mind_claims",
            f"{len(other_mind_matches)} instances across {len(para_counts)} paragraph(s)",
            f"the narrator attributes internal states to others {len(other_mind_matches)} times "
            f"(phrases like 'she must have been angry', 'he probably knew')",
            "these are guesses about other people's minds — they can feel invasive or "
            "over-certain in memoir, where the narrator only truly knows their own experience",
            [
                "convert one guess to a question ('Was she angry? I couldn't tell.')",
                "describe the observable behavior instead ('She slammed the door — I assumed she was angry')",
                "keep as-is if the guess is named as a guess ('I imagine she was angry, though she never said')",
            ],
            loc=loc,
            evidence_quote=evidence,
            why_it_matters="The memoir contract is 'I will tell you what I experienced, not what I imagined others experienced.' Crossing into others' minds is the novelists' territory."
        ))

    word_count = len(text.split())
    summary = plain_summary(
        what=f"Memory-truth analysis of {word_count} words",
        found=f"{len(uncertainty_matches)} memory hedges, {len(absolute_matches)} absolute claims, "
              f"{len(other_mind_matches)} other-mind attributions",
        next_step="Noticing these patterns is the work — none of them are wrong, but each is a craft choice"
    )

    return {
        "word_count": word_count,
        "memory_uncertainty_count": len(uncertainty_matches),
        "absolute_claim_count": len(absolute_matches),
        "other_mind_claim_count": len(other_mind_matches),
        "memory_uncertainty_examples": [m["match"] for m in uncertainty_matches[:8]],
        "absolute_claim_examples": [m["match"] for m in absolute_matches[:8]],
        "other_mind_examples": [m["match"] for m in other_mind_matches[:8]],
        "observations": observations,
        "summary": summary,
    }


def _find_pattern_matches(text: str, passage_idx: Dict, patterns: List) -> List[Dict]:
    """Find all matches of (regex, label) patterns with paragraph numbers."""
    matches = []
    if not passage_idx.get("paragraphs"):
        return matches
    for pattern, label in patterns:
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error:
            continue
        for p in passage_idx["paragraphs"]:
            for m in rx.finditer(p["text"]):
                matches.append({
                    "match": m.group(0),
                    "label": label,
                    "paragraph": p["index"],
                    "char_start": m.start(),
                    "char_end": m.end(),
                })
    return matches


def _excerpt_for_paragraphs(passage_idx: Dict, para_nums: List[int], max_chars: int = 220) -> str:
    """Return a short excerpt from the first matching paragraph."""
    if not para_nums or not passage_idx.get("paragraphs"):
        return ""
    for p in passage_idx["paragraphs"]:
        if p["index"] == para_nums[0]:
            return p["text"][:max_chars - 1] + "…" if len(p["text"]) > max_chars else p["text"]
    return ""
