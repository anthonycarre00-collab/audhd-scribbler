#!/usr/bin/env python3
"""Emotional arc comparison.

Runs themes.analyze() on each selected chapter, extracts the smoothed
per-sentence valence curve, downsamples to a common length for visualization,
and returns a comparison payload suitable for an overlaid line chart.

Also computes per-chapter summary stats (shape, average, range, turning point)
and a brief interpretation of how the arcs differ.
"""
from typing import Dict, List, Any
from pathlib import Path
import re

from .analyzers import themes
from .file_io import read_text_file


def compare_arcs(file_paths: List[str], target_points: int = 50) -> Dict[str, Any]:
    """Compare the emotional arcs of 2+ chapters.

    Args:
        file_paths: List of paths to chapter files.
        target_points: Number of points to downsample each curve to (default 50).

    Returns:
        {
          "chapters": [
            {
              "filename": "...",
              "path": "...",
              "word_count": N,
              "sentence_count": N,
              "arc": { average, min, max, range, shape, shape_description },
              "curve": [valence, valence, ...],  # downsampled to target_points
              "turning_point": { sentence_index, valence, fraction },  # the biggest inflection
            }
          ],
          "target_points": N,
          "interpretation": "...",
          "differences": {
            "average_spread": float,  # max - min of chapter averages
            "shape_agreement": bool,  # True if all chapters share the same shape
            "shapes": ["rags_to_riches", "man_in_a_hole", ...],
          }
        }
    """
    if not file_paths or len(file_paths) < 2:
        return {"error": "Select at least 2 chapters to compare"}

    chapters = []
    for fp in file_paths:
        try:
            p = Path(fp)
            if not p.exists():
                continue
            text = read_text_file(p)
            # Strip YAML frontmatter
            if text.startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    text = text[end + 3:].strip()
            text = re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->', '', text).strip()

            # Run themes analysis to get the emotional arc
            result = themes.analyze(text)
            arc = result.get("emotional_arc", {})
            shape_info = result.get("arc_shape", {})

            smoothed = arc.get("smoothed", [])
            # Downsample to target_points for visualization
            curve = _downsample(smoothed, target_points)

            # Find the turning point (biggest single-sentence swing)
            turning_point = _find_turning_point(smoothed)

            chapters.append({
                "filename": p.name,
                "path": str(p.resolve()).replace("\\", "/"),
                "word_count": len(text.split()),
                "sentence_count": len(smoothed),
                "arc": {
                    "average": arc.get("average", 0),
                    "min": arc.get("min", 0),
                    "max": arc.get("max", 0),
                    "range": arc.get("range", 0),
                    "shape": shape_info.get("shape", "unknown"),
                    "shape_description": shape_info.get("description", ""),
                },
                "curve": curve,
                "turning_point": turning_point,
            })
        except Exception as e:
            chapters.append({
                "filename": Path(fp).name if fp else "unknown",
                "path": fp,
                "error": str(e),
            })

    if len(chapters) < 2:
        return {"error": "Need at least 2 readable chapters"}

    # Compute differences
    averages = [c["arc"]["average"] for c in chapters if "arc" in c]
    shapes = [c["arc"]["shape"] for c in chapters if "arc" in c]
    avg_spread = max(averages) - min(averages) if averages else 0
    shape_agreement = len(set(shapes)) == 1 if shapes else False

    interpretation = _build_interpretation(chapters, shapes, avg_spread, shape_agreement)

    return {
        "chapters": chapters,
        "target_points": target_points,
        "interpretation": interpretation,
        "differences": {
            "average_spread": round(avg_spread, 3),
            "shape_agreement": shape_agreement,
            "shapes": shapes,
        },
    }


def _downsample(curve: List[float], target_points: int) -> List[float]:
    """Downsample a curve to target_points by averaging windows.

    If the curve is shorter than target_points, pad with the last value.
    If it's empty, return a flat zero line.
    """
    if not curve:
        return [0.0] * target_points
    if len(curve) <= target_points:
        # Pad with last value
        return curve + [curve[-1]] * (target_points - len(curve))
    # Average windows
    out = []
    window_size = len(curve) / target_points
    for i in range(target_points):
        start = int(i * window_size)
        end = int((i + 1) * window_size)
        if end <= start:
            end = start + 1
        window = curve[start:end]
        out.append(round(sum(window) / len(window), 3))
    return out


def _find_turning_point(curve: List[float]) -> Dict:
    """Find the biggest single-step swing in the curve — the emotional turn."""
    if not curve or len(curve) < 2:
        return {"sentence_index": 0, "valence": 0, "fraction": 0}
    max_swing = 0
    max_idx = 0
    for i in range(1, len(curve)):
        swing = abs(curve[i] - curve[i - 1])
        if swing > max_swing:
            max_swing = swing
            max_idx = i
    return {
        "sentence_index": max_idx,
        "valence": curve[max_idx],
        "fraction": round(max_idx / len(curve), 3),
        "swing": round(max_swing, 3),
    }


def _build_interpretation(chapters: List[Dict], shapes: List[str],
                          avg_spread: float, shape_agreement: bool) -> str:
    """Build a plain-English interpretation of how the arcs differ."""
    if not chapters:
        return "No chapters to compare."

    parts = []

    if shape_agreement and shapes and shapes[0] != "unknown":
        parts.append(f"All {len(chapters)} chapters share the '{shapes[0]}' arc shape.")
    elif len(set(shapes)) > 1:
        shape_list = ", ".join(f"{c['filename']}={s}" for c, s in zip(chapters, shapes) if s != "unknown")
        parts.append(f"The chapters have different arc shapes ({shape_list}).")

    if avg_spread > 0.3:
        parts.append(f"Large spread in average valence ({avg_spread:.2f}) — the chapters sit at very different emotional baselines.")
    elif avg_spread > 0.1:
        parts.append(f"Moderate spread in average valence ({avg_spread:.2f}) — the chapters share a baseline but drift apart.")
    else:
        parts.append(f"Small spread in average valence ({avg_spread:.2f}) — the chapters sit at similar emotional baselines.")

    # Find the chapter with the biggest range
    ranged_chapters = [(c["filename"], c["arc"]["range"]) for c in chapters if "arc" in c]
    if ranged_chapters:
        ranged_chapters.sort(key=lambda x: x[1], reverse=True)
        biggest = ranged_chapters[0]
        if biggest[1] > 0.5:
            parts.append(f"{biggest[0]} has the widest emotional range ({biggest[1]:.2f}) — its valence swings the most.")

    return " ".join(parts)
