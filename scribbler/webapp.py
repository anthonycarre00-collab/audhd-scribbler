"""The single interactive desktop workspace for Audhd Scribbler.

The browser is only the local UI. All writing remains on the user's machine.
The workspace deliberately separates:
  INBOX / TAGGING  -> raw brain dumps and notes
  MANUSCRIPT       -> chapters and drafts
  ANALYSIS         -> deliberate analysis of selected manuscript material
"""
from __future__ import annotations
import html, json, mimetypes, os, re, urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from . import db, llm, tagger
from .config import PROJECT_ROOT, FOLDERS
from .file_io import read_text_file
from .analyzers import craft, voice_tense, characters, continuity, themes, editor
from .writer_intelligence import cadence_rhythm, motif_scan, structural_anchors, metrics, voice_report, chapter_comparison, ai_perceptions
from . import safety

ANALYZERS = {
    "craft": ("Craft & Rhythm", "Prose", "draft", craft.analyze),
    "voice": ("Voice & Tense", "Prose", "draft", voice_tense.analyze),
    "characters": ("Characters & Relationships", "Story", "draft", characters.analyze),
    "continuity": ("Continuity & Timeline", "Story", "draft", continuity.analyze),
    "themes": ("Themes & Emotional Arc", "Story", "draft", themes.analyze),
    "editor": ("Editorial Patterns", "Editorial", "near-final", editor.analyze),
    "cadence": ("Cadence & Rhythm", "Prose", "draft", cadence_rhythm),
    "motifs": ("Motifs & Echoes", "Story", "draft", motif_scan),
    "anchors": ("Structural Anchors", "Structure", "draft", structural_anchors),
    "voice_dna": ("Voice DNA", "Writer", "draft", voice_report),
}

def _safe_name(name):
    name = Path(str(name or "untitled.txt")).name
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .") or "untitled.txt"
    if Path(name).suffix.lower() not in {".txt", ".md", ".text"}: name += ".txt"
    return name

def _unique_path(folder, filename):
    p = folder / filename
    if not p.exists(): return p
    for i in range(2, 10000):
        q = folder / f"{p.stem} ({i}){p.suffix}"
        if not q.exists(): return q
    raise RuntimeError("Could not create a unique filename")

def _find_file(raw):
    p = Path(str(raw or ""))
    if not p.is_absolute(): p = PROJECT_ROOT / p
    p = p.resolve()
    try: p.relative_to(PROJECT_ROOT.resolve())
    except ValueError: raise ValueError("File is outside the Scribbler project")
    if not p.exists() or p.suffix.lower() not in {".txt", ".md", ".text"}: raise ValueError("Writing file not found")
    return p

def _json_safe(v):
    if isinstance(v, dict): return {str(k): _json_safe(x) for k,x in v.items()}
    if isinstance(v, (list,tuple)): return [_json_safe(x) for x in v]
    if isinstance(v, (str,int,float,bool)) or v is None: return v
    return str(v)

def _api_files():
    out=[]
    for x in db.get_all_files():
        out.append({"path":x.get("path"),"filename":x.get("filename"),"folder":x.get("folder"),"word_count":x.get("word_count",0),"status":x.get("status","seedling"),"characters":x.get("characters") or [],"places":x.get("places") or [],"themes":x.get("themes") or [],"last_analyzed":x.get("last_analyzed") or ""})
    # Include imported files even before the index catches up.
    known={x["path"] for x in out}
    for folder in ("raw-dumps","triage","chapters","drafts","final"):
        root=PROJECT_ROOT/folder
        if root.exists():
            for p in root.glob("*"):
                if p.is_file() and p.suffix.lower() in {".txt",".md",".text"}:
                    rel=str(p.relative_to(PROJECT_ROOT))
                    if rel not in known:
                        try: wc=len(read_text_file(p).split())
                        except Exception: wc=0
                        out.append({"path":rel,"filename":p.name,"folder":folder,"word_count":wc,"status":"unindexed","characters":[],"places":[],"themes":[],"last_analyzed":""})
    return sorted(out,key=lambda x:(x.get("folder", ""),x.get("filename", "").lower()))

