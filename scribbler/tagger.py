#!/usr/bin/env python3
"""Auto-labeller for The Audhd Scribbler.

Reads raw text dumps and proposes YAML frontmatter tags.
Combines rule-based NLP, lexicon matching, and optional LLM assistance.
Never alters the body text — only the metadata.
"""
import re
import os
import sys
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
from .file_io import read_text_file, write_text_file


def count_words(text: str) -> int:
    return len(re.findall(r'\b\w+\b', text))


def split_sentences(text: str) -> List[str]:
    protected = text
    for abbr in ["Mr.", "Mrs.", "Dr.", "Ms.", "Prof.", "Sr.", "Jr.", "vs.", "etc.", "i.e.", "e.g.", "U.S.", "U.K."]:
        protected = protected.replace(abbr, abbr.replace(".", "<DOT>"))
    sentences = re.split(r'(?<=[.!?])\s+', protected)
    return [s.replace("<DOT>", ".").strip() for s in sentences if s.strip()]


def _spacy_ner_chunked(text: str, nlp, entity_types: set, max_chars_per_chunk: int = 50000):
    entities = set()
    if not nlp or not text:
        return entities
    if len(text) <= max_chars_per_chunk:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in entity_types and len(ent.text.strip()) > 1:
                entities.add(ent.text.strip())
        return entities
    start = 0
    while start < len(text):
        end = min(start + max_chars_per_chunk, len(text))
        chunk = text[start:end]
        if end < len(text):
            last_para = chunk.rfind('\n\n')
            if last_para > max_chars_per_chunk // 2:
                end = start + last_para
                chunk = text[start:end]
        try:
            doc = nlp(chunk)
            for ent in doc.ents:
                if ent.label_ in entity_types and len(ent.text.strip()) > 1:
                    entities.add(ent.text.strip())
        except Exception:
            pass
        start = end
    return entities


def detect_characters(text: str, nlp=None) -> List[str]:
    from .config import STOPLIST_CHARACTERS
    characters = set()
    if nlp is None: nlp = _get_spacy()
    if nlp:
        characters = _spacy_ner_chunked(text, nlp, {"PERSON"})
    else:
        words = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        from collections import Counter
        word_counts = Counter(words)
        for word, count in word_counts.items():
            if count >= 2 and word.lower() not in {'the','and','but','she','he','they','i','we','it','there','this','that','what','when','where','why','how','who'}:
                characters.add(word)
    family_patterns = [r'\b(Mom|Mum|Mother|Dad|Father|Grandma|Grandpa|Grandmother|Grandfather|Nana|Papa|Sister|Brother|Aunt|Uncle|Cousin)\b']
    for pattern in family_patterns:
        characters.update(re.findall(pattern, text))
    # Phase 12: filter out stoplisted tokens that spaCy mis-tags as PERSON
    filtered = set()
    for c in characters:
        cl = c.lower()
        # Skip if the entire token is in the stoplist
        if cl in STOPLIST_CHARACTERS:
            continue
        # Skip single-word entities that are common nouns
        if " " not in c and cl in STOPLIST_CHARACTERS:
            continue
        # Skip if it looks like a sentence-start capitalization of a common word
        if cl in {"the","and","but","when","after","before","during","while","then","because","although","however"}:
            continue
        # Apply classification — only keep if it plausibly looks like a person
        if _classify_entity(c, "") == "person":
            filtered.add(c)
        else:
            # If classification is uncertain, keep it (better to over-tag than miss)
            filtered.add(c)
    return sorted(filtered)[:20]


