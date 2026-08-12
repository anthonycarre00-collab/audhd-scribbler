"""Data-safety primitives for Scribbler.

The rule is simple: never make a meaningful change to writer-owned data
without first preserving the previous state. Backups stay local and are
created before tagging, analysis-result replacement, or future manuscript
editing.
"""
from datetime import datetime
from pathlib import Path
import shutil
import sqlite3

from .config import PROJECT_ROOT, DATA_DIR, DB_PATH

BACKUP_DIR = DATA_DIR / "backups"


def _stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]


def ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_database(reason="change"):
    """Create a consistent SQLite backup before changing metadata/results."""
    ensure_backup_dir()
    if not DB_PATH.exists():
        return None
    destination = BACKUP_DIR / f"scribbler-{_stamp()}-{reason}.db"
    source = sqlite3.connect(str(DB_PATH))
    target = sqlite3.connect(str(destination))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return destination


def backup_file(path, reason="change"):
    """Preserve a writer-owned text file before it is modified."""
    path = Path(path).resolve()
    if not path.exists():
        return None
    try:
        relative = path.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        raise ValueError("Cannot back up a file outside the Scribbler project")
    destination = BACKUP_DIR / "files" / relative
    destination = destination.parent / f"{destination.stem}-{_stamp()}{destination.suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    return destination


def project_snapshot(reason="manual"):
    """Create a lightweight safety snapshot of the database and all text files."""
    db_backup = backup_database(reason)
    file_count = 0
    root = PROJECT_ROOT
    for folder in ("raw-dumps", "triage", "chapters", "drafts", "final", "archive", "characters", "places", "themes", "research"):
        directory = root / folder
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".txt", ".md", ".text"}:
                backup_file(path, reason)
                file_count += 1
    return {"database": str(db_backup) if db_backup else None, "files": file_count, "timestamp": datetime.now().isoformat()}
