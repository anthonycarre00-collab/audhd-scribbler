#!/usr/bin/env python3
"""Live writing checks — lightweight, instant feedback while typing.

Checks:
  - Spelling (pyspellchecker, offline)
  - Run-on sentences (>45 words or >3 clause separators)
  - Repeated words (same word 3+ times in one paragraph, excluding stopwords)
  - Double spaces
  - Trailing whitespace on lines
  - Passive voice (was/were/been + past participle, simple heuristic)
  - Filter words (existing FILTER_WORDS list)
  - Weak words (existing WEAK_WORDS list)
  - Repeated sentence openers (same opener 3+ times in a row)

Performance:
  - Only analyses the current paragraph ± 2 (not the whole document)
  - Returns markers with paragraph index, char offsets, message, severity
  - Target: < 100ms per run
"""
import re
from typing import Dict, List, Any, Optional
from collections import Counter

# Lazy-load spell checker
_SPELL = None

def _get_spell():
    global _SPELL
    if _SPELL is not None:
        return _SPELL
    try:
        from spellchecker import SpellChecker
        _SPELL = SpellChecker()
    except Exception:
        _SPELL = False
    return _SPELL

# Word lists (local copies to avoid import issues in frozen exe)
FILTER_WORDS = {
    "saw", "heard", "felt", "noticed", "realized", "knew", "thought", "wondered",
    "looked", "watched", "seemed", "appeared", "decided", "remembered", "recognized",
    "touched", "smelled",
}

WEAK_WORDS = {
    "just", "really", "very", "suddenly", "somewhat", "quite", "rather",
    "actually", "basically", "literally", "simply", "totally", "ultimately",
    "virtually", "practically", "seemingly",
}

STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with","by",
    "is","was","are","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","must","shall","can",
    "i","you","he","she","it","we","they","me","him","her","us","them",
    "my","your","his","its","our","their","this","that","these","those",
    "what","which","who","whom","whose","where","when","why","how",
    "if","then","than","so","as","also","not","no","nor","too",
}


def split_paragraphs(text: str) -> List[Dict]:
    """Split text into paragraphs with char offsets. Returns [{index, start, end, text}]."""
    if not text:
        return []
    paragraphs = []
    para_re = re.compile(r'[ \t]*([^\n].*?)(?=\n[ \t]*\n|\Z)', re.DOTALL)
    for m in para_re.finditer(text):
        para_text = m.group(1)
        start = m.start(1)
        while start < len(text) and text[start] in ' \t':
            start += 1
        end = start + len(para_text.rstrip())
        paragraphs.append({
            "index": len(paragraphs) + 1,
            "start": start,
            "end": end,
            "text": para_text.rstrip(),
        })
    return paragraphs