def _classify_entity(name: str, context_sentence: str = "") -> str:
    """Classify a capitalized token as 'person', 'place', or 'other' using context.

    Uses the preceding verb/preposition to guess. Always-on rule-based
    disambiguation — Phase 12.
    """
    if not name:
        return "other"
    nl = name.lower()
    # Family roles are always persons
    if nl in {"mom", "mum", "mother", "dad", "father", "grandma", "grandpa",
              "grandmother", "grandfather", "nana", "papa", "sister", "brother",
              "aunt", "uncle", "cousin", "parents"}:
        return "person"
    # Stoplisted common nouns
    from .config import STOPLIST_CHARACTERS, THEME_AS_PLACE_STOP
    if nl in STOPLIST_CHARACTERS:
        return "other"
    if nl in THEME_AS_PLACE_STOP:
        return "other"
    # If context_sentence contains verbs that take persons as objects, classify as person
    if context_sentence:
        # "said X", "X said", "X told", "X smiled", "X looked at"
        if re.search(r'\b' + re.escape(name) + r'\b\s+(said|told|smiled|laughed|cried|nodded|looked|walked|sat|stood|gave|took|put|felt|knew|thought|remembered)\b', context_sentence, re.IGNORECASE):
            return "person"
        if re.search(r'\b(said|told|saw|heard|met|called|visited|remembered|missed|loved|hated)\s+' + re.escape(name) + r'\b', context_sentence, re.IGNORECASE):
            return "person"
        # "at X", "to X", "in X" with capitalized X — could be place
        if re.search(r'\b(at|to|in|from|into|near|around|across)\s+' + re.escape(name) + r'\b', context_sentence, re.IGNORECASE):
            # But "to Mom" is a person — only treat as place if not a family role
            if nl not in {"mom", "mum", "mother", "dad", "father", "grandma", "grandpa"}:
                return "place"
    # Default: assume person (spaCy tagged it as PERSON)
    return "person"


def detect_time_markers(text: str) -> List[str]:
    """Detect time markers like 'summer of 1994', 'the day after', 'two weeks ago'.

    Phase 13: rule-based, always-on.
    """
    from .config import TIME_MARKER_PATTERNS
    markers = set()
    for pattern in TIME_MARKER_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            markers.add(m.group(0).strip())
    return sorted(markers)[:20]


def detect_objects(text: str, nlp=None) -> List[str]:
    """Detect recurring physical objects (potential motifs).

    Phase 13: uses spaCy NOUN entities + frequency count.
    """
    if nlp is None: nlp = _get_spacy()
    if not nlp:
        # Fallback: find capitalized nouns that appear 3+ times
        words = re.findall(r'\b([a-z]{4,})\b', text)
        from collections import Counter
        counts = Counter(words)
        # Filter out common words
        stop = {"the","and","but","was","were","that","this","with","from","have","were","they","their","what","when","where","which","there","then","than","them","some","many","most","such","very","just","really","also","only","more","much","into","upon","about","after","before","because","although","however"}
        candidates = [w for w, c in counts.items() if c >= 3 and w not in stop]
        return candidates[:10]
    # Use spaCy to find nouns, then count
    try:
        doc = nlp(text[:50000])  # cap at 50k chars
        from collections import Counter
        noun_counts = Counter()
        for token in doc:
            if token.pos_ == "NOUN" and len(token.text) >= 4 and token.text.lower() not in {
                "time","year","day","week","month","moment","thing","something","everything",
                "nothing","anything","someone","everyone","anyone","somewhere","anywhere",
                "kitchen","room","house","home","school","work","life","world","hand","eye",
                "eyes","face","head","voice","mind","heart","breath","door","table","window",
            }:
                noun_counts[token.text.lower()] += 1
        # Return top nouns that appear 3+ times
        return [n for n, c in noun_counts.most_common(15) if c >= 3][:10]
    except Exception:
        return []


