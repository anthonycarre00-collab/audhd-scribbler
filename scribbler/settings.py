#!/usr/bin/env python3
"""Settings management for The Audhd Scribbler.

Stores user settings in settings.json (gitignored).
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict

from .config import PROJECT_ROOT

SETTINGS_PATH = PROJECT_ROOT / "settings.json"

DEFAULT_SETTINGS = {
    "zai_api_key": "",
    "zai_base_url": "https://api.z.ai/api/paas/v4",
    "zai_model": "glm-4-plus",
    "git_auto_commit": False,
    "git_remote": "",
    "theme": "calm-blue",
    "stale_nudge_days": 7,
}


def load_settings() -> Dict:
    """Load settings from settings.json, creating with defaults if missing."""
    if not SETTINGS_PATH.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            settings = json.load(f)
        # Merge with defaults to handle new keys
        merged = DEFAULT_SETTINGS.copy()
        merged.update(settings)
        return merged
    except (json.JSONDecodeError, IOError):
        return DEFAULT_SETTINGS.copy()


def save_settings(settings: Dict):
    """Save settings to settings.json."""
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)


def get_setting(key: str, default=None):
    """Get a single setting value."""
    settings = load_settings()
    return settings.get(key, default)


def set_setting(key: str, value):
    """Set a single setting value and save."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)


def has_api_key() -> bool:
    """Check if a Z.ai API key is configured."""
    key = get_setting("zai_api_key", "")
    return bool(key and len(key) > 10)


def get_api_key() -> Optional[str]:
    """Get the Z.ai API key."""
    key = get_setting("zai_api_key", "")
    return key if key and len(key) > 10 else None
