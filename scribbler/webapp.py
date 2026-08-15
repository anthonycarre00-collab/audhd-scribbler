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
 "craft":("Craft & Rhythm","Prose","Sentence rhythm, balance and craft signals.",craft.analyze),"voice":("Voice & Tense","Prose","Narrator voice, tense and narrative stance.",voice_tense.analyze),"characters":("Characters & Relationships","Story","Presence, relationships and character movement.",characters.analyze),"continuity":("Continuity & Timeline","Story","Chronology, recurring facts and inconsistencies.",continuity.analyze),"themes":("Themes & Emotional Arc","Story","Themes and emotional movement.",themes.analyze),"editor":("Editorial Patterns","Editorial","Clarity, redundancy and editorial signals.",editor.analyze),"repetition":("Repetition & Echoes","Prose","Repeated words and phrases.",None),"pacing":("Pacing & Momentum","Structure","Acceleration, slowing and sentence/paragraph movement.",None),"structure":("Structure & Chapter Purpose","Structure","Openings, endings, paragraph shape and structural signals.",None),"memoir":("Memoir Lens","Memoir","Reflection, event balance and memory uncertainty. Optional for non-memoir work.",None),"reader":("Reader Experience","Editorial","Opening, dialogue and possible reader-friction signals.",None),"research":("Research & Fact Flags","Accuracy","Dates and claims worth checking; never declares facts true/false.",None),"cadence":("Cadence & Rhythm","Prose","Sentence movement, pauses and contrast.",cadence_rhythm),"motifs":("Motifs & Echoes","Story","Recurring words/phrases; candidate patterns, not automatic meanings.",motif_scan),"anchors":("Structural Anchors","Structure","Recurring openings, endings and textual anchors.",structural_anchors),"voice_dna":("Voice DNA","Writer","Compare against approved personal writing samples.",voice_report),"reader_perception":("Reader Perception","Writer","Textual impression of narrator/author and named characters; evidence-first AI when available.",None),}

def safe_name(n):
 n=Path(str(n or "untitled.txt")).name; n=re.sub(r"[^A-Za-z0-9._ -]+","_",n).strip(" .") or "untitled.txt"; return n if Path(n).suffix.lower() in {".txt",".md",".text"} else n+".txt"
def unique(folder,name):
 p=folder/name
 if not p.exists(): return p
 for i in range(2,10000):
  q=folder/f"{p.stem} ({i}){p.suffix}"
  if not q.exists(): return q
 raise RuntimeError("Unable to create a unique filename")
def find_file(raw):
 home=Path(os.environ.get("AUDHD_SCRIBBLER_HOME",str(PROJECT_ROOT))).expanduser().resolve(); p=Path(str(raw)); p=(home/p if not p.is_absolute() else p).resolve()
 try:p.relative_to(home)
 except ValueError:raise ValueError("File is outside the Scribbler project")
 if not p.exists() or not p.is_file() or p.suffix.lower() not in {".txt",".md",".text"}:raise ValueError("Writing file not found")
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
  p=x.get("path"); seen.add(p); out.append({"path":p,"filename":x.get("filename"),"folder":x.get("folder"),"word_count":x.get("word_count",0),"status":x.get("status","seedling"),"last_analyzed":x.get("last_analyzed","")})
 for folder in ("raw-dumps","triage","chapters","drafts","final"):
  root=PROJECT_ROOT/folder
  if root.exists():
   for p in root.iterdir():
    if p.is_file() and p.suffix.lower() in {".txt",".md",".text"}:
     rel=str(p.relative_to(PROJECT_ROOT))
     if rel not in seen:out.append({"path":rel,"filename":p.name,"folder":folder,"word_count":len(body(p).split()),"status":"unindexed","last_analyzed":""})
 return sorted(out,key=lambda x:(x["folder"],x["filename"].lower()))
def tag_preview(p,use_ai=True):
 text=body(p)
 return {"filename":p.name,"word_count":len(text.split()),"voice":tagger.detect_voice(text),"era":tagger.detect_era(text),"emotional_register":tagger.detect_emotional_register(text),"sensory":tagger.detect_sensory(text),"themes":tagger.detect_themes(text),"characters":tagger.detect_characters(text),"places":tagger.detect_places(text),"ai_available":llm.llm_available() if use_ai else False}
def run_tool(key,text,all_files):
 meta=TOOLS[key]; fn=meta[3]
 if key=="reader_perception":
  r=ai_perceptions(text); return r or {"status":"AI unavailable","note":"Enable a configured AI provider for reader-perception analysis."}
 if key=="voice_dna":return voice_report(text)
 if fn:
  if key=="characters":return fn(text,all_files=all_files)
  return fn(text)
 return suite_run(key,text)

class Handler(BaseHTTPRequestHandler):
 server_version="AudhdScribbler/4.0"
 def log_message(self,*a):pass
 def send_json(self,v,status=200):
  d=json.dumps(v,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(d)));self.end_headers();self.wfile.write(d)
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
 def html(self):
  from . import ui
  return self.send_json({"ok":True})

def run_server(open_browser=False):
 return ThreadingHTTPServer(("127.0.0.1",0),Handler)
