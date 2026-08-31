"""Small release-layer improvements applied to the established Scribbler backend/UI.

This module deliberately avoids replacing the existing tagging/analysis engines. It
only wires presentation, exports and the safety policy used by the Windows release.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import PROJECT_ROOT
from . import export as export_mod


def _safe_report_name(file_path: str, analysis_type: str) -> str:
    stem = Path(file_path).stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-") or "writing"
    tool = re.sub(r"[^A-Za-z0-9._-]+", "-", analysis_type).strip("-") or "analysis"
    return f"{safe}__{tool}.md"


def _safe_tag_name(file_path: str) -> str:
    stem = Path(file_path).stem
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-") or "writing"
    return f"{safe}__tagged.md"


def prepare_backend(webapp):
    """Apply release-only wiring without replacing established engines."""
    # Database writes are already transactional; full project snapshots before every
    # DB update were copying entire writing folders and made large jobs painfully slow.
    webapp.db.backup_database = lambda reason="": None

    # Only an actual tagging operation changes the source document. Imports, notes and
    # analysis create/add data and therefore do not need a full project snapshot.
    original_snapshot = webapp.safety.create_snapshot

    def selective_snapshot(reason="manual save"):
        if reason == "before-tagging":
            return original_snapshot(reason)
        return None

    webapp.safety.create_snapshot = selective_snapshot

    # Every successful tag operation produces a clean tagged copy in one predictable
    # export folder. The original tagged source remains untouched by the export.
    original_tag_file = webapp.tagger.tag_file

    def tag_file_and_export(file_path: str, use_llm: bool = True):
        meta = original_tag_file(file_path, use_llm=use_llm)
        out_dir = PROJECT_ROOT / "data" / "exports" / "tagged"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = export_mod.export_markdown(file_path, out_dir / _safe_tag_name(file_path))
        meta["tagged_export"] = str(out)
        return meta

    webapp.tagger.tag_file = tag_file_and_export

    # Each analysis type gets its own report. This makes reports useful as standalone
    # editorial documents and avoids one giant mixed report when several tools run.
    original_save_analysis = webapp.db.save_analysis

    def save_analysis_and_export(file_path: str, analysis_type: str, result: dict):
        original_save_analysis(file_path, analysis_type, result)
        out_dir = PROJECT_ROOT / "data" / "exports" / "analysis"
        out_dir.mkdir(parents=True, exist_ok=True)
        export_mod.export_analysis_report(
            file_path,
            {analysis_type: result},
            out_dir / _safe_report_name(file_path, analysis_type),
        )

    webapp.db.save_analysis = save_analysis_and_export

    # Add an explicit tagged-export action for the Inbox. Manuscript exports are no
    # longer presented as a parallel workflow: analysis produces its reports instead.
    original_export = webapp.Handler.export

    def export(self):
        b = json.loads(self.read_body() or b"{}")
        if b.get("kind") != "tagged":
            # Reconstruct the body for the existing handler path.
            raw = json.dumps(b).encode()
            self.headers["Content-Length"] = str(len(raw))
            self.rfile = _BodyReader(raw)
            return original_export(self)
        p = webapp.find_file(b.get("path"))
        folder = p.relative_to(PROJECT_ROOT).parts[0]
        if folder not in {"raw-dumps", "triage"}:
            raise ValueError("Tagged export is only available for Inbox material")
        out_dir = PROJECT_ROOT / "data" / "exports" / "tagged"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = export_mod.export_markdown(p, out_dir / _safe_tag_name(str(p)))
        return self.send_json({"ok": True, "path": str(out)})

    webapp.Handler.export = export


def enhance_ui(app: str) -> str:
    """Make the existing release UI clearer without changing its underlying workflow."""
    # Add a compact, writerly progress overlay. It is intentionally indeterminate: we
    # cannot honestly predict how long a large tagging/analysis job will take.
    progress_css = r'''<style>
#scribblerProgress{display:none;position:fixed;inset:0;background:rgba(38,49,47,.30);z-index:100;align-items:center;justify-content:center;padding:25px}
#scribblerProgress.open{display:flex}.progressbox{width:min(520px,92vw);background:#fffdf8;border:1px solid #d8d2c6;border-radius:16px;padding:25px 27px;box-shadow:0 18px 55px rgba(30,40,37,.20)}
.progressmark{font:700 25px Georgia;color:#26312f;margin-bottom:8px}.progressline{height:4px;background:#e5e0d7;border-radius:4px;overflow:hidden;margin:17px 0 13px}.progressline i{display:block;width:35%;height:100%;background:#52777a;border-radius:4px;animation:scribbleProgress 1.8s ease-in-out infinite}.progresswords{color:#52605c;font-family:Georgia,serif;font-size:16px}.progresstime{font-size:12px;color:#7a817d;margin-top:7px}@keyframes scribbleProgress{0%{transform:translateX(-120%)}100%{transform:translateX(310%)}}
</style>'''
    progress_html = r'''<div id="scribblerProgress"><div class="progressbox"><div class="progressmark">Scribbler is thinking…</div><div id="scribblerProgressWords" class="progresswords">Giving the words a little room.</div><div class="progressline"><i></i></div><div id="scribblerProgressTime" class="progresstime">0:00 · Please leave Scribbler open</div></div></div>'''
    progress_js = r'''<script>
(function(){
 const overlay=document.getElementById('scribblerProgress'), words=document.getElementById('scribblerProgressWords'), clock=document.getElementById('scribblerProgressTime');
 let timer=null, started=0, rot=0;
 const messages={
  '/api/tag-preview':['Reading between the lines.','Finding the threads that keep returning.','Listening for people, places and patterns.','Sorting the useful bits from the noise.'],
  '/api/tag':['Following the threads.','Giving each fragment a place to land.','Listening for recurring people, places and ideas.','Putting the messy pieces into some order.'],
  '/api/analyze':['Giving the words a little room.','Following the shape of the prose.','Listening for rhythm, cadence and echoes.','Looking for what keeps returning.','Comparing the voice without judging its growth.','Reading the structure from the inside out.','Checking the joins, the turns and the quiet bits.'],
  '/api/import':['Making room for the new pages.','Bringing the pages into the workshop.'],
  '/api/note':['Tucking that thought safely into the Inbox.'],
  '/api/export':['Gathering the useful pages.','Making a clean copy for you.'],
  '/api/backup':['Packing the workshop carefully.']
 };
 function begin(url){
  const list=messages[url]||['Working through the pages.','Giving the words a little room.']; rot=0; started=Date.now(); words.textContent=list[0]; overlay.classList.add('open');
  clearInterval(timer); timer=setInterval(()=>{rot=(rot+1)%list.length;words.textContent=list[rot];const s=Math.floor((Date.now()-started)/1000);clock.textContent=Math.floor(s/60)+':'+String(s%60).padStart(2,'0')+' · Please leave Scribbler open';},1800);
 }
 function end(){clearInterval(timer);timer=null;overlay.classList.remove('open')}
 const nativeFetch=window.fetch.bind(window);
 window.fetch=function(input,init){
  const url=typeof input==='string'?input:(input&&input.url)||''; const method=((init&&init.method)||'GET').toUpperCase();
  const path=url.split('?')[0]; if(method==='POST' && messages[path]) begin(path);
  return nativeFetch(input,init).finally(()=>{if(method==='POST'&&messages[path])end()});
 };
})();
</script>'''
    app = app.replace('</head>', progress_css + '</head>', 1)
    app = app.replace('<div id="modal" class="modal">', progress_html + '<div id="modal" class="modal">', 1)

    # Put the tagged export exactly where a writer expects it: beside tagging.
    app = app.replace(
        '<button class="btn primary" onclick="applyTags()">Apply tags</button>',
        '<button class="btn primary" onclick="applyTags()">Apply tags</button><button class="btn" onclick="exportTagged()">Export tagged document</button>',
        1,
    )

    # Replace the old export-heavy Safety view with a deliberately small control panel.
    old_safety = '''<section id="safety" class="view"><h1>Export & Safety</h1><p class="lead">Scribbler is designed to make experimentation safe: snapshots before changes, analysis history retained, exports never silently overwrite.</p><div class="panel"><h3>Portable project backup</h3><p class="muted">Creates a ZIP containing your writing folders, database and project manifest.</p><button class="btn primary" onclick="backup()">Create backup ZIP</button></div><div class="panel"><h3>Export manuscript</h3><div id="exportList" class="filelist"></div><div class="actions"><button class="btn" onclick="exportFile('docx')">DOCX</button><button class="btn" onclick="exportFile('md')">Markdown</button><button class="btn" onclick="exportFile('txt')">Plain text</button></div></div></section>'''
    new_safety = '''<section id="safety" class="view"><h1>Exports & Safety</h1><p class="lead">Scribbler keeps this simple: tagged copies go to <b>Exports / Tagged</b>; analysis feedback goes to <b>Exports / Analysis</b>. Backups are manual, not constant.</p><div class="panel"><h3>Tagged material</h3><p class="muted">Use <b>Export tagged document</b> in the Scribble Inbox after tagging. Scribbler keeps the original and creates a clean exported copy.</p></div><div class="panel"><h3>Analysis reports</h3><p class="muted">Every analysis you run automatically produces its own report. If you run four tools, you get four clearly named reports rather than one giant mixed document.</p></div><div class="panel"><h3>Portable project backup</h3><p class="muted">A full ZIP is created only when you ask for one.</p><button class="btn primary" onclick="backup()">Create backup ZIP</button></div></section>'''
    app = app.replace(old_safety, new_safety, 1)

    # render() no longer needs the removed export picker.
    app = app.replace(
        "document.getElementById('exportList').innerHTML=list(by(['chapters','drafts','final']),'export');",
        "",
        1,
    )

    # Add the explicit Inbox export action and keep the old generic export function for
    # compatibility with older calls, but the UI no longer presents it as a main workflow.
    export_js = r'''async function exportTagged(){let p=selected('inbox');if(p.length!==1)return alert('Select one tagged Inbox item first.');setStatus('Preparing tagged copy…');let j=await(await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p[0],kind:'tagged'})})).json();if(!j.ok)return alert(j.error);setStatus('✓ Tagged document exported');alert('Tagged document created at:\n'+j.path)}
'''
    app = app.replace('async function exportFile(kind){', export_js + 'async function exportFile(kind){', 1)
    app = app.replace('</script></body></html>', progress_js + '</script></body></html>', 1)
    return app


class _BodyReader:
    """Minimal readable stream used only to feed the existing export handler."""
    def __init__(self, data: bytes): self._data = data; self._done = False
    def read(self, n=-1):
        if self._done: return b""
        self._done = True
        return self._data
    def close(self): pass
