"""Project safety primitives: snapshots, protected writes and portable backups."""
from __future__ import annotations
import json, shutil, sqlite3, zipfile
from datetime import datetime
from pathlib import Path
from .config import PROJECT_ROOT, DB_PATH

SNAPSHOT_ROOT = PROJECT_ROOT / "backups"
WRITER_FOLDERS = ("raw-dumps", "triage", "chapters", "drafts", "final", "archive", "characters", "places", "themes", "research")

def _stamp(): return datetime.now().strftime("%Y%m%d-%H%M%S-%f")

def create_snapshot(reason="manual save"):
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    target = SNAPSHOT_ROOT / _stamp(); target.mkdir(parents=True, exist_ok=False)
    for name in WRITER_FOLDERS:
        src = PROJECT_ROOT / name
        if src.exists(): shutil.copytree(src, target / name, dirs_exist_ok=True)
    if DB_PATH.exists():
        dest = target / "scribbler.db"
        src_conn = sqlite3.connect(str(DB_PATH)); dst_conn = sqlite3.connect(str(dest))
        try: src_conn.backup(dst_conn)
        finally: dst_conn.close(); src_conn.close()
    (target / "manifest.json").write_text(json.dumps({"created": datetime.now().isoformat(timespec="seconds"), "reason": reason}, indent=2), encoding="utf-8")
    return target

def backup_database(reason="database change"):
    """Compatibility API used by the database layer; preserves the full project state."""
    return create_snapshot(reason)

def snapshot_before_file_change(path, reason="file change"):
    path = Path(path).resolve()
    try: path.relative_to(PROJECT_ROOT.resolve())
    except ValueError: raise ValueError("Cannot protect a file outside the Scribbler project")
    return create_snapshot(f"{reason}: {path.name}")

def recent_snapshots(limit=10):
    if not SNAPSHOT_ROOT.exists(): return []
    return sorted((p for p in SNAPSHOT_ROOT.iterdir() if p.is_dir()), reverse=True)[:limit]

def unique_output_path(path):
    path = Path(path)
    if not path.exists(): return path
    for i in range(2, 10000):
        candidate = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not candidate.exists(): return candidate
    raise RuntimeError("Could not find a safe non-overwriting export filename")

def export_project_zip(output_path=None):
    if output_path is None: output_path = PROJECT_ROOT.parent / f"Scribbler-Backup-{datetime.now().strftime('%Y-%m-%d-%H%M')}.zip"
    output = unique_output_path(output_path); output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in WRITER_FOLDERS:
            root = PROJECT_ROOT / name
            if root.exists():
                for file in root.rglob("*"):
                    if file.is_file(): zf.write(file, file.relative_to(PROJECT_ROOT).as_posix())
        if DB_PATH.exists(): zf.write(DB_PATH, "data/scribbler.db")
        zf.writestr("project-manifest.json", json.dumps({"created": datetime.now().isoformat(timespec="seconds"), "format": "Audhd Scribbler portable project backup v1", "project": PROJECT_ROOT.name}, indent=2))
    return str(output)