def detect_places(text: str, nlp=None) -> List[str]:
    places = set(); place_counts = {}
    FALSE_POSITIVES = {'australia','america','europe','asia','africa','england','france','germany','italy','spain','china','japan','india','canada','mexico','brazil','russia','london','paris','tokyo','new york','los angeles','chicago','boston','seattle'}
    NEVER_PLACES = {'one','two','three','first','second','third','monday','tuesday','wednesday','thursday','friday','saturday','sunday','january','february','march','april','may','june','july','august','september','october','november','december','spring','summer','autumn','winter','fall','morning','afternoon','evening','night','today','tomorrow','yesterday','school','work','home','church','hospital','office'}
    if nlp is None: nlp = _get_spacy()
    if nlp:
        all_entities = _spacy_ner_chunked(text, nlp, {"GPE", "LOC", "FAC", "ORG"})
        for name in all_entities:
            name_lower = name.lower()
            if name_lower in NEVER_PLACES or len(name) < 2 or name.isdigit(): continue
            if name_lower in FALSE_POSITIVES:
                setting_pattern = r'\b(?:lived|live|grew up|born|raised|stayed|visit|visited|moved|move|went to school|school|work|working|grew|born in|raised in)\s+(?:in\s+)?' + re.escape(name) + r'\b'
                in_pattern = r'\bin\s+' + re.escape(name) + r'\b'
                count = len(re.findall(r'\b' + re.escape(name) + r'\b', text, re.IGNORECASE))
                if not re.search(setting_pattern, text, re.IGNORECASE) and (not re.search(in_pattern, text, re.IGNORECASE) or count < 3) and count < 3: continue
            place_counts[name] = place_counts.get(name, 0) + 1; places.add(name)
    else:
        for pattern in [r'(?:in|at|to|from|near|around)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)']:
            for m in re.findall(pattern, text):
                if m.lower() not in NEVER_PLACES and m.lower() not in ['the','a','an']: places.add(m)
    domestic = re.findall(r'\b(kitchen|bedroom|bathroom|living room|garden|yard|garage|basement|attic|hallway|porch|driveway)\b', text, re.IGNORECASE)
    places.update(d.lower() for d in domestic)
    return sorted(places)[:15]


def detect_era(text: str) -> Optional[str]:
    years = re.findall(r'\b(19[8-9]\d|20[0-2]\d)\b', text)
    if years:
        year_ints = [int(y) for y in years]; avg_year = sum(year_ints) / len(year_ints)
        if avg_year < 2000: return "childhood"
        if avg_year < 2010: return "twenties"
        if avg_year < 2020: return "thirties"
        return "now"
    era_keywords = {"childhood":["child","kid","elementary","primary school","grade school","little"],"adolescence":["teen","teenager","high school","secondary","puberty","adolescent"],"twenties":["college","university","twenties","first job","early twenties"],"now":["today","now","currently","present","this year","recently"]}
    low=text.lower(); scores={era:sum(low.count(k) for k in ks) for era,ks in era_keywords.items()}
    return max(scores,key=scores.get) if any(scores.values()) else None


def detect_themes(text: str) -> List[str]:
    low=text.lower(); scores={theme:sum(low.count(k.lower()) for k in keywords) for theme,keywords in AUDHD_THEMES.items()}
    return sorted((t for t,s in scores.items() if s>0),key=lambda t:scores[t],reverse=True)[:5]


def detect_voice(text: str) -> str:
    sentences=split_sentences(text)
    if not sentences:return "narrator"
    first_person=len(re.findall(r'\b(I|me|my|mine|myself|we|us|our)\b',text,re.I))
    citation_cues=len(re.findall(r'\b(according to|studies show|research|found that|data suggests|evidence|cited|reported|survey|statistics)\b',text,re.I))
    sensory_count=sum(len(re.findall(r'\b'+re.escape(w)+r'\b',text,re.I)) for ws in SENSORY_CATEGORIES.values() for w in ws)
    hedges=len(re.findall(r'\b(may|might|could|suggests|appears to|seems to|perhaps|possibly|likely)\b',text,re.I)); wc=count_words(text)
    if not wc:return "narrator"
    if (citation_cues+hedges)/wc*100>1.5:return "research"
    if sensory_count/wc*100>2 and first_person/wc*100<3:return "lyric"
    return "narrator"


def detect_sensory(text: str) -> List[str]:
    low=text.lower(); found=[]
    for sense,ws in SENSORY_CATEGORIES.items():
        for w in ws:
            if re.search(r'\b'+re.escape(w)+r'\b',low): found.append(f"{sense}: {w}"); break
    return found[:8]


