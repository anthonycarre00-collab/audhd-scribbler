"""Small desktop-only correctness patches kept outside the UI renderer."""
from __future__ import annotations
import json, re
from pathlib import Path
from . import safety, tagger, llm
from .config import PROJECT_ROOT


def install(Handler):
    """Patch the HTTP handler with correctness fixes that are easy to test in isolation."""
    original_import = Handler._import

    def safe_import(self):
        # The original multipart parser must preserve the destination field.
        ctype = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in ctype:
            raise ValueError("Invalid upload")
        match = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", ctype)
        if not match:
            raise ValueError("Upload boundary missing")
        boundary = (match.group(1) or match.group(2)).encode()
        body = self._body()
        files, destination = [], "raw-dumps"
        for part in body.split(b"--" + boundary):
            end = part.find(b"\r\n\r\n")
            if end < 0:
                continue
            headers = part[:end].decode("utf-8", errors="replace")
            content = part[end + 4:]
            if content.endswith(b"\r\n"):
                content = content[:-2]
            field = re.search(r'name="([^"]+)"', headers)
            if not field:
                continue
            name = field.group(1)
            if name == "destination":
                value = content.decode("utf-8", errors="replace").strip()
                if value in {"raw-dumps", "chapters", "drafts"}:
                    destination = value
                continue
            filename = re.search(r'filename="([^"]*)"', headers)
            if not filename:
                continue
            clean = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(filename.group(1)).name).strip(" .") or "untitled.txt"
            if Path(clean).suffix.lower() not in {".txt", ".md", ".text"}:
                continue
            files.append((clean, content))
        target = PROJECT_ROOT / destination
        target.mkdir(parents=True, exist_ok=True)
        safety.create_snapshot("before-import")
        saved=[]
        for filename, content in files:
            path = target / filename
            if path.exists():
                for i in range(2,10000):
                    candidate=target / f"{path.stem} ({i}){path.suffix}"
                    if not candidate.exists():
                        path=candidate; break
            path.write_bytes(content)
            saved.append(str(path.relative_to(PROJECT_ROOT)))
        return self._json({"ok":True,"saved":saved,"folder":destination,"message":f"Saved {len(saved)} file(s) to {destination}."})

    Handler._import = safe_import
    return Handler
