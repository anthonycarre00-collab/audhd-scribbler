#!/usr/bin/env python3
"""Local interactive web application for The Audhd Scribbler.

The existing dashboard is intentionally static. This small localhost server
adds the actions a writer actually needs from the UI: import files, tag chosen
material, analyse chosen material, refresh the index, and see clear status.
No cloud service is involved; the server binds only to localhost.
"""
import html
import json
import mimetypes
import os
import re
import threading
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import db, llm, tagger
from .config import PROJECT_ROOT, DASHBOARD_DIR, FOLDERS
from .file_io import read_text_file
from .dashboard import generate
from .analyzers import craft, voice_tense, characters, continuity, themes, editor

ALLOWED_UPLOAD_FOLDERS = {"raw-dumps", "triage", "chapters", "drafts", "final"}
ANALYZERS = {
    "craft": craft.analyze,
    "voice": voice_tense.analyze,
    "characters": characters.analyze,
    "continuity": continuity.analyze,
    "themes": themes.analyze,
    "editor": editor.analyze,
}


def _safe_name(name):
    name = Path(str(name or "untitled.txt")).name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    if not name:
        name = "untitled.txt"
    if Path(name).suffix.lower() not in {".txt", ".md", ".text"}:
        name += ".txt"
    return name


def _unique_path(folder, filename):
    path = folder / filename
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    for i in range(2, 10000):
        candidate = folder / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Could not create a unique filename")


def _find_file(file_path):
    raw = str(file_path or "")
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError:
        raise ValueError("File is outside the Scribbler project")
    if not path.exists() or path.suffix.lower() not in {".txt", ".md", ".text"}:
        raise ValueError("Writing file not found")
    return path


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _api_files():
    files = []
    for item in db.get_all_files():
        files.append({
            "path": item.get("path"), "filename": item.get("filename"),
            "folder": item.get("folder"), "word_count": item.get("word_count", 0),
            "status": item.get("status", "seedling"), "characters": item.get("characters") or [],
            "places": item.get("places") or [], "themes": item.get("themes") or [],
            "era": item.get("era") or "", "last_analyzed": item.get("last_analyzed") or "",
        })
    return files


def _analyze_file(path, selected_tools):
    text = read_text_file(path)
    if text.startswith("---"):
        match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.S)
        if match:
            text = text[match.end():]
    text = re.sub(r"<!-- SCRIBBLER SUMMARY[\s\S]*?-->", "", text).strip()
    if len(text.split()) < 10:
        raise ValueError(f"{path.name} is too short for meaningful analysis")
    results = {}
    all_files = db.get_all_files()
    for tool in selected_tools:
        fn = ANALYZERS.get(tool)
        if not fn:
            continue
        if tool == "characters":
            result = fn(text, all_files=all_files)
            db_key = "characters"
        elif tool == "voice":
            result = fn(text)
            db_key = "voice_tense"
        else:
            result = fn(text)
            db_key = tool
        result = _json_safe(result)
        results[db_key] = result
        db.save_analysis(str(path.resolve()), db_key, result)
    return results