def detect_emotional_register(text: str) -> Optional[str]:
    registers={"tender":["soft","gentle","warm","tender","love","beloved","darling","sweet","kind"],"enraged":["angry","furious","rage","enraged","livid","fury","wrath","screamed","shouted"],"numb":["numb","empty","hollow","nothing","blank","disconnected","dissociated","checked out","frozen"],"funny":["laughed","funny","hilarious","joke","ridiculous","absurd","comic","grinned"],"grief":["grief","mourning","loss","lost","died","death","funeral","tears","wept","cried"],"anxious":["anxious","anxiety","worried","worry","panic","dread","fear","afraid","terrified"],"tender_remembrance":["remember","memory","recall","reminded","nostalgia","nostalgic","used to","those days"],"defensive":["because","had to","needed to","no choice","forced","had no option","justify","explained"]}
    low=text.lower(); scores={r:sum(low.count(k) for k in ks) for r,ks in registers.items()}; return max(scores,key=scores.get) if any(scores.values()) else None


def detect_anachronisms(text: str, scene_year: int = None) -> List[Dict]:
    """Detect potential anachronisms based on the era span (80s-2025).

    The ANACHRONISM_WATCHLIST is structured as {category: [item1, item2, ...]}.
    We flatten it and search for each item in the text. Since the config doesn't
    have per-item first_attested years, we use the ERA_SPAN_START as the baseline
    and flag any modern term that appears in a scene set before that term existed.
    """
    flags = []
    low = text.lower()

    # Flatten the watchlist: {category: [items]} -> [(item, category), ...]
    items_to_check = []
    for category, items in ANACHRONISM_WATCHLIST.items():
        if isinstance(items, list):
            for item in items:
                items_to_check.append((item, category))
        elif isinstance(items, int):
            # Backward compat: old format was {item: year}
            items_to_check.append((category, None))

    for item, category in items_to_check:
        if re.search(r'\b' + re.escape(item.lower()) + r'\b', low):
            # Estimate first_attested based on category (rough heuristic)
            if category == "technology":
                first_attested = 2007  # smartphone era
            elif category == "media":
                first_attested = 2008  # streaming era
            elif category == "modern_terms":
                first_attested = 1995  # internet era
            else:
                first_attested = 2000  # default

            if scene_year and scene_year < first_attested:
                flags.append({
                    "item": item,
                    "category": category,
                    "first_attested": first_attested,
                    "scene_year": scene_year,
                    "message": f"'{item}' (category: {category}) first appeared around {first_attested}, but scene appears set in {scene_year}. Worth a check."
                })
            elif not scene_year:
                flags.append({
                    "item": item,
                    "category": category,
                    "first_attested": first_attested,
                    "message": f"'{item}' (category: {category}) first appeared around {first_attested}. If the scene is set earlier, this may be an anachronism."
                })
    return flags

_spacy_nlp=None
def _get_spacy():
    """Lazy-load spaCy. Handles both dev and frozen (PyInstaller) modes."""
    global _spacy_nlp
    if _spacy_nlp is False:return None
    if _spacy_nlp is not None:return _spacy_nlp
    try:
        import spacy
        try:
            _spacy_nlp=spacy.load("en_core_web_sm")
        except Exception:
            # In frozen exe, try loading from the bundled path
            if getattr(sys, "frozen", False):
                import en_core_web_sm
                _spacy_nlp = en_core_web_sm.load()
            else:
                _spacy_nlp=False
    except Exception:
        _spacy_nlp=False
    return _spacy_nlp


