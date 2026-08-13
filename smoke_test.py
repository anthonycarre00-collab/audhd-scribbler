"""Release smoke test: prove the real application imports and serves before packaging."""
from __future__ import annotations
import os
import sys
import urllib.request

os.environ["AUDHD_SCRIBBLER_NO_BROWSER"] = "1"

from scribbler import webapp  # noqa: E402
from scribbler import db, tagger, llm, safety  # noqa: E402
from scribbler.analyzers import craft, voice_tense, characters, continuity, themes, editor  # noqa: E402
from scribbler.writer_intelligence import cadence_rhythm, motif_scan, structural_anchors, voice_report  # noqa: E402


def main():
    server = webapp.run_server(open_browser=False)
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/status"
        import threading
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"status endpoint returned HTTP {response.status}")
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/api/tools", timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"tools endpoint returned HTTP {response.status}")
        print("SMOKE TEST PASSED: imports, database initialization and HTTP workspace startup are healthy.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