def run_live_checks(text: str, cursor_offset: int = 0) -> Dict[str, Any]:
    """Run all live checks on the text, focused on the paragraph near cursor_offset.

    Returns:
      {
        "markers": [
          {
            "paragraph": int,       # 1-based
            "char_start": int,      # offset within the whole text
            "char_end": int,
            "message": str,
            "severity": "error"|"warning"|"info",
            "check_type": "spelling"|"run_on"|"repeated_word"|...
          }
        ],
        "counts": {spelling: N, run_on: N, ...},
        "total": N
      }
    """
    if not text or not text.strip():
        return {"markers": [], "counts": {}, "total": 0}

    paragraphs = split_paragraphs(text)

    # Determine which paragraphs to check (cursor ± 2)
    if cursor_offset > 0:
        current_para = 1
        for p in paragraphs:
            if p["start"] <= cursor_offset < p["end"]:
                current_para = p["index"]
                break
        start_idx = max(0, current_para - 3)  # 0-based, include 2 before
        end_idx = min(len(paragraphs), current_para + 2)  # include 2 after
        paras_to_check = paragraphs[start_idx:end_idx]
    else:
        paras_to_check = paragraphs

    markers = []
    counts = Counter()

    for p in paras_to_check:
        para_text = p["text"]
        para_offset = p["start"]

        # Spelling
        spell = _get_spell()
        if spell:
            words_in_para = re.findall(r"\b([a-zA-Z']+)\b", para_text)
            misspelled = spell.unknown([w.lower() for w in words_in_para])
            for m in re.finditer(r"\b([a-zA-Z']+)\b", para_text):
                word = m.group(1)
                if word.lower() in misspelled:
                    # Skip proper nouns (capitalized mid-sentence)
                    if word[0].isupper() and m.start() > 0 and para_text[m.start()-1] not in '.!?\n':
                        continue
                    markers.append({
                        "paragraph": p["index"],
                        "char_start": para_offset + m.start(),
                        "char_end": para_offset + m.end(),
                        "message": f"Possible spelling: '{word}'",
                        "severity": "error",
                        "check_type": "spelling",
                    })
                    counts["spelling"] += 1

        # Run-on sentences
        sentences = re.split(r'(?<=[.!?])\s+', para_text)
        for sent in sentences:
            words = sent.split()
            if len(words) > 45:
                # Find the sentence in the paragraph
                sent_start = para_text.find(sent)
                if sent_start >= 0:
                    markers.append({
                        "paragraph": p["index"],
                        "char_start": para_offset + sent_start,
                        "char_end": para_offset + sent_start + len(sent),
                        "message": f"Long sentence ({len(words)} words) — consider breaking it up",
                        "severity": "warning",
                        "check_type": "run_on",
                    })
                    counts["run_on"] += 1
            # Clause count (simple: count , ; —)
            clause_count = len(re.findall(r'[,;—]', sent))
            if clause_count > 3 and len(words) > 25:
                sent_start = para_text.find(sent)
                if sent_start >= 0:
                    markers.append({
                        "paragraph": p["index"],
                        "char_start": para_offset + sent_start,
                        "char_end": para_offset + sent_start + len(sent),
                        "message": f"Complex sentence ({clause_count} clauses) — may be hard to follow",
                        "severity": "warning",
                        "check_type": "run_on",
                    })
                    counts["run_on"] += 1

        # Repeated words (3+ times in one paragraph, excluding stopwords)
        word_freq = Counter(w.lower() for w in re.findall(r'\b[a-zA-Z]+\b', para_text))
        for word, count in word_freq.items():
            if count >= 3 and word not in STOPWORDS and len(word) >= 4:
                # Find first occurrence for the marker
                m = re.search(r'\b' + re.escape(word) + r'\b', para_text, re.IGNORECASE)
                if m:
                    markers.append({
                        "paragraph": p["index"],
                        "char_start": para_offset + m.start(),
                        "char_end": para_offset + m.end(),
                        "message": f"'{word}' repeated {count} times in this paragraph",
                        "severity": "warning",
                        "check_type": "repeated_word",
                    })
                    counts["repeated_word"] += 1

        # Double spaces
        for m in re.finditer(r'  +', para_text):
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": "Double space",
                "severity": "info",
                "check_type": "double_space",
            })
            counts["double_space"] += 1

        # Trailing whitespace on lines
        for m in re.finditer(r'[ \t]+$', para_text, re.MULTILINE):
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": "Trailing whitespace",
                "severity": "info",
                "check_type": "trailing_ws",
            })
            counts["trailing_ws"] += 1

        # Passive voice (simple: was/were/been + past participle)
        for m in re.finditer(r'\b(was|were|been|being|is|are|am)\s+(\w+ed|written|done|gone|seen|known|taken|given|made|come|become)\b', para_text, re.IGNORECASE):
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": f"Passive voice: '{m.group(0)}'",
                "severity": "info",
                "check_type": "passive",
            })
            counts["passive"] += 1

        # Filter words
        for m in re.finditer(r'\b(' + '|'.join(re.escape(w) for w in FILTER_WORDS) + r')\b', para_text, re.IGNORECASE):
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": f"Filter word: '{m.group(0)}'",
                "severity": "info",
                "check_type": "filter_word",
            })
            counts["filter_word"] += 1

        # Weak words
        for m in re.finditer(r'\b(' + '|'.join(re.escape(w) for w in WEAK_WORDS) + r')\b', para_text, re.IGNORECASE):
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": f"Weak word: '{m.group(0)}'",
                "severity": "info",
                "check_type": "weak_word",
            })
            counts["weak_word"] += 1

    # Repeated sentence openers (across the whole text, not just cursor)
    if len(paragraphs) >= 1:
        # Collect all sentences across all paragraphs, in order
        all_sentences = []
        for p in paragraphs:
            sents = re.split(r'(?<=[.!?])\s+', p["text"])
            for s in sents:
                if s.strip():
                    all_sentences.append((p, s))
        for i in range(len(all_sentences) - 2):
            opener_a = re.match(r'\s*([A-Za-z]+)', all_sentences[i][1])
            opener_b = re.match(r'\s*([A-Za-z]+)', all_sentences[i+1][1])
            opener_c = re.match(r'\s*([A-Za-z]+)', all_sentences[i+2][1])
            if opener_a and opener_b and opener_c:
                a, b, c = opener_a.group(1).lower(), opener_b.group(1).lower(), opener_c.group(1).lower()
                if a and a == b == c:
                    p, sent = all_sentences[i + 2]
                    sent_start = p["text"].find(sent)
                    if sent_start >= 0:
                        markers.append({
                            "paragraph": p["index"],
                            "char_start": p["start"] + sent_start,
                            "char_end": p["start"] + sent_start + opener_c.end(),
                            "message": f"Repeated sentence opener: '{a}' (3 times in a row)",
                            "severity": "warning",
                            "check_type": "opener",
                        })
                        counts["opener"] += 1

    return {
        "markers": markers,
        "counts": dict(counts),
        "total": len(markers),
    }
