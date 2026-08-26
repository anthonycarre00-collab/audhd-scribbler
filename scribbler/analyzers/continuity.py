#!/usr/bin/env python3
"""Continuity & timeline analyzer.

Reconstructs temporal structure, detects flashbacks, checks setting consistency,
flags anachronisms (80s-2025 era span), and tracks research claims.
"""
import re
from collections import defaultdict
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag
from .. import tagger
from ..config import ANACHRONISM_WATCHLIST, ERA_SPAN_START, ERA_SPAN_END


def analyze(text: str) -> Dict:
    """Run continuity and timeline analysis."""
    sentences = tagger.split_sentences(text)
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 10:
        return {"error": "Text too short", "word_count": word_count}

    temporal_exprs = _extract_temporal_expressions(text)
    timeline = _build_timeline(temporal_exprs, sentences)
    flashbacks = _detect_flashbacks(sentences)
    settings = _extract_settings(text)
    anachronisms = _detect_anachronisms(text)
    claims = _extract_research_claims(text)

    observations = _generate_observations(temporal_exprs, flashbacks, anachronisms, claims)

    return {
        "word_count": word_count,
        "temporal_expressions": temporal_exprs,
        "timeline": timeline,
        "flashback_signals": flashbacks,
        "settings_detected": settings,
        "anachronism_flags": anachronisms,
        "research_claims": claims,
        "observations": observations,
        "summary": _generate_summary(word_count, len(temporal_exprs), len(anachronisms), len(claims)),
    }


def _extract_temporal_expressions(text: str) -> List[Dict]:
    """Extract temporal expressions: dates, years, seasons, relative time."""
    exprs = []

    # 4-digit years
    for match in re.finditer(r'\b(19[8-9]\d|20[0-2]\d)\b', text):
        exprs.append({
            "type": "year",
            "value": match.group(1),
            "position": match.start(),
            "context": text[max(0, match.start() - 40):match.end() + 40].strip(),
        })

    # Months + years ("summer of 1995", "January 2003")
    for match in re.finditer(r'\b(spring|summer|autumn|fall|winter|January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:of\s+)?(\d{4})\b', text, re.IGNORECASE):
        exprs.append({
            "type": "month_year",
            "value": f"{match.group(1)} {match.group(2)}",
            "position": match.start(),
        })

    # Seasons alone
    for match in re.finditer(r'\b(spring|summer|autumn|fall|winter)\b', text, re.IGNORECASE):
        if not any(e["position"] == match.start() for e in exprs):
            exprs.append({
                "type": "season",
                "value": match.group(1).lower(),
                "position": match.start(),
            })

    # Relative time ("three years later", "the next day", "that summer")
    for match in re.finditer(r'\b(\d+ years? later|the next day|the following day|that (?:summer|winter|spring|autumn|fall|night|morning|evening|afternoon)|years? (?:later|before|after)|a few (?:days|weeks|months|years) (?:later|before|after))\b', text, re.IGNORECASE):
        exprs.append({
            "type": "relative_time",
            "value": match.group(1),
            "position": match.start(),
        })

    # Ages ("when I was seven", "at twelve")
    for match in re.finditer(r'\b(?:when (?:i|he|she|they) was|at age|aged)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)\b', text, re.IGNORECASE):
        exprs.append({
            "type": "age_reference",
            "value": match.group(1),
            "position": match.start(),
        })

    return sorted(exprs, key=lambda e: e["position"])


def _build_timeline(temporal_exprs: List[Dict], sentences: List[str]) -> Dict:
    """Build a rough timeline from temporal expressions."""
    years_found = [int(e["value"]) for e in temporal_exprs if e["type"] == "year"]
    if years_found:
        return {
            "years_referenced": sorted(set(years_found)),
            "earliest_year": min(years_found),
            "latest_year": max(years_found),
            "span": max(years_found) - min(years_found),
            "assessment": f"Timeline spans {max(years_found) - min(years_found)} years ({min(years_found)}-{max(years_found)})",
        }
    return {
        "years_referenced": [],
        "assessment": "No specific years detected — timeline is implicit",
    }


def _detect_flashbacks(sentences: List[str]) -> List[Dict]:
    """Detect flashback signals."""
    flashback_cues = [
        r'\b(i remember|i recall|looking back|in those days|back then|that (?:summer|winter|year|day)|years? (?:before|earlier|ago))\b',
        r'\b(before that|previously|it was (?:a year|two years|several years) (?:before|earlier|prior))\b',
        r'\b(when i was|as a child|as a (?:boy|girl|teenager|kid))\b',
    ]

    flashbacks = []
    for i, s in enumerate(sentences):
        for pattern in flashback_cues:
            if re.search(pattern, s, re.IGNORECASE):
                flashbacks.append({
                    "sentence_number": i + 1,
                    "cue": re.search(pattern, s, re.IGNORECASE).group(0),
                    "preview": s[:120] + ("..." if len(s) > 120 else ""),
                })
                break

    return flashbacks


def _extract_settings(text: str) -> List[str]:
    """Extract setting/location references."""
    from ..tagger import detect_places
    return detect_places(text)


