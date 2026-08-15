"""Console-free Windows launcher for the unified Audhd Scribbler workspace."""
from pathlib import Path
import os, sys, traceback, ctypes, shutil

APP_HOME = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Audhd Scribbler"
APP_HOME.mkdir(parents=True, exist_ok=True)
LOG_PATH = APP_HOME / "startup-error.log"


def clear_packaged_caches(root: Path):
    """Remove only disposable packaged Python caches; never touch project data."""
    for p in root.rglob("__pycache__"):
        if p.is_dir(): shutil.rmtree(p, ignore_errors=True)
    for p in root.rglob("*.pyc"):
        try: p.unlink()
        except OSError: pass


def main():
    root = Path(__file__).resolve().parent
    clear_packaged_caches(root)
    sys.path.insert(0, str(root))
    from scribbler import webapp
    from scribbler.release_ui import APP as RELEASE_APP
    # Keep the established backend/tagging/analyzer engines; replace only the
    # presentation shell so the installed build cannot fall back to an older UI.
    webapp.APP = RELEASE_APP
    server = webapp.run_server(open_browser=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        LOG_PATH.write_text(traceback.format_exc(), encoding="utf-8")
        try:
            ctypes.windll.user32.MessageBoxW(
                0,
                "Scribbler could not start.\n\nThe startup log is here:\n" + str(LOG_PATH) +
                "\n\nPlease send that log to support rather than guessing at the problem.",
                "The Audhd Scribbler - startup error",
                0x10,
            )
        except Exception:
            pass
