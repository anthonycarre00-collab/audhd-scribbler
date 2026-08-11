#!/usr/bin/env python3
"""LLM interface for The Audhd Scribbler.

Supports multiple AI providers — pick whichever you have access to:
- Google Gemini (FREE — recommended, generous free tier)
- Groq (FREE — very fast, llama models)
- Ollama (LOCAL — completely free, runs on your machine)
- Z.ai (requires credits)
"""
import json
import os
import shutil
import subprocess
import sys
from typing import Optional

from . import settings


def _try_openai_package(prompt: str, system: str = None) -> Optional[str]:
    """Use the openai Python package with the configured provider."""
    # Ollama doesn't need an API key
    provider = settings.get_provider()
    if provider != "ollama":
        api_key = settings.get_api_key()
        if not api_key:
            return None
    else:
        api_key = "ollama"  # Ollama accepts any non-empty string

    try:
        from openai import OpenAI
    except ImportError:
        # Try to install it
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "openai", "--quiet"],
                         capture_output=True, timeout=60)
            from openai import OpenAI
        except Exception as e:
            print(f"  [LLM Error] Could not install openai package: {e}", file=sys.stderr)
            return None

    base_url = settings.get_base_url()
    model = settings.get_model()

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


def _find_zai_cli() -> Optional[str]:
    """Find the z-ai CLI executable, handling Windows PATH issues."""
    # First try: is it in PATH?
    path = shutil.which("z-ai")
    if path:
        return path

    # On Windows: npm installs global packages to a specific folder
    # that might not be in PATH yet (if the parent shell was started before npm install)
    if sys.platform == "win32":
        # Common npm global locations on Windows
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            win_path = os.path.join(appdata, "npm", "z-ai.cmd")
            if os.path.exists(win_path):
                return win_path

        # Try user profile
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            win_path = os.path.join(userprofile, "AppData", "Roaming", "npm", "z-ai.cmd")
            if os.path.exists(win_path):
                return win_path

    # On Mac/Linux: npm global is usually in /usr/local/bin or ~/.npm-global/bin
    else:
        for candidate in ["/usr/local/bin/z-ai", "/usr/bin/z-ai", os.path.expanduser("~/.local/bin/z-ai")]:
            if os.path.exists(candidate):
                return candidate

    return None


def _try_zai_cli(prompt: str, system: str = None) -> Optional[str]:
    """Use the z-ai CLI (free, no API key needed)."""
    zai_path = _find_zai_cli()
    if not zai_path:
        return None
    try:
        cmd = [zai_path, "chat", "-p", prompt]
        if system:
            cmd.extend(["-s", system])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if result.returncode != 0:
            return None

        output = result.stdout.strip()

        # The z-ai CLI outputs status lines (🚀, ✅) followed by a JSON block
        # Strategy: find the first '{' and try to parse from there to the matching '}'
        json_start = output.find('{')
        if json_start == -1:
            # No JSON found, return cleaned text
            lines = [l for l in output.split("\n") if not l.startswith("🚀") and not l.startswith("✅")]
            return "\n".join(lines).strip() or None

        # Try to parse the JSON starting from json_start
        # The JSON might be multi-line, so we need to find the matching closing brace
        json_text = output[json_start:]
        try:
            data = json.loads(json_text)
            return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except json.JSONDecodeError:
            # The JSON might have trailing text. Try to find the matching brace
            depth = 0
            in_string = False
            escape_next = False
            end_pos = 0
            for i, char in enumerate(json_text):
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break
            if end_pos > 0:
                try:
                    data = json.loads(json_text[:end_pos])
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                except json.JSONDecodeError:
                    pass

            # Last resort: return cleaned text
            lines = [l for l in output.split("\n") if not l.startswith("🚀") and not l.startswith("✅")]
            return "\n".join(lines).strip() or None

    except Exception:
        return None


def llm_complete(prompt: str, system: str = None, max_retries: int = 2) -> Optional[str]:
    """Call the LLM. Returns None if all methods fail.

    Priority:
    1. If provider is 'zai_cli': use the z-ai CLI (free, no key needed)
    2. If provider is 'ollama': use openai package with local endpoint
    3. Otherwise: use openai package with configured API key
    4. Fallback: z-ai CLI if available
    """
    provider = settings.get_provider()

    # z-ai CLI provider: uses the CLI directly (no API key, no credits)
    if provider == "zai_cli":
        for attempt in range(max_retries):
            result = _try_zai_cli(prompt, system)
            if result and len(result) > 5:
                return result
        return None

    # Other providers: use openai package
    if settings.has_api_key():
        for attempt in range(max_retries):
            result = _try_openai_package(prompt, system)
            if result and len(result) > 5:
                return result

    # Last-resort fallback: z-ai CLI if installed
    result = _try_zai_cli(prompt, system)
    if result and len(result) > 5:
        return result

    return None


def llm_available() -> bool:
    """Check if any LLM method is available."""
    if settings.has_api_key():
        return True
    return _find_zai_cli() is not None


def llm_status() -> str:
    """Return human-readable status of LLM availability."""
    provider = settings.get_provider()
    config = settings.get_provider_config(provider)
    provider_name = config.get("name", provider)

    if provider == "zai_cli":
        zai_path = _find_zai_cli()
        if zai_path:
            return f"Connected via Z.ai CLI (free, no API key needed)"
        else:
            return f"Z.ai CLI not installed. Run: npm install -g z-ai-web-dev-sdk"
    elif provider == "ollama":
        # Check if Ollama is running
        try:
            import urllib.request
            urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
            return f"Connected to Ollama (local, {config.get('model', 'llama3.2')})"
        except Exception:
            return f"Ollama selected but not running. Start it with: ollama serve"
    elif settings.has_api_key():
        model = settings.get_model()
        return f"Connected to {provider_name} ({model})"
    elif _find_zai_cli():
        return f"Connected via z-ai CLI (no provider configured)"
    else:
        return f"Not configured — pick a provider in Settings (menu option 13)"


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
