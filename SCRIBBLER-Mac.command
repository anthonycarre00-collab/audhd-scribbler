#!/bin/bash
cd "$(dirname "$0")"

# Check if installed
if [ ! -f ".venv/bin/activate" ]; then
    echo ""
    echo "  The Audhd Scribbler is not installed yet."
    echo ""
    echo "  Please double-click INSTALL-Mac.command first to install it."
    echo ""
    read -p "  Press Enter to close..."
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Launch the menu
python -m scribbler.menu

echo ""
read -p "  Press Enter to close..."
