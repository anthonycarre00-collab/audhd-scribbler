#!/usr/bin/env python3
"""Emotional-beats analyzer.

Locates named vs shown emotions, tracks whether each scene has an emotional
turn, and flags scenes where the stated emotion differs from the scene
register (the body language, action, and sensory detail of the scene).
"""
import re
from typing import Dict, List
from collections import Counter

from ..feedback import format_flag, plain_summary
from ..passage import build_index as build_passage_index, make_loc


# Named emotion words — direct statements of feeling
NAMED_EMOTION_PATTERNS = [
    (r'\b(i (was|felt|feel|am|felt like)\s+)(angry|furious|mad|rage|enraged)\b', 'anger'),
    (r'\b(i (was|felt|feel|am|felt like)\s+)(sad|grief|grieved|heartbroken|devastated|miserable)\b', 'sadness'),
    (r'\b(i (was|felt|feel|am|felt like)\s+)(happy|joyful|glad|delighted|elated|content)\b', 'joy'),
    (r'\b(i (was|felt|feel|am|felt like)\s+)(afraid|scared|terrified|frightened|anxious|worried|nervous)\b', 'fear'),
    (r'\b(i (was|felt|feel|am|felt like)\s+)(ashamed|embarrassed|humiliated|guilty)\b', 'shame'),
    (r'\b(i (was|felt|feel|am|felt like)\s+)(surprised|shocked|stunned|amazed)\b', 'surprise'),
    (r'\b(i (was|felt|feel|am|felt like)\s+)(numb|empty|hollow|detached|disconnected)\b', 'dissociation'),
    (r'\b(i (was|felt|feel|am|felt like)\s+)(confused|lost|uncertain|unsure)\b', 'confusion'),
    (r'\b(i (was|felt|feel|am)\s+)(relieved|grateful|thankful)\b', 'relief'),
    (r'\b(i (was|felt|feel|am)\s+)(proud|accomplished|capable)\b', 'pride'),
]

# Shown emotion cues — physical, sensory, behavioral signals of emotion
SHOWN_EMOTION_PATTERNS = [
    (r'\b(my (hands|knees|legs|fingers)\s+(shook|trembled|were shaking))\b', 'physical_fear'),
    (r'\b(my (throat|chest)\s+(tightened|constricted|closed|ached|burned))\b', 'physical_emotion'),
    (r'\b(tears|crying|wept|sob|sobbed|wet cheeks)\b', 'shown_sadness'),
    (r'\b(laughed|laughter|smile|smiled|grinning)\b', 'shown_joy'),
    (r'\b(clenched (fist|jaw|teeth)|ground (my )?teeth|set my jaw)\b', 'shown_anger'),
    (r'\b(my (stomach|gut)\s+(dropped|sank|knotted|churned))\b', 'physical_dread'),
    (r'\b((my )?breath (caught|stopped|halted|quickened|slowed))\b', 'breath_emotion'),
    (r'\b((my )?heart (raced|pounded|hammered|sank|skipped))\b', 'heart_emotion'),
    (r'\b(flushed|blushed|heat (rose|crept) (to|up) my)\b', 'shown_shame'),
    (r'\b(stared|froze|frozen|couldn\'t move|paralyzed)\b', 'shown_shock'),
]


