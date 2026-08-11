#!/usr/bin/env python3
"""Market & comp-title research analyzer.

Surfaces comparable titles from a curated neurodiversity-memoir seed list
and positions the manuscript in the current market.
"""
import re
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag
from ..config import COMP_SEED_LIST


def analyze(manuscript_description: str = None, chapter_themes: List[str] = None) -> Dict:
    """Analyze market position and suggest comp titles.

    Args:
        manuscript_description: One-paragraph description of the manuscript
        chapter_themes: List of themes detected in the manuscript
    """
    if not manuscript_description and not chapter_themes:
        return {
            "error": "Provide either a manuscript description or chapter themes for comp analysis",
            "note": "Run 'scribbler analyze <chapter>' first to detect themes, then 'scribbler market --description \"your blurb\"'",
        }

    # Find matching comps
    comps = _find_comps(manuscript_description or "", chapter_themes or [])

    # Positioning advice
    positioning = _positioning_advice(manuscript_description, chapter_themes, comps)

    # Observations
    observations = _generate_observations(comps, positioning)

    return {
        "manuscript_description": manuscript_description,
        "chapter_themes": chapter_themes,
        "comp_suggestions": comps,
        "positioning": positioning,
        "observations": observations,
        "summary": _generate_summary(comps, positioning),
    }


def _find_comps(description: str, themes: List[str]) -> List[Dict]:
    """Find comp titles that match by theme or description keywords."""
    description_lower = description.lower()
    theme_set = set(themes)

    scored_comps = []
    for comp in COMP_SEED_LIST:
        score = 0
        match_reasons = []

        # Theme overlap
        comp_themes = set(comp.get("themes", []))
        shared_themes = theme_set & comp_themes
        if shared_themes:
            score += len(shared_themes) * 2
            match_reasons.append(f"shared themes: {', '.join(shared_themes)}")

        # Description keyword overlap
        for theme in comp_themes:
            if theme in description_lower:
                score += 1
                if f"keyword '{theme}'" not in match_reasons:
                    match_reasons.append(f"keyword '{theme}' in description")

        # Form match (if description mentions form)
        form = comp.get("form", "")
        if "memoir" in description_lower and "memoir" in form:
            score += 1
            match_reasons.append("form: memoir")
        if "essay" in description_lower and "essay" in form:
            score += 1
            match_reasons.append("form: essays")
        if "research" in description_lower and "research" in form:
            score += 1
            match_reasons.append("form: research-braid")

        # Neurodiversity-specific
        if any(t in description_lower for t in ["autism", "autistic", "adhd", "audhd", "neurodivergent", "neurodiversity"]):
            if any(t in comp_themes for t in ["autism", "adhd", "identity"]):
                score += 3
                match_reasons.append("neurodiversity focus")

        if score > 0:
            scored_comps.append({
                **comp,
                "match_score": score,
                "match_reasons": match_reasons,
            })

    # Sort by score
    scored_comps.sort(key=lambda x: x["match_score"], reverse=True)

    # Flag comps that are too famous, too old, or too obscure
    for comp in scored_comps:
        flags = []
        if comp["year"] < 2018:
            flags.append(f"published {comp['year']} — older than the ideal 2-3 year window for recent comps")
        if comp["title"] in ["Educated", "Eat Pray Love", "The Body Keeps the Score"]:
            flags.append("very famous — may set unreachable sales expectations")
        comp["flags"] = flags

    return scored_comps[:5]


