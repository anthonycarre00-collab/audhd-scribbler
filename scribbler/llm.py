#!/usr/bin/env python3
"""LLM interface for The Audhd Scribbler.

Uses Z.ai API (GLM-4-Plus) via the openai-compatible endpoint.
Requires API key in settings.json (set via menu option 12 - Settings).
"""
import json
import os
import shutil
import subprocess
import sys
from typing import Optional

from . import settings


def _try_openai_package(prompt: str, system: str = None) -> Optional[str]:
    """Use the openai Python package with Z.ai API key from settings."""
    api_key = settings.get_api_key()
    if not api_key:
        return None

    try:
        from openai import OpenAI
    except ImportError:
        # Try to install it
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "openai", "--quiet"],
                         capture_output=True, timeout=60)
            from openai import OpenAI
        except Exception:
            return None

    base_url = settings.get_setting("zai_base_url", "https://api.z.ai/api/paas/v4")
    model = settings.get_setting("zai_model", "glm-4-plus")

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=4000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [LLM Error] {e}", file=sys.stderr)
        return None


def _try_zai_cli(prompt: str, system: str = None) -> Optional[str]:
    """Fallback: try z-ai CLI via subprocess (works in some environments)."""
    if not shutil.which("z-ai"):
        return None
    try:
        cmd = ["z-ai", "chat", "-p", prompt]
        if system:
            cmd.extend(["-s", system])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        # Try to parse JSON response
        try:
            data = json.loads(output)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except json.JSONDecodeError:
            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    except json.JSONDecodeError:
                        continue
            lines = [l for l in output.split("\n") if not l.startswith("🚀") and not l.startswith("✅")]
            return "\n".join(lines).strip() or None
    except Exception:
        return None


def llm_complete(prompt: str, system: str = None, max_retries: int = 2) -> Optional[str]:
    """Call the LLM. Returns None if all methods fail.

    Priority:
    1. Z.ai API via openai package (requires API key in settings)
    2. z-ai CLI fallback (if installed)
    """
    # Try API first (if key configured)
    if settings.has_api_key():
        for attempt in range(max_retries):
            result = _try_openai_package(prompt, system)
            if result and len(result) > 5:
                return result
        return None

    # Fallback to CLI
    result = _try_zai_cli(prompt, system)
    if result and len(result) > 5:
        return result

    return None


def llm_available() -> bool:
    """Check if any LLM method is available."""
    return settings.has_api_key() or shutil.which("z-ai") is not None


def llm_status() -> str:
    """Return human-readable status of LLM availability."""
    if settings.has_api_key():
        model = settings.get_setting("zai_model", "glm-4-plus")
        return f"Connected to Z.ai ({model}) via API key"
    elif shutil.which("z-ai"):
        return "Connected via z-ai CLI"
    else:
        return "Not configured — using rule-based detection only. Set API key in Settings (menu option 12)."


def llm_json(prompt: str, system: str = None) -> Optional[dict]:
    """Call LLM and parse JSON response. Returns None on failure."""
    full_prompt = prompt + "\n\nRespond with valid JSON only. No markdown, no code fences, no extra text."
    result = llm_complete(full_prompt, system)
    if not result:
        return None
    result = result.strip()
    if result.startswith("```"):
        lines = result.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        result = "\n".join(lines)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{[\s\S]*\}', result)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None
