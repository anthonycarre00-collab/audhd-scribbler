"""Unified local writer workspace for Audhd Scribbler."""
from __future__ import annotations
import html,json,os,re,urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from datetime import datetime
from . import db,llm,tagger,safety
from .config import PROJECT_ROOT,FOLDERS
from .file_io import read_text_file, write_text_file
from .analysis_catalog import ANALYSIS_CATALOG
from .analyzers import craft,voice_tense,characters,continuity,themes,editor

# Default empty APP HTML — gets replaced by release_ui when ScribblerWindows.py runs
APP = "<!doctype html><html><body><h1>Audhd Scribbler</h1><p>Loading… Run ScribblerWindows.py to start the full UI.</p></body></html>"
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
    if p.is_file() and p.suffix.lower() in {".txt",".md",".text"} and p.name.upper()!="README.MD":
     resolved=str(p.resolve())
     if resolved not in seen:
      seen.add(resolved)
      out.append({"path":str(p),"filename":p.name,"folder":folder,"word_count":len(body(p).split()),"status":"unindexed","last_analyzed":""})
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

def _parse_multipart(body_bytes, boundary):
 """Parse multipart form data without cgi module (deprecated in 3.13)."""
 if isinstance(boundary, str):
  boundary = boundary.encode("utf-8")
 delimiter = b"--" + boundary
 parts = body_bytes.split(delimiter)
 files = []
 fields = {}
 for part in parts:
  if part in (b"", b"--", b"--\r\n", b"\r\n"): continue
  if part.startswith(b"\r\n"): part = part[2:]
  if part.endswith(b"\r\n"): part = part[:-2]
  if b"\r\n\r\n" not in part: continue
  header_part, content = part.split(b"\r\n\r\n", 1)
  headers = header_part.decode("utf-8", errors="replace")
  cd = re.search(r'Content-Disposition:.*?name="([^"]+)"(?:;\s*filename="([^"]*)")?', headers, re.I)
  if not cd: continue
  name = cd.group(1)
  filename = cd.group(2)
  if filename:
   files.append((name, filename, content))
  else:
   fields[name] = content.decode("utf-8", errors="replace")
 return files, fields

