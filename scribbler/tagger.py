#!/usr/bin/env python3
"""Auto-labeller for The Audhd Scribbler.

Reads raw text dumps and proposes YAML frontmatter tags.
Combines rule-based NLP, lexicon matching, and LLM assistance.
Never alters the body text — only the metadata.
"""
import re
import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json

from .config import (
    PROJECT_ROOT, FOLDERS, ERAS, STATUSES, VOICES, SENSORY_CATEGORIES,
    AUDHD_THEMES, WEAK_WORDS, FILTER_WORDS, ANACHRONISM_WATCHLIST,
    ERA_SPAN_START, ERA_SPAN_END
)
from . import llm
from . import db


def count_words(text: str) -> int:
    """Count words in text."""
    return len(re.findall(r'\b\w+\b', text))


def split_sentences(text: str) -> List[str]:
    """Split text into sentences. Handles common abbreviations."""
    # Protect common abbreviations
    protected = text
    for abbr in ["Mr.", "Mrs.", "Dr.", "Ms.", "Prof.", "Sr.", "Jr.", "vs.", "etc.", "i.e.", "e.g.", "U.S.", "U.K."]:
        protected = protected.replace(abbr, abbr.replace(".", "<DOT>"))
    # Split on sentence-ending punctuation
    sentences = re.split(r'(?<=[.!?])\s+', protected)
    # Restore abbreviations
    return [s.replace("<DOT>", ".").strip() for s in sentences if s.strip()]


def detect_characters(text: str, nlp=None) -> List[str]:
    """Detect character names. Uses spaCy NER if available, falls back to regex."""
    characters = set()

    # Try spaCy
    if nlp is None:
        nlp = _get_spacy()
    if nlp:
        doc = nlp(text[:50000])  # Limit for performance
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text.strip()
                # Filter out single common words that get misclassified
                if len(name) > 1 and name[0].isupper() and name.lower() not in ['the', 'and', 'but', 'she', 'he', 'they']:
                    characters.add(name)
    else:
        # Fallback: regex for capitalized words (not sentence starters)
        # Find all capitalized words/phrases that appear more than once
        words = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        from collections import Counter
        word_counts = Counter(words)
        for word, count in word_counts.items():
            if count >= 2 and word.lower() not in ['the', 'and', 'but', 'she', 'he', 'they', 'i', 'we', 'it', 'there', 'this', 'that', 'what', 'when', 'where', 'why', 'how', 'who']:
                characters.add(word)

    # Also detect family role references (Mom, Dad, Grandma, etc.)
    family_patterns = [
        r'\b(Mom|Mum|Mother|Dad|Father|Grandma|Grandpa|Grandmother|Grandfather|Nana|Papa|Sister|Brother|Aunt|Uncle|Cousin)\b',
    ]
    for pattern in family_patterns:
        matches = re.findall(pattern, text)
        for m in set(matches):
            characters.add(m)

    # Deduplicate (merge "Mom" and "Mother" if both appear? No — let the writer decide)
    return sorted(characters)[:20]  # Cap at 20


