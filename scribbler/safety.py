"""Data-safety primitives for Scribbler.

Never make a meaningful change to writer-owned data without first preserving
its previous state. Backups stay local and are created before tagging,
analysis-result replacement, or future manuscript editing.
"""
from datetime import datetime
from pathlib import Path
import json
import shutil
import sqlite3
import zipfile

from .config import PROJECT_ROOT, DATA_DIR, DB_PATH

BACKUP_DIR = DATA_DIR / "backups"
WRITER_FOLDERS = ("raw-dumps", "triage", "chapters", "drafts", "final", "archive", "characters", "places", "themes", "research")


def _stamp():
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]


def ensure_backup_dir():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def backup_database(reason="change"):
    ensure_backup_dir()
    if not DB_PATH.exists(): return None
    destination = BACKUP_DIR / f"scribbler-{_stamp()}-{reason}.db"
    source = sqlite3.connect(str(DB_PATH)); target = sqlite3.connect(str(destination))
    try: source.backup(target)
    finally: target.close(); source.close()
    return destination


def backup_file(path, reason="change"):
    path = Path(path).resolve()
    if not path.exists(): return None
    try: relative = path.relative_to(PROJECT_ROOT.resolve())
    except ValueError: raise ValueError("Cannot back up a file outside the Scribbler project")
    destination = BACKUP_DIR / "files" / relative
    destination = destination.parent / f"{destination.stem}-{_stamp()}{destination.suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    return destination


def project_snapshot(reason="manual"):
    """Preserve the database and all writer-owned text before a risky operation."""
    db_backup = backup_database(reason); file_count = 0
    for folder in WRITER_FOLDERS:
        directory = PROJECT_ROOT / folder
        if not directory.exists(): continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".txt", ".md", ".text"}:
                backup_file(path, reason); file_count += 1
    result = {"database": str(db_backup) if db_backup else None, "files": file_count, "timestamp": datetime.now().isoformat(timespec="seconds"), "reason": reason}
    manifest_dir = BACKUP_DIR / "manifests"; manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / f"{_stamp()}-{reason}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def recent_backups(limit=12):
    ensure_backup_dir(); return sorted(BACKUP_DIR.rglob("*.db"), reverse=True)[:limit]


def unique_output_path(path):
    """Never silently overwrite an export."""
    path = Path(path)
    if not path.exists(): return path
    for i in range(2, 10000):
        candidate = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not candidate.exists(): return candidate
    raise RuntimeError("Could not find a safe export filename")


def export_project_zip(output_path=None):
    """Create a portable backup without modifying project files."""
    if output_path is None:
        output_path = PROJECT_ROOT.parent / f"Scribbler-Backup-{datetime.now().strftime('%Y-%m-%d-%H%M')}.zip"
    output = unique_output_path(output_path); output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for folder in WRITER_FOLDERS:
            root = PROJECT_ROOT / folder
            if root.exists():
                for file in root.rglob("*"):
                    if file.is_file(): zf.write(file, file.relative_to(PROJECT_ROOT).as_posix())
        if DB_PATH.exists(): zf.write(DB_PATH, "data/scribbler.db")
        zf.writestr("project-manifest.json", json.dumps({"created": datetime.now().isoformat(timespec="seconds"), "format":"Audhd Scribbler portable backup v1"}, indent=2))
    return str(output)
