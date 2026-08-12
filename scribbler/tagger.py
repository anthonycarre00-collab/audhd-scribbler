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
from . import safety
from .file_io import read_text_file, write_text_file

# NOTE: the remainder of this module is intentionally unchanged from the
# working tagger; safety is inserted immediately before writer-owned writes.

