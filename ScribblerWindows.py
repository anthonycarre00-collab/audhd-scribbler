"""Silent Windows launcher for the Audhd Scribbler workspace."""
from pathlib import Path
import sys
import traceback
import webbrowser


def main():
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))

    from scribbler import db
    from scribbler.config import FOLDERS, DATA_DIR, DASHBOARD_DIR, PROJECT_ROOT
    from scribbler.dashboard import generate

    for folder in FOLDERS:
        (PROJECT_ROOT / folder).mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

    db.get_db().close()
    output = generate()
    webbrowser.open(Path(output).resolve().as_uri())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        root = Path(__file__).resolve().parent
        (root / "scribbler-launch-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "Scribbler could not open.\n\nA technical log was saved as scribbler-launch-error.log.", "The Audhd Scribbler", 0x10)
        except Exception:
            pass
