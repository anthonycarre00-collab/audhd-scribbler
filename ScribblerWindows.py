"""Silent Windows launcher for the Audhd Scribbler workspace."""
from pathlib import Path
import sys
import traceback
import webbrowser


def main():
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))

    from scribbler import db
    from scribbler.config import FOLDERS, DATA_DIR, DASHBOARD_DIR
    from scribbler.dashboard import generate

    for folder in FOLDERS:
        (root / folder).mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    # Generate a fresh local workspace, then open it in the user's browser.
    db.get_db().close()
    output = generate()
    webbrowser.open(Path(output).resolve().as_uri())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never expose a console window to the writer. Leave a useful local log.
        root = Path(__file__).resolve().parent
        (root / "scribbler-launch-error.log").write_text(traceback.format_exc(), encoding="utf-8")