def llm_assisted_tagging(text: str) -> Optional[Dict]:
    if not llm.llm_available():return None
    if len(text)<=12000:return _llm_tag_single_chunk(text)
    chunk_size=10000; overlap=1000; chunks=[]; start=0
    while start<len(text):
        end=min(start+chunk_size,len(text)); chunk=text[start:end]
        if end<len(text):
            last_para=chunk.rfind('\n\n')
            if last_para>chunk_size//2:end=start+last_para;chunk=text[start:end]
        chunks.append(chunk); start=end-overlap if end<len(text) else end
        if start>=len(text):break
    all_beats=[];all_themes=[];chunk_summaries=[];chunk_emotions=[];strength_signals=[]
    failed_chunks=[]
    for i,chunk in enumerate(chunks):
        # Progress output to stderr so it shows in the console
        print(f"  [AI] Processing chunk {i+1} of {len(chunks)}...", file=sys.stderr, flush=True)
        try:
            result=_llm_tag_single_chunk(chunk,chunk_num=i+1,total_chunks=len(chunks))
        except Exception as e:
            print(f"  [Warning] Chunk {i+1} failed: {e}", file=sys.stderr)
            result=None
        if result:
            all_beats.extend(result.get("beats",[]));all_themes.extend(result.get("themes",[]));
            if result.get("summary"):chunk_summaries.append(result["summary"])
            if result.get("emotional_register"):chunk_emotions.append(result["emotional_register"])
            if result.get("strength_signal"):strength_signals.append(result["strength_signal"])
        else:
            failed_chunks.append(i+1)
    if failed_chunks:
        print(f"  [Warning] {len(failed_chunks)} chunk(s) failed: {failed_chunks}. Those sections may be under-tagged.", file=sys.stderr)
    from collections import Counter
    merged_themes=[t for t,_ in Counter(all_themes).most_common(8)]
    seen=set();unique_beats=[]
    for beat in all_beats:
        key=re.sub(r'\W+',' ',beat.lower()).strip()
        if key and key not in seen:seen.add(key);unique_beats.append(beat)
    unique_beats=unique_beats[:30]
    merged_summary=_llm_merge_summaries(chunk_summaries) if len(chunk_summaries)>1 else (chunk_summaries[0] if chunk_summaries else "")
    emotion_counts=Counter(chunk_emotions);dominant_emotion=emotion_counts.most_common(1)[0][0] if emotion_counts else None
    return {"beats":unique_beats,"themes":merged_themes,"emotional_register":dominant_emotion,"summary":merged_summary,"strength_signal":strength_signals[0] if strength_signals else None}


def _llm_tag_single_chunk(text: str, chunk_num: int=1, total_chunks: int=1) -> Optional[Dict]:
    system="""You are a literary analysis assistant helping a writer organize raw brain dumps. Extract useful metadata, not judgments. Preserve uncertainty. Do not invent facts or themes unsupported by the text."""
    chunk_note=f" (chunk {chunk_num} of {total_chunks})" if total_chunks>1 else ""
    prompt=f'''Read this text and extract JSON metadata{chunk_note}. Text:\n---\n{text}\n---\nReturn JSON with these fields:
{{
  "beats": ["scene beats or units of change"],
  "themes": ["3-5 supported themes"],
  "emotional_register": "dominant tone",
  "summary": "2-3 line plain-English summary",
  "strength_signal": "one supported strength signal",
  "persons": [{{"name": "Mom", "role": "family|friend|professional|self|other"}}],
  "places": [{{"name": "kitchen", "type": "domestic|geographic|institutional|imagined"}}],
  "objects": ["recurring physical items, e.g. blue coat, tea pot"],
  "relationships": [{{"a": "Mom", "b": "Dad", "relation": "spouse|parent-child|rival|friend"}}],
  "emotional_beats": [{{"quote": "I felt small", "intensity": 1-3}}],
  "time_markers": ["summer of 1994", "the day after"]
}}
Valid JSON only. Only include fields you can support from the text.'''
    return llm.llm_json(prompt,system)


def _llm_merge_summaries(summaries: list) -> str:
    if not summaries:return ""
    if len(summaries)==1:return summaries[0]
    system="You are a literary analysis assistant. Merge section summaries without inventing events or meanings."
    prompt="These are summaries of sections of one document. Merge into one cohesive 3-line summary:\n\n"+"\n\n".join(f"Section {i+1}: {s}" for i,s in enumerate(summaries))
    result=llm.llm_complete(prompt,system);return result.strip() if result else summaries[0]


