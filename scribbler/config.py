#!/usr/bin/env python3
"""Configuration for The Audhd Scribbler."""
import os
import sys
from pathlib import Path

_CODE_ROOT = Path(__file__).resolve().parent.parent
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(os.environ.get("AUDHD_SCRIBBLER_HOME", Path.home() / "Documents" / "Audhd Scribbler"))
else:
    PROJECT_ROOT = _CODE_ROOT

FOLDERS = {
    "raw-dumps": "Brain dumps, voice-to-text transcripts, freewrites. No structure required.",
    "triage": "Dumps with suggested tags applied; awaiting writer confirmation.",
    "chapters": "Chapter drafts in progress.",
    "characters": "Character notes, aliases, relationships and timeline notes.",
    "places": "Recurring places and consistency notes.",
    "themes": "Themes, motifs and recurrences.",
    "research": "Source claims, citations and bibliography.",
    "comps": "Comparable-title research.",
    "drafts": "Chapters past first draft but not yet final.",
    "final": "Polished chapters ready for the manuscript.",
    "archive": "Older drafts and deliberately archived material. Never deleted by Scribbler.",
}

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "scribbler.db"
REPORTS_DIR = DATA_DIR / "reports"

ERA_SPAN_START = 1980
ERA_SPAN_END = 2025
ERAS = [
    ("childhood", "Early years, pre-adolescence"),
    ("adolescence", "Teen years"),
    ("twenties", "Approximately 20-29"),
    ("thirties", "Approximately 30-39"),
    ("forties", "Approximately 40-49"),
    ("fifties_plus", "50 and beyond"),
    ("now", "Present-day reflective voice"),
]
STATUSES = ["seedling", "growing", "shaping", "polishing", "resting"]
VOICES = ["narrator", "character", "research", "lyric", "other"]

SENSORY_CATEGORIES = {
    "sight": ["see", "saw", "look", "watch", "stare", "gaze", "glance", "gleam", "glow", "shadow", "color", "bright", "dim", "flash"],
    "sound": ["hear", "heard", "listen", "sound", "noise", "quiet", "loud", "hum", "buzz", "ring", "whisper", "shout", "creak", "crash"],
    "smell": ["smell", "scent", "odor", "aroma", "whiff", "stink", "fragrance", "reek", "pungent", "musty"],
    "taste": ["taste", "flavor", "bitter", "sweet", "sour", "salty", "savory", "metallic", "bile"],
    "touch": ["feel", "felt", "touch", "smooth", "rough", "soft", "hard", "warm", "cold", "wet", "dry", "sticky", "velvet", "sandpaper"],
    "proprioception": ["balance", "dizzy", "steady", "tilt", "fall", "stumble", "grounded", "weightless", "heavy", "light"],
    "interoception": ["heartbeat", "pulse", "breath", "breathing", "chest", "stomach", "gut", "throat", "tension", "tight", "knot", "hollow", "full", "empty", "racing", "flutter"],
}

AUDHD_THEMES = {
    "diagnosis": ["diagnosis", "diagnosed", "diagnostic", "assessment", "evaluated", "tested", "labeled", "identified"],
    "masking": ["masking", "mask", "pretending", "passing", "camouflage", "camouflaging", "fake", "pretend", "perform", "performing", "script", "scripting"],
    "sensory": ["sensory", "overload", "overwhelm", "overstimulated", "understimulated", "stim", "stimming", "sensory diet", "dysregulation", "regulated", "dysregulated"],
    "meltdown": ["meltdown", "meltdowns", "shutdown", "shut down", "frozen", "freeze", "froze", "flooded", "incapacitated"],
    "special_interest": ["special interest", "hyperfixation", "hyperfixated", "obsessed", "obsession", "deep dive", "rabbit hole", "infodump", "info dump", "passionate about"],
    "executive_function": ["executive function", "task initiation", "working memory", "planning", "prioritizing", "overwhelmed by", "paralyzed", "stuck", "frozen", "can't start", "can't begin"],
    "stimming": ["stimming", "stim", "rocking", "flapping", "humming", "tapping", "fidget", "fidgeting", "repetitive", "pace", "pacing", "spinning"],
    "burnout": ["burnout", "burned out", "burnt out", "exhausted", "depleted", "drained", "empty", "hollow", "numb", "checked out", "dissociated"],
    "routine": ["routine", "ritual", "same", "change", "transition", "transitioning", "disruption", "unexpected", "surprise", "sameness", "consistent"],
    "social": ["social", "socializing", "party", "gatherings", "small talk", "eye contact", "cue", "cues", "social cues", "norms", "unwritten rules", "etiquette"],
    "identity": ["identity", "autistic", "adhd", "audhd", "neurodivergent", "neurodiversity", "neurotypical", "disabled", "difference", "different", "normal", "normalcy"],
    "grief": ["grief", "mourning", "loss", "lost", "death", "died", "gone", "funeral", "memorial", "anniversary", "missing", "miss"],
    "shame": ["shame", "ashamed", "embarrassed", "humiliated", "stupid", "lazy", "broken", "defective", "wrong", "failure", "failing"],
}

WEAK_WORDS = ["just", "really", "very", "suddenly", "somewhat", "quite", "rather", "actually", "basically", "literally", "simply", "totally", "ultimately", "virtually", "practically", "seemingly", "apparently", "perhaps", "maybe", "kind of", "sort of", "a bit", "slightly", "almost", "nearly", "began to", "started to", "proceeded to", "in order to", "due to the fact that", "at this point in time", "the fact that", "it is important to note that"]
FILTER_WORDS = ["saw", "heard", "felt", "noticed", "realized", "knew", "thought", "wondered", "looked", "watched", "seemed", "appeared", "decided", "remembered", "recognized", "touched", "smelled", "tasted", "observed", "perceived", "understood", "grasped", "sensed"]
