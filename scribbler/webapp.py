"""Unified local writer workspace for Audhd Scribbler."""
from __future__ import annotations
import html,json,os,re,urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from . import db,llm,tagger,safety
from .config import PROJECT_ROOT,FOLDERS
from .file_io import read_text_file
from .analysis_catalog import ANALYSIS_CATALOG
from .analyzers import craft,voice_tense,characters,continuity,themes,editor
from .analysis_suite import run as suite_run
from .writer_intelligence import cadence_rhythm,motif_scan,structural_anchors,voice_report,chapter_comparison,ai_perceptions
from .export import export_markdown,export_plain_text,export_docx,export_analysis_report

TOOLS={
 "craft":("Craft & Rhythm","Prose","Sentence rhythm, balance and craft signals.",craft.analyze),
 "voice":("Voice & Tense","Prose","Narrator voice, tense and narrative stance.",voice_tense.analyze),
 "characters":("Characters & Relationships","Story","Presence, relationships and character movement.",characters.analyze),
 "continuity":("Continuity & Timeline","Story","Chronology, recurring facts and inconsistencies.",continuity.analyze),
 "themes":("Themes & Emotional Arc","Story","Themes and emotional movement.",themes.analyze),
 "editor":("Editorial Patterns","Editorial","Clarity, redundancy and editorial signals.",editor.analyze),
 "repetition":("Repetition & Echoes","Prose","Repeated words and phrases.",None),
 "pacing":("Pacing & Momentum","Structure","Acceleration, slowing and sentence/paragraph movement.",None),
 "structure":("Structure & Chapter Purpose","Structure","Openings, endings, paragraph shape and structural signals.",None),
 "memoir":("Memoir Lens","Memoir","Reflection, event balance and memory uncertainty. Optional for non-memoir work.",None),
 "reader":("Reader Experience","Editorial","Opening, dialogue and possible reader-friction signals.",None),
 "research":("Research & Fact Flags","Accuracy","Dates and claims worth checking; never declares facts true/false.",None),
 "cadence":("Cadence & Rhythm","Prose","Sentence movement, pauses and contrast.",cadence_rhythm),
 "motifs":("Motifs & Echoes","Story","Recurring words/phrases; candidate patterns, not automatic meanings.",motif_scan),
 "anchors":("Structural Anchors","Structure","Recurring openings, endings and textual anchors.",structural_anchors),
 "voice_dna":("Voice DNA","Writer","Compare against approved personal writing samples.",voice_report),
 "reader_perception":("Reader Perception","Writer","Textual impression of narrator/author and named characters; evidence-first AI when available.",None),
}

def safe_name(n):
 n=Path(str(n or "untitled.txt")).name; n=re.sub(r"[^A-Za-z0-9._ -]+","_",n).strip(" .") or "untitled.txt"
 return n if Path(n).suffix.lower() in {".txt",".md",".text"} else n+".txt"

def unique(folder,name):
 p=folder/name
 if not p.exists(): return p
 for i in range(2,10000):
  q=folder/f"{p.stem} ({i}){p.suffix}"
  if not q.exists(): return q
 raise RuntimeError("Unable to create a unique filename")

def find_file(raw):
 p=Path(str(raw)); p=PROJECT_ROOT/p if not p.is_absolute() else p; p=p.resolve()
 try:p.relative_to(PROJECT_ROOT.resolve())
 except ValueError:raise ValueError("File is outside the Scribbler project")
 if not p.exists() or p.suffix.lower() not in {".txt",".md",".text"}:raise ValueError("Writing file not found")
 return p

def body(path):
 t=read_text_file(path)
 if t.startswith("---"):
  m=re.match(r"^---\s*\n.*?\n---\s*\n",t,re.S)
  if m:t=t[m.end():]
 return re.sub(r"<!-- SCRIBBLER SUMMARY[\s\S]*?-->","",t).strip()

def js(v):
 if isinstance(v,dict):return {str(k):js(x) for k,x in v.items()}
 if isinstance(v,(list,tuple)):return [js(x) for x in v]
 if isinstance(v,(str,int,float,bool)) or v is None:return v
 return str(v)

