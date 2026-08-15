"""Release smoke test: prove the established application imports and serves."""
from __future__ import annotations
import os
import threading
import urllib.request
from http.server import ThreadingHTTPServer

os.environ["AUDHD_SCRIBBLER_NO_BROWSER"] = "1"

from scribbler import webapp  # noqa: E402
from scribbler import db, tagger, llm, safety  # noqa: E402
from scribbler.analyzers import craft, voice_tense, characters, continuity, themes, editor  # noqa: E402
from scribbler.writer_intelligence import cadence_rhythm, motif_scan, structural_anchors, voice_report  # noqa: E402


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), webapp.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urllib.request.urlopen(base + "/api/status", timeout=5) as response:
            assert response.status == 200
        with urllib.request.urlopen(base + "/api/tools", timeout=5) as response:
            assert response.status == 200
        print("SMOKE TEST PASSED: imports, database initialization and HTTP workspace startup are healthy.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
