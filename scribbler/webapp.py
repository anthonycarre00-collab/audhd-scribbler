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
 root=Path(os.environ.get("AUDHD_SCRIBBLER_HOME",PROJECT_ROOT))
 p=Path(str(raw)); p=root/p if not p.is_absolute() else p; p=p.resolve()
 try:p.relative_to(root.resolve())
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
  p=x.get("path"); seen.add(p); out.append({"path":p,"filename":x.get("filename"),"folder":x.get("folder"),"word_count":x.get("word_count",0),"status":x.get("status","seedling"),"last_analyzed":x.[...]
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
 return {"filename":p.name,"word_count":len(text.split()),"voice":tagger.detect_voice(text),"era":tagger.detect_era(text),"emotional_register":tagger.detect_emotional_register(text),"sensory":tagg[...]

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
  d=json.dumps(v,ensure_ascii=False).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.s[...]
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
  d=APP.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(d)));se[...]

def run_server(open_browser=True):
 for f in FOLDERS:(PROJECT_ROOT/f).mkdir(parents=True,exist_ok=True)
 (PROJECT_ROOT/"data").mkdir(parents=True,exist_ok=True);db.get_db().close();s=ThreadingHTTPServer(("127.0.0.1",0),Handler)
 if open_browser:
  import webbrowser;webbrowser.open(f"http://127.0.0.1:{s.server_port}/")
 return s

APP=r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Audhd Scribbler 4.0</title><style>
:root{--ink:#28312f;--muted:#707975;--paper:#f8f7f3;--panel:#fff;--line:#ddd9d0;--accent:#4f7375;--soft:#e9efed;--danger:#fff0ed}*{box-sizing:border-box}body{margin:0;background:var(--paper);colo[...]
</style></head><body><header class="top"><div class="brand">Audhd Scribbler</div><div class="sub">one workspace for ideas, writing & analysis</div><div class="right"><span id="status">Ready</span[...]
<section id="home" class="view active"><h1>Your writing workshop</h1><p class="lead">Messy material and serious writing live together without being confused. Nothing is analysed until you choose [...]
<section id="inbox" class="view"><h1>Scribble Inbox</h1><p class="lead">Raw thoughts, voice transcripts, fragments and half-formed ideas.</p><div class="actions"><button class="btn primary" oncli[...]
<section id="manuscript" class="view"><h1>Manuscript</h1><p class="lead">Chapters, drafts and final material. This is the analysis side of Scribbler.</p><div class="actions"><button class="btn pr[...]
<section id="analysis" class="view"><h1>Analysis Suite</h1><p class="lead">Every tool is explicit. Some are deterministic; AI is used only where interpretation adds value.</p><div class="panel"><[...]
<section id="notes" class="view"><h1>Quick Note</h1><p class="lead">A scratchpad for the thought that arrives before you have time to organise it.</p><div class="panel"><input id="noteTitle" type[...]
<section id="exports" class="view"><h1>Export & Safety</h1><p class="lead">Backups and exports are copies. Existing files are never silently overwritten.</p><div class="panel"><h3>Portable projec[...]
</main></div><input id="upload" type="file" multiple accept=".txt,.md,.text" hidden><div id="modal"></div><script>
let DATA={files:[]},status=document.getElementById('status');const esc=s=>String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));const setStatus=x=[...]
</script></body></html>'''