def files():
 out=[]; seen=set()
 for x in db.get_all_files():
  p=x.get("path"); seen.add(p); out.append({"path":p,"filename":x.get("filename"),"folder":x.get("folder"),"word_count":x.get("word_count",0),"status":x.get("status","seedling"),"last_analyzed":x.get("last_analyzed") or ""})
 for folder in ("raw-dumps","triage","chapters","drafts","final"):
  root=PROJECT_ROOT/folder
  if root.exists():
   for p in root.iterdir():
    if p.is_file() and p.suffix.lower() in {".txt",".md",".text"}:
     rel=str(p.relative_to(PROJECT_ROOT))
     if rel not in seen:
      out.append({"path":rel,"filename":p.name,"folder":folder,"word_count":len(body(p).split()),"status":"unindexed","last_analyzed":""})
 return sorted(out,key=lambda x:(x["folder"],x["filename"].lower()))

def tag_preview(p,use_ai=True):
 text=body(p)
 return {"filename":p.name,"word_count":len(text.split()),"voice":tagger.detect_voice(text),"era":tagger.detect_era(text),"emotional_register":tagger.detect_emotional_register(text),"sensory":tagger.detect_sensory(text),"themes":tagger.detect_themes(text),"characters":tagger.detect_characters(text),"places":tagger.detect_places(text),"ai_available":llm.llm_available() if use_ai else False}

def run_tool(key,text,all_files):
 meta=TOOLS[key]; fn=meta[3]
 if key=="reader_perception":
  r=ai_perceptions(text)
  return r or {"status":"AI unavailable","note":"Enable a configured AI provider for reader-perception analysis."}
 if key=="voice_dna":return voice_report(text)
 if fn:
  if key=="characters":return fn(text,all_files=all_files)
  return fn(text)
 return suite_run(key,text)

