#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo "  ============================================================
              THE AUDHD SCRIBLER - INSTALLER
        Your memoir's calm companion. One click. Done.
  ============================================================
"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "  [ERROR] Python 3 is not installed."
    echo ""
    echo "  Please install Python 3.8 or newer:"
    echo ""
    echo "    Option A: Download from https://www.python.org/downloads/"
    echo "    Option B: If you have Homebrew:  brew install python3"
    echo ""
    echo "  Then re-run this script."
    echo ""
    read -p "  Press Enter to close..."
    exit 1
fi

PYVER=$(python3 --version 2>&1)
echo "  [OK] Found $PYVER"

# Check pip
if ! python3 -m pip --version &> /dev/null; then
    echo "  [ERROR] pip is not available."
    echo "  Try: python3 -m ensurepip --upgrade"
    read -p "  Press Enter to close..."
    exit 1
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "  Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "  [ERROR] Failed to create virtual environment."
        read -p "  Press Enter to close..."
        exit 1
    fi
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
echo "  Updating pip..."
python -m pip install --upgrade pip --quiet

# Install dependencies
echo "  Installing dependencies (this takes 2-3 minutes)..."
pip install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "  [WARNING] Retrying dependency install..."
    pip install -r requirements.txt
fi

# Install the package
echo "  Installing scribbler..."
pip install -e . --quiet

# Download spaCy model
echo "  Downloading language model (this takes a minute)..."
python -m spacy download en_core_web_sm --quiet
if [ $? -ne 0 ]; then
    echo "  [WARNING] Language model download skipped. Character detection will use fallback."
fi

# Initialize project
echo "  Setting up folders..."
python -m scribbler.cli init

echo ""
echo "  ============================================================
                    INSTALLATION COMPLETE!
  ============================================================
"
echo "  Your tool is ready. To use it:"
echo ""
echo "    1. Drop text files (.txt or .md) into the 'raw-dumps' folder"
echo "       (brain dumps, voice memos, freewrites — anything goes)"
echo ""
echo "    2. Double-click 'SCRIBBLER-Mac.command' to open the menu"
echo ""
echo "    3. Pick option 1 to tag your files"
echo ""
echo "    4. Pick option 2 to see your dashboard"
echo ""
echo "  That's it. No console needed."
echo ""
read -p "  Press Enter to close..."