def _body_text(path):
    text=read_text_file(path)
    if text.startswith("---"):
        m=re.match(r"^---\s*\n.*?\n---\s*\n",text,re.S)
        if m: text=text[m.end():]
    return re.sub(r"<!-- SCRIBBLER SUMMARY[\s\S]*?-->","",text).strip()

def _run_tool(tool,text,all_files=None):
    if tool=="voice_dna": return voice_report(text)
    fn=ANALYZERS.get(tool,(None,None,None,None))[3]
    if not fn: raise ValueError(f"Unknown analysis tool: {tool}")
    if tool=="characters": return fn(text,all_files=all_files or [])
    return fn(text)

def _save_result(path,tool,result):
    db.save_analysis(str(path.resolve()),tool,_json_safe(result))

class Handler(BaseHTTPRequestHandler):
    server_version="AudhdScribbler/3.0"
    def log_message(self,*args): return
    def _json(self,payload,status=200):
        data=json.dumps(payload,ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def _body(self):
        n=int(self.headers.get("Content-Length","0"))
        if n>50*1024*1024: raise ValueError("File is larger than 50 MB")
        return self.rfile.read(n)
    def do_GET(self):
        try:
            path=urllib.parse.urlparse(self.path).path
            if path=="/api/files": return self._json({"files":_api_files(),"llm":llm.llm_status(),"snapshots":len(safety.recent_snapshots())})
            if path=="/api/status": return self._json({"llm":llm.llm_status(),"project":str(PROJECT_ROOT),"snapshots":len(safety.recent_snapshots())})
            return self._html()
        except Exception as e: return self._json({"ok":False,"error":str(e)},400)
    def do_POST(self):
        try:
            path=urllib.parse.urlparse(self.path).path
            if path=="/api/import": return self._import()
            if path=="/api/note": return self._note()
            if path=="/api/tag": return self._tag()
            if path=="/api/analyze": return self._analyze()
            if path=="/api/backup": return self._backup()
            if path=="/api/refresh": return self._json({"ok":True})
            if path=="/api/open-folder":
                b=json.loads(self._body() or b"{}"); folder=b.get("folder","raw-dumps")
                if folder not in FOLDERS: raise ValueError("Unknown folder")
                os.startfile(str(PROJECT_ROOT/folder)); return self._json({"ok":True})
            return self._json({"ok":False,"error":"Unknown action"},404)
        except Exception as e: return self._json({"ok":False,"error":str(e)},400)
    def _import(self):
        ctype=self.headers.get("Content-Type","")
        if "multipart/form-data" not in ctype: raise ValueError("Invalid upload")
        m=re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))",ctype)
        if not m: raise ValueError("Upload boundary missing")
        boundary=(m.group(1) or m.group(2)).encode(); body=self._body(); marker=b"--"+boundary; files=[]; folder="raw-dumps"
        for part in body.split(marker):
            end=part.find(b"\r\n\r\n")
            if end<0: continue
            headers=part[:end].decode("utf-8",errors="replace"); content=part[end+4:]
            if content.endswith(b"\r\n"): content=content[:-2]
            fm=re.search(r'filename="([^"]*)"',headers)
            if not fm: continue
            fn=_safe_name(fm.group(1))
            if Path(fn).suffix.lower() not in {".txt",".md",".text"}: continue
            files.append((fn,content))
            if 'name="destination"' in headers:
                try: folder=content.decode().strip()
                except Exception: pass
        if folder not in {"raw-dumps","chapters","drafts"}: folder="raw-dumps"
        target=PROJECT_ROOT/folder; target.mkdir(parents=True,exist_ok=True); saved=[]
        # Import is a copy operation; original files are never modified.
        safety.create_snapshot("before-import")
        for fn,content in files:
            p=_unique_path(target,fn); p.write_bytes(content); saved.append(str(p.relative_to(PROJECT_ROOT)))
        return self._json({"ok":True,"saved":saved,"folder":folder,"message":f"Saved {len(saved)} file(s) to {folder}."})
    def _note(self):
        b=json.loads(self._body() or b"{}"); text=str(b.get("text","")).strip(); title=_safe_name(b.get("title") or "Quick note.txt")
        if not text: raise ValueError("Write something first")
        safety.create_snapshot("before-quick-note"); p=_unique_path(PROJECT_ROOT/"raw-dumps",title); p.write_text(text,encoding="utf-8")
        return self._json({"ok":True,"path":str(p.relative_to(PROJECT_ROOT)),"message":"Note saved to Scribble Inbox."})
    def _tag(self):
        b=json.loads(self._body() or b"{}"); paths=b.get("paths") or []
        if not paths: raise ValueError("Choose at least one brain dump")
        tagged=[]; errors=[]; safety.create_snapshot("before-tagging")
        for raw in paths:
            try:
                p=_find_file(raw)
                if p.relative_to(PROJECT_ROOT).parts[0] not in {"raw-dumps","triage"}: raise ValueError("Tagging is for Inbox/triage material. Import or move the draft into manuscript analysis instead.")
                meta=tagger.tag_file(str(p),use_llm=bool(b.get("use_llm",True)) and llm.llm_available())
                tagged.append({"filename":p.name,"status":meta.get("status","seedling"),"word_count":meta.get("word_count",0),"characters":meta.get("characters",[]),"themes":meta.get("themes",[])})
            except Exception as e: errors.append({"file":str(raw),"error":str(e)})
        return self._json({"ok":True,"tagged":tagged,"errors":errors})
    def _analyze(self):
        b=json.loads(self._body() or b"{}"); paths=b.get("paths") or []; tools=[x for x in b.get("tools",[]) if x in ANALYZERS]
        if not paths: raise ValueError("Choose at least one chapter or draft")
        if not tools: raise ValueError("Choose at least one analysis tool")
        safety.create_snapshot("before-analysis"); all_files=db.get_all_files(); results=[]; errors=[]
        selected=[]
        for raw in paths:
            try:
                p=_find_file(raw); folder=p.relative_to(PROJECT_ROOT).parts[0]
                if folder not in {"chapters","drafts","final"}: raise ValueError("Analysis is reserved for chapters/drafts/final manuscript material. Tag raw brain dumps first.")
                text=_body_text(p)
                if len(text.split())<10: raise ValueError("Too short for meaningful analysis")
                row={"filename":p.name,"results":{}}
                for tool in tools:
                    result=_run_tool(tool,text,all_files); _save_result(p,tool,result); row["results"][tool]=_json_safe(result)
                selected.append({"label":p.stem,"path":str(p),"text":text}); results.append(row)
            except Exception as e: errors.append({"file":str(raw),"error":str(e)})
        # Cross-chapter comparisons are calculated only when multiple drafts are selected.
        if len(selected)>1 and any(x in tools for x in ("voice_dna","cadence","motifs","anchors")):
            comparison=chapter_comparison(selected); results.append({"filename":"Selected chapters — comparison","results":{"chapter_comparison":comparison}})
            db.log_activity("chapter-comparison",None,"Compared selected chapters for voice/cadence/motif/anchor change")
        return self._json({"ok":True,"results":results,"errors":errors})
    def _backup(self):
        return self._json({"ok":True,"path":safety.export_project_zip()})
    def _html(self):
        return self._send_html(APP_HTML)
    def _send_html(self,text):
        data=text.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)