def _positioning_advice(description: str, themes: List[str], comps: List[Dict]) -> Dict:
    """Provide positioning advice based on the manuscript's signals."""
    desc_lower = (description or "").lower()

    # Detect form
    form_signals = {
        "hybrid_memoir_research": ["research", "studies", "science", "theory", "braid"],
        "essay_collection": ["essays", "linked", "fragments"],
        "linear_memoir": ["chronological", "childhood", "growing up", "life story"],
        "illness_diagnosis": ["diagnosis", "diagnosed", "illness", "condition"],
    }

    detected_forms = []
    for form, signals in form_signals.items():
        if any(s in desc_lower for s in signals):
            detected_forms.append(form)

    # BISAC recommendation
    if any(t in themes for t in ["autism", "adhd", "audhd", "neurodiversity"]):
        bisac_primary = "BIO026000 - Biography & Autobiography / Personal Memoirs"
        bisac_secondary = "PSY004000 - Psychology / Pathologies"
        shelf = "Memoir / Psychology"
    elif "diagnosis" in themes or "illness" in themes:
        bisac_primary = "BIO026000 - Biography & Autobiography / Personal Memoirs"
        bisac_secondary = "HEA000000 - Health & Fitness"
        shelf = "Memoir / Health"
    else:
        bisac_primary = "BIO026000 - Biography & Autobiography / Personal Memoirs"
        bisac_secondary = "LCO015000 - Literary Collections / Essays"
        shelf = "Memoir / Essays"

    # Market gap assessment
    gaps = []
    if "audhd" in desc_lower or ("autism" in desc_lower and "adhd" in desc_lower):
        gaps.append("AUDHD-specific (combined autism+ADHD) memoirs are still scarce — a real positioning opportunity")
    if "literary" in desc_lower and any(t in themes for t in ["autism", "neurodiversity"]):
        gaps.append("The literary essay-memoir end of the neurodiversity shelf is less crowded than the trade-explanatory end")

    # Anti-patterns
    anti_patterns = []
    if len(detected_forms) > 2:
        anti_patterns.append("the manuscript may be trying to be too many forms at once — consider which form is primary")

    return {
        "detected_forms": detected_forms,
        "bisac_primary": bisac_primary,
        "bisac_secondary": bisac_secondary,
        "shelf": shelf,
        "market_gaps": gaps,
        "anti_patterns": anti_patterns,
    }


def _generate_observations(comps: List[Dict], positioning: Dict) -> List[Dict]:
    observations = []

    # Top comp suggestion
    if comps:
        top = comps[0]
        observations.append(format_flag(
            "comp_title",
            "manuscript positioning",
            f"strongest comp match: '{top['title']}' by {top['author']} ({top['year']})",
            f"this book shares {', '.join(top.get('match_reasons', [])[:2])} with your manuscript",
            [
                f"read '{top['title']}' to understand reader expectations for this shelf",
                f"use it as a comp in queries: 'for readers of {top['author']}'",
                "find a second comp that differs in form or audience to round out the positioning",
            ]
        ))

    # Flagged comps
    flagged = [c for c in comps if c.get("flags")]
    for comp in flagged[:2]:
        for flag in comp["flags"]:
            observations.append(format_flag(
                "comp_caution",
                f"'{comp['title']}'",
                flag,
                "this comp may not serve its purpose effectively",
                [
                    "find a more recent comp (ideally published within 2-3 years)",
                    "choose a comp that's successful but not a mega-blockbuster",
                    "keep as a secondary comp if it has strong thematic overlap",
                ]
            ))

    # Market gaps
    for gap in positioning.get("market_gaps", []):
        observations.append(format_flag(
            "market_opportunity",
            "manuscript positioning",
            gap,
            "this gap represents a genuine opportunity for your book",
            [
                "emphasize this distinction in your query letter or book description",
                "research whether agents/editors have asked for books in this space",
                "keep in mind that gaps can also mean limited market — verify with current sales data",
            ]
        ))

    # Anti-patterns
    for pattern in positioning.get("anti_patterns", []):
        observations.append(format_flag(
            "positioning_risk",
            "manuscript form",
            pattern,
            "booksellers struggle to hand-sell books that don't fit a clear shelf",
            [
                "identify which form is primary and commit to it",
                "ensure the blurb leads with the primary form",
                "keep the hybrid elements as texture rather than structure",
            ]
        ))

    return observations


def _generate_summary(comps: List[Dict], positioning: Dict) -> str:
    shelf = positioning.get("shelf", "unknown")
    top_comp = comps[0]["title"] if comps else "none found"
    return plain_summary(
        what="Market and comp-title analysis",
        found=f"Shelf: {shelf}. Top comp: {top_comp}. {len(comps)} comp suggestions total.",
        next_step="Read the top comp to understand reader expectations for your shelf; use comps in queries and positioning"
    )
