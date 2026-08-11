#!/usr/bin/env python3
"""Settings management for The Audhd Scribbler.

Stores user settings in settings.json (gitignored).
Supports multiple AI providers — including FREE ones (Gemini, Groq, Ollama).
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict

from .config import PROJECT_ROOT

SETTINGS_PATH = PROJECT_ROOT / "settings.json"

# Multi-provider support — pick whichever you have access to
# z-ai CLI is the recommended option: same AI you're chatting with, no API key needed
PROVIDERS = {
    "zai_cli": {
        "name": "Z.ai CLI (FREE — the AI you're chatting with, no API key needed)",
        "base_url": "",  # Uses the z-ai CLI, not the API
        "model": "glm-4-plus",
        "free": True,
        "get_key_url": "https://nodejs.org",
        "get_key_instructions": "The z-ai CLI uses the same AI you're chatting with right now.\nNo API key needed. No credits. No payment.\n\nTo install:\n1. Install Node.js from https://nodejs.org (if you don't have it)\n2. The installer will automatically run: npm install -g z-ai-web-dev-sdk\n3. That's it. The tool will use z-ai automatically.",
    },
    "gemini": {
        "name": "Google Gemini (FREE — needs API key)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-2.0-flash",
        "free": True,
        "get_key_url": "https://aistudio.google.com/app/apikey",
        "get_key_instructions": "1. Go to https://aistudio.google.com/app/apikey\n2. Sign in with Google\n3. Click 'Create API key'\n4. Copy the key (starts with 'AIza...')\n5. Paste it below\n\nNo credit card needed. Free tier: 15 requests/min, 1500/day.",
    },
    "groq": {
        "name": "Groq (FREE — very fast, needs API key)",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "free": True,
        "get_key_url": "https://console.groq.com/keys",
        "get_key_instructions": "1. Go to https://console.groq.com/keys\n2. Sign up (Google or GitHub login)\n3. Click 'Create API Key'\n4. Copy the key\n5. Paste it below\n\nNo credit card needed. Free tier: 30 requests/min, 14400/day.",
    },
    "ollama": {
        "name": "Ollama (LOCAL — completely free, runs on your machine)",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "free": True,
        "get_key_url": "https://ollama.com",
        "get_key_instructions": "1. Download Ollama from https://ollama.com\n2. Install it\n3. Open a terminal and run: ollama pull llama3.2\n4. Ollama runs locally — no API key needed!\n5. Just select Ollama as your provider below\n\nYour text never leaves your machine. Completely free, no limits.",
    },
    "zai": {
        "name": "Z.ai API (requires credits — NOT recommended)",
        "base_url": "https://api.z.ai/api/paas/v4",
        "model": "glm-4-plus",
        "free": False,
        "get_key_url": "https://z.ai",
        "get_key_instructions": "1. Go to https://z.ai\n2. Sign up and add credits\n3. Get an API key\n4. Paste it below\n\nNOTE: Z.ai API requires payment. Use the Z.ai CLI option instead — it's free.",
    },
}

DEFAULT_SETTINGS = {
    "provider": "zai_cli",  # Default to z-ai CLI (free, no key needed)
    "api_key": "",
    "model": "",  # Empty = use provider default
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
    # Don't save the api_key if it's clearly invalid
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


def get_provider() -> str:
    """Get the current provider ID."""
    return get_setting("provider", "gemini")


def get_provider_config(provider_id: str = None) -> Dict:
    """Get the config for a provider."""
    if provider_id is None:
        provider_id = get_provider()
    return PROVIDERS.get(provider_id, PROVIDERS["gemini"])


def has_api_key() -> bool:
    """Check if an API key is configured (not needed for Ollama or z-ai CLI)."""
    provider = get_provider()
    if provider in ("ollama", "zai_cli"):
        return True  # These don't need an API key
    key = get_setting("api_key", "")
    return bool(key and len(key) > 10)


def get_api_key() -> Optional[str]:
    """Get the API key."""
    key = get_setting("api_key", "")
    return key if key and len(key) > 10 else None


def get_base_url() -> str:
    """Get the base URL for the current provider."""
    config = get_provider_config()
    return config.get("base_url", "")


def get_model() -> str:
    """Get the model to use (custom or provider default)."""
    custom = get_setting("model", "")
    if custom:
        return custom
    config = get_provider_config()
    return config.get("model", "gemini-2.0-flash")