def run_server(open_browser=True):
    for folder in FOLDERS: (PROJECT_ROOT/folder).mkdir(parents=True,exist_ok=True)
    (PROJECT_ROOT/"data").mkdir(parents=True,exist_ok=True); db.get_db().close()
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    if open_browser:
        import webbrowser; webbrowser.open(f"http://127.0.0.1:{server.server_port}/")
    return server

APP_HTML=r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Audhd Scribbler</title><style>
:root{--ink:#27302f;--muted:#717872;--paper:#faf9f5;--panel:#fff;--line:#e1ded6;--accent:#55777a;--soft:#edf2f0;--warn:#fff5df}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.55 'Segoe UI',Arial,sans-serif}.app{min-height:100vh}.top{background:#27302f;color:white;padding:18px 28px;display:flex;align-items:center;gap:22px;position:sticky;top:0;z-index:10}.brand{font:700 25px Georgia,serif;white-space:nowrap}.tagline{opacity:.7;font-size:12px}.top button{border:1px solid #5c6867;background:#34403f;color:#fff;border-radius:7px;padding:8px 11px;cursor:pointer}.top button:hover{background:#465352}.top .status{margin-left:auto;font-size:12px;opacity:.75}.layout{display:grid;grid-template-columns:220px 1fr;max-width:1450px;margin:auto;min-height:calc(100vh - 70px)}aside{border-right:1px solid var(--line);padding:24px 15px;background:#f5f3ee}aside h3{font-size:11px;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);margin:8px 10px}aside button{display:block;width:100%;text-align:left;border:0;background:transparent;padding:11px 12px;border-radius:8px;color:var(--ink);cursor:pointer}aside button.active,aside button:hover{background:#e5ebe9}main{padding:30px 38px;max-width:1100px;width:100%}h1{font:700 36px Georgia,serif;margin:0 0 8px}h2{font:700 25px Georgia,serif;margin:0 0 8px}.lead{color:var(--muted);max-width:760px}.view{display:none}.view.active{display:block}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}.card h3{margin:0 0 5px;font:700 18px Georgia,serif}.card p{color:var(--muted);margin:5px 0 15px}.btn{border:1px solid var(--line);background:white;color:var(--ink);padding:9px 13px;border-radius:7px;cursor:pointer}.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}.btn.big{padding:11px 16px}.actions{display:flex;gap:9px;flex-wrap:wrap;margin:18px 0}.section{background:white;border:1px solid var(--line);border-radius:12px;padding:20px;margin:16px 0}.section h3{font:700 19px Georgia,serif;margin:0 0 5px}.muted{color:var(--muted)}.file-list{border:1px solid var(--line);border-radius:9px;background:white;max-height:440px;overflow:auto}.file{display:flex;gap:12px;align-items:center;padding:11px 13px;border-bottom:1px solid var(--line)}.file:last-child{border:0}.file input{width:18px;height:18px}.file .meta{margin-left:auto;color:var(--muted);font-size:12px}.pill{display:inline-block;padding:3px 7px;border-radius:99px;background:var(--soft);font-size:11px;margin-left:5px}.tools{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.tool{border:1px solid var(--line);border-radius:9px;padding:13px;background:white}.tool strong{display:block}.tool small{color:var(--muted)}textarea,input[type=text]{width:100%;border:1px solid var(--line);border-radius:8px;padding:11px;font:inherit;background:#fff}textarea{min-height:180px;resize:vertical}.modal{position:fixed;inset:0;background:#1d252488;display:none;align-items:center;justify-content:center;padding:25px;z-index:50}.modal.open{display:flex}.dialog{background:var(--paper);border-radius:14px;width:min(900px,96vw);max-height:90vh;overflow:auto;padding:26px;box-shadow:0 20px 70px #0004}.dialog .actions{justify-content:flex-end}.notice{padding:13px;border-radius:8px;background:var(--soft);margin:10px 0}.warning{background:var(--warn)}pre{white-space:pre-wrap;background:#f0eee8;padding:12px;border-radius:8px;font:12px/1.5 Consolas,monospace}.empty{padding:30px;text-align:center;color:var(--muted)}@media(max-width:850px){.layout{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid var(--line);display:flex;overflow:auto}aside h3{display:none}aside button{white-space:nowrap;width:auto}main{padding:22px}.cards{grid-template-columns:1fr}.tools{grid-template-columns:1fr}.tagline{display:none}}
</style></head><body><div class="app"><header class="top"><div class="brand">Audhd Scribbler</div><div class="tagline">A writer's workshop for messy ideas, manuscripts and patterns</div><button onclick="backup()">Backup project</button><span class="status" id="status">Ready</span></header><div class="layout"><aside><h3>Workspace</h3><button data-view="home" class="active">Home</button><button data-view="inbox">Scribble Inbox</button><button data-view="manuscript">Manuscript</button><button data-view="analysis">Analysis</button><button data-view="notes">Quick Notes</button><h3>Project</h3><button data-view="safety">Safety & exports</button></aside><main>
<section id="home" class="view active"><h1>Your writing workspace</h1><p class="lead">One place for the messy stuff and the serious stuff — without confusing the two.</p><div class="cards"><div class="card"><h3>01 · Scribble Inbox</h3><p>Brain dumps, fragments and random thoughts. Tag them without judging the writing.</p><button class="btn primary" onclick="show('inbox');openImport('raw-dumps')">Import brain dumps</button></div><div class="card"><h3>02 · Manuscript</h3><p>Chapters and drafts are deliberately separate from raw material.</p><button class="btn primary" onclick="show('manuscript');openImport('chapters')">Import chapter / draft</button></div><div class="card"><h3>03 · Analysis</h3><p>Choose the exact draft and the exact question. Nothing is analysed by accident.</p><button class="btn primary" onclick="show('analysis')">Open analysis</button></div></div><div class="section"><h3>The rule</h3><p><strong>Raw material gets organised. Drafts get analysed.</strong> Scribbler never silently turns a brain dump into a manuscript or treats messy notes as failed prose.</p></div></section>
<section id="inbox" class="view"><h1>Scribble Inbox</h1><p class="lead">Your safe landing place for unfinished thoughts, brain dumps, notes and fragments.</p><div class="actions"><button class="btn primary" onclick="openImport('raw-dumps')">＋ Import brain dumps</button><button class="btn" onclick="openTag()">Tag selected</button><button class="btn" onclick="openNote()">＋ Write a quick note</button></div><div class="section"><h3>Inbox material</h3><p class="muted">Tagging may add metadata, but it does not rewrite the body of your writing.</p><div id="inboxFiles" class="file-list"></div></div></section>
<section id="manuscript" class="view"><h1>Manuscript</h1><p class="lead">Only material you consider a chapter or draft belongs here. This is what the analysis suite works on.</p><div class="actions"><button class="btn primary" onclick="openImport('chapters')">＋ Import chapter</button><button class="btn" onclick="openImport('drafts')">＋ Import draft</button><button class="btn" onclick="show('analysis')">Analyse selected</button></div><div class="section"><h3>Chapters & drafts</h3><div id="manuscriptFiles" class="file-list"></div></div></section>
<section id="analysis" class="view"><h1>Analysis</h1><p class="lead">Separate tools for separate questions. Run one, several, or the cautious recommended set.</p><div class="section"><h3>1. Choose your writing</h3><div id="analysisFiles" class="file-list"></div></div><div class="section"><h3>2. Choose your analysis</h3><div class="tools" id="tools"></div><div class="actions"><button class="btn" onclick="selectTools(true)">Select recommended</button><button class="btn" onclick="selectTools(false)">Clear</button><button class="btn primary big" onclick="runAnalysis()">Run selected analysis</button></div><div class="notice warning"><strong>Run all is not a default.</strong> Some diagnostics overlap or can be misleading when deliberate voice, genre, POV or author growth is involved. Scribbler flags patterns; you decide whether they matter.</div></div><div class="section"><h3>Results</h3><div id="results"><div class="empty">Run an analysis to see results here.</div></div></div></section>
<section id="notes" class="view"><h1>Quick Notes</h1><p class="lead">A little scratchpad for the thought that arrives while you're doing something else.</p><div class="section"><input id="noteTitle" type="text" placeholder="Optional title"><br><br><textarea id="noteText" placeholder="Type the thought. Don't organise it yet."></textarea><div class="actions"><button class="btn primary" onclick="saveNote()">Save to Scribble Inbox</button></div></div></section>
<section id="safety" class="view"><h1>Safety & exports</h1><p class="lead">Scribbler treats your writing as valuable source material.</p><div class="section"><h3>Before important changes</h3><p>Tagging, importing and analysis create a local safety snapshot first. Previous analysis results are retained rather than silently replaced.</p><button class="btn primary" onclick="backup()">Create portable project backup</button></div><div class="section"><h3>Export rule</h3><p>Exports never silently overwrite an existing file. A new numbered copy is created instead.</p><p class="muted">Project data stays local. The browser is only the interface.</p></div></section>
</main></div></div><div id="modal" class="modal"><div id="dialog" class="dialog"></div></div><input id="upload" type="file" multiple accept=".txt,.md,.text" hidden><script>
let files=[];const statusEl=document.getElementById('status'),modal=document.getElementById('modal'),dialog=document.getElementById('dialog');const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));const setStatus=s=>statusEl.textContent=s;const show=id=>{document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));document.getElementById(id).classList.add('active');document.querySelectorAll('aside button[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===id));render();};document.querySelectorAll('aside button[data-view]').forEach(x=>x.onclick=()=>show(x.dataset.view));const openModal=h=>{dialog.innerHTML=h;modal.classList.add('open')};const closeModal=()=>modal.classList.remove('open');modal.onclick=e=>{if(e.target===modal)closeModal()};
async function load(){const j=await (await fetch('/api/files')).json();files=j.files||[];return j}function folderFiles(folder){return files.filter(x=>x.folder===folder)}function listHTML(items,scope){if(!items.length)return '<div class="empty">Nothing here yet.</div>';return items.map(f=>`<label class="file"><input type="checkbox" data-scope="${scope}" value="${esc(f.path)}"><span><strong>${esc(f.filename)}</strong><br><span class="muted">${f.word_count||0} words · ${esc(f.status)}${f.last_analyzed?` · analysed ${esc(f.last_analyzed)}`:''}</span></span><span class="meta">${esc(f.folder)}</span></label>`).join('')}function selected(scope){return [...document.querySelectorAll(`input[data-scope="${scope}"]:checked`)].map(x=>x.value)}
function render(){document.getElementById('inboxFiles').innerHTML=listHTML([...folderFiles('raw-dumps'),...folderFiles('triage')],'inbox');document.getElementById('manuscriptFiles').innerHTML=listHTML([...folderFiles('chapters'),...folderFiles('drafts'),...folderFiles('final')],'manuscript');document.getElementById('analysisFiles').innerHTML=listHTML([...folderFiles('chapters'),...folderFiles('drafts'),...folderFiles('final')],'analysis');document.getElementById('tools').innerHTML=TOOLS.map(t=>`<label class="tool"><input type="checkbox" class="toolbox" value="${t[0]}"> <strong>${t[1]}</strong><small>${t[3]} · Best on ${t[2]}</small></label>`).join('')}
const TOOLS=[['craft','Craft & Rhythm','draft','Sentence rhythm, balance and craft signals.'],['voice','Voice & Tense','draft','Narrator voice, tense and narrative stance.'],['characters','Characters & Relationships','draft','Presence, relationships and character movement.'],['continuity','Continuity & Timeline','draft','Chronology, recurring facts and continuity signals.'],['themes','Themes & Emotional Arc','draft','Themes, motifs and emotional movement.'],['cadence','Cadence & Rhythm','draft','Sentence-length movement, pauses and contrast.'],['motifs','Motifs & Echoes','draft','Recurring words and phrases across the selected writing.'],['anchors','Structural Anchors','draft','Repeated openings, endings and textual anchors.'],['voice_dna','Voice DNA','draft','Compare against approved personal writing samples.'],['editor','Editorial Patterns','near-final','Clarity, redundancy and memoir-specific editorial signals.']];
async function openImport(dest){openModal(`<h2>Import ${dest==='raw-dumps'?'brain dumps':'chapters / drafts'}</h2><p class="muted">Choose files from your computer. Scribbler copies them into the selected workspace and leaves your originals untouched.</p><div class="section"><label><input type="radio" name="dest" value="raw-dumps" ${dest==='raw-dumps'?'checked':''}> Scribble Inbox</label><br><label><input type="radio" name="dest" value="chapters" ${dest==='chapters'?'checked':''}> Chapters</label><br><label><input type="radio" name="dest" value="drafts"> Drafts</label></div><div class="actions"><button class="btn" onclick="closeModal()">Cancel</button><button class="btn primary" onclick="chooseUpload()">Choose files</button></div>`)}function chooseUpload(){const i=document.getElementById('upload');i.value='';i.onchange=async()=>{if(!i.files.length)return;const dest=document.querySelector('input[name="dest"]:checked').value;const fd=new FormData();fd.append('destination',dest);[...i.files].forEach(f=>fd.append('files',f));setStatus('Saving copies…');const j=await(await fetch('/api/import',{method:'POST',body:fd})).json();if(!j.ok)return alert(j.error);await load();render();closeModal();setStatus('✓ '+j.message);show(dest==='raw-dumps'?'inbox':'manuscript')};i.click()}
function openTag(){const p=selected('inbox');if(!p.length)return alert('Select one or more brain dumps first.');openModal(`<h2>Tag selected material</h2><p>Your prose will not be rewritten. Scribbler will create a safety snapshot before adding/updating tags.</p><div class="notice">Selected: ${p.length} item(s)</div><div class="actions"><button class="btn" onclick="closeModal()">Cancel</button><button class="btn primary" onclick="runTag(${JSON.stringify(p)})">Tag and save</button></div>`)}async function runTag(p){closeModal();if(!confirm('Tag these brain dumps now?\n\nA safety snapshot will be created first.'))return;setStatus('Tagging…');const j=await(await fetch('/api/tag',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:p,use_llm:true})})).json();await load();render();setStatus(j.ok?'✓ Tagging saved':'Tagging failed');openModal(`<h2>Tagging complete</h2><div class="notice">${j.tagged.length} item(s) processed. Previous project state was preserved.</div>${j.errors.length?`<div class="notice warning">${esc(JSON.stringify(j.errors))}</div>`:''}<div class="actions"><button class="btn primary" onclick="closeModal()">Done</button></div>`)}
function selectTools(v){document.querySelectorAll('.toolbox').forEach((x,i)=>x.checked=v&&(i<7))}async function runAnalysis(){const p=selected('analysis'),t=[...document.querySelectorAll('.toolbox:checked')].map(x=>x.value);if(!p.length)return alert('Select one or more chapters/drafts first.');if(!t.length)return alert('Select at least one analysis tool.');if(!confirm(`Run ${t.length} analysis tool(s) on ${p.length} file(s)?\n\nA safety snapshot will be created first. Previous results are retained.`))return;setStatus('Analysing…');const j=await(await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:p,tools:t})})).json();await load();render();setStatus(j.ok?'✓ Analysis saved':'Analysis failed');let out='';j.results.forEach(x=>{out+=`<div class="section"><h3>${esc(x.filename)}</h3><pre>${esc(JSON.stringify(x.results,null,2))}</pre></div>`});document.getElementById('results').innerHTML=out||'<div class="empty">No results returned.</div>';if(j.errors.length)document.getElementById('results').innerHTML+=`<div class="notice warning">${esc(JSON.stringify(j.errors))}</div>`}
async function saveNote(){const text=document.getElementById('noteText').value.trim();if(!text)return alert('Write something first.');setStatus('Saving note…');const j=await(await fetch('/api/note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:document.getElementById('noteTitle').value,text})})).json();if(!j.ok)return alert(j.error);document.getElementById('noteText').value='';document.getElementById('noteTitle').value='';await load();render();setStatus('✓ Note saved to Scribble Inbox');show('inbox')}
async function backup(){setStatus('Creating backup…');const j=await(await fetch('/api/backup',{method:'POST'})).json();setStatus(j.ok?'✓ Backup created':'Backup failed');if(j.ok)alert('Portable project backup created:\n\n'+j.path)}load().then(render)
</script></body></html>'''
