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
ERAS = [("childhood", "Early years, pre-adolescence"),("adolescence", "Teen years"),("twenties", "Approximately 20-29"),("thirties", "Approximately 30-39"),("forties", "Approximately 40-49"),("fif[...]
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
AUDHD_THEMES = {"diagnosis": ["diagnosis", "diagnosed", "diagnostic", "assessment", "evaluated", "tested", "labeled", "identified"], "masking": ["masking", "mask", "pretending", "passing", "camouf[...]
WEAK_WORDS = ["just", "really", "very", "suddenly", "somewhat", "quite", "rather", "actually", "basically", "literally", "simply", "totally", "ultimately", "virtually", "practically", "seemingly",[...]
FILTER_WORDS = ["saw", "heard", "felt", "noticed", "realized", "knew", "thought", "wondered", "looked", "watched", "seemed", "appeared", "decided", "remembered", "recognized", "touched", "smelled"[...]
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
