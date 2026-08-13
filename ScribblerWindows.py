"""Console-free Windows launcher for the unified Audhd Scribbler workspace."""
from pathlib import Path
import sys, traceback

def main():
    root=Path(__file__).resolve().parent
    sys.path.insert(0,str(root))
    from scribbler import webapp
    server=webapp.run_server(open_browser=True)
    try: server.serve_forever()
    finally: server.server_close()

if __name__=="__main__":
    try: main()
    except Exception:
        root=Path(__file__).resolve().parent
        (root/"scribbler-launch-error.log").write_text(traceback.format_exc(),encoding="utf-8")
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,"Scribbler could not open.\n\nA technical log was saved as scribbler-launch-error.log.","The Audhd Scribbler",0x10)
        except Exception: pass
