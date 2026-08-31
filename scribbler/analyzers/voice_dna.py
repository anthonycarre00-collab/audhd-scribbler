#!/usr/bin/env python3
"""Voice DNA analyzer.

Compares a text's voice fingerprint against approved personal writing
samples. The writer can designate "this is my authentic voice" files,
and this tool flags drift.

Deterministic — no LLM needed. Uses function-word distribution, punctuation
habits, MATTR, sentence-length stats, dialogue ratio, and paragraph length.
"""
import re
import math
from collections import Counter
from typing import Dict, List, Any

from ..feedback import plain_summary, format_flag
from .. import tagger
from .. import db


def analyze(text: str, approved_samples: List[str] = None) -> Dict:
    """Run voice DNA analysis.

    Args:
        text: The text to analyze
        approved_samples: List of approved voice sample texts. If None, tries
                         to load from DB (files marked as strength_signal).
    """
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 50:
        return {"error": "Text too short for voice DNA", "word_count": word_count}

    # Get the current text's fingerprint
    current_fp = _compute_fingerprint(text)

    # Get approved samples
    if approved_samples is None:
        approved_samples = _load_approved_samples()

    if not approved_samples:
        return {
            "word_count": word_count,
            "current_fingerprint": current_fp,
            "approved_samples_count": 0,
            "similarity_to_approved": None,
            "drift_dimensions": [],
            "drift_assessment": "No approved voice samples found. Mark 2-3 files as 'strength_signal' to establish your voice baseline.",
            "observations": [],
            "summary": _generate_summary(word_count, current_fp, None, 0),
        }

    # Compute fingerprints for all approved samples
    approved_fps = [_compute_fingerprint(s) for s in approved_samples]

    # Compute centroid (average) of approved fingerprints
    centroid = _compute_centroid(approved_fps)

    # Compute similarity and per-dimension drift
    similarity = _cosine_similarity(current_fp, centroid)
    drift_dims = _compute_drift_dimensions(current_fp, centroid)

    drift_assessment = _assess_drift(similarity, drift_dims)

    observations = _generate_observations(similarity, drift_dims, drift_assessment)

    return {
        "word_count": word_count,
        "current_fingerprint": current_fp,
        "approved_samples_count": len(approved_samples),
        "similarity_to_approved": round(similarity, 3),
        "drift_dimensions": drift_dims,
        "drift_assessment": drift_assessment,
        "observations": observations,
        "summary": _generate_summary(word_count, current_fp, similarity, len(approved_samples)),
    }


def _compute_fingerprint(text: str) -> Dict:
    """Compute a voice fingerprint vector for a text."""
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)
    sentences = tagger.split_sentences(text)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    if not words or not sentences:
        return {}

    # Function word distribution (top 30)
    function_words = [
        "the", "of", "and", "to", "a", "in", "is", "that", "it", "was",
        "for", "on", "with", "as", "he", "i", "they", "we", "she", "you",
        "but", "not", "this", "from", "had", "by", "his", "her", "or", "an",
    ]
    text_lower = text.lower()
    fw_freq = {}
    for fw in function_words:
        count = len(re.findall(r'\b' + fw + r'\b', text_lower))
        fw_freq[fw] = count / word_count * 1000  # per 1000 words

    # Punctuation habits
    punct = {}
    for p, name in [(",", "comma"), (".", "period"), (";", "semicolon"),
                    ("—", "em_dash"), ("!", "exclamation"), ("?", "question")]:
        punct[name] = text.count(p) / word_count * 1000

    # MATTR (lexical diversity)
    if word_count > 500:
        window = 500
        ttrs = []
        for i in range(0, word_count - window, 100):
            window_words = words[i:i + window]
            ttrs.append(len(set(window_words)) / len(window_words))
        mattr = sum(ttrs) / len(ttrs) if ttrs else 0
    else:
        mattr = len(set(words)) / word_count

    # Sentence length stats
    sentence_lengths = [len(re.findall(r'\b\w+\b', s)) for s in sentences]
    mean_len = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    variance = sum((l - mean_len) ** 2 for l in sentence_lengths) / len(sentence_lengths) if sentence_lengths else 0
    std_len = math.sqrt(variance)

    # Paragraph length
    para_lengths = [len(re.findall(r'\b\w+\b', p)) for p in paragraphs]
    mean_para = sum(para_lengths) / len(para_lengths) if para_lengths else 0

    # First-person pronoun ratio
    first_person = len(re.findall(r'\b(I|me|my|mine|myself|we|us|our)\b', text, re.IGNORECASE))
    first_person_ratio = first_person / word_count * 100

    # Dialogue ratio
    dialogue_matches = re.findall(r'"([^"]+)"|"[^"]*"', text)
    dialogue_words = sum(len(re.findall(r'\b\w+\b', d)) for d in dialogue_matches)
    dialogue_ratio = dialogue_words / word_count * 100

    return {
        "function_word_freq": {k: round(v, 1) for k, v in fw_freq.items()},
        "punctuation_per_1000": {k: round(v, 2) for k, v in punct.items()},
        "lexical_diversity_mattr": round(mattr, 3),
        "mean_sentence_length": round(mean_len, 1),
        "std_sentence_length": round(std_len, 1),
        "mean_paragraph_length": round(mean_para, 1),
        "first_person_ratio": round(first_person_ratio, 2),
        "dialogue_ratio": round(dialogue_ratio, 2),
    }


