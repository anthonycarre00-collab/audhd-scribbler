#!/usr/bin/env python3
"""LLM interface for The Audhd Scribbler.

Tries multiple methods to call the LLM (Z.ai):
1. z-ai CLI via subprocess (works in this environment)
2. openai Python package with SCRIBBLER_LLM_API_KEY env var (for user's local install)
3. Returns None if no LLM available (caller falls back to rule-based)
"""
import json
import os
import shutil
import subprocess
import sys
from typing import Optional


def _try_zai_cli(prompt: str, system: str = None) -> Optional[str]:
    """Try calling z-ai CLI via subprocess."""
    if not shutil.which("z-ai"):
        return None
    try:
        cmd = ["z-ai", "chat", "-p", prompt]
        if system:
            cmd.extend(["-s", system])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return None
        # z-ai outputs JSON; extract the content
        # Find the JSON block
        output = result.stdout.strip()
        # Try to parse as JSON
        try:
            data = json.loads(output)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except json.JSONDecodeError:
            # Sometimes z-ai prepends status lines; find the JSON
            for line in output.split("\n"):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    except json.JSONDecodeError:
                        continue
                    break
            # If all else fails, return the raw output minus known status lines
            lines = [l for l in output.split("\n") if not l.startswith("🚀") and not l.startswith("✅")]
            return "\n".join(lines).strip() or None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def _try_openai_package(prompt: str, system: str = None) -> Optional[str]:
    """Try using openai Python package with Z.ai endpoint."""
    api_key = os.environ.get("SCRIBBLER_LLM_API_KEY") or os.environ.get("ZAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        base_url = os.environ.get("SCRIBBLER_LLM_BASE_URL", "https://api.z.ai/api/paas/v4")
        client = OpenAI(api_key=api_key, base_url=base_url)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model="glm-4-plus",
            messages=messages,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def llm_complete(prompt: str, system: str = None, max_retries: int = 2) -> Optional[str]:
    """Call the LLM with fallback chain. Returns None if all methods fail."""
    # Try z-ai CLI first
    for attempt in range(max_retries):
        result = _try_zai_cli(prompt, system)
        if result and len(result) > 5:
            return result

    # Try openai package
    result = _try_openai_package(prompt, system)
    if result and len(result) > 5:
        return result

    return None


def llm_available() -> bool:
    """Check if any LLM method is available."""
    return shutil.which("z-ai") is not None or bool(os.environ.get("SCRIBBLER_LLM_API_KEY"))


def llm_json(prompt: str, system: str = None) -> Optional[dict]:
    """Call LLM and parse JSON response. Returns None on failure."""
    full_prompt = prompt + "\n\nRespond with valid JSON only. No markdown, no code fences, no extra text."
    result = llm_complete(full_prompt, system)
    if not result:
        return None
    # Strip markdown code fences if present
    result = result.strip()
    if result.startswith("```"):
        lines = result.split("\n")
        # Remove first and last line (fences)
        lines = [l for l in lines if not l.strip().startswith("```")]
        result = "\n".join(lines)
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        import re
        match = re.search(r'\{[\s\S]*\}', result)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return None
