#!/usr/bin/env python3
"""Configuration for The Audhd Scribbler."""
import os
import sys
from pathlib import Path
from datetime import date

# In a normal developer/repository run, content lives beside the project.
# In the packaged Windows application, content must live somewhere writable
# and persistent rather than inside PyInstaller's temporary extraction folder.
_CODE_ROOT = Path(__file__).resolve().parent.parent
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(os.environ.get("AUDHD_SCRIBBLER_HOME", Path.home() / "Documents" / "Audhd Scribbler"))
else:
    PROJECT_ROOT = _CODE_ROOT

# Writing folders
FOLDERS = {
    "raw-dumps": "Brain dumps, voice-to-text transcripts, freewrites. No structure required.",
    "triage": "Dumps with suggested tags applied; awaiting writer confirmation.",
    "chapters": "Chapter drafts in progress. Named ch-XX-short-slug.md.",
    "characters": "One file per character. Aliases, relationships, timeline notes.",
    "places": "One file per recurring place. Description consistency, sensory associations.",
    "themes": "One file per theme. Motifs, recurrences, scenes that carry it.",
    "research": "Source claims, citations, bibliography for the research braid.",
    "comps": "Comparable-title research. Curated neurodiversity-memoir seed list.",
    "drafts": "Chapters past first-draft but not yet final.",
    "final": "Polished chapters ready for the manuscript. The analysis suite's primary input.",
    "archive": "Older drafts, abandoned material, snapshots. Never deleted.",
}

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "scribbler.db"
REPORTS_DIR = DATA_DIR / "reports"
DASHBOARD_DIR = DATA_DIR / "dashboard"

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
CRUTCH_PHRASES = ["it was as if", "the kind of", "the sort of", "I remember", "I knew that", "there was a", "there were", "it felt like", "the way that", "the fact that", "at the same time", "in that moment", "for a moment", "all of a sudden", "out of nowhere", "without thinking", "before I knew it"]

ANACHRONISM_WATCHLIST = {
    "smartphone": 2007, "iPhone": 2007, "Android": 2008, "Facebook": 2004, "Twitter": 2006, "Instagram": 2010, "TikTok": 2016, "Snapchat": 2011, "YouTube": 2005, "Netflix streaming": 2007, "WiFi": 1997, "Wi-Fi": 1997, "wifi": 1997, "Google": 1998, "google": 1998, "text message": 1992, "texting": 1994, "SMS": 1992, "email": 1971, "e-mail": 1971, "laptop": 1983, "modem": 1981, "dial-up": 1980, "CD player": 1982, "Walkman": 1979, "Discman": 1984, "MP3 player": 1998, "iPod": 2001, "DVD": 1996, "VHS": 1976, "Betamax": 1975, "cassette": 1962, "vinyl": 1940, "pager": 1949, "beeper": 1980, "mobile phone": 1983, "cell phone": 1984, "car phone": 1980, "internet": 1983, "World Wide Web": 1991, "web browser": 1993, "Zoom": 2012, "FaceTime": 2010, "Skype": 2003, "Uber": 2011, "Airbnb": 2008, "Alexa": 2014, "Siri": 2011, "9/11": 2001, "September 11": 2001, "COVID": 2019, "pandemic": 2019, "lockdown": 2020, "awesome": 1980, "rad": 1980, "grody": 1982, "gag me": 1982, "totally": 1980, "like": 1980, "whatever": 1983, "duh": 1983, "dude": 1985, "as if": 1990, "talk to the hand": 1994, "phat": 1993, "da bomb": 1995, "tight": 1995, "lit": 2015, "yeet": 2014, "cap": 2019, "no cap": 2019, "slay": 2016, "bet": 2017, "sus": 2020, "Tamagotchi": 1996, "Furby": 1998, "Beanie Baby": 1993, "Polly Pocket": 1989, "Easy-Bake Oven": 1963,
}

COMP_SEED_LIST = [
    {"title": "Unmasking Autism", "author": "Devon Price", "year": 2022, "form": "research+memoir", "themes": ["autism", "masking", "identity"]},
    {"title": "We're Not Broken", "author": "Eric Garcia", "year": 2022, "form": "reportage+memoir", "themes": ["autism", "policy", "identity"]},
    {"title": "I Overcame My Autism and All I Got Was This Lousy Anxiety Disorder", "author": "Sarah Kurchak", "year": 2020, "form": "memoir", "themes": ["autism", "masking", "anxiety"]},
    {"title": "The Collected Schizophrenias", "author": "Esmé Weijun Wang", "year": 2019, "form": "essays", "themes": ["diagnosis", "mental illness", "stigma"]},
    {"title": "Bluets", "author": "Maggie Nelson", "year": 2009, "form": "hybrid fragments", "themes": ["obsession", "grief", "philosophy"]},
    {"title": "The Argonauts", "author": "Maggie Nelson", "year": 2015, "form": "hybrid memoir+theory", "themes": ["queerness", "motherhood", "identity"]},
    {"title": "The Empathy Exams", "author": "Leslie Jamison", "year": 2014, "form": "essays", "themes": ["empathy", "pain", "witnessing"]},
    {"title": "Trick Mirror", "author": "Jia Tolentino", "year": 2019, "form": "essays+criticism", "themes": ["culture", "self", "internet"]},
    {"title": "The Undying", "author": "Anne Boyer", "year": 2019, "form": "illness+critique", "themes": ["cancer", "care", "capitalism"]},
    {"title": "Different, Not Less", "author": "Chloé Hayden", "year": 2023, "form": "memoir", "themes": ["autism", "adhd", "identity"]},
    {"title": "Untypical", "author": "Pete Wharmby", "year": 2023, "form": "research+memoir", "themes": ["autism", "society", "accommodation"]},
    {"title": "Strong Female Character", "author": "Fern Brady", "year": 2022, "form": "memoir", "themes": ["autism", "comedy", "identity"]},
]

WORD_SWAPS = {"should": "you might", "must": "could", "need to": "could", "fix": "refine", "problem": "pattern", "issue": "thing", "incomplete": "not yet connected", "behind": "at your own pace", "error": "hmm", "wrong": "let's look at this", "overdue": "resting", "fail": "revisit", "failure": "revisit", "bad": "worth a look"}

PALETTE = {"bg": "#F7F8FA", "surface": "#EEF1F5", "card_bg": "#E8EDF3", "text_primary": "#1A2332", "text_muted": "#5C6878", "accent": "#4A6FA5", "accent_dark": "#365680", "accent_light": "#7B9BC8", "border": "#D1D9E3", "success": "#5B8C6E", "warning": "#B8956A", "status_seedling": "#A8C4E0", "status_growing": "#7B9BC8", "status_shaping": "#4A6FA5", "status_polishing": "#365680", "status_resting": "#9BA8B8"}