def _load_approved_samples() -> List[str]:
    """Load approved voice samples from the database (files with strength_signal=1)."""
    try:
        all_files = db.get_all_files()
        samples = []
        for f in all_files:
            if f.get("strength_signal"):
                path = f.get("path", "")
                if path:
                    try:
                        from ..file_io import read_text_file
                        from pathlib import Path
                        text = read_text_file(Path(path))
                        # Strip frontmatter
                        if text.startswith("---"):
                            end = text.find("---", 3)
                            if end != -1:
                                text = text[end + 3:].strip()
                        samples.append(text)
                    except Exception:
                        pass
        return samples
    except Exception:
        return []


def _compute_centroid(fingerprints: List[Dict]) -> Dict:
    """Compute the average (centroid) of multiple fingerprints."""
    if not fingerprints:
        return {}

    # Collect all numeric values
    centroid = {}

    # Average scalar values
    for key in ["lexical_diversity_mattr", "mean_sentence_length", "std_sentence_length",
                "mean_paragraph_length", "first_person_ratio", "dialogue_ratio"]:
        values = [fp.get(key, 0) for fp in fingerprints if key in fp]
        if values:
            centroid[key] = round(sum(values) / len(values), 2)

    # Average function word freq
    fw_keys = set()
    for fp in fingerprints:
        fw_keys.update(fp.get("function_word_freq", {}).keys())
    fw_centroid = {}
    for key in fw_keys:
        values = [fp.get("function_word_freq", {}).get(key, 0) for fp in fingerprints]
        fw_centroid[key] = round(sum(values) / len(values), 1)
    centroid["function_word_freq"] = fw_centroid

    # Average punctuation
    punct_keys = set()
    for fp in fingerprints:
        punct_keys.update(fp.get("punctuation_per_1000", {}).keys())
    punct_centroid = {}
    for key in punct_keys:
        values = [fp.get("punctuation_per_1000", {}).get(key, 0) for fp in fingerprints]
        punct_centroid[key] = round(sum(values) / len(values), 2)
    centroid["punctuation_per_1000"] = punct_centroid

    return centroid


def _cosine_similarity(a: Dict, b: Dict) -> float:
    """Compute cosine similarity between two fingerprints (scalar dimensions only)."""
    keys = ["lexical_diversity_mattr", "mean_sentence_length", "std_sentence_length",
            "mean_paragraph_length", "first_person_ratio", "dialogue_ratio"]

    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    mag_a = math.sqrt(sum(a.get(k, 0) ** 2 for k in keys))
    mag_b = math.sqrt(sum(b.get(k, 0) ** 2 for k in keys))

    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _compute_drift_dimensions(current: Dict, approved: Dict) -> List[Dict]:
    """Compute per-dimension drift between current and approved centroid."""
    drifts = []
    for key in ["lexical_diversity_mattr", "mean_sentence_length", "std_sentence_length",
                "mean_paragraph_length", "first_person_ratio", "dialogue_ratio"]:
        cur = current.get(key, 0)
        appr = approved.get(key, 0)
        if appr > 0:
            pct_diff = (cur - appr) / appr * 100
            if abs(pct_diff) > 15:  # Only report significant drift
                direction = "higher" if pct_diff > 0 else "lower"
                drifts.append({
                    "dimension": key,
                    "approved_value": appr,
                    "current_value": cur,
                    "pct_difference": round(pct_diff, 1),
                    "direction": direction,
                })
    return drifts


def _assess_drift(similarity: float, drift_dims: List[Dict]) -> str:
    if similarity > 0.85:
        return "low drift — the voice is consistent with your approved samples"
    elif similarity > 0.7:
        return "moderate drift — some dimensions differ from your approved voice"
    elif similarity > 0.5:
        return "significant drift — the voice differs noticeably from your approved samples"
    else:
        return "high drift — this text reads quite differently from your approved voice"


def _generate_observations(similarity: float, drift_dims: List[Dict], assessment: str) -> List[Dict]:
    observations = []

    if similarity < 0.7 and drift_dims:
        top_drift = drift_dims[0]
        observations.append(format_flag(
            "voice_drift",
            top_drift["dimension"],
            f"{top_drift['dimension']} is {top_drift['pct_difference']:.0f}% {top_drift['direction']} than your approved samples",
            f"this dimension of your voice has drifted — {assessment}",
            [
                "check if the drift is intentional (different register, different scene type)",
                "if unintentional, review your approved samples to recalibrate your ear",
                "keep as-is if the drift serves the current passage (e.g., heightened emotion, different POV)",
            ]
        ))

    if len(drift_dims) >= 3:
        observations.append(format_flag(
            "multi_dimension_drift",
            f"{len(drift_dims)} dimensions",
            f"{len(drift_dims)} voice dimensions have drifted from your approved baseline",
            "multi-dimension drift suggests this passage is in a different voice mode — not necessarily wrong, but worth noticing",
            [
                "check if this passage is intentionally in a different voice (flashback, letter, dialogue-heavy)",
                "if unintentional, pick one dimension to recalibrate toward your baseline",
                "keep as-is if the voice shift is serving the content",
            ]
        ))

    return observations


def _generate_summary(word_count: int, fingerprint: Dict, similarity: float, sample_count: int) -> str:
    if similarity is not None:
        return plain_summary(
            what=f"Voice DNA analysis of {word_count} words against {sample_count} approved sample(s)",
            found=f"Similarity to approved voice: {similarity:.1%}. MATTR={fingerprint.get('lexical_diversity_mattr', 0)}.",
            next_step="If drift is detected, check if it's intentional (different scene type) or unconscious"
        )
    else:
        return plain_summary(
            what=f"Voice DNA fingerprint of {word_count} words",
            found=f"MATTR={fingerprint.get('lexical_diversity_mattr', 0)}, mean sentence={fingerprint.get('mean_sentence_length', 0)} words, first-person={fingerprint.get('first_person_ratio', 0)}%",
            next_step="Mark 2-3 files as 'strength_signal' to establish your voice baseline, then re-run"
        )
