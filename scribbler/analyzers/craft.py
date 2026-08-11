#!/usr/bin/env python3
"""Line-level craft analyzer.

Analyzes sentence rhythm, paragraph distribution, repetition, readability,
sensory density, dialogue/narrative/interiority ratio, weak words, filter words.
All signals reported as bands, self-relative to the author's own book average.
"""
import re
import math
from collections import Counter
from typing import Dict, List, Any
from pathlib import Path

from ..config import WEAK_WORDS, FILTER_WORDS, SENSORY_CATEGORIES
from ..feedback import make_observation, plain_summary, strengths_first, format_flag
from .. import tagger


def analyze(text: str) -> Dict:
    """Run full line-level craft analysis on a text."""
    sentences = tagger.split_sentences(text)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    words = re.findall(r'\b\w+\b', text)
    word_count = len(words)

    if word_count < 10:
        return {
            "error": "Text too short for meaningful analysis",
            "word_count": word_count,
        }

    return {
        "word_count": word_count,
        "sentence_count": len(sentences),
        "paragraph_count": len(paragraphs),
        "sentence_length_rhythm": _sentence_rhythm(sentences),
        "paragraph_distribution": _paragraph_distribution(paragraphs),
        "repetition": _repetition_analysis(text, words),
        "readability": _readability(text, sentences, words),
        "sensory_density": _sensory_density(text, word_count),
        "dialogue_ratio": _dialogue_ratio(text, word_count),
        "weak_words": _weak_word_density(text, word_count),
        "filter_words": _filter_word_density(text, word_count),
        "alliteration": _alliteration_detection(sentences),
        "observations": _generate_observations(sentences, paragraphs, words, word_count),
        "summary": _generate_summary(word_count, len(sentences), len(paragraphs)),
    }


