"""Console-free Windows launcher for the unified Audhd Scribbler workspace."""
from pathlib import Path
import os, sys, traceback, ctypes

APP_HOME = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Audhd Scribbler"
APP_HOME.mkdir(parents=True, exist_ok=True)
LOG_PATH = APP_HOME / "startup-error.log"


def main():
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))
    from scribbler import webapp
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
        raise
