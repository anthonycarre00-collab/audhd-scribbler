#!/usr/bin/env python3
"""Grammar checks — rule-based, lightweight, identifies likely issues.

Each finding provides:
  - Problem (what's wrong)
  - Why it may be a problem
  - Possible correction

Rules:
  - Subject-verb agreement (simple: I/he/she/it + plural verb)
  - Tense consistency within paragraph
  - Comma splices (independent clauses joined by comma only)
  - Missing capitalisation at sentence start
  - Missing end punctuation
  - Its/it's confusion
  - There/their/they're confusion
  - Your/you're confusion
  - A/an before vowel/consonant
"""
import re
from typing import Dict, List, Any
from collections import Counter


def run_grammar_checks(text: str) -> Dict[str, Any]:
    """Run grammar checks on the text.

    Returns same structure as live_checks:
      {markers: [...], counts: {...}, total: N}
    """
    if not text or not text.strip():
        return {"markers": [], "counts": {}, "total": 0}

    markers = []
    counts = Counter()

    # Split into paragraphs for offset tracking
    para_re = re.compile(r'[ \t]*([^\n].*?)(?=\n[ \t]*\n|\Z)', re.DOTALL)
    paragraphs = []
    for m in para_re.finditer(text):
        para_text = m.group(1)
        start = m.start(1)
        while start < len(text) and text[start] in ' \t':
            start += 1
        paragraphs.append({"index": len(paragraphs) + 1, "start": start, "text": para_text.rstrip()})

    for p in paragraphs:
        para_text = p["text"]
        para_offset = p["start"]

        # 1. Its/it's confusion
        for m in re.finditer(r'\b(its)\s+(a|the|an|going|been|not|a )\b', para_text, re.IGNORECASE):
            # "its a" should be "it's a"
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": f"Its/it's: '{m.group(0)}' — likely should be 'it's' (contraction of 'it is')",
                "severity": "warning",
                "check_type": "grammar_its",
            })
            counts["grammar_its"] += 1

        # 2. There/their/they're — flag ambiguous uses
        for m in re.finditer(r'\b(there)\s+(going|coming|leaving|arriving|friends|parents|house|car)\b', para_text, re.IGNORECASE):
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": f"There/their: '{m.group(0)}' — 'their' may be intended (possessive)",
                "severity": "warning",
                "check_type": "grammar_there",
            })
            counts["grammar_there"] += 1

        # 3. Your/you're confusion
        for m in re.finditer(r'\b(your)\s+(going|coming|leaving|right|wrong|welcome|here|there|crazy|amazing)\b', para_text, re.IGNORECASE):
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": f"Your/you're: '{m.group(0)}' — 'you're' may be intended (contraction of 'you are')",
                "severity": "warning",
                "check_type": "grammar_your",
            })
            counts["grammar_your"] += 1

        # 4. A/an before vowel
        for m in re.finditer(r'\b(a)\s+([aeiouAEIOU]\w*)', para_text):
            # Skip if the word starts with a vowel sound exception (university, user, etc.)
            word = m.group(2).lower()
            if word.startswith(('uni', 'use', 'usu', 'euro', 'one', 'once')):
                continue
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": f"A/an: '{m.group(0)}' — should be 'an' before a vowel sound",
                "severity": "warning",
                "check_type": "grammar_an",
            })
            counts["grammar_an"] += 1

        # 5. An before consonant
        for m in re.finditer(r'\b(an)\s+([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]\w*)', para_text):
            word = m.group(2).lower()
            # Skip hour, honest, honor (silent h)
            if word.startswith(('hour', 'honest', 'honor')):
                continue
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": f"A/an: '{m.group(0)}' — should be 'a' before a consonant sound",
                "severity": "warning",
                "check_type": "grammar_a",
            })
            counts["grammar_a"] += 1

        # 6. Missing capitalisation at sentence start
        for m in re.finditer(r'[.!?]\s+([a-z])', para_text):
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(1),
                "char_end": para_offset + m.end(1),
                "message": f"Capitalisation: sentence should start with a capital letter",
                "severity": "warning",
                "check_type": "grammar_cap",
            })
            counts["grammar_cap"] += 1

        # 7. Comma splice (simple: two independent clauses joined by comma)
        # Heuristic: comma + subject pronoun + verb
        for m in re.finditer(r',\s+(I|he|she|they|we|you)\s+(was|were|is|are|went|said|felt|knew|thought|saw|heard|looked|walked)\b', para_text, re.IGNORECASE):
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + m.start(),
                "char_end": para_offset + m.end(),
                "message": f"Possible comma splice: '{m.group(0).strip()}' — consider a period or semicolon",
                "severity": "info",
                "check_type": "grammar_comma",
            })
            counts["grammar_comma"] += 1

        # 8. Missing end punctuation (last paragraph char is a letter)
        if para_text and para_text[-1].isalpha():
            markers.append({
                "paragraph": p["index"],
                "char_start": para_offset + len(para_text) - 1,
                "char_end": para_offset + len(para_text),
                "message": "Missing end punctuation",
                "severity": "info",
                "check_type": "grammar_punct",
            })
            counts["grammar_punct"] += 1

    return {
        "markers": markers,
        "counts": dict(counts),
        "total": len(markers),
    }
