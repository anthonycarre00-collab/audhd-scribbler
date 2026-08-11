#!/usr/bin/env python3
"""Low-shame feedback engine for The Audhd Scribbler.

Every output follows the grammar:
  I noticed [observation]. It had [effect on reader]. Would you like to [option A], [option B], or keep as-is?

Never says "fix this". Always offers 2+ paths. One option is always "this may be intentional".
"""
import re
from typing import List, Dict
from .config import WORD_SWAPS


def swap_shame_words(text: str) -> str:
    """Replace shame-triggering words with gentler alternatives."""
    swapped = text
    for bad, good in WORD_SWAPS.items():
        # Case-insensitive whole-word replacement
        swapped = re.sub(r'\b' + re.escape(bad) + r'\b', good, swapped, flags=re.IGNORECASE)
    return swapped


def make_observation(what_noticed: str, reader_effect: str, options: List[str]) -> str:
    """Build a low-shame feedback observation.

    Args:
        what_noticed: Specific, located observation. "In chapter 3, paragraph 4, three sentences start with 'I felt'"
        reader_effect: Named effect on the reader. "the narrative distance increased and I felt like an observer rather than present in the scene"
        options: 2-3 optional paths forward. One should be "keep as-is" or "this may be intentional"

    Returns:
        Formatted observation string
    """
    # Ensure there's always a "keep as-is" option
    has_keep = any("keep" in o.lower() or "intentional" in o.lower() or "as-is" in o.lower() for o in options)
    if not has_keep:
        options.append("keep as-is if this is intentional")

    options_text = ", ".join(f"({chr(97+i)}) {o}" for i, o in enumerate(options))

    return f"I noticed {what_noticed}. It had the effect that {reader_effect}. Would you like to {options_text}?"


def strengths_first(strengths: List[str], observations: List[str]) -> Dict:
    """Format output with strengths first, then observations.

    Args:
        strengths: List of genuine strengths found
        observations: List of low-shame observation strings

    Returns:
        Dict with 'strengths' and 'observations' keys
    """
    return {
        "strengths": strengths if strengths else ["The fact that this material exists and was shared is itself a strength."],
        "observations": observations,
    }


def plain_summary(what: str, found: str, next_step: str) -> str:
    """Generate a 3-line plain-English summary.

    Line 1: What this is
    Line 2: What it found
    Line 3: What you could do next (optional, always)
    """
    return f"What this is: {what}\nWhat it found: {found}\nWhat you could do next: {next_step}"


def format_flag(category: str, location: str, observation: str, effect: str, options: List[str]) -> Dict:
    """Format a single flag for structured output."""
    return {
        "category": category,
        "location": location,
        "observation": observation,
        "effect": effect,
        "options": options,
        "formatted": make_observation(f"{observation} ({location})", effect, options),
    }