def analyze(text: str) -> Dict:
    """Run emotional-beats analysis on the text."""
    if len(text.split()) < 10:
        return {"error": "Text too short for meaningful analysis"}

    try:
        passage_idx = build_passage_index(text)
    except Exception:
        passage_idx = {"paragraphs": []}

    # Find all matches
    named_matches = _find_pattern_matches(text, passage_idx, NAMED_EMOTION_PATTERNS)
    shown_matches = _find_pattern_matches(text, passage_idx, SHOWN_EMOTION_PATTERNS)

    # Per-paragraph analysis: which paragraphs have named vs shown emotions?
    para_emotions = {}  # para_num -> {named: [...], shown: [...]}
    for m in named_matches:
        p = m["paragraph"]
        if p not in para_emotions:
            para_emotions[p] = {"named": [], "shown": []}
        para_emotions[p]["named"].append(m)
    for m in shown_matches:
        p = m["paragraph"]
        if p not in para_emotions:
            para_emotions[p] = {"named": [], "shown": []}
        para_emotions[p]["shown"].append(m)

    # Find paragraphs with only named emotions (telling not showing)
    only_named_paras = [p for p, e in para_emotions.items() if e["named"] and not e["shown"]]
    # Find paragraphs with shown emotions (good — showing)
    shown_paras = [p for p, e in para_emotions.items() if e["shown"]]
    # Find paragraphs with both named and shown — these are explicit emotional turns
    both_paras = [p for p, e in para_emotions.items() if e["named"] and e["shown"]]

    observations = []

    # Telling without showing
    if len(only_named_paras) >= 2:
        evidence = _excerpt_for_paragraphs(passage_idx, only_named_paras[:3])
        loc = make_loc(only_named_paras[:5], evidence_quote=evidence)
        top_emotion = Counter(m["label"] for m in named_matches).most_common(1)[0][0] if named_matches else "emotion"
        observations.append(format_flag(
            "telling_not_showing",
            f"{len(only_named_paras)} paragraph(s) name emotions without showing them",
            f"{len(only_named_paras)} paragraph(s) state emotions directly ('I was {top_emotion}') "
            f"without physical, sensory, or behavioral cues",
            "naming an emotion without showing it can flatten the moment — readers feel "
            "emotions through the body of the scene, not through the label",
            [
                "in one paragraph, replace the named emotion with a physical sensation (tight chest, dropped stomach)",
                "in one paragraph, describe an action that reveals the emotion (slamming a door, picking at a nail)",
                "keep the named emotion if the scene is reflective summary rather than present-tense scene",
            ],
            loc=loc,
            evidence_quote=evidence,
            why_it_matters="Anton Chekhov: 'Don't tell me the moon is shining; show me the glint of light on broken glass.' The same applies to emotion — show the body, not the label."
        ))

    # Showing without telling — usually good, worth affirming
    if len(shown_paras) >= 3 and len(only_named_paras) <= 1:
        evidence = _excerpt_for_paragraphs(passage_idx, shown_paras[:3])
        loc = make_loc(shown_paras[:5], evidence_quote=evidence)
        observations.append(format_flag(
            "showing_emotion",
            f"{len(shown_paras)} paragraph(s) show emotion through body and behavior",
            f"emotion is shown through physical and behavioral cues in {len(shown_paras)} paragraph(s) "
            f"({len(shown_matches)} total cues)",
            "this is strong memoir craft — readers inhabit the body of the scene rather "
            "than being told how to feel",
            [
                "notice which shown cues land hardest — those are your signature emotional vocabulary",
                "consider whether one or two named emotions would clarify the scene (showing and telling together is fine)",
                "keep going — this is the right instinct",
            ],
            loc=loc,
            evidence_quote=evidence,
            why_it_matters="Showing emotion is harder than naming it, but it's what makes memoir feel lived-in rather than reported."
        ))

    # Paragraphs with both — these are emotional turns
    if len(both_paras) >= 1:
        evidence = _excerpt_for_paragraphs(passage_idx, both_paras[:2])
        loc = make_loc(both_paras[:5], evidence_quote=evidence)
        observations.append(format_flag(
            "emotional_turn",
            f"{len(both_paras)} paragraph(s) with both named and shown emotion",
            f"{len(both_paras)} paragraph(s) contain both a named emotion and a physical/behavioral cue — "
            f"these are likely emotional turns",
            "naming + showing together lets the reader both understand and feel the emotion — "
            "this is the strongest pattern for memoir",
            [
                "study these paragraphs — they may be the emotional spine of the chapter",
                "consider whether the named emotion is necessary (sometimes the shown cue is enough)",
                "keep this pattern where the emotion is unfamiliar or surprising to the narrator",
            ],
            loc=loc,
            evidence_quote=evidence,
            why_it_matters="The emotional turn is where memoir earns its keep — the moment the narrator notices and the reader feels."
        ))

    # Scenes with no emotion at all (potential flat scenes)
    total_paragraphs = len(passage_idx.get("paragraphs", []))
    paras_with_emotion = set(para_emotions.keys())
    paras_without = total_paragraphs - len(paras_with_emotion)
    if total_paragraphs >= 5 and paras_without >= total_paragraphs * 0.6:
        flat_paras = [p["index"] for p in passage_idx["paragraphs"] if p["index"] not in paras_with_emotion][:5]
        evidence = _excerpt_for_paragraphs(passage_idx, flat_paras[:3])
        loc = make_loc(flat_paras[:5], evidence_quote=evidence) if flat_paras else None
        observations.append(format_flag(
            "emotion_absent_scenes",
            f"{paras_without} of {total_paragraphs} paragraph(s) have no emotional cue",
            f"{paras_without} of {total_paragraphs} paragraph(s) contain neither named nor shown emotion",
            "long stretches without emotional cues can read as flat or dissociated — "
            "the reader may lose the sense of the narrator's interior life",
            [
                "add one body cue (breath, stomach, throat) to a key flat paragraph",
                "add one named emotion to a moment of decision or realization",
                "keep as-is if the absence is intentional (a numb chapter, a dissociative passage)",
            ],
            loc=loc,
            evidence_quote=evidence,
            why_it_matters="Sometimes absence is the point — a numb chapter can mirror dissociation. But it should be a choice, not an accident."
        ))

    word_count = len(text.split())
    summary = plain_summary(
        what=f"Emotional-beats analysis of {word_count} words",
        found=f"{len(named_matches)} named emotions, {len(shown_matches)} shown cues, "
              f"{len(both_paras)} emotional turn(s)",
        next_step="Look for paragraphs that name without showing — those are opportunities to ground the feeling"
    )

    return {
        "word_count": word_count,
        "named_emotion_count": len(named_matches),
        "shown_emotion_count": len(shown_matches),
        "emotional_turn_count": len(both_paras),
        "paragraphs_with_emotion": len(paras_with_emotion),
        "paragraphs_without_emotion": paras_without,
        "total_paragraphs": total_paragraphs,
        "named_emotion_examples": [m["match"] for m in named_matches[:8]],
        "shown_emotion_examples": [m["match"] for m in shown_matches[:8]],
        "observations": observations,
        "summary": summary,
    }


def _find_pattern_matches(text: str, passage_idx: Dict, patterns: List) -> List[Dict]:
    """Find all matches of (regex, label) patterns with paragraph numbers."""
    matches = []
    if not passage_idx.get("paragraphs"):
        return matches
    for pattern, label in patterns:
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error:
            continue
        for p in passage_idx["paragraphs"]:
            for m in rx.finditer(p["text"]):
                matches.append({
                    "match": m.group(0),
                    "label": label,
                    "paragraph": p["index"],
                    "char_start": m.start(),
                    "char_end": m.end(),
                })
    return matches


def _excerpt_for_paragraphs(passage_idx: Dict, para_nums: List[int], max_chars: int = 220) -> str:
    """Return a short excerpt from the first matching paragraph."""
    if not para_nums or not passage_idx.get("paragraphs"):
        return ""
    for p in passage_idx["paragraphs"]:
        if p["index"] == para_nums[0]:
            return p["text"][:max_chars - 1] + "…" if len(p["text"]) > max_chars else p["text"]
    return ""