def _sentence_rhythm(sentences: List[str]) -> Dict:
    """Analyze sentence length variation and rhythm."""
    lengths = []
    for s in sentences:
        words = re.findall(r'\b\w+\b', s)
        lengths.append(len(words))

    if not lengths:
        return {"error": "No sentences found"}

    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    std = math.sqrt(variance)
    cv = std / mean if mean > 0 else 0

    # Detect runs of 4+ consecutive similar-length sentences (±2 words)
    monotony_runs = []
    run_start = 0
    for i in range(1, len(lengths)):
        if abs(lengths[i] - lengths[i-1]) <= 2:
            if run_start == 0:
                run_start = i - 1
        else:
            if i - run_start >= 4:
                monotony_runs.append({
                    "start_sentence": run_start + 1,
                    "end_sentence": i,
                    "lengths": lengths[run_start:i],
                })
            run_start = 0
    # Check final run
    if len(lengths) - run_start >= 4 and run_start > 0:
        monotony_runs.append({
            "start_sentence": run_start + 1,
            "end_sentence": len(lengths),
            "lengths": lengths[run_start:],
        })

    # Length distribution
    short = sum(1 for l in lengths if l <= 8)
    medium = sum(1 for l in lengths if 9 <= l <= 20)
    long = sum(1 for l in lengths if 21 <= l <= 35)
    very_long = sum(1 for l in lengths if l > 35)

    return {
        "mean_length": round(mean, 1),
        "median_length": sorted(lengths)[len(lengths) // 2],
        "std_dev": round(std, 1),
        "coefficient_of_variation": round(cv, 2),
        "rhythm_assessment": _assess_rhythm(cv),
        "short_sentences_pct": round(short / len(lengths) * 100, 1),
        "medium_sentences_pct": round(medium / len(lengths) * 100, 1),
        "long_sentences_pct": round(long / len(lengths) * 100, 1),
        "very_long_sentences_pct": round(very_long / len(lengths) * 100, 1),
        "monotony_runs": monotony_runs,
        "length_histogram": {
            "1-5": sum(1 for l in lengths if l <= 5),
            "6-10": sum(1 for l in lengths if 6 <= l <= 10),
            "11-15": sum(1 for l in lengths if 11 <= l <= 15),
            "16-25": sum(1 for l in lengths if 16 <= l <= 25),
            "26-40": sum(1 for l in lengths if 26 <= l <= 40),
            "40+": sum(1 for l in lengths if l > 40),
        }
    }


def _assess_rhythm(cv: float) -> str:
    if cv < 0.5:
        return "monotonous — sentences are similar in length, which can create a droning effect"
    elif cv < 0.7:
        return "somewhat uniform — some variation but could benefit from more contrast"
    elif cv <= 1.2:
        return "healthy variation — good mix of short and long sentences"
    elif cv <= 1.4:
        return "varied — strong contrast between short and long sentences"
    else:
        return "erratic — very wide variation; may feel choppy or disjointed"


def _paragraph_distribution(paragraphs: List[str]) -> Dict:
    """Analyze paragraph length distribution."""
    lengths = [len(re.findall(r'\b\w+\b', p)) for p in paragraphs]
    if not lengths:
        return {"error": "No paragraphs found"}

    mean = sum(lengths) / len(lengths)
    one_liners = sum(1 for l in lengths if l <= 12)
    walls = sum(1 for l in lengths if l > 250)

    return {
        "mean_paragraph_length": round(mean, 1),
        "median_paragraph_length": sorted(lengths)[len(lengths) // 2],
        "longest_paragraph": max(lengths),
        "shortest_paragraph": min(lengths),
        "one_line_paragraphs_pct": round(one_liners / len(lengths) * 100, 1),
        "wall_of_text_count": walls,
        "assessment": _assess_paragraphs(mean, one_liners / len(lengths) * 100, walls),
    }


def _assess_paragraphs(mean: float, one_liner_pct: float, walls: int) -> str:
    parts = []
    if mean > 200:
        parts.append("paragraphs tend to be long, which can slow the reader's pace")
    elif mean < 30:
        parts.append("paragraphs tend to be very short, creating a staccato effect")
    if one_liner_pct > 30:
        parts.append(f"{one_liner_pct:.0f}% of paragraphs are single lines — a memoir tic that can lose its punch if overused")
    if walls > 0:
        parts.append(f"{walls} paragraph(s) exceed 250 words — readers may lose the thread")
    if not parts:
        return "paragraph lengths are well-distributed"
    return "; ".join(parts)


def _repetition_analysis(text: str, words: List[str]) -> Dict:
    """Detect repeated words, sentence openers, and crutch phrases."""
    word_lower = [w.lower() for w in words]

    # Word frequency
    word_freq = Counter(word_lower)
    # Filter out common stopwords
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'of', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'i', 'me', 'my', 'we', 'us', 'our', 'you', 'your', 'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they', 'them', 'their', 'this', 'that', 'these', 'those', 'as', 'if', 'then', 'than', 'so', 'because', 'while', 'when', 'where', 'what', 'who', 'how', 'why', 'not', 'no', 'yes', 'all', 'some', 'any', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'such', 'only', 'own', 'same', 'too', 'very', 'just', 'now'}
    content_words = {w: c for w, c in word_freq.items() if w not in stopwords and len(w) > 2 and c >= 3}

    # Top repeated content words (potential crutch words)
    top_repeated = sorted(content_words.items(), key=lambda x: x[1], reverse=True)[:10]

    # Sentence openers
    sentences = tagger.split_sentences(text)
    openers = []
    for s in sentences:
        words_in_s = re.findall(r'\b\w+\b', s)
        if words_in_s:
            openers.append(words_in_s[0].lower())
    opener_freq = Counter(openers)

    # Check for "I" opener overuse (common in memoir)
    i_opener_pct = opener_freq.get('i', 0) / len(sentences) * 100 if sentences else 0

    # 3-6 gram phrase repetition
    phrases = []
    for n in [4, 5, 6]:
        ngrams = []
        for i in range(len(words) - n + 1):
            ngram = ' '.join(words[i:i+n]).lower()
            ngrams.append(ngram)
        ngram_freq = Counter(ngrams)
        for phrase, count in ngram_freq.items():
            if count >= 3:
                phrases.append({"phrase": phrase, "count": count, "ngram_size": n})

    return {
        "top_repeated_words": top_repeated,
        "sentence_opener_frequency": opener_freq.most_common(5),
        "i_opener_percentage": round(i_opener_pct, 1),
        "repeated_phrases": sorted(phrases, key=lambda x: x["count"], reverse=True)[:10],
    }


def _readability(text: str, sentences: List[str], words: List[str]) -> Dict:
    """Compute multiple readability formulas and report as a band."""
    if not sentences or not words:
        return {"error": "Insufficient text"}

    # Syllable count (approximate)
    def count_syllables(word):
        word = word.lower()
        if len(word) <= 3:
            return 1
        word = re.sub(r'(?:[^laeiouy]es|ed|[^laeiouy]e)$', '', word)
        word = re.sub(r'^y', '', word)
        matches = re.findall(r'[aeiouy]{1,2}', word)
        return max(1, len(matches))

    total_syllables = sum(count_syllables(w) for w in words)
    total_words = len(words)
    total_sentences = len(sentences)

    # Flesch Reading Ease
    if total_sentences == 0 or total_words == 0:
        flesch = 0
    else:
        flesch = 206.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words)

    # Flesch-Kincaid Grade Level
    if total_sentences == 0 or total_words == 0:
        fkgl = 0
    else:
        fkgl = 0.39 * (total_words / total_sentences) + 11.8 * (total_syllables / total_words) - 15.59

    # Gunning Fog
    complex_words = sum(1 for w in words if count_syllables(w) >= 3)
    if total_sentences == 0 or total_words == 0:
        fog = 0
    else:
        fog = 0.4 * ((total_words / total_sentences) + 100 * (complex_words / total_words))

    # Determine grade band
    avg_grade = (fkgl + fog) / 2
    if avg_grade < 6:
        band = "elementary (grades 4-5) — very accessible"
    elif avg_grade < 9:
        band = "middle school (grades 6-8) — accessible to most readers"
    elif avg_grade < 12:
        band = "high school (grades 9-11) — standard trade memoir range"
    elif avg_grade < 14:
        band = "college (grades 12-13) — literary memoir range"
    else:
        band = "advanced (grade 14+) — may challenge some readers; fine for research-braid sections"

    return {
        "flesch_reading_ease": round(flesch, 1),
        "flesch_kincaid_grade": round(fkgl, 1),
        "gunning_fog": round(fog, 1),
        "average_grade_level": round(avg_grade, 1),
        "grade_band": band,
        "note": "Reported as a band across formulas. For memoir, grade 7-11 is typical; research-braid sections may legitimately run higher."
    }