def tag_file(file_path: str, use_llm: bool=True) -> Dict:
    path=Path(file_path)
    if not path.exists():raise FileNotFoundError(f"File not found: {file_path}")
    text=read_text_file(path);word_count=count_words(text)
    if text.startswith("---"):
        end=text.find("---",3);body_text=text[end+3:].strip() if end!=-1 else text
    else:body_text=text
    nlp=_get_spacy()
    characters=detect_characters(body_text,nlp)
    places=detect_places(body_text,nlp)
    era=detect_era(body_text)
    rule_themes=detect_themes(body_text)
    themes=list(rule_themes)
    voice=detect_voice(body_text)
    sensory=detect_sensory(body_text)
    emotional_register=detect_emotional_register(body_text)
    anachronisms=detect_anachronisms(body_text)
    # Phase 13: new tag types (rule-based, always on)
    time_markers=detect_time_markers(body_text)
    objects=detect_objects(body_text,nlp)
    relationships=[]
    emotional_beats=[]
    beats=[];summary="";strength_signal=None
    if use_llm and llm.llm_available():
        llm_result=llm_assisted_tagging(body_text)
        if llm_result:
            beats=llm_result.get("beats",[]);llm_themes=llm_result.get("themes",[])
            # Keep deterministic AUDHD tags and add semantic LLM themes rather than discarding either.
            seen={str(x).lower() for x in themes}
            for theme in llm_themes:
                if str(theme).lower() not in seen:themes.append(theme);seen.add(str(theme).lower())
            themes=themes[:10]
            if not emotional_register:emotional_register=llm_result.get("emotional_register")
            summary=llm_result.get("summary","");strength_signal=llm_result.get("strength_signal")
            # Phase 12: merge LLM-typed entities with rule-based output
            llm_persons=llm_result.get("persons",[])
            llm_places=llm_result.get("places",[])
            llm_objects=llm_result.get("objects",[])
            llm_relationships=llm_result.get("relationships",[])
            llm_emotional_beats=llm_result.get("emotional_beats",[])
            llm_time_markers=llm_result.get("time_markers",[])
            # Merge persons (dedupe by lowercased name; prefer LLM-typed)
            char_lower={c.lower() for c in characters}
            for p in llm_persons:
                if isinstance(p,dict):
                    name=p.get("name","").strip()
                    if name and name.lower() not in char_lower:
                        characters.append(name)
                        char_lower.add(name.lower())
                elif isinstance(p,str) and p.lower() not in char_lower:
                    characters.append(p)
                    char_lower.add(p.lower())
            # Merge places
            place_lower={p.lower() for p in places}
            for p in llm_places:
                if isinstance(p,dict):
                    name=p.get("name","").strip()
                    if name and name.lower() not in place_lower:
                        places.append(name)
                        place_lower.add(name.lower())
                elif isinstance(p,str) and p.lower() not in place_lower:
                    places.append(p)
                    place_lower.add(p.lower())
            # Merge objects
            obj_lower={o.lower() for o in objects}
            for o in llm_objects:
                if isinstance(o,str) and o.lower() not in obj_lower:
                    objects.append(o)
                    obj_lower.add(o.lower())
            # Relationships and emotional_beats come only from LLM (no rule-based equivalent)
            relationships=llm_relationships if isinstance(llm_relationships,list) else []
            emotional_beats=llm_emotional_beats if isinstance(llm_emotional_beats,list) else []
            # Merge time markers
            tm_lower={t.lower() for t in time_markers}
            for t in llm_time_markers:
                if isinstance(t,str) and t.lower() not in tm_lower:
                    time_markers.append(t)
                    tm_lower.add(t.lower())
    characters=characters[:20];places=places[:15]
    # Determine folder — handle paths outside PROJECT_ROOT gracefully (smoke tests, temp dirs)
    try:
        rel_path=path.resolve().relative_to(PROJECT_ROOT.resolve())
        folder=str(rel_path.parent) if str(rel_path.parent)!="." else "root"
        for f in FOLDERS:
            if folder==f or folder.startswith(f+"/"):folder=f;break
        else:folder="raw-dumps"
    except ValueError:
        # Path is outside PROJECT_ROOT (e.g. temp dir in smoke test) — default to raw-dumps
        folder="raw-dumps"
    status_map={"raw-dumps":"seedling","triage":"growing","chapters":"growing","drafts":"shaping","final":"polishing","archive":"resting"};status=status_map.get(folder,"seedling")
    chapter_no=None;ch_match=re.match(r'ch-?(\d+)',path.stem,re.I)
    if ch_match:chapter_no=int(ch_match.group(1))
    meta={"path":str(path.resolve()),"filename":path.name,"folder":folder,"word_count":word_count,"status":status,"chapter_no":chapter_no,"characters":characters,"places":places,"era":era,"beats":beats,"themes":themes,"voice":voice,"sensory":sensory,"continuity":[],"emotional_register":emotional_register,"motifs":[],"summary":summary,"strength_signal":1 if strength_signal else 0,"tagger_version":"5.0","anachronisms":anachronisms,
          # Phase 13: new tag types
          "relationships":relationships,"emotional_beats":emotional_beats,"time_markers":time_markers,"objects":objects}
    # Save to database so search/stats/coverage actually work (db.upsert_file filters non-DB keys)
    try:
        from . import db
        db.upsert_file(meta)
        # Phase 4: index tag occurrences at the paragraph level + FTS content
        _index_tag_occurrences(str(path.resolve()), body_text, meta)
        db.index_file_content(str(path.resolve()), path.name, body_text)
    except Exception as e:
        # Don't fail the whole tag if DB write fails — return meta anyway
        print(f"  [Warning] Could not save to database: {e}", file=sys.stderr)
    return meta


