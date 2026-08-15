"""Console-free Windows launcher for the established Audhd Scribbler workspace."""
from pathlib import Path
import os, sys, traceback, ctypes, shutil, webbrowser
from http.server import ThreadingHTTPServer

APP_HOME = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Audhd Scribbler"
APP_HOME.mkdir(parents=True, exist_ok=True)
LOG_PATH = APP_HOME / "startup-error.log"
STATUS_PATH = APP_HOME / "startup-status.txt"


def clear_packaged_caches(root: Path):
    for p in root.rglob("__pycache__"):
        if p.is_dir(): shutil.rmtree(p, ignore_errors=True)
    for p in root.rglob("*.pyc"):
        try: p.unlink()
        except OSError: pass


def open_url(url: str):
    try:
        if webbrowser.open(url, new=1): return True
    except Exception: pass
    try:
        os.startfile(url); return True
    except Exception: return False


def main():
    root = Path(__file__).resolve().parent
    clear_packaged_caches(root)
    sys.path.insert(0, str(root))

    from scribbler import webapp
    from scribbler.release_ui import APP as RELEASE_APP
    from scribbler.release_runtime import prepare_backend, enhance_ui

    # The release layer is deliberately thin: existing tagging, analysis, database and
    # safety engines remain the source of truth. It only changes presentation, export
    # wiring and the frequency of expensive full-project snapshots.
    prepare_backend(webapp)
    webapp.APP = enhance_ui(RELEASE_APP)

    server = ThreadingHTTPServer(("127.0.0.1", 0), webapp.Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    STATUS_PATH.write_text(
        f"Scribbler started successfully.\nURL: {url}\nPID: {os.getpid()}\n",
        encoding="utf-8",
    )

    if not open_url(url):
        ctypes.windll.user32.MessageBoxW(
            0,
            "Scribbler is running, but Windows could not open your browser automatically.\n\n"
            f"Open this address manually:\n{url}\n\nStatus: {STATUS_PATH}",
            "The Audhd Scribbler",
            0x40,
        )

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
                "Scribbler could not start.\n\nThe startup log is here:\n" + str(LOG_PATH),
                "The Audhd Scribbler - startup error",
                0x10,
            )
        except Exception: pass