def _sensory_density(text: str, word_count: int) -> Dict:
    """Compute sensory detail density per 1000 words."""
    text_lower = text.lower()
    by_sense = {}
    total = 0

    for sense, words in SENSORY_CATEGORIES.items():
        count = sum(len(re.findall(r'\b' + re.escape(w) + r'\b', text_lower)) for w in words)
        if count > 0:
            by_sense[sense] = count
            total += count

    per_1000 = total / word_count * 1000 if word_count > 0 else 0

    # Identify underrepresented senses
    all_senses = list(SENSORY_CATEGORIES.keys())
    missing = [s for s in all_senses if s not in by_sense]

    return {
        "total_sensory_words": total,
        "per_1000_words": round(per_1000, 1),
        "by_sense": by_sense,
        "missing_senses": missing,
        "note": "Smell and taste are linked to memory (Proust's madeleine). Their absence may mean the prose hasn't caught the lived experience."
    }


def _dialogue_ratio(text: str, word_count: int) -> Dict:
    """Estimate dialogue vs. narrative vs. interiority ratio."""
    # Dialogue: text within quotes or em-dashes
    dialogue_matches = re.findall(r'"([^"]+)"|"[^"]*"|—[^—]*—', text)
    dialogue_words = sum(len(re.findall(r'\b\w+\b', d)) for d in dialogue_matches)

    # Interiority: sentences with mental-state verbs
    interiority_verbs = r'\b(thought|felt|realized|wondered|knew|remembered|imagined|considered|decided|noticed|reflected|pondered|understood|believed|suspected)\b'
    interiority_sentences = [s for s in tagger.split_sentences(text) if re.search(interiority_verbs, s, re.IGNORECASE)]
    interiority_words = sum(len(re.findall(r'\b\w+\b', s)) for s in interiority_sentences)

    if word_count == 0:
        return {"error": "No words"}

    dialogue_pct = dialogue_words / word_count * 100
    interiority_pct = interiority_words / word_count * 100
    narrative_pct = max(0, 100 - dialogue_pct - interiority_pct)

    return {
        "dialogue_pct": round(dialogue_pct, 1),
        "interiority_pct": round(interiority_pct, 1),
        "narrative_pct": round(narrative_pct, 1),
        "assessment": _assess_ratio(dialogue_pct, interiority_pct),
    }