def _index_tag_occurrences(file_path: str, body_text: str, meta: dict):
    """Populate the tag_occurrences table with paragraph-level positions for every tag value.

    Called from tag_file() after the meta is built. Idempotent — clears existing
    occurrences for the file before re-indexing.
    """
    from . import db
    from .passage import build_index, find_paragraphs_containing
    db.clear_tag_occurrences(file_path)
    idx = build_index(body_text)
    # Tag types and their corresponding values from meta
    tag_buckets = [
        ("characters", meta.get("characters", [])),
        ("places",     meta.get("places", [])),
        ("themes",     meta.get("themes", [])),
        ("sensory",    meta.get("sensory", [])),
        ("beats",      meta.get("beats", [])),
        # Phase 13: new tag types
        ("time_markers", meta.get("time_markers", [])),
        ("objects",      meta.get("objects", [])),
    ]
    # Emotional beats are dicts with quote + intensity — index by quote
    for eb in meta.get("emotional_beats", []):
        if isinstance(eb, dict) and eb.get("quote"):
            matches = find_paragraphs_containing(idx, eb["quote"][:50], case_sensitive=False)
            for m in matches:
                db.add_tag_occurrence(
                    file_path=file_path, tag_type="emotional_beats", tag_value=eb["quote"][:80],
                    paragraph=m["paragraph"],
                    char_start=m.get("char_offsets_in_paragraph", [0])[0],
                    char_end=m.get("char_offsets_in_paragraph", [0])[0] + len(eb["quote"][:50]),
                    snippet=m.get("snippet", ""),
                )
    for tag_type, values in tag_buckets:
        if not values:
            continue
        for v in values:
            if not v or not isinstance(v, str):
                continue
            matches = find_paragraphs_containing(idx, v, case_sensitive=False)
            for m in matches:
                db.add_tag_occurrence(
                    file_path=file_path,
                    tag_type=tag_type,
                    tag_value=v,
                    paragraph=m["paragraph"],
                    char_start=m.get("char_offsets_in_paragraph", [0])[0],
                    char_end=m.get("char_offsets_in_paragraph", [0])[0] + len(v),
                    snippet=m.get("snippet", ""),
                )
    # Era is a single value, not a list — index it too if present
    era = meta.get("era")
    if era and isinstance(era, str):
        # Only index 4-digit years (avoid tagging "1990s" everywhere it appears)
        import re as _re
        for year_match in _re.finditer(r'\b(\d{4})\b', era):
            year = year_match.group(1)
            matches = find_paragraphs_containing(idx, year, case_sensitive=True)
            for m in matches:
                db.add_tag_occurrence(
                    file_path=file_path, tag_type="era", tag_value=year,
                    paragraph=m["paragraph"],
                    char_start=m.get("char_offsets_in_paragraph", [0])[0],
                    char_end=m.get("char_offsets_in_paragraph", [0])[0] + len(year),
                    snippet=m.get("snippet", ""),
                )


def find_links(file_path: str):
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