def _detect_anachronisms(text: str) -> List[Dict]:
    """Detect potential anachronisms based on the 80s-2025 era span.

    The ANACHRONISM_WATCHLIST is structured as {category: [item1, item2, ...]}.
    We flatten it and search for each item in the text.
    """
    text_lower = text.lower()
    flags = []

    # Flatten: {category: [items]} -> [(item, category), ...]
    items_to_check = []
    for category, items in ANACHRONISM_WATCHLIST.items():
        if isinstance(items, list):
            for item in items:
                items_to_check.append((item, category))
        elif isinstance(items, int):
            items_to_check.append((category, None))

    for item, category in items_to_check:
        if re.search(r'\b' + re.escape(item.lower()) + r'\b', text_lower):
            # Estimate first_attested based on category
            if category == "technology":
                first_year = 2007
            elif category == "media":
                first_year = 2008
            elif category == "modern_terms":
                first_year = 1995
            else:
                first_year = 2000

            match = re.search(r'\b' + re.escape(item.lower()) + r'\b', text_lower)
            if match:
                pos = match.start()
                context = text[max(0, pos - 50):pos + len(item) + 50].strip()
                nearby_years = re.findall(r'\b(19[8-9]\d|20[0-2]\d)\b', text[max(0, pos - 200):pos + 200])
                scene_year = int(nearby_years[0]) if nearby_years else None

                if scene_year and scene_year < first_year:
                    flags.append({
                        "item": item,
                        "category": category,
                        "first_attested": first_year,
                        "scene_year": scene_year,
                        "context": context,
                        "severity": "potential_anachronism",
                        "message": f"'{item}' ({category}) first appeared around {first_year}, but the scene seems set in {scene_year}. Worth checking.",
                    })
                else:
                    flags.append({
                        "item": item,
                        "category": category,
                        "first_attested": first_year,
                        "context": context,
                        "severity": "note",
                        "message": f"'{item}' ({category}) first appeared around {first_year}. If the scene is set earlier, this may be an anachronism.",
                    })

    return flags


def _extract_research_claims(text: str) -> List[Dict]:
    """Extract research claims that should have citations."""
    claim_cues = [
        r'\b(studies show|research shows?|according to|scientists (?:say|found|believe))\b',
        r'\b(\d+(?:\.\d+)?%|one in \d+|\d+ times more likely|twice as likely|half of)\b',
        r'\b(experts (?:say|believe|agree|argue))\b',
        r'\b(a \d{4} (?:study|survey|report) (?:found|showed|revealed))\b',
    ]

    claims = []
    sentences = tagger.split_sentences(text)
    for i, s in enumerate(sentences):
        for pattern in claim_cues:
            match = re.search(pattern, s, re.IGNORECASE)
            if match:
                # Check if there's a citation nearby
                has_citation = bool(re.search(r'\([A-Z][a-z]+,? \d{4}\)|\[[\d,]+\]|et al\.', s))
                claims.append({
                    "sentence_number": i + 1,
                    "claim_cue": match.group(0),
                    "preview": s[:150] + ("..." if len(s) > 150 else ""),
                    "has_citation": has_citation,
                    "needs_citation": not has_citation,
                })
                break

    return claims


def _generate_observations(temporal_exprs: List, flashbacks: List, anachronisms: List, claims: List) -> List[Dict]:
    observations = []

    # Anachronisms
    for flag in anachronisms:
        if flag["severity"] == "potential_anachronism":
            observations.append(format_flag(
                "anachronism",
                flag["context"][:80],
                f"'{flag['item']}' (first attested ~{flag['first_attested']}) appears in a scene set around {flag['scene_year']}",
                "readers familiar with the era may notice the anachronism",
                [
                    f"replace '{flag['item']}' with something available in {flag['scene_year']}",
                    "adjust the scene's year to match the item",
                    "keep as-is if you have a specific reason for the temporal placement",
                ]
            ))

    # Uncited research claims
    uncited = [c for c in claims if c["needs_citation"]]
    if uncited:
        observations.append(format_flag(
            "research_claims",
            f"sentence(s) {', '.join(str(c['sentence_number']) for c in uncited[:3])}",
            f"{len(uncited)} research claim(s) without an obvious citation",
            "uncited claims are the highest-liability sentences in a research-braid memoir",
            [
                "add a citation (parenthetical author-date or footnote)",
                "rephrase to make clear this is your observation rather than a research finding",
                "remove the claim if you can't source it",
            ]
        ))

    # Many flashbacks
    if len(flashbacks) > 8:
        observations.append(format_flag(
            "flashback_density",
            f"throughout ({len(flashbacks)} flashback signals)",
            f"the chapter contains {len(flashbacks)} flashback signals",
            "frequent flashbacks can fragment the reader's sense of time",
            [
                "check if all flashbacks are necessary or if some can be integrated into the main timeline",
                "consider using section breaks to signal temporal shifts",
                "keep as-is if the associative structure is intentional",
            ]
        ))

    return observations


def _generate_summary(word_count: int, temporal_count: int, anach_count: int, claim_count: int) -> str:
    return plain_summary(
        what=f"Continuity and timeline analysis of {word_count} words",
        found=f"{temporal_count} temporal expressions, {anach_count} anachronism flags, {claim_count} research claims",
        next_step="Check anachronism flags first (they're the most concrete issues), then review uncited research claims"
    )