def detect_places(text: str, nlp=None) -> List[str]:
    """Detect place names. Uses spaCy NER if available."""
    places = set()

    if nlp is None:
        nlp = _get_spacy()
    if nlp:
        doc = nlp(text[:50000])
        for ent in doc.ents:
            if ent.label_ in ("GPE", "LOC", "FAC", "ORG"):
                name = ent.text.strip()
                if len(name) > 1:
                    places.add(name)
    else:
        # Fallback: look for "in/at/to the [Place]" patterns
        patterns = [
            r'(?:in|at|to|from|near|around)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                if m.lower() not in ['the', 'a', 'an', 'morning', 'afternoon', 'evening', 'night', 'kitchen', 'bedroom', 'bathroom', 'living', 'dining']:
                    places.add(m)

    # Common domestic places
    domestic = re.findall(r'\b(kitchen|bedroom|bathroom|living room|garden|yard|garage|basement|attic|hallway|porch|driveway)\b', text, re.IGNORECASE)
    for d in domestic:
        places.add(d.lower())

    return sorted(places)[:15]


def detect_era(text: str) -> Optional[str]:
    """Detect era from temporal expressions in text."""
    # Look for 4-digit years
    years = re.findall(r'\b(19[8-9]\d|20[0-2]\d)\b', text)
    if years:
        year_ints = [int(y) for y in years]
        avg_year = sum(year_ints) / len(year_ints)
        # Map to era
        if avg_year < 1990:
            return "childhood"
        elif avg_year < 2000:
            return "childhood"
        elif avg_year < 2010:
            return "twenties"
        elif avg_year < 2020:
            return "thirties"
        else:
            return "now"

    # Look for era keywords
    era_keywords = {
        "childhood": ["child", "kid", "elementary", "primary school", "grade school", "little"],
        "adolescence": ["teen", "teenager", "high school", "secondary", "puberty", "adolescent"],
        "twenties": ["college", "university", "twenties", "first job", "early twenties"],
        "now": ["today", "now", "currently", "present", "this year", "recently"],
    }
    text_lower = text.lower()
    scores = {}
    for era, keywords in era_keywords.items():
        scores[era] = sum(text_lower.count(kw) for kw in keywords)

    if any(scores.values()):
        return max(scores, key=scores.get)
    return None


def detect_themes(text: str) -> List[str]:
    """Detect themes using AUDHD lexicon + keyword matching."""
    text_lower = text.lower()
    theme_scores = {}
    for theme, keywords in AUDHD_THEMES.items():
        score = sum(text_lower.count(kw.lower()) for kw in keywords)
        if score > 0:
            theme_scores[theme] = score

    # Return top themes (score > 0)
    return sorted(theme_scores.keys(), key=lambda t: theme_scores[t], reverse=True)[:5]


def detect_voice(text: str) -> str:
    """Detect the dominant voice mode: narrator, character, research, lyric."""
    sentences = split_sentences(text)
    if not sentences:
        return "narrator"

    # First-person pronoun density → narrator
    first_person = len(re.findall(r'\b(I|me|my|mine|myself|we|us|our)\b', text, re.IGNORECASE))

    # Citation cues → research
    citation_cues = len(re.findall(r'\b(according to|studies show|research|found that|data suggests|evidence|cited|reported|survey|statistics)\b', text, re.IGNORECASE))

    # Sensory density → lyric
    sensory_count = 0
    for sense_words in SENSORY_CATEGORIES.values():
        for w in sense_words:
            sensory_count += len(re.findall(r'\b' + re.escape(w) + r'\b', text, re.IGNORECASE))

    # Hedge density → research
    hedges = len(re.findall(r'\b(may|might|could|suggests|appears to|seems to|perhaps|possibly|likely)\b', text, re.IGNORECASE))

    word_count = count_words(text)
    if word_count == 0:
        return "narrator"

    first_person_ratio = first_person / word_count * 100
    citation_ratio = (citation_cues + hedges) / word_count * 100
    sensory_ratio = sensory_count / word_count * 100

    if citation_ratio > 1.5:
        return "research"
    elif sensory_ratio > 2.0 and first_person_ratio < 3.0:
        return "lyric"
    elif first_person_ratio > 2.0:
        return "narrator"
    else:
        return "narrator"


def detect_sensory(text: str) -> List[str]:
    """Detect sensory details, tagged by sense."""
    text_lower = text.lower()
    found = []

    for sense, words in SENSORY_CATEGORIES.items():
        for w in words:
            if re.search(r'\b' + re.escape(w) + r'\b', text_lower):
                found.append(f"{sense}: {w}")
                break  # One per sense is enough for the tag

    return found[:8]


def detect_emotional_register(text: str) -> Optional[str]:
    """Detect primary emotional register using keyword lexicons."""
    registers = {
        "tender": ["soft", "gentle", "warm", "tender", "love", "beloved", "darling", "sweet", "kind"],
        "enraged": ["angry", "furious", "rage", "enraged", "livid", "fury", "wrath", "screamed", "shouted"],
        "numb": ["numb", "empty", "hollow", "nothing", "blank", "disconnected", "dissociated", "checked out", "frozen"],
        "funny": ["laughed", "funny", "hilarious", "joke", "ridiculous", "absurd", "comic", "grinned"],
        "grief": ["grief", "mourning", "loss", "lost", "died", "death", "funeral", "tears", "wept", "cried"],
        "anxious": ["anxious", "anxiety", "worried", "worry", "panic", "dread", "fear", "afraid", "terrified"],
        "tender_remembrance": ["remember", "memory", "recall", "reminded", "nostalgia", "nostalgic", "used to", "those days"],
        "defensive": ["because", "had to", "needed to", "no choice", "forced", "had no option", "justify", "explained"],
    }

    text_lower = text.lower()
    scores = {}
    for register, keywords in registers.items():
        scores[register] = sum(text_lower.count(kw) for kw in keywords)

    if any(scores.values()):
        return max(scores, key=scores.get)
    return None


def detect_anachronisms(text: str, scene_year: int = None) -> List[Dict]:
    """Detect potential anachronisms based on era span (80s-2025)."""
    flags = []
    text_lower = text.lower()

    for item, first_year in ANACHRONISM_WATCHLIST.items():
        # Check if this item appears in text
        if re.search(r'\b' + re.escape(item) + r'\b', text_lower):
            # If we know the scene's year, check if the item existed then
            if scene_year and scene_year < first_year:
                flags.append({
                    "item": item,
                    "first_attested": first_year,
                    "scene_year": scene_year,
                    "message": f"'{item}' first attested around {first_year}, but scene appears set in {scene_year}. Worth a check."
                })
            elif not scene_year:
                # No year context — just note it exists for the writer to verify
                flags.append({
                    "item": item,
                    "first_attested": first_year,
                    "message": f"'{item}' first attested around {first_year}. If the scene is set earlier, this may be an anachronism."
                })
    return flags


_spacy_nlp = None

def _get_spacy():
    """Lazy-load spaCy. Returns None if not available."""
    global _spacy_nlp
    if _spacy_nlp is False:  # Already tried and failed
        return None
    if _spacy_nlp is not None:
        return _spacy_nlp
    try:
        import spacy
        _spacy_nlp = spacy.load("en_core_web_sm")
        return _spacy_nlp
    except Exception:
        try:
            import spacy
            spacy.cli.download("en_core_web_sm")
            _spacy_nlp = spacy.load("en_core_web_sm")
            return _spacy_nlp
        except Exception:
            _spacy_nlp = False
            return None


def llm_assisted_tagging(text: str) -> Optional[Dict]:
    """Use LLM to extract deeper tags: beats, themes, emotional register, summary."""
    if not llm.llm_available():
        return None

    # Truncate very long texts
    sample = text[:8000] if len(text) > 8000 else text

    system = """You are a literary analysis assistant helping an AUDHD writer organize their memoir brain dumps.
Your job is to read the text and extract structured metadata. You are gentle, observant, and never judgmental.
You never say the writing is bad. You describe what you notice and offer the writer metadata to use or ignore."""

    prompt = f"""Read this text and extract the following metadata as JSON.

Text:
---
{sample}
---

Respond with this JSON structure:
{{
  "beats": ["one-line description of each scene beat or unit of change"],
  "themes": ["3-5 main themes you notice, single words or short phrases"],
  "emotional_register": "the dominant emotional tone (one of: tender, enraged, numb, funny, grief, anxious, tender_remembrance, defensive, or your own word)",
  "summary": "3-line plain-English summary of what this text is about, what it contains, and what the writer might do with it",
  "strength_signal": "one sentence describing what feels strong or alive in this text"
}}

Respond with valid JSON only."""

    return llm.llm_json(prompt, system)


def tag_file(file_path: str, use_llm: bool = True) -> Dict:
    """Tag a single file. Returns the metadata dict.

    Args:
        file_path: Path to the text file
        use_llm: Whether to use LLM for deeper analysis (beats, themes, summary)

    Returns:
        Metadata dict with all detected tags
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text = path.read_text(encoding="utf-8")
    word_count = count_words(text)

    # Strip existing YAML frontmatter before analysis
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            body_text = text[end + 3:].strip()
        else:
            body_text = text
    else:
        body_text = text

    # Rule-based detection
    nlp = _get_spacy()
    characters = detect_characters(body_text, nlp)
    places = detect_places(body_text, nlp)
    era = detect_era(body_text)
    themes = detect_themes(body_text)
    voice = detect_voice(body_text)
    sensory = detect_sensory(body_text)
    emotional_register = detect_emotional_register(body_text)
    anachronisms = detect_anachronisms(body_text)

    # LLM-assisted detection (if available)
    beats = []
    summary = ""
    strength_signal = None
    if use_llm and llm.llm_available():
        llm_result = llm_assisted_tagging(body_text)
        if llm_result:
            beats = llm_result.get("beats", [])
            if not themes:  # Only override if rule-based found nothing
                themes = llm_result.get("themes", [])[:5]
            if not emotional_register:
                emotional_register = llm_result.get("emotional_register")
            summary = llm_result.get("summary", "")
            strength_signal = llm_result.get("strength_signal")

    # Determine folder from path
    rel_path = path.resolve().relative_to(PROJECT_ROOT.resolve())
    folder = str(rel_path.parent) if str(rel_path.parent) != "." else "root"
    # Normalize folder name
    for f in FOLDERS:
        if folder == f or folder.startswith(f + "/"):
            folder = f
            break
    else:
        folder = "raw-dumps"  # Default

    # Determine status based on folder
    status_map = {
        "raw-dumps": "seedling",
        "triage": "growing",
        "chapters": "growing",
        "drafts": "shaping",
        "final": "polishing",
        "archive": "resting",
    }
    status = status_map.get(folder, "seedling")

    # Detect chapter number from filename
    chapter_no = None
    ch_match = re.match(r'ch-?(\d+)', path.stem, re.IGNORECASE)
    if ch_match:
        chapter_no = int(ch_match.group(1))

    meta = {
        "path": str(path.resolve()),
        "filename": path.name,
        "folder": folder,
        "word_count": word_count,
        "status": status,
        "chapter_no": chapter_no,
        "characters": characters,
        "places": places,
        "era": era,
        "beats": beats,
        "themes": themes,
        "voice": voice,
        "sensory": sensory,
        "continuity": [],  # Populated by link stage
        "emotional_register": emotional_register,
        "motifs": [],
        "strength_signal": 1 if strength_signal else 0,
        "summary": summary,
        "dump_date": date.today().isoformat(),
    }

    # Save to database
    db.upsert_file(meta)

    # Write YAML frontmatter to the file
    write_frontmatter(path, meta, body_text)

    return meta


def write_frontmatter(path: Path, meta: Dict, body_text: str):
    """Write YAML frontmatter to a file, preserving the body text."""
    # Build YAML
    lines = ["---"]
    lines.append(f"status: {meta.get('status', 'seedling')}")

    if meta.get("chapter_no") is not None:
        lines.append(f"chapter_no: {meta['chapter_no']}")
    else:
        lines.append("chapter_no: null")

    # Lists
    for key in ["characters", "places", "beats", "themes", "sensory", "continuity", "motifs"]:
        val = meta.get(key, [])
        if val:
            yaml_list = ", ".join(f'"{v}"' for v in val)
            lines.append(f"{key}: [{yaml_list}]")
        else:
            lines.append(f"{key}: []")

    if meta.get("era"):
        lines.append(f"era: {meta['era']}")
    if meta.get("voice"):
        lines.append(f"voice: {meta['voice']}")
    if meta.get("emotional_register"):
        lines.append(f"emotional_register: {meta['emotional_register']}")

    lines.append(f"dump_date: {meta.get('dump_date', date.today().isoformat())}")

    if meta.get("strength_signal"):
        lines.append("strength_signal: true")

    lines.append("---")

    # Build the new file content
    yaml_block = "\n".join(lines)
    new_content = f"{yaml_block}\n\n{body_text}"

    # Append summary as a comment block at the end
    if meta.get("summary"):
        new_content += f"\n\n<!-- SCRIBBLER SUMMARY\n{meta['summary']}\n-->\n"

    path.write_text(new_content, encoding="utf-8")


def tag_all_in_folder(folder_name: str = "raw-dumps", use_llm: bool = True) -> List[Dict]:
    """Tag all files in a folder."""
    folder_path = PROJECT_ROOT / folder_name
    if not folder_path.exists():
        return []

    results = []
    for ext in ["*.txt", "*.md", "*.text"]:
        for path in folder_path.glob(ext):
            try:
                meta = tag_file(str(path), use_llm=use_llm)
                results.append(meta)
            except Exception as e:
                results.append({"path": str(path), "error": str(e)})
    return results


def find_links(file_path: str) -> List[Dict]:
    """Find other files that reference the same characters, places, or themes."""
    from . import db
    target = db.get_file(file_path)
    if not target:
        return []

    all_files = db.get_all_files()
    links = []

    for other in all_files:
        if other["path"] == file_path:
            continue

        shared_characters = set(target.get("characters", [])) & set(other.get("characters", []))
        shared_places = set(target.get("places", [])) & set(other.get("places", []))
        shared_themes = set(target.get("themes", [])) & set(other.get("themes", []))

        if shared_characters or shared_places or shared_themes:
            links.append({
                "file": other["filename"],
                "path": other["path"],
                "shared_characters": list(shared_characters),
                "shared_places": list(shared_places),
                "shared_themes": list(shared_themes),
            })

    return links
