#!/usr/bin/env python3
"""Cross-tool synthesis report.

After all analysis tools run, this module connects signals across tools
to produce a unified report: voice consistency, narrator distance,
recurring signals, top things to notice, and what the signals do NOT mean.
"""
import re
from typing import Dict, List, Any
from collections import Counter

from .feedback import plain_summary


def generate(results: Dict[str, Any], word_count: int = 0) -> Dict:
    """Generate a cross-tool synthesis from all analysis results.

    Args:
        results: Dict of {tool_name: result_dict} from all analyzers
        word_count: Total word count of the analyzed text
    """
    synthesis = {
        "voice_consistency": _voice_consistency(results),
        "narrator_distance": _narrator_distance(results),
        "recurring_signals": _recurring_signals(results),
        "top_things_to_notice": _top_things_to_notice(results),
        "what_this_does_not_mean": _what_this_does_not_mean(results),
        "audhd_aware_notes": _audhd_aware_notes(results),
    }

    synthesis["summary"] = _generate_summary(results, word_count)
    return synthesis


def _voice_consistency(results: Dict) -> str:
    """Synthesize voice consistency signals from voice_tense, voice_dna, cadence."""
    parts = []

    voice = results.get("voice_tense", results.get("voice", {}))
    if voice and "error" not in voice:
        tense = voice.get("tense_distribution", {})
        dominant = tense.get("dominant_tense", "unknown")
        pct = tense.get("percentages", {}).get(dominant, 0)
        if pct > 80:
            parts.append(f"Tense dominant ({dominant}, {pct:.0f}%).")
        elif pct > 60:
            parts.append(f"Tense mixed ({dominant} {pct:.0f}%).")
        else:
            parts.append(f"Tense varied (no single dominant tense).")

    vdna = results.get("voice_dna", {})
    if vdna and "error" not in vdna:
        sim = vdna.get("similarity_to_approved")
        drift = vdna.get("drift_assessment", "")
        if sim is not None:
            if sim > 0.85:
                parts.append(f"Voice DNA drift: low (similarity {sim:.0%}).")
            elif sim > 0.7:
                parts.append(f"Voice DNA drift: moderate (similarity {sim:.0%}).")
            else:
                parts.append(f"Voice DNA drift: significant (similarity {sim:.0%}).")
        elif drift:
            parts.append(drift)

    cadence = results.get("cadence", {})
    if cadence and "error" not in cadence:
        opener_var = cadence.get("opener_variety_score", 0)
        if opener_var < 0.4:
            parts.append(f"Low opener variety ({opener_var}) — repetitive sentence starts.")

    if not parts:
        return "Voice signals not available (run voice, voice_dna, and cadence tools for full synthesis)."

    return " ".join(parts) + " The chapter reads as " + ("settled in voice." if "low" in parts[-1].lower() or "dominant" in parts[0].lower() else "varied in voice.")


def _narrator_distance(results: Dict) -> str:
    """Synthesize narrator distance from voice_tense, editor, reader_perception."""
    parts = []

    voice = results.get("voice_tense", results.get("voice", {}))
    if voice and "error" not in voice:
        distance = voice.get("narrator_distance", {})
        ratio = distance.get("narrating_self_ratio", 0.5)
        assessment = distance.get("assessment", "")
        if ratio > 0.7:
            parts.append(f"Narrating self dominates (ratio {ratio:.2f}).")
        elif ratio < 0.2:
            parts.append(f"Experiencing self dominates (ratio {ratio:.2f}).")
        else:
            parts.append(f"Balanced narrator distance (ratio {ratio:.2f}).")

    editor = results.get("editor", {})
    if editor and "error" not in editor:
        obs = editor.get("observations", [])
        distant_obs = [o for o in obs if isinstance(o, dict) and "distant" in o.get("category", "").lower()]
        defensive_obs = [o for o in obs if isinstance(o, dict) and "defensive" in o.get("category", "").lower()]
        if distant_obs:
            parts.append(f"Distant narrator signal detected ({len(distant_obs)} observation(s)).")
        if defensive_obs:
            parts.append(f"Defensive register detected ({len(defensive_obs)} observation(s)).")

    rp = results.get("reader_perception", {})
    if rp and "error" not in rp:
        narrator = rp.get("narrator_perception", {})
        closeness = narrator.get("closeness", 5)
        if closeness <= 3:
            parts.append(f"Reader-perceived closeness: {closeness}/10 (distant).")
        elif closeness >= 8:
            parts.append(f"Reader-perceived closeness: {closeness}/10 (close).")

    if not parts:
        return "Narrator distance signals not available."

    result = " ".join(parts)
    # Add synthesis interpretation
    if "distant" in result.lower() or "defensive" in result.lower():
        result += " Combined signals suggest the narrator may be protecting or explaining rather than reliving."
    elif "experiencing" in result.lower() or "close" in result.lower():
        result += " Readers are likely inside the experience."
    return result