def _assess_ratio(dialogue_pct: float, interiority_pct: float) -> str:
    parts = []
    if interiority_pct > 60:
        parts.append("interiority dominates (>60%) — readers may feel they're inside the narrator's head without enough external grounding")
    elif interiority_pct < 10:
        parts.append("very little interiority — readers see actions but may not feel the narrator's inner experience")
    if dialogue_pct > 50:
        parts.append("dialogue-heavy — fast-paced but may lack descriptive grounding")
    elif dialogue_pct < 5:
        parts.append("minimal dialogue — the narrator is doing most of the talking")
    if not parts:
        return "balanced mix of dialogue, narrative, and interiority"
    return "; ".join(parts)


def _weak_word_density(text: str, word_count: int) -> Dict:
    """Count weak/filler words per 1000 words."""
    text_lower = text.lower()
    found = {}
    for word in WEAK_WORDS:
        count = len(re.findall(r'\b' + re.escape(word) + r'\b', text_lower))
        if count > 0:
            found[word] = count

    total = sum(found.values())
    per_1000 = total / word_count * 1000 if word_count > 0 else 0

    return {
        "total": total,
        "per_1000_words": round(per_1000, 1),
        "found": sorted(found.items(), key=lambda x: x[1], reverse=True)[:10],
        "assessment": "high density (>40/1000) may indicate reliance on filler" if per_1000 > 40 else "within typical range"
    }


def _filter_word_density(text: str, word_count: int) -> Dict:
    """Count filter words (saw, felt, noticed, etc.) per 1000 words."""
    text_lower = text.lower()
    found = {}
    for word in FILTER_WORDS:
        count = len(re.findall(r'\b' + re.escape(word) + r'\b', text_lower))
        if count > 0:
            found[word] = count

    total = sum(found.values())
    per_1000 = total / word_count * 1000 if word_count > 0 else 0

    return {
        "total": total,
        "per_1000_words": round(per_1000, 1),
        "found": sorted(found.items(), key=lambda x: x[1], reverse=True)[:10],
        "note": "Filter words create narrative distance. In memoir, some are doing attention-filtering work; not all need cutting."
    }


def _alliteration_detection(sentences: List[str]) -> Dict:
    """Detect alliteration clusters (simplified — based on first letters, not phonemes)."""
    clusters = []
    for i, sentence in enumerate(sentences):
        words = [w.lower() for w in re.findall(r'\b[a-z]+\b', sentence) if len(w) > 2]
        if len(words) < 4:
            continue
        # Check for 4+ words with same first letter in a 10-word window
        for start in range(len(words) - 3):
            window = words[start:start + 10]
            first_letters = [w[0] for w in window]
            letter_counts = Counter(first_letters)
            for letter, count in letter_counts.items():
                if count >= 4 and letter not in 'aeiou':  # Skip vowel alliteration (too common)
                    clusters.append({
                        "sentence": i + 1,
                        "letter": letter,
                        "count": count,
                        "preview": ' '.join(window[:10]),
                    })
                    break

    return {
        "alliteration_clusters": clusters[:5],
        "total_clusters": len(clusters),
        "note": "Dense alliteration can be intentional (literary effect) or accidental (tong-twister). Context decides."
    }


