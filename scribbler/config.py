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
    ("fifties", "Approximately 50-59"),
    ("sixties", "Approximately 60-69"),
    ("seventies", "Approximately 70+"),
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
    "masking": ["masking", "mask", "pretending", "passing", "camouflage", "camouflaging", "blending in", "fake", "perform", "performing", "script", "scripting"],
    "sensory_processing": ["sensory", "overload", "overwhelm", "overstimulated", "understimulated", "fluorescent", "loud", "bright", "texture", "tag", "seam", "scratchy", "hum", "buzz", "overwhelmed"],
    "special_interests": ["obsession", "obsessed", "fascinated", "hyperfixation", "hyperfixated", "deep dive", "rabbit hole", "infodump", "passionate about", "special interest"],
    "executive_function": ["executive function", "task initiation", "working memory", "planning", "prioritizing", "couldn't start", "paralyzed", "stuck", "frozen", "can't begin"],
    "burnout": ["burnout", "burned out", "burnt out", "exhausted", "depleted", "drained", "empty", "hollow", "checked out", "collapse"],
    "meltdowns": ["meltdown", "meltdowns", "shutdown", "shut down", "screaming", "crying", "lost control", "flooded", "incapacitated"],
    "stimming": ["stimming", "stim", "rocking", "flapping", "humming", "tapping", "fidget", "fidgeting", "repetitive", "pacing", "spinning"],
    "late_discovery": ["late diagnosis", "adult diagnosis", "didn't know", "all along", "realization", "discovered", "found out"],
    "identity_integration": ["unmasking", "becoming", "who i am", "authentic", "real self", "identity", "neurodivergent", "autistic", "adhd", "audhd"],
    "monotropism": ["absorbed", "tunnel", "focus", "one thing", "couldn't shift", "tunnel vision", "monotropism"],
    "demand_avoidance": ["demand", "pda", "avoid", "refusal", "couldn't make myself", "won't", "pathological demand"],
    "hyperfocus": ["hours passed", "didn't notice", "time disappeared", "absorbed", "lost track of time", "flow state"],
    "alexithymia": ["couldn't name", "didn't know what i felt", "feeling", "identify emotion", "can't describe", "numb"],
    "interoception": ["body", "signal", "hunger", "tired", "pain", "didn't notice", "heartbeat", "breath", "chest", "stomach", "gut", "throat"],
    "rejection_sensitivity": ["rsd", "criticism", "rejected", "slight", "perceived", "hypersensitive", "rejection sensitive"],
    "accommodation": ["accommodation", "support", "needs", "iep", "504", "therapy", "occupational", "sensory diet"],
    "self_advocacy": ["advocate", "speak up", "needs", "boundaries", "asked for", "self-advocacy"],
    "routine": ["routine", "ritual", "same", "change", "transition", "disruption", "unexpected", "surprise", "sameness"],
    "social": ["social", "socializing", "party", "gatherings", "small talk", "eye contact", "cue", "cues", "social cues", "norms", "unwritten rules"],
}
WEAK_WORDS = [
    "just", "really", "very", "suddenly", "somewhat", "quite", "rather", "actually", "basically",
    "literally", "simply", "totally", "ultimately", "virtually", "practically", "seemingly",
]
FILTER_WORDS = [
    "saw", "heard", "felt", "noticed", "realized", "knew", "thought", "wondered", "looked", "watched",
    "seemed", "appeared", "decided", "remembered", "recognized", "touched", "smelled",
]
ANACHRONISM_WATCHLIST = {
    "technology": ["smartphone", "iphone", "android", "facebook", "instagram", "whatsapp", "twitter", "tiktok", "google"],
    "media": ["streaming", "netflix", "spotify", "podcast"],
    "modern_terms": ["email", "emailing", "internet", "wifi", "wi-fi", "app", "online"]
}
# Required by the low-shame feedback layer. Kept here as data only so analyzers remain import-safe.
WORD_SWAPS = {
    "bad": "notable",
    "wrong": "different",
    "failure": "attempt",
    "failed": "did not work yet",
    "lazy": "low-energy",
    "stupid": "unclear",
    "terrible": "challenging",
    "awful": "rough",
}
# Comparable titles seed list for market analysis
COMP_SEED_LIST = [
    {
        "title": "Educated",
        "author": "Tara Westover",
        "year": 2018,
        "form": "memoir",
        "themes": ["identity", "education", "family", "neurodiversity"],
    },
    {
        "title": "The Reason I Jump",
        "author": "Naoki Higashida",
        "year": 2012,
        "form": "memoir",
        "themes": ["autism", "identity", "communication"],
    },
    {
        "title": "Thinking in Pictures",
        "author": "Temple Grandin",
        "year": 1995,
        "form": "hybrid_memoir_research",
        "themes": ["autism", "identity", "research", "science"],
    },
    {
        "title": "Brainstorm",
        "author": "Daniel J. Siegel",
        "year": 2013,
        "form": "research-braid",
        "themes": ["development", "brain", "science", "identity"],
    },
    {
        "title": "The Body Keeps the Score",
        "author": "Bessel van der Kolk",
        "year": 2014,
        "form": "hybrid_memoir_research",
        "themes": ["trauma", "neuroscience", "healing", "research"],
    },
    {
        "title": "I Am My Mother's Daughter",
        "author": "Cristina Alger",
        "year": 2019,
        "form": "memoir",
        "themes": ["family", "identity", "resilience"],
    },
    {
        "title": "Eat Pray Love",
        "author": "Elizabeth Gilbert",
        "year": 2006,
        "form": "essay_collection",
        "themes": ["identity", "self-discovery", "narrative"],
    },
    {
        "title": "Dept. of Speculation",
        "author": "Jenny Offill",
        "year": 2014,
        "form": "essay_collection",
        "themes": ["identity", "motherhood", "fragments", "literary"],
    },
    {
        "title": "The Upside of Stress",
        "author": "Kelly McGonigal",
        "year": 2015,
        "form": "research-braid",
        "themes": ["neuroscience", "psychology", "research", "self-help"],
    },
    {
        "title": "Neurotribes",
        "author": "Steve Silberman",
        "year": 2015,
        "form": "research-braid",
        "themes": ["autism", "neurodiversity", "history", "research"],
    },
]
