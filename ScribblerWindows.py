"""Windows GUI-free launcher: initializes the local project and opens the workspace."""
from pathlib import Path
import webbrowser

from scribbler import db
from scribbler.config import FOLDERS, DATA_DIR, DASHBOARD_DIR
from scribbler.dashboard import generate


def main():
    for folder in FOLDERS:
        (Path(__file__).resolve().parent / folder).mkdir(exist_ok=True)
    DATA_DIR.mkdir(exist_ok=True)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    db.get_db().close()
    output = generate()
    webbrowser.open(Path(output).resolve().as_uri())


if __name__ == "__main__":
    main()