def _recurring_signals(results: Dict) -> List[str]:
    """Find signals that recur across multiple tools."""
    signals = []

    # Check if "diagnosis" or key themes appear in multiple tools
    themes = results.get("themes", {})
    if themes and "error" not in themes:
        theme_density = themes.get("theme_density", {})
        dominant = theme_density.get("dominant_theme", "")
        if dominant:
            # Check if it also appears in repetition
            rep = results.get("repetition", {})
            if rep and "error" not in rep:
                repeated_words = rep.get("repeated_words", [])
                for rw in repeated_words:
                    if isinstance(rw, dict) and dominant.lower() in rw.get("term", "").lower():
                        signals.append(f"'{dominant}' appears as both a theme (themes tool) and a repeated word (repetition tool, {rw.get('count')}x).")
                        break

    # Check sensory density across tools
    craft = results.get("craft", {})
    if craft and "error" not in craft:
        sensory = craft.get("sensory_density", {})
        per_1000 = sensory.get("per_1000_words", 0)
        if per_1000 > 10:
            # Check if motifs also detected sensory clusters
            motifs = results.get("motifs", {})
            if motifs and "error" not in motifs:
                sensory_clusters = motifs.get("sensory_motif_clusters", motifs.get("sensory_motifs", []))
                if sensory_clusters:
                    signals.append(f"Strong sensory grounding ({per_1000}/1000) confirmed by motif analysis ({len(sensory_clusters)} sensory cluster(s)).")

    # Check tense consistency
    voice = results.get("voice_tense", results.get("voice", {}))
    if voice and "error" not in voice:
        tense_shifts = voice.get("tense_shifts", [])
        if len(tense_shifts) > 5:
            cadence = results.get("cadence", {})
            if cadence and "error" not in cadence:
                drop_beats = cadence.get("drop_beat_count", 0)
                if drop_beats > 2:
                    signals.append(f"Frequent tense shifts ({len(tense_shifts)}) combined with drop beats ({drop_beats}) — may indicate associative rather than linear thinking.")

    # Check dialogue ratio across craft and reader
    if craft and "error" not in craft:
        dialogue = craft.get("dialogue_ratio", {})
        dialogue_pct = dialogue.get("dialogue_pct", 0)
        if dialogue_pct > 50:
            signals.append(f"Dialogue-heavy ({dialogue_pct:.0f}%) — other voices dominate. Check character agency for balance.")

    return signals


def _top_things_to_notice(results: Dict) -> List[str]:
    """Pick the top 3-5 most important signals across all tools."""
    candidates = []

    # Count observations per tool
    for tool_name, result in results.items():
        if not isinstance(result, dict) or "error" in result:
            continue
        obs = result.get("observations", [])
        if obs:
            for o in obs:
                if isinstance(o, dict):
                    cat = o.get("category", "")
                    formatted = o.get("formatted", "")
                    if formatted:
                        candidates.append({
                            "tool": tool_name,
                            "category": cat,
                            "text": formatted,
                            "priority": _priority_score(cat, tool_name),
                        })

    # Sort by priority and return top 5
    candidates.sort(key=lambda x: x["priority"], reverse=True)
    return [f"[{c['tool']}/{c['category']}] {c['text']}" for c in candidates[:5]]