class ScribblerHandler(BaseHTTPRequestHandler):
    server_version = "AudhdScribbler/2.1"

    def log_message(self, fmt, *args):
        # Deliberately quiet: this is a desktop app, not a console application.
        return

    def _send_json(self, payload, status=HTTPStatus.OK):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_text(self, text, content_type="text/html; charset=utf-8", status=HTTPStatus.OK):
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 50 * 1024 * 1024:
            raise ValueError("Upload is larger than the 50 MB limit")
        return self.rfile.read(length)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/files":
            return self._send_json({"files": _api_files(), "llm": llm.llm_status()})
        if parsed.path == "/api/status":
            return self._send_json({"llm": llm.llm_status(), "llm_available": llm.llm_available(), "project": str(PROJECT_ROOT)})
        if parsed.path == "/":
            path = DASHBOARD_DIR / "dashboard.html"
        else:
            rel = urllib.parse.unquote(parsed.path.lstrip("/"))
            if ".." in Path(rel).parts:
                return self._send_text("Not found", status=HTTPStatus.NOT_FOUND)
            path = DASHBOARD_DIR / rel
        if not path.exists() or not path.is_file():
            return self._send_text("Scribbler page not found. Return to the Home page and refresh.", status=HTTPStatus.NOT_FOUND)
        data = path.read_bytes()
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if ctype == "text/html":
            text = data.decode("utf-8", errors="replace")
            text = inject_controls(text)
            return self._send_text(text)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        try:
            if self.path == "/api/upload":
                return self._upload()
            if self.path == "/api/tag":
                return self._tag()
            if self.path == "/api/analyze":
                return self._analyze()
            if self.path == "/api/refresh":
                generate()
                return self._send_json({"ok": True})
            if self.path == "/api/open-folder":
                body = json.loads(self._body() or b"{}")
                folder = body.get("folder", "raw-dumps")
                if folder not in FOLDERS:
                    raise ValueError("Unknown folder")
                os.startfile(str(PROJECT_ROOT / folder))
                return self._send_json({"ok": True})
            return self._send_json({"ok": False, "error": "Unknown action"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def _upload(self):
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("Upload must use multipart/form-data")
        boundary_match = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", content_type)
        if not boundary_match:
            raise ValueError("Upload boundary missing")
        boundary = (boundary_match.group(1) or boundary_match.group(2)).encode()
        body = self._body()
        marker = b"--" + boundary
        uploaded = []
        for part in body.split(marker):
            if b"Content-Disposition:" not in part:
                continue
            header_end = part.find(b"\r\n\r\n")
            if header_end < 0:
                continue
            headers = part[:header_end].decode("utf-8", errors="replace")
            content = part[header_end + 4:]
            if content.endswith(b"\r\n"):
                content = content[:-2]
            name_match = re.search(r'filename="([^"]*)"', headers)
            if not name_match:
                continue
            filename = _safe_name(name_match.group(1))
            if Path(filename).suffix.lower() not in {".txt", ".md", ".text"}:
                continue
            folder_match = re.search(r'name="folder"', headers)
            # Folder field is handled separately below; default is raw-dumps.
            uploaded.append((filename, content))
        # The destination is intentionally conservative: uploads are raw material.
        folder = "raw-dumps"
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if query.get("folder") and query["folder"][0] in ALLOWED_UPLOAD_FOLDERS:
            folder = query["folder"][0]
        target = PROJECT_ROOT / folder
        target.mkdir(parents=True, exist_ok=True)
        saved = []
        for filename, content in uploaded:
            path = _unique_path(target, filename)
            path.write_bytes(content)
            saved.append(str(path.relative_to(PROJECT_ROOT)))
        generate()
        return self._send_json({"ok": True, "saved": saved, "message": f"Imported {len(saved)} file(s) into {folder}."})

    def _tag(self):
        body = json.loads(self._body() or b"{}")
        paths = body.get("paths") or []
        if not paths:
            raise ValueError("Choose at least one piece of writing")
        use_llm = bool(body.get("use_llm", True)) and llm.llm_available()
        tagged = []
        errors = []
        for raw in paths:
            try:
                path = _find_file(raw)
                meta = tagger.tag_file(str(path), use_llm=use_llm)
                tagged.append({"filename": path.name, "word_count": meta.get("word_count", 0), "status": meta.get("status", "seedling"), "characters": meta.get("characters", []), "themes": meta.get("themes", [])})
            except Exception as exc:
                errors.append({"file": str(raw), "error": str(exc)})
        generate()
        return self._send_json({"ok": True, "tagged": tagged, "errors": errors, "used_llm": use_llm})

    def _analyze(self):
        body = json.loads(self._body() or b"{}")
        paths = body.get("paths") or []
        tools = [x for x in (body.get("tools") or list(ANALYZERS)) if x in ANALYZERS]
        if not paths:
            raise ValueError("Choose at least one piece of writing")
        if not tools:
            raise ValueError("Choose at least one analysis tool")
        results = []
        errors = []
        for raw in paths:
            try:
                path = _find_file(raw)
                results.append({"filename": path.name, "path": str(path), "results": _analyze_file(path, tools)})
            except Exception as exc:
                errors.append({"file": str(raw), "error": str(exc)})
        from .dashboard.analysis_view import generate_analysis_view
        generate_analysis_view()
        return self._send_json({"ok": True, "results": results, "errors": errors})


def inject_controls(page):
    """Add the functional desktop toolbar without rewriting the static design."""
    if "id=\"scribblerAppControls\"" in page:
        return page
    overlay = r'''<style>
#scribblerAppControls{position:sticky;top:0;z-index:9999;background:#252a2b;color:#fff;padding:10px 14px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font:13px 'Segoe UI',Arial,sans-serif;box-shadow:0 3px 18px rgba(0,0,0,.12)}#scribblerAppControls button,#scribblerAppControls label{border:1px solid rgba(255,255,255,.28);background:#394143;color:#fff;border-radius:7px;padding:8px 11px;cursor:pointer;font:inherit}#scribblerAppControls button:hover,#scribblerAppControls label:hover{background:#4b5557}#scribblerAppControls .primary{background:#476b70;border-color:#476b70}.s-status{margin-left:auto;opacity:.75;font-size:12px}.s-modal{position:fixed;inset:0;background:rgba(20,24,24,.55);z-index:10000;display:none;align-items:center;justify-content:center;padding:24px}.s-modal.open{display:flex}.s-dialog{background:#fbfaf7;color:#252a2b;width:min(900px,96vw);max-height:90vh;overflow:auto;border-radius:14px;padding:26px;box-shadow:0 20px 70px rgba(0,0,0,.25)}.s-dialog h2{font:700 27px Georgia,serif;margin:0 0 7px}.s-muted{color:#74766f;font-size:13px}.s-row{display:flex;gap:12px;align-items:center;padding:11px 4px;border-bottom:1px solid #ddd8ce}.s-row input{width:18px;height:18px}.s-tools{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:15px 0}.s-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:20px}.s-results pre{white-space:pre-wrap;background:#f0eee8;padding:12px;border-radius:8px;font:12px/1.5 Consolas,monospace}.s-good{padding:11px;background:#edf3ef;border-radius:8px;margin:8px 0}.s-help{line-height:1.7}.s-help strong{font-family:Georgia,serif;font-size:17px}@media(max-width:650px){.s-status{width:100%;margin-left:0}.s-tools{grid-template-columns:1fr}}
</style>
<div id="scribblerAppControls"><button class="primary" onclick="Scribbler.importFiles()">＋ Import writing</button><button onclick="Scribbler.tag()">Tag material</button><button onclick="Scribbler.analyze()">Analyse selected</button><button onclick="Scribbler.refresh()">↻ Refresh</button><button onclick="Scribbler.help()">How this works</button><span class="s-status" id="scribblerStatus">Ready</span></div>
<div class="s-modal" id="scribblerModal"><div class="s-dialog" id="scribblerDialog"></div></div>
<input id="scribblerUpload" type="file" multiple accept=".txt,.md,.text" style="display:none">
<script>
const Scribbler=(()=>{
 const modal=document.getElementById('scribblerModal'),dialog=document.getElementById('scribblerDialog'),status=document.getElementById('scribblerStatus');
 let files=[];
 const setStatus=x=>status.textContent=x;
 const esc=x=>String(x??'').replace(/[&<>\"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[m]));
 async function load(){const r=await fetch('/api/files');const j=await r.json();files=j.files||[];setStatus(j.llm||'Ready');return j}
 function open(html){dialog.innerHTML=html;modal.classList.add('open')}
 function close(){modal.classList.remove('open')}
 modal.addEventListener('click',e=>{if(e.target===modal)close()});
 function picker(title,action,tools=false){
   const rows=files.map((f,i)=>`<label class="s-row"><input type="checkbox" data-file="${esc(f.path)}"><span><strong>${esc(f.filename)}</strong><br><span class="s-muted">${f.word_count||0} words · ${esc(f.folder)} · ${esc(f.status)}</span></span></label>`).join('')||'<p class="s-muted">No writing is indexed yet. Import a .txt or .md file first.</p>';
   const toolBox=tools?`<div class="s-muted">Analysis tools to run</div><div class="s-tools">${[['craft','Craft & rhythm'],['voice','Voice & tense'],['characters','Characters'],['continuity','Continuity & timeline'],['themes','Themes & emotional arc'],['editor','Editor / memoir patterns']].map(([v,l])=>`<label><input type="checkbox" class="s-tool" value="${v}" checked> ${l}</label>`).join('')}</div>`:'';
   open(`<h2>${title}</h2><p class="s-muted">Choose exactly what you want to work on. Nothing is run until you press the button.</p><div style="display:flex;gap:8px;margin:12px 0"><button onclick="Scribbler.all(true)">Select all</button><button onclick="Scribbler.all(false)">Clear</button></div><div>${rows}</div>${toolBox}<div class="s-actions"><button onclick="Scribbler.close()">Cancel</button><button class="primary" onclick="${action}">Continue</button></div>`);
 }
 function selected(){return [...dialog.querySelectorAll('input[data-file]:checked')].map(x=>x.dataset.file)}
 async function importFiles(){const input=document.getElementById('scribblerUpload');input.value='';input.onchange=async()=>{if(!input.files.length)return;setStatus('Importing…');const fd=new FormData();[...input.files].forEach(f=>fd.append('files',f));const r=await fetch('/api/upload',{method:'POST',body:fd});const j=await r.json();if(!j.ok){alert(j.error);setStatus('Import failed');return}await load();setStatus(j.message);alert(j.message+'\n\nThe material is now in Scribble Inbox. Tag it when you are ready.')};input.click()}
 async function tag(){await load();picker('Tag writing','Scribbler.doTag()')}
 async function doTag(){const paths=selected();if(!paths.length)return alert('Choose at least one piece of writing.');close();setStatus('Tagging…');const r=await fetch('/api/tag',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths,use_llm:true})});const j=await r.json();await load();setStatus(j.ok?`Tagged ${j.tagged.length} piece(s)`:j.error||'Tagging failed');open(`<h2>Tagging complete</h2><p class="s-muted">${j.used_llm?'AI-assisted tagging was available.':'Rule-based tagging was used.'}</p>${j.tagged.map(x=>`<div class="s-good"><strong>${esc(x.filename)}</strong><br>${x.word_count} words · ${esc(x.status)}<br>${x.characters?.length?`People: ${esc(x.characters.join(', '))}<br>`:''}${x.themes?.length?`Themes: ${esc(x.themes.join(', '))}`:''}</div>`).join('')}${j.errors.length?`<p class="s-muted">Some files could not be tagged: ${esc(JSON.stringify(j.errors))}</p>`:''}<div class="s-actions"><button onclick="Scribbler.close()">Done</button></div>`)}
 async function analyze(){await load();picker('Analyse writing','Scribbler.doAnalyze()',true)}
 async function doAnalyze(){const paths=selected();const tools=[...dialog.querySelectorAll('.s-tool:checked')].map(x=>x.value);if(!paths.length)return alert('Choose at least one piece of writing.');if(!tools.length)return alert('Choose at least one analysis tool.');close();setStatus('Analysing selected writing…');const r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths,tools})});const j=await r.json();await load();setStatus(j.ok?`Analysed ${j.results.length} piece(s)`:'Analysis failed');let out='';for(const item of j.results){out+=`<div class="s-good"><strong>${esc(item.filename)}</strong><pre>${esc(JSON.stringify(item.results,null,2))}</pre></div>`}open(`<h2>Analysis finished</h2><p class="s-muted">The results are saved to the project and are also available from Analyse. Raw detail is shown here so you can inspect exactly what the engines found.</p><div class="s-results">${out||'<p>No results returned.</p>'}</div><div class="s-actions"><button onclick="Scribbler.close()">Done</button><a href="analysis.html"><button>Open analysis page</button></a></div>`)}
 function all(value){dialog.querySelectorAll('input[data-file]').forEach(x=>x.checked=value)}
 async function refresh(){setStatus('Refreshing…');await fetch('/api/refresh',{method:'POST'});location.reload()}
 function help(){open(`<h2>How Scribbler works</h2><div class="s-help"><p><strong>1. Import writing</strong><br>Bring in .txt or .md files from anywhere on your computer. Imported material goes into <em>Scribble Inbox</em> (raw-dumps) so nothing is silently classified for you.</p><p><strong>2. Tag material</strong><br>Choose one or many pieces. Scribbler analyses the text and records metadata such as people, places, themes, era, status and summary. Your prose itself is not rewritten.</p><p><strong>3. Analyse writing</strong><br>Choose the exact files and the exact analysis tools you want. Craft, voice, characters, continuity, themes and editor analysis are independent tools; you do not have to run all of them every time.</p><p><strong>4. Explore</strong><br>People, themes and time views are ways of spotting connections. They are not claims about what your memoir 'means'.</p><p><strong>5. Manuscript</strong><br>Use the chapter/draft/final material as the emerging book. Raw scribbles can remain raw until you decide they are worth developing.</p><p><strong>AI status</strong><br>The toolbar shows whether your configured AI provider is available. If it isn't, tagging still works using the built-in rule-based system. Nothing requires an online AI service.</p><p><strong>Your files</strong><br>Everything stays local on this computer. The browser is only the interface; Scribbler's local server performs the actions.</p></div><div class="s-actions"><button onclick="Scribbler.close()">Close</button></div>`)}
 return {importFiles,tag,doTag,analyze,doAnalyze,all,refresh,help,close,load}
})();
Scribbler.load();
</script>'''
    return page.replace('<body>', '<body>'+overlay, 1)


def run_server(open_browser=True):
    """Start localhost server and optionally open the workspace in the default browser."""
    for folder in FOLDERS:
        (PROJECT_ROOT / folder).mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    generate()
    server = ThreadingHTTPServer(("127.0.0.1", 0), ScribblerHandler)
    if open_browser:
        import webbrowser
        webbrowser.open(f"http://127.0.0.1:{server.server_port}/")
    return server