class Handler(BaseHTTPRequestHandler):
 server_version="AudhdScribbler/4.0"
 def log_message(self,*a):pass
 def send_json(self,v,status=200):
  d=json.dumps(v,ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(d))); self.end_headers(); self.wfile.write(d)
 def read_body(self):
  n=int(self.headers.get("Content-Length","0"));
  if n>60*1024*1024:raise ValueError("Request is too large")
  return self.rfile.read(n)
 def do_GET(self):
  try:
   p=urllib.parse.urlparse(self.path).path
   if p=="/api/files":return self.send_json({"files":files(),"llm":llm.llm_status(),"snapshots":len(safety.recent_snapshots()),"version":"4.0"})
   if p=="/api/tools":return self.send_json({"tools":{k:{"title":v[0],"group":v[1],"purpose":v[2]} for k,v in TOOLS.items()},"catalog":ANALYSIS_CATALOG})
   if p=="/api/status":return self.send_json({"ok":True,"version":"4.0","llm":llm.llm_status()})
   return self.html()
  except Exception as e:return self.send_json({"ok":False,"error":str(e)},400)
 def do_POST(self):
  try:
   p=urllib.parse.urlparse(self.path).path
   if p=="/api/import":return self.import_files()
   if p=="/api/note":return self.note()
   if p=="/api/tag-preview":return self.preview()
   if p=="/api/tag":return self.tag()
   if p=="/api/analyze":return self.analyze()
   if p=="/api/export":return self.export()
   if p=="/api/backup":return self.send_json({"ok":True,"path":safety.export_project_zip()})
   return self.send_json({"ok":False,"error":"Unknown action"},404)
  except Exception as e:return self.send_json({"ok":False,"error":str(e)},400)
 def import_files(self):
  c=self.headers.get("Content-Type","")
  if "multipart/form-data" not in c:raise ValueError("Invalid upload")
  m=re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))",c)
  if not m:raise ValueError("Upload boundary missing")
  b=(m.group(1) or m.group(2)).encode(); raw=self.read_body(); parts=raw.split(b"--"+b); dest="raw-dumps"; incoming=[]
  for part in parts:
   sep=part.find(b"\r\n\r\n")
   if sep<0:continue
   h=part[:sep].decode("utf-8","replace"); content=part[sep+4:]
   if content.endswith(b"\r\n"):content=content[:-2]
   fm=re.search(r'filename="([^"]*)"',h)
   if 'name="destination"' in h and not fm:
    dest=content.decode("utf-8","replace").strip();continue
   if fm:
    fn=safe_name(fm.group(1))
    if Path(fn).suffix.lower() in {".txt",".md",".text"}:incoming.append((fn,content))
  if dest not in {"raw-dumps","chapters","drafts"}:raise ValueError("Invalid destination")
  safety.create_snapshot("before-import"); target=PROJECT_ROOT/dest;target.mkdir(parents=True,exist_ok=True);saved=[]
  for fn,cnt in incoming:
   p=unique(target,fn);p.write_bytes(cnt);saved.append(str(p.relative_to(PROJECT_ROOT)))
  return self.send_json({"ok":True,"saved":saved,"folder":dest,"message":f"Imported {len(saved)} file(s) into {dest}."})
 def note(self):
  b=json.loads(self.read_body() or b"{}");t=str(b.get("text","")).strip()
  if not t:raise ValueError("Write something first")
  safety.create_snapshot("before-quick-note");p=unique(PROJECT_ROOT/"raw-dumps",safe_name(b.get("title") or "Quick note.txt"));p.write_text(t,encoding="utf-8")
  return self.send_json({"ok":True,"message":"Saved to Scribble Inbox.","path":str(p.relative_to(PROJECT_ROOT))})
 def preview(self):
  b=json.loads(self.read_body() or b"{}"); paths=b.get("paths") or []
  if not paths:raise ValueError("Select at least one brain dump")
  result=[]
  for x in paths:
   p=find_file(x)
   if p.relative_to(PROJECT_ROOT).parts[0] not in {"raw-dumps","triage"}:raise ValueError("Tagging is only for Inbox/triage material")
   result.append(tag_preview(p))
  return self.send_json({"ok":True,"preview":result})
 def tag(self):
  b=json.loads(self.read_body() or b"{}");paths=b.get("paths") or []
  if not paths:raise ValueError("Select at least one brain dump")
  safety.create_snapshot("before-tagging");done=[];errors=[]
  for x in paths:
   try:
    p=find_file(x)
    if p.relative_to(PROJECT_ROOT).parts[0] not in {"raw-dumps","triage"}:raise ValueError("Tagging is only for Inbox/triage material")
    done.append(tagger.tag_file(str(p),use_llm=bool(b.get("use_llm",True)) and llm.llm_available()))
   except Exception as e:errors.append({"file":x,"error":str(e)})
  return self.send_json({"ok":True,"tagged":done,"errors":errors})
 def analyze(self):
  b=json.loads(self.read_body() or b"{}");paths=b.get("paths") or [];tools=[x for x in b.get("tools",[]) if x in TOOLS]
  if not paths:raise ValueError("Select at least one chapter or draft")
  if not tools:raise ValueError("Select at least one analysis tool")
  safety.create_snapshot("before-analysis");allf=db.get_all_files();results=[];selected=[]
  for x in paths:
   p=find_file(x);folder=p.relative_to(PROJECT_ROOT).parts[0]
   if folder not in {"chapters","drafts","final"}:raise ValueError("Raw brain dumps cannot be analysed. Move/import them as chapters or drafts first.")
   text=body(p);row={"filename":p.name,"results":{}}
   if len(text.split())<10:raise ValueError(f"{p.name} is too short for meaningful analysis")
   for tool in tools:
    r=js(run_tool(tool,text,allf));db.save_analysis(str(p.resolve()),tool,r);row["results"][tool]=r
   results.append(row);selected.append({"label":p.stem,"path":str(p),"text":text})
  if len(selected)>1 and any(x in tools for x in ("voice_dna","cadence","motifs","anchors")):
   results.append({"filename":"Cross-chapter comparison","results":{"chapter_comparison":js(chapter_comparison(selected))}})
  return self.send_json({"ok":True,"results":results,"message":f"Completed {len(tools)} analysis tool(s) across {len(paths)} file(s)."})
 def export(self):
  b=json.loads(self.read_body() or b"{}");p=find_file(b.get("path"));kind=b.get("kind","docx")
  fn={"docx":export_docx,"md":export_markdown,"txt":export_plain_text}.get(kind)
  if not fn:raise ValueError("Unsupported export")
  return self.send_json({"ok":True,"path":fn(str(p))})
 def html(self):
  d=APP.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(d)));self.end_headers();self.wfile.write(d)

