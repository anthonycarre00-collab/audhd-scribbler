"""Deterministic, genre-neutral analysis tools for Scribbler.

These tools flag evidence and patterns; they do not grade writing or rewrite it.
AI interpretation remains optional and provider-agnostic.
"""
from __future__ import annotations
import re
from collections import Counter
from statistics import mean, pstdev


def words(text): return re.findall(r"\b[\w’'-]+\b", text, re