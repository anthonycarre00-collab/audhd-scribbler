#!/usr/bin/env bash
# The Audhd Scribbler — one-command installer
# Usage: ./install.sh

set -e

echo ""
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║         The Audhd Scribbler — Installer          ║"
echo "  ║     Your memoir's calm companion. Low-shame.      ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "  ✗ Python 3 not found. Please install Python 3.8+ and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  ✓ Python $PYTHON_VERSION found"

# Create virtual environment
VENV_DIR="$(dirname "$0")/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "  → Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install
source "$VENV_DIR/bin/activate"

echo "  → Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r "$(dirname "$0")/requirements.txt" --quiet

# Install the package in development mode
echo "  → Installing scribbler CLI..."
pip install -e "$(dirname "$0")" --quiet

# Create the CLI entry point
BIN_DIR="$(dirname "$0")/bin"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/scribbler" << 'EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
python -m scribbler.cli "$@"
EOF
chmod +x "$BIN_DIR/scribbler"

# Initialize the project structure
echo "  → Creating folder structure..."
python -m scribbler.cli init

# Try to download spaCy model (optional, non-blocking)
echo "  → Installing spaCy language model (optional, may take a moment)..."
python -m spacy download en_core_web_sm --quiet 2>/dev/null || echo "    (spaCy model install skipped — character detection will use fallback)"

# Create convenience symlink in project root
ROOT_DIR="$(dirname "$0")"
if [ ! -f "$ROOT_DIR/scribbler" ]; then
    ln -s "$BIN_DIR/scribbler" "$ROOT_DIR/scribbler"
fi

echo ""
echo "  ╔═══════════════════════════════════════════════════╗"
echo "  ║                  INSTALLATION DONE                ║"
echo "  ╚═══════════════════════════════════════════════════╝"
echo ""
echo "  Quick start:"
echo ""
echo "    1. Drop text files into raw-dumps/"
echo "       (any .txt or .md file — brain dumps, voice memos, freewrites)"
echo ""
echo "    2. Tag them:"
echo "       ./scribbler label-all"
echo ""
echo "    3. See your project at a glance:"
echo "       ./scribbler dashboard"
echo ""
echo "    4. Get 3 things you could do next:"
echo "       ./scribbler next"
echo ""
echo "    5. Analyze a final-draft chapter:"
echo "       ./scribbler analyze chapters/my-chapter.md"
echo ""
echo "  Other commands:"
echo "    ./scribbler label <file>       Tag a single file"
echo "    ./scribbler analyze-all        Analyze all chapters"
echo "    ./scribbler market -d \"desc\"   Comp-title research"
echo "    ./scribbler links <file>       Show connected files"
echo "    ./scribbler stats              Project statistics"
echo "    ./scribbler export <file> -f docx   Export to Word"
echo ""
echo "  The tool is private. Your text stays on your machine."
echo "  LLM-assisted tagging uses Z.ai (the 'z-ai' CLI) if available."
echo "  Without it, rule-based tagging still works fully."
echo ""
echo "  Happy scribbling."
echo ""
