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
    return sorted(characters)[:20]


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
    """Lazy-load spaCy if the model is already installed; never download during tagging."""
    global _spacy_nlp
    if _spacy_nlp is False:return None
    if _spacy_nlp is not None:return _spacy_nlp
    try:
        import spacy
        try:
            _spacy_nlp=spacy.load("en_core_web_sm")
        except Exception:
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
    prompt=f'''Read this text and extract JSON metadata{chunk_note}. Text:\n---\n{text}\n---\nReturn: {{"beats":["scene beats or units of change"],"themes":["3-5 supported themes"],"emotional_register":"dominant tone", "summary":"2-3 line plain-English summary", "strength_signal":"one supported strength signal"}}. Valid JSON only.'''
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
    nlp=_get_spacy();characters=detect_characters(body_text,nlp);places=detect_places(body_text,nlp);era=detect_era(body_text);rule_themes=detect_themes(body_text);themes=list(rule_themes);voice=detect_voice(body_text);sensory=detect_sensory(body_text);emotional_register=detect_emotional_register(body_text);anachronisms=detect_anachronisms(body_text)
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
    meta={"path":str(path.resolve()),"filename":path.name,"folder":folder,"word_count":word_count,"status":status,"chapter_no":chapter_no,"characters":characters,"places":places,"era":era,"beats":beats,"themes":themes,"voice":voice,"sensory":sensory,"continuity":[],"emotional_register":emotional_register,"motifs":[],"summary":summary,"strength_signal":1 if strength_signal else 0,"tagger_version":"4.1","anachronisms":anachronisms}
    # Save to database so search/stats/coverage actually work (db.upsert_file filters non-DB keys)
    try:
        from . import db
        db.upsert_file(meta)
    except Exception as e:
        # Don't fail the whole tag if DB write fails — return meta anyway
        print(f"  [Warning] Could not save to database: {e}", file=sys.stderr)
    return meta


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