def _priority_score(category: str, tool: str) -> int:
    """Score observation priority — higher = more important."""
    score = 0
    cat_lower = category.lower()

    # High-priority categories
    if "distant" in cat_lower or "defensive" in cat_lower:
        score += 10
    if "anachronism" in cat_lower:
        score += 9
    if "research_claim" in cat_lower:
        score += 8
    if "voice_drift" in cat_lower:
        score += 8
    if "tense" in cat_lower:
        score += 7
    if "rhythm" in cat_lower:
        score += 5
    if "sensory" in cat_lower:
        score += 5
    if "arc_shape" in cat_lower:
        score += 4
    if "recurring" in cat_lower:
        score += 6
    if "parallelism" in cat_lower:
        score += 4

    # Tool-based priority
    if tool == "editor":
        score += 3
    if tool == "reader_perception":
        score += 2

    return score


def _what_this_does_not_mean(results: Dict) -> List[str]:
    """Explicitly state what the analysis does NOT mean — anti-anxiety framing."""
    return [
        "These signals describe patterns; they do not decide whether the chapter is good.",
        "You are the writer; Scribbler is a noticing tool, not an editor.",
        "Every observation includes a 'keep as-is if intentional' option — nothing here is a mandate.",
        "AUDHD patterns (hyperfocus, sensory clustering, associative jumps) are traits, not deficits.",
        "If a signal feels wrong for your chapter, trust your instinct over the tool.",
    ]


def _audhd_aware_notes(results: Dict) -> List[str]:
    """Generate AUDHD-aware notes based on detected patterns."""
    notes = []

    # Check for hyperfocus passages
    craft = results.get("craft", {})
    if craft and "error" not in craft:
        rhythm = craft.get("sentence_length_rhythm", {})
        cv = rhythm.get("coefficient_of_variation", 0)
        very_long_pct = rhythm.get("very_long_sentences_pct", 0)
        if very_long_pct > 15:
            notes.append("High proportion of very long sentences — this can indicate hyperfocus passages (an AUDHD writing strength). Check if the depth serves the reader or stretches their stamina.")

    # Check for masking language
    editor = results.get("editor", {})
    if editor and "error" not in editor:
        obs = editor.get("observations", [])
        for o in obs:
            if isinstance(o, dict) and "defensive" in o.get("category", "").lower():
                notes.append("Defensive/explanatory language detected — this can be masking (an AUDHD trait where you explain yourself before being asked). Check if it's your authentic voice or a protective pattern.")
                break

    # Check for sensory clustering
    if craft and "error" not in craft:
        sensory = craft.get("sensory_density", {})
        missing = sensory.get("missing_senses", [])
        if len(missing) >= 3:
            notes.append(f"Sensory detail is clustered in some senses but absent in others ({', '.join(missing)} missing). This is common in AUDHD writing — senses fire together or not at all. Consider whether the absence is intentional.")

    # Check for associative jumps
    voice = results.get("voice_tense", results.get("voice", {}))
    if voice and "error" not in voice:
        shifts = voice.get("tense_shifts", [])
        if len(shifts) > 8:
            notes.append(f"Frequent tense shifts ({len(shifts)}) — this can be associative thinking (an AUDHD cognitive style) rather than error. Check if the jumps are intentional or could use transition phrases.")

    # Check for parallelism (list-making)
    cadence = results.get("cadence", {})
    if cadence and "error" not in cadence:
        parallelism = cadence.get("parallelism_runs", [])
        if parallelism:
            notes.append(f"Parallelism detected ({len(parallelism)} run(s)) — list-making and enumeration are common AUDHD writing patterns. They can create powerful rhythm when intentional.")

    if not notes:
        notes.append("No strong AUDHD-specific patterns detected in this chapter. The analysis above applies to all writers.")

    return notes


def _generate_summary(results: Dict, word_count: int) -> str:
    tool_count = len([r for r in results.values() if isinstance(r, dict) and "error" not in r])
    obs_count = sum(len(r.get("observations", [])) for r in results.values() if isinstance(r, dict) and "observations" in r)

    return plain_summary(
        what=f"Cross-tool synthesis of {tool_count} analysis tools ({word_count} words)",
        found=f"{obs_count} total observations synthesized into recurring signals and AUDHD-aware notes",
        next_step="Read the top things to notice first, then scan the recurring signals — each is a pattern to notice, not a problem to fix"
    )
