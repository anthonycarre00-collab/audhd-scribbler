#!/usr/bin/env bash
# The Audhd Scribbler — CLI entry point
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
fi
cd "$SCRIPT_DIR"
python -m scribbler.cli "$@"