class Handler(BaseHTTPRequestHandler):
 server_version="AudhdScribbler/4.0"
 def log_message(self,*a):pass
 def send_json(self,v,status=200):
  d=json.dumps(v,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(d)));self.end_headers();self.wfile.write(d)
 def send_html(self,html_str):
  b=html_str.encode("utf-8");self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(b)));self.end_headers();self.wfile.write(b)
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
   if p=="/api/delete":return self.delete_file()
   if p=="/api/backup":return self.send_json({"ok":True,"path":safety.export_project_zip()})
   return self.send_json({"ok":False,"error":"Unknown action"},404)
  except Exception as e:return self.send_json({"ok":False,"error":str(e)},400)
 def html(self):
  return self.send_html(APP)

 def import_files(self):
  """Handle file upload via multipart form data."""
  ct = self.headers.get("Content-Type","")
  if "multipart/form-data" not in ct:
   return self.send_json({"ok":False,"error":"Expected multipart form data"},400)
  boundary = ct.split("boundary=")[-1].strip().strip('"')
  raw = self.read_body()
  uploaded, fields = _parse_multipart(raw, boundary)
  destination = fields.get("destination","raw-dumps")
  if destination not in ("raw-dumps","triage","chapters","drafts","final"):
   return self.send_json({"ok":False,"error":f"Invalid destination: {destination}"},400)
  dest_folder = PROJECT_ROOT / destination
  dest_folder.mkdir(parents=True, exist_ok=True)
  count = 0
  errors = []
  for _, filename, content in uploaded:
   try:
    name = safe_name(filename)
    dest = unique(dest_folder, name)
    dest.write_bytes(content)
    count += 1
   except Exception as e:
    errors.append(f"{filename}: {e}")
  return self.send_json({"ok":True,"message":f"Imported {count} file(s) into {destination}","errors":errors})

 def note(self):
  """Save a quick note to the Inbox."""
  b = json.loads(self.read_body() or b"{}")
  text = (b.get("text") or "").strip()
  if not text:
   return self.send_json({"ok":False,"error":"Note is empty"},400)
  title = (b.get("title") or "").strip()
  name = safe_name((title or f"note-{datetime.now():%Y%m%d-%H%M%S}") + ".txt")
  dest = unique(PROJECT_ROOT / "raw-dumps", name)
  write_text_file(dest, text)
  return self.send_json({"ok":True,"message":"Saved to Inbox"})

 def preview(self):
  """Preview tags for selected files without applying."""
  b = json.loads(self.read_body() or b"{}")
  paths = b.get("paths") or []
  use_ai = bool(b.get("use_ai", False))
  if not paths:
   return self.send_json({"ok":False,"error":"Select one or more files first"},400)
  previews = []
  errors = []
  for raw_path in paths:
   try:
    p = find_file(raw_path)
    previews.append(tag_preview(p, use_ai))
   except Exception as e:
    errors.append(str(e))
  return self.send_json({"ok":True,"preview":previews,"errors":errors})

 def tag(self):
  """Apply tags to selected files."""
  b = json.loads(self.read_body() or b"{}")
  paths = b.get("paths") or []
  use_llm = bool(b.get("use_llm", True))
  if not paths:
   return self.send_json({"ok":False,"error":"Select one or more files first"},400)
  tagged = []
  errors = []
  for raw_path in paths:
   try:
    p = find_file(raw_path)
    meta = tagger.tag_file(str(p), use_llm=use_llm)
    tagged.append(p.name)
   except Exception as e:
    errors.append(f"{p.name if 'p' in dir() else raw_path}: {e}")
  return self.send_json({"ok":True,"tagged":tagged,"errors":errors})

 def analyze(self):
  """Run analysis tools on selected manuscript files."""
  b = json.loads(self.read_body() or b"{}")
  paths = b.get("paths") or []
  tools = b.get("tools") or []
  if not paths:
   return self.send_json({"ok":False,"error":"Select one or more manuscript files first"},400)
  if not tools:
   return self.send_json({"ok":False,"error":"Choose at least one analysis tool"},400)
  all_files = files()
  results = []
  for raw_path in paths:
   try:
    p = find_file(raw_path)
    text = body(p)
    per_file = {}
    for tool_key in tools:
     if tool_key not in TOOLS:
      per_file[tool_key] = {"error": f"Unknown tool: {tool_key}"}
      continue
     try:
      result = run_tool(tool_key, text, all_files)
      per_file[tool_key] = js(result)
      try:
       db.save_analysis(str(p.resolve()), tool_key, result)
      except Exception:
       pass
     except Exception as e:
      per_file[tool_key] = {"error": str(e)}
    results.append({"filename": p.name, "results": per_file})
   except Exception as e:
    results.append({"filename": raw_path, "results": {}, "error": str(e)})
  return self.send_json({"ok":True,"results":results,"message":f"Analyzed {len(paths)} file(s) with {len(tools)} tool(s)"})

 def export(self):
  """Export a file to docx, md, or txt."""
  b = json.loads(self.read_body() or b"{}")
  file_path = b.get("path") or b.get("file")
  fmt = b.get("format") or b.get("kind") or "docx"
  if not file_path:
   return self.send_json({"ok":False,"error":"No file path provided"},400)
  try:
   p = find_file(file_path)
   if fmt == "docx":
    out = export_docx(str(p))
   elif fmt == "md":
    out = export_markdown(str(p))
   elif fmt == "txt":
    out = export_plain_text(str(p))
   else:
    return self.send_json({"ok":False,"error":f"Unknown format: {fmt}"},400)
   return self.send_json({"ok":True,"path":out})
  except Exception as e:
   return self.send_json({"ok":False,"error":str(e)},500)

 def delete_file(self):
  """Delete a file from the project (moves to archive)."""
  b = json.loads(self.read_body() or b"{}")
  file_path = b.get("path")
  if not file_path:
   return self.send_json({"ok":False,"error":"No file path provided"},400)
  try:
   p = find_file(file_path)
   # Move to archive instead of permanent delete
   archive = PROJECT_ROOT / "archive"
   archive.mkdir(exist_ok=True)
   dest = unique(archive, p.name)
   p.rename(dest)
   # Remove from database
   conn = db.get_db()
   conn.execute("DELETE FROM files WHERE path = ?", (str(p.resolve()),))
   conn.execute("DELETE FROM analysis_results WHERE file_path = ?", (str(p.resolve()),))
   conn.execute("INSERT INTO activity_log (timestamp, action, file_path, details) VALUES (?, ?, ?, ?)",
    (datetime.now().isoformat(), "delete", str(p.resolve()), f"Moved to archive/{dest.name}"))
   conn.commit()
   conn.close()
   return self.send_json({"ok":True,"message":f"Moved to archive/{dest.name}"})
  except Exception as e:
   return self.send_json({"ok":False,"error":str(e)},500)

def run_server(open_browser=False):
 return ThreadingHTTPServer(("127.0.0.1",0),Handler)