def run_server(open_browser=True):
 for f in FOLDERS:(PROJECT_ROOT/f).mkdir(parents=True,exist_ok=True)
 (PROJECT_ROOT/"data").mkdir(parents=True,exist_ok=True);db.get_db().close();s=ThreadingHTTPServer(("127.0.0.1",0),Handler)
 if open_browser:
  import webbrowser;webbrowser.open(f"http://127.0.0.1:{s.server_port}/")
 return s

APP=r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Audhd Scribbler 4.0</title><style>
:root{--ink:#28312f;--muted:#707975;--paper:#f8f7f3;--panel:#fff;--line:#ddd9d0;--accent:#4f7375;--soft:#e9efed;--danger:#fff0ed}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.5 Segoe UI,Arial,sans-serif}.top{height:70px;background:#28312f;color:white;display:flex;align-items:center;padding:0 28px;gap:20px;position:sticky;top:0;z-index:5}.brand{font:bold 24px Georgia}.sub{opacity:.65;font-size:12px}.top .right{margin-left:auto;display:flex;gap:10px;align-items:center}.top button{background:#374442;color:#fff;border:1px solid #5d6967;border-radius:7px;padding:8px 12px}.app{display:grid;grid-template-columns:230px minmax(0,1100px);max-width:1400px;margin:auto;min-height:calc(100vh - 70px)}aside{background:#f0eee8;border-right:1px solid var(--line);padding:24px 14px}aside h4{text-transform:uppercase;font-size:10px;letter-spacing:1.4px;color:var(--muted);margin:12px 10px 6px}nav button{display:block;width:100%;border:0;background:transparent;text-align:left;padding:11px 12px;border-radius:8px;color:var(--ink);cursor:pointer}nav button.active,nav button:hover{background:#dfe8e5}main{padding:32px 38px}.view{display:none}.view.active{display:block}h1{font:700 35px Georgia;margin:0 0 7px}h2{font:700 24px Georgia;margin:0 0 7px}h3{font:700 18px Georgia;margin:0 0 5px}.lead{color:var(--muted);max-width:780px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}.card,.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}.card p,.muted{color:var(--muted)}.panel{margin:16px 0}.actions{display:flex;gap:9px;flex-wrap:wrap;margin:16px 0}.btn{border:1px solid var(--line);background:#fff;padding:9px 13px;border-radius:7px;cursor:pointer}.primary{background:var(--accent);color:#fff;border-color:var(--accent)}.filelist{border:1px solid var(--line);border-radius:9px;background:#fff;max-height:420px;overflow:auto}.file{display:flex;gap:12px;align-items:center;padding:11px;border-bottom:1px solid var(--line)}.file:last-child{border:0}.file input{width:18px;height:18px}.file .meta{margin-left:auto;color:var(--muted);font-size:12px}.tools{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.tool{border:1px solid var(--line);border-radius:9px;padding:13px;background:#fff;cursor:pointer}.tool:has(input:checked){border-color:var(--accent);background:var(--soft)}.tool strong{display:block}.tool small{color:var(--muted)}textarea,input[type=text]{width:100%;padding:11px;border:1px solid var(--line);border-radius:8px;font:inherit}.notearea{min-height:220px}.results{background:#fff;border:1px solid var(--line);border-radius:9px;padding:15px;max-height:620px;overflow:auto}pre{white-space:pre-wrap;background:#f0eee8;padding:12px;border-radius:7px;font:12px Consolas}.tagbox{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.tag{background:var(--soft);padding:10px;border-radius:8px}.notice{padding:12px;border-radius:8px;background:var(--soft);margin:10px 0}.danger{background:var(--danger)}.empty{text-align:center;padding:30px;color:var(--muted)}.version{font-size:11px;opacity:.55}@media(max-width:850px){.app{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid var(--line);padding:8px;overflow:auto}nav{display:flex;gap:4px}nav button{white-space:nowrap;width:auto}main{padding:22px}.grid{grid-template-columns:1fr}.tools,.tagbox{grid-template-columns:1fr}.sub{display:none}}
</style></head><body><header class="top"><div class="brand">Audhd Scribbler</div><div class="sub">one workspace for ideas, writing & analysis</div><div class="right"><span id="status">Ready</span><button onclick="backup()">Backup</button></div></header><div class="app"><aside><nav><h4>Workspace</h4><button data-v="home" class="active">Home</button><button data-v="inbox">Scribble Inbox</button><button data-v="manuscript">Manuscript</button><button data-v="analysis">Analysis Suite</button><h4>Utilities</h4><button data-v="notes">Quick Note</button><button data-v="exports">Export & Safety</button></nav><div class="version">Scribbler 4.0</div></aside><main>
<section id="home" class="view active"><h1>Your writing workshop</h1><p class="lead">Messy material and serious writing live together without being confused. Nothing is analysed until you choose it.</p><div class="grid"><div class="card"><h3>Scribble Inbox</h3><p>Import dumps or type a thought. Tag first; don't polish prematurely.</p><button class="btn primary" onclick="openImport('raw-dumps')">Import brain dumps</button></div><div class="card"><h3>Manuscript</h3><p>Import chapters and drafts into the material that analysis is allowed to touch.</p><button class="btn primary" onclick="openImport('chapters')">Import chapter / draft</button></div><div class="card"><h3>Analysis Suite</h3><p>Pick the exact writing and exact questions. Individual tools plus a cautious run-all.</p><button class="btn primary" onclick="go('analysis')">Open suite</button></div></div><div class="panel"><h3>The simple rule</h3><p><b>Inbox gets organised. Manuscript gets analysed.</b> Your source prose is never silently rewritten by analysis.</p></div></section>
<section id="inbox" class="view"><h1>Scribble Inbox</h1><p class="lead">Raw thoughts, voice transcripts, fragments and half-formed ideas.</p><div class="actions"><button class="btn primary" onclick="openImport('raw-dumps')">＋ Import raw dumps</button><button class="btn" onclick="go('notes')">＋ Quick note</button><button class="btn" onclick="previewTags()">Preview tags</button><button class="btn" onclick="applyTags()">Apply tags</button></div><div class="panel"><div id="inboxList" class="filelist"></div></div></section>
<section id="manuscript" class="view"><h1>Manuscript</h1><p class="lead">Chapters, drafts and final material. This is the analysis side of Scribbler.</p><div class="actions"><button class="btn primary" onclick="openImport('chapters')">＋ Import chapter</button><button class="btn" onclick="openImport('drafts')">＋ Import draft</button><button class="btn" onclick="go('analysis')">Analyse selected</button></div><div class="panel"><div id="manuscriptList" class="filelist"></div></div></section>
<section id="analysis" class="view"><h1>Analysis Suite</h1><p class="lead">Every tool is explicit. Some are deterministic; AI is used only where interpretation adds value.</p><div class="panel"><h3>1 · Choose manuscript material</h3><div id="analysisList" class="filelist"></div></div><div class="panel"><h3>2 · Choose tools</h3><div id="tools" class="tools"></div><div class="actions"><button class="btn" onclick="recommended()">Recommended</button><button class="btn" onclick="selectAllTools()">Select all</button><button class="btn" onclick="clearTools()">Clear</button><button class="btn primary" onclick="runAnalysis()">Run selected</button></div><div class="notice">Run All is available as <b>Select all</b>, but Scribbler does not pretend every diagnostic is compatible. Review the tools you want first; findings are observations, not instructions.</div></div><div class="panel"><h3>Results</h3><div id="results" class="results"><div class="empty">Choose writing and tools, then run.</div></div></div></section>
<section id="notes" class="view"><h1>Quick Note</h1><p class="lead">A scratchpad for the thought that arrives before you have time to organise it.</p><div class="panel"><input id="noteTitle" type="text" placeholder="Optional title"><br><br><textarea id="noteText" class="notearea" placeholder="Write the thought here…"></textarea><div class="actions"><button class="btn primary" onclick="saveNote()">Save to Scribble Inbox</button></div></div></section>
<section id="exports" class="view"><h1>Export & Safety</h1><p class="lead">Backups and exports are copies. Existing files are never silently overwritten.</p><div class="panel"><h3>Portable project backup</h3><p class="muted">Includes writing folders, database and manifest.</p><button class="btn primary" onclick="backup()">Create project backup ZIP</button></div><div class="panel"><h3>Export selected manuscript</h3><p class="muted">Select one manuscript file below, then choose a format.</p><div id="exportList" class="filelist"></div><div class="actions"><button class="btn" onclick="exportFile('docx')">DOCX</button><button class="btn" onclick="exportFile('md')">Markdown</button><button class="btn" onclick="exportFile('txt')">Plain text</button></div></div><div class="panel"><h3>Safety</h3><p>Important operations create a local snapshot first. Analysis history is retained. Tagging never intentionally changes the prose body.</p></div></section>
</main></div><input id="upload" type="file" multiple accept=".txt,.md,.text" hidden><div id="modal"></div><script>
let DATA={files:[]},status=document.getElementById('status');const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));const setStatus=x=>status.textContent=x;function go(id){document.querySelectorAll('.view').forEach(x=>x.classList.toggle('active',x.id===id));document.querySelectorAll('nav button[data-v]').forEach(x=>x.classList.toggle('active',x.dataset.v===id));render()}document.querySelectorAll('nav button[data-v]').forEach(x=>x.onclick=()=>go(x.dataset.v));async function load(){DATA=await(await fetch('/api/files')).json()}function by(folders){return DATA.files.filter(x=>folders.includes(x.folder))}function list(items,scope){if(!items.length)return '<div class="empty">Nothing here yet.</div>';return items.map(x=>`<label class="file"><input type="checkbox" data-s="${scope}" value="${esc(x.path)}"><span><b>${esc(x.filename)}</b><br><span class="muted">${x.word_count||0} words · ${esc(x.status)}${x.last_analyzed?' · analysed':''}</span></span><span class="meta">${esc(x.folder)}</span></label>`).join('')}function selected(s){return [...document.querySelectorAll(`input[data-s="${s}"]:checked`)].map(x=>x.value)}function render(){document.getElementById('inboxList').innerHTML=list(by(['raw-dumps','triage']),'inbox');document.getElementById('manuscriptList').innerHTML=list(by(['chapters','drafts','final']),'manuscript');document.getElementById('analysisList').innerHTML=list(by(['chapters','drafts','final']),'analysis');document.getElementById('exportList').innerHTML=list(by(['chapters','drafts','final']),'export');renderTools()}const TOOLS=[['craft','Craft & Rhythm','Prose'],['voice','Voice & Tense','Prose'],['characters','Characters & Relationships','Story'],['continuity','Continuity & Timeline','Story'],['themes','Themes & Emotional Arc','Story'],['editor','Editorial Patterns','Editorial'],['repetition','Repetition & Echoes','Prose'],['pacing','Pacing & Momentum','Structure'],['structure','Structure & Chapter Purpose','Structure'],['memoir','Memoir Lens','Memoir'],['reader','Reader Experience','Editorial'],['research','Research & Fact Flags','Accuracy'],['cadence','Cadence & Rhythm','Prose'],['motifs','Motifs & Echoes','Story'],['anchors','Structural Anchors','Structure'],['voice_dna','Voice DNA','Writer'],['reader_perception','Reader Perception','Writer']];function renderTools(){document.getElementById('tools').innerHTML=TOOLS.map(t=>`<label class="tool"><input type="checkbox" class="toolbox" value="${t[0]}"><strong>${t[1]}</strong><small>${t[2]} · ${esc((DATA.catalog||{})[t[0]]?.purpose||'Evidence-led analysis tool.')}</small></label>`).join('')}async function openImport(defaultDest){const dest=prompt('Import destination: type INBOX, CHAPTERS or DRAFTS',defaultDest==='raw-dumps'?'INBOX':'CHAPTERS');if(!dest)return;let d=dest.toLowerCase();d=d==='inbox'?'raw-dumps':d==='chapters'?'chapters':d==='drafts'?'drafts':null;if(!d)return alert('Use INBOX, CHAPTERS or DRAFTS.');let i=document.getElementById('upload');i.value='';i.onchange=async()=>{if(!i.files.length)return;let fd=new FormData();fd.append('destination',d);[...i.files].forEach(f=>fd.append('files',f));setStatus('Saving copies…');let j=await(await fetch('/api/import',{method:'POST',body:fd})).json();if(!j.ok)return alert(j.error);await load();render();setStatus('✓ '+j.message);go(d==='raw-dumps'?'inbox':'manuscript')};i.click()}function previewTags(){let p=selected('inbox');if(!p.length)return alert('Select brain dumps first.');fetch('/api/tag-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:p})}).then(r=>r.json()).then(j=>{if(!j.ok)return alert(j.error);document.getElementById('results').innerHTML=j.preview.map(x=>`<div class="panel"><h3>${esc(x.filename)}</h3><div class="tagbox">${[['Voice',x.voice],['Era',x.era],['Emotion',x.emotional_register],['Themes',(x.themes||[]).join(', ')],['Characters',(x.characters||[]).join(', ')],['Places',(x.places||[]).join(', ')],['Sensory',(x.sensory||[]).join(', ')]].map(a=>`<div class="tag"><b>${esc(a[0])}</b><br>${esc(a[1]||'—')}</div>`).join('')}</div></div>`).join('');setStatus('Tag preview ready')})}async function applyTags(){let p=selected('inbox');if(!p.length)return alert('Select brain dumps first.');if(!confirm(`Tag ${p.length} item(s)? A safety snapshot will be created first.`))return;let j=await(await fetch('/api/tag',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:p,use_llm:true})})).json();if(!j.ok)return alert(j.error);await load();render();setStatus(`✓ Tagged ${j.tagged.length} item(s)`);alert(`Tagging saved. ${j.tagged.length} item(s) processed. Your prose was not rewritten.`)}function toolSelected(){return [...document.querySelectorAll('.toolbox:checked')].map(x=>x.value)}function clearTools(){document.querySelectorAll('.toolbox').forEach(x=>x.checked=false)}function selectAllTools(){document.querySelectorAll('.toolbox').forEach(x=>x.checked=true)}function recommended(){clearTools();['craft','voice','characters','continuity','themes','cadence','motifs','anchors'].forEach(k=>{let x=document.querySelector(`.toolbox[value="${k}"]`);if(x)x.checked=true})}async function runAnalysis(){let p=selected('analysis'),t=toolSelected();if(!p.length)return alert('Select one or more chapters/drafts first.');if(!t.length)return alert('Select at least one analysis tool.');if(!confirm(`Run ${t.length} analysis tool(s) across ${p.length} file(s)? A safety snapshot will be created first.`))return;setStatus('Analysing…');let j=await(await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({paths:p,tools:t})})).json();if(!j.ok)return alert(j.error);document.getElementById('results').innerHTML=j.results.map(r=>`<div class="panel"><h3>${esc(r.filename)}</h3>${Object.entries(r.results).map(([k,v])=>`<details open><summary><b>${esc(k)}</b></summary><pre>${esc(JSON.stringify(v,null,2))}</pre></details>`).join('')}</div>`).join('');setStatus('✓ '+j.message)}async function saveNote(){let text=document.getElementById('noteText').value.trim();if(!text)return alert('Write something first.');let j=await(await fetch('/api/note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:document.getElementById('noteTitle').value,text})})).json();if(!j.ok)return alert(j.error);document.getElementById('noteText').value='';document.getElementById('noteTitle').value='';await load();render();setStatus('✓ Saved to Scribble Inbox');go('inbox')}async function backup(){setStatus('Creating backup…');let j=await(await fetch('/api/backup',{method:'POST'})).json();if(!j.ok)return alert(j.error);setStatus('✓ Backup created');alert('Portable project backup created:\n'+j.path)}async function exportFile(kind){let p=selected('export')[0];if(!p)return alert('Select one manuscript file first.');let j=await(await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:p,kind})})).json();if(!j.ok)return alert(j.error);setStatus('✓ Export created');alert('Export created:\n'+j.path)}load().then(render).catch(e=>{status.textContent='Load error';alert(e)});
</script></body></html>'''