def _generate_observations(sentences: List[str], paragraphs: List[str], words: List[str], word_count: int) -> List[Dict]:
    """Generate low-shame observations based on the analysis."""
    observations = []

    rhythm = _sentence_rhythm(sentences)
    if rhythm.get("monotony_runs"):
        for run in rhythm["monotony_runs"][:2]:  # Top 2 runs
            observations.append(format_flag(
                "rhythm",
                f"sentences {run['start_sentence']}-{run['end_sentence']}",
                f"{len(run['lengths'])} consecutive sentences of similar length ({', '.join(str(l) for l in run['lengths'][:5])}{'...' if len(run['lengths']) > 5 else ''} words)",
                "the prose rhythm became uniform, which can create a droning quality",
                [
                    "break the pattern with a very short sentence (3-5 words)",
                    "vary the next sentence's structure significantly",
                    "keep as-is if the uniformity mirrors the narrator's mental state",
                ]
            ))

    if rhythm.get("coefficient_of_variation", 0) < 0.5:
        observations.append(format_flag(
            "rhythm",
            "whole chapter",
            f"the coefficient of variation in sentence length is {rhythm['coefficient_of_variation']}, which is quite low",
            "the prose may feel monotonous over a sustained read",
            [
                "intentionally mix short punchy sentences with longer ones",
                "try breaking some long sentences into fragments",
                "keep as-is if the steady rhythm is the voice you want",
            ]
        ))

    rep = _repetition_analysis(' '.join(words), words)
    if rep.get("i_opener_percentage", 0) > 40:
        observations.append(format_flag(
            "sentence_openers",
            "whole chapter",
            f"{rep['i_opener_percentage']:.0f}% of sentences start with 'I'",
            "the narration may feel self-referential, which is natural in memoir but can be varied for impact",
            [
                "try starting some sentences with a sensory detail or action",
                "restructure a few sentences to begin with time or place",
                "keep as-is if the 'I'-forward voice is intentional and consistent",
            ]
        ))

    weak = _weak_word_density(' '.join(words), word_count)
    if weak.get("per_1000_words", 0) > 40:
        top_weak = weak.get("found", [])
        if top_weak:
            observations.append(format_flag(
                "weak_words",
                "whole chapter",
                f"weak-word density is {weak['per_1000_words']}/1000 words; most frequent: '{top_weak[0][0]}' ({top_weak[0][1]} times)",
                "these words can dilute the prose's impact without adding meaning",
                [
                    f"try removing some instances of '{top_weak[0][0]}' and notice the effect",
                    "keep the ones that feel natural to the voice",
                    "leave as-is if the casual register is intentional",
                ]
            ))

    sensory = _sensory_density(' '.join(words), word_count)
    if sensory.get("per_1000_words", 0) < 5:
        observations.append(format_flag(
            "sensory_density",
            "whole chapter",
            f"sensory detail density is {sensory['per_1000_words']}/1000 words, which is quite low",
            "readers may struggle to feel present in the scene without sensory grounding",
            [
                "add one smell, taste, or tactile detail to a key scene",
                "check if the absence is intentional (interior monologue chapters may not need it)",
                "keep as-is if the chapter is reflective rather than scenic",
            ]
        ))

    return observations


def _generate_summary(word_count: int, sentence_count: int, paragraph_count: int) -> str:
    """Generate a 3-line plain-English summary."""
    return plain_summary(
        what=f"Line-level craft analysis of {word_count} words across {sentence_count} sentences and {paragraph_count} paragraphs",
        found=f"Sentence rhythm, paragraph distribution, repetition patterns, readability, sensory density, and weak/filter word usage",
        next_step="Review the observations below — each offers 2-3 optional paths; pick what feels right or skip"
    )
