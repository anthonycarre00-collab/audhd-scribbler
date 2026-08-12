"""Analysis catalogue: separate writer stages and avoid indiscriminate Run All."""

ANALYSIS_CATALOG = {
    "craft": {"title": "Craft & Rhythm", "stage": "draft", "group": "Prose", "safe_with": ["voice", "editor", "repetition"], "purpose": "Sentence rhythm, craft signals and places worth a closer human look."},
    "voice": {"title": "Voice & Tense", "stage": "draft", "group": "Prose", "safe_with": ["craft", "characters", "editor"], "purpose": "Narrator voice, tense consistency and shifts in narrative stance."},
    "characters": {"title": "Characters & Relationships", "stage": "draft", "group": "Story", "safe_with": ["voice", "continuity", "themes"], "purpose": "Presence, relationships, character movement and voice distinctions."},
    "continuity": {"title": "Continuity & Timeline", "stage": "draft", "group": "Story", "safe_with": ["characters", "themes"], "purpose": "Chronology, recurring facts, ages, places and unresolved inconsistencies."},
    "themes": {"title": "Themes & Emotional Arc", "stage": "draft", "group": "Story", "safe_with": ["characters", "continuity"], "purpose": "Recurring themes, motifs and emotional movement through the selected material."},
    "editor": {"title": "Editorial / Memoir Patterns", "stage": "near-final", "group": "Editorial", "safe_with": ["craft", "voice", "repetition"], "purpose": "Higher-level editorial signals such as clarity, redundancy and memoir-specific balance."},
    "repetition": {"title": "Repetition & Echoes", "stage": "draft", "group": "Prose", "safe_with": ["craft", "editor"], "purpose": "Repeated words, phrases and nearby echoes across the selected draft."},
    "pacing": {"title": "Pacing & Momentum", "stage": "draft", "group": "Structure", "safe_with": ["themes", "continuity"], "purpose": "Where the manuscript accelerates, stalls or changes gear."},
    "structure": {"title": "Structure & Chapter Purpose", "stage": "near-final", "group": "Structure", "safe_with": ["pacing", "themes", "continuity"], "purpose": "Chapter roles, openings, endings, sequence and cause/effect."},
    "memoir": {"title": "Memoir Lens", "stage": "near-final", "group": "Memoir", "safe_with": ["themes", "structure", "voice"], "purpose": "Reflection vs event, narrator distance, memory/claim uncertainty and thematic coherence."},
    "reader": {"title": "Reader Experience", "stage": "near-final", "group": "Editorial", "safe_with": ["pacing", "structure", "themes"], "purpose": "Opening promise, likely confusion points, engagement dips and emotional peaks."},
    "research": {"title": "Research & Fact Flags", "stage": "near-final", "group": "Accuracy", "safe_with": ["continuity", "memoir"], "purpose": "Surfaces claims and dates worth verifying; it does not declare facts true or false."},
    "market": {"title": "Comps & Market Position", "stage": "final", "group": "Publishing", "safe_with": ["themes", "structure", "memoir"], "purpose": "Comparable titles and positioning once the book's identity is reasonably settled."},
}


def recommended(stage="draft"):
    order = {"draft": 0, "near-final": 1, "final": 2}
    return [k for k, v in ANALYSIS_CATALOG.items() if order.get(v["stage"], 0) <= order.get(stage, 0)]


def run_all_warning(selected):
    selected = list(dict.fromkeys(selected))
    if len(selected) < 2:
        return None
    risky = []
    for key in selected:
        meta = ANALYSIS_CATALOG.get(key, {})
        conflicts = [other for other in selected if other != key and other not in meta.get("safe_with", [])]
        if conflicts:
            risky.append((key, conflicts))
    if not risky:
        return None
    return "Run All is deliberately cautious: some analyses overlap or require a different manuscript stage. Scribbler will run compatible diagnostics first and leave stage-specific/interpretive tools for explicit confirmation."
