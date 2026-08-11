#!/usr/bin/env python3
"""File reading utilities for The Audhd Scribbler.

Handles the messy reality of text file encodings on Windows + Mac.
Tries UTF-8 first, then falls back to Windows-1252 (cp1252), Latin-1, UTF-16.
"""
from pathlib import Path
from typing import Optional


def read_text_file(path: Path or str) -> str:
    """Read a text file with automatic encoding detection.

    Tries encodings in order:
    1. UTF-8 (modern standard, what most apps use)
    2. UTF-8 with BOM (some Windows apps add a byte-order mark)
    3. Windows-1252 / cp1252 (Windows default, has smart quotes like 0x93, 0x94)
    4. Latin-1 / iso-8859-1 (never fails, but may misread some chars)
    5. UTF-16 (some Windows apps save as this)

    Args:
        path: Path to the file

    Returns:
        The file contents as a string.

    Raises:
        FileNotFoundError if the file doesn't exist.
        UnicodeDecodeError only if ALL encodings fail (very rare).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Read raw bytes once
    raw_bytes = path.read_bytes()

    # If file is empty, return empty string
    if not raw_bytes:
        return ""

    # Try each encoding in order
    encodings_to_try = [
        "utf-8",              # Modern standard
        "utf-8-sig",          # UTF-8 with BOM (byte-order mark)
        "cp1252",             # Windows-1252 (smart quotes, em-dashes)
        "iso-8859-1",         # Latin-1 (never fails on any byte)
        "utf-16",             # UTF-16 (some Windows apps)
        "utf-16-le",         # UTF-16 little-endian
        "utf-16-be",         # UTF-16 big-endian
    ]

    for encoding in encodings_to_try:
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    # If all else fails, read with errors='replace' (won't crash, but may show ?)
    return raw_bytes.decode("utf-8", errors="replace")


def write_text_file(path: Path or str, content: str, encoding: str = "utf-8"):
    """Write text to a file, always as UTF-8 (the modern standard).

    Args:
        path: Path to write to
        content: Text content to write
        encoding: Encoding to use (default utf-8)
    """
    path = Path(path)
    path.write_text(content, encoding=encoding)
