#!/usr/bin/env python3
"""Turn existing analysis results into writer-facing findings.

The analyzers remain untouched. This layer changes presentation only.
"""
import html
import json
import re
from pathlib import Path

from .. import db
from ..config import PROJECT_ROOT, DASHBOARD_DIR


def esc(v):
    return html.escape(str(v or ""), quote=True)


def title_for(item):
    return Path(item.get("filename", "Untitled")).stem.replace("_", " ").replace("-", " ").strip().title()


def reader_name(item):
    return "reader_" + re.sub(r"[^A-Za-z0-9_-]+", "_", item.get("filename", "file")) + ".html"


def read_text(item):
    path=Path(item.get("path", ""))
    if not path.is_absolute(): path=PROJECT_ROOT/path
    try: text=path.read_text(encoding="utf-8",errors="replace")
    except Exception: return ""
    if text.startswith("---"):
        m=re.match(r"^---\s*\n.*?\n---\s*\n",text,re.S)
        if m: text=text[m.end():]
    return re.sub(r"<!-- SCRIBBLER SUMMARY[\s\S]*?-->","",text).strip()

CSS='''
:root{--paper:#fbfaf7;--ink:#252a2b;--muted:#74766f;--line:#ddd8ce;--accent:#476b70;--warm:#f5eadf;--white:#fffefa;--serif:Georgia,"Times New Roman",serif;--sans:Inter,"Segoe UI",Arial,sans-serif;--shadow:0 8px 30px rgba(35,38,36,.06)}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 var(--sans)}a{color:inherit}.topbar{border-bottom:1px solid var(--line);background:#f0eee8;padding:16px 28px;display:flex;align-items:center;gap:20px}.brand{font:700 19px var(--serif)}.topbar a{text-decoration:none;color:#59605b;font-size:13px}.main{max-width:1060px;margin:auto;padding:42px 34px 70px}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:1.8px;color:var(--accent);font-weight:700}.title{font:700 40px/1.08 var(--serif);margin:6px 0}.lede{color:var(--muted);max-width:720px}.card{background:var(--white);border:1px solid var(--line);border-radius:13px;padding:22px;margin-top:18px;box-shadow:var(--shadow)}.card h2{font:700 23px var(--serif);margin:0}.meta{font-size:12px;color:var(--muted);margin:4px 0 16px}.finding{border-top:1px solid var(--line);padding:18px 0}.finding:first-child{border-top:0}.finding h3{margin:0 0 6px;font:700 18px var(--serif)}.label{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--accent);font-weight:700}.why{color:#555b57}.passage{background:#f7f3eb;border-left:3px solid #c9b49d;padding:13px 15px;margin-top:11px;font:15px/1.7 var(--serif)}.link{display:inline-block;margin-top:9px;color:var(--accent);font-size:12px;font-weight:700;text-decoration:none}.strength{background:#edf3ef}.empty{color:var(--muted);font-style:italic}@media(max-width:700px){.main{padding:28px 18px}.title{font-size:32px}.topbar{padding:13px 18px;flex-wrap:wrap}}
'''

def page(body):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Analysis · The Audhd Scribbler</title><style>{CSS}</style></head><body><header class="topbar"><div class="brand">The Audhd Scribbler</div><a href="dashboard.html">Home</a><a href="manuscript.html">Manuscript</a><a href="explore.html">Explore</a><a href="analysis.html">Analysis</a></header><main class="main">{body}</main></body></html>'''

def excerpt(text, needle=None):
    clean=re.sub(r"\s+"," ",text).strip()
    if not clean:return ""
    if needle:
        pos=clean.lower().find(str(needle).lower())
        if pos>=0:return clean[max(0,pos-110):pos+250]
    return clean[:330]+("…" if len(clean)>330 else "")

def collect_findings(item):
    findings=[]
    for tool in ["craft","voice_tense","characters","continuity","themes","editor"]:
        result=db.get_analysis(str(Path(item.get("path","")).resolve()),tool)
        if not result: continue
        if result.get("strengths"):
            for s in result["strengths"][:2]: findings.append(("strength", "A strength worth keeping", str(s), "", item))
        for obs in result.get("observations",[])[:3]:
            if isinstance(obs,dict):
                text=obs.get("formatted") or obs.get("description") or obs.get("observation") or ""
                if text: findings.append(("observation", obs.get("category","Something to notice").replace("_"," ").title(), str(text), obs.get("why") or obs.get("recommendation") or "This is a place you may want to look at, not a rule you have to obey.", item))
            elif obs: findings.append(("observation", tool.replace("_"," ").title(), str(obs), "See what happens in the actual prose.", item))
        summary=result.get("summary")
        if summary and not findings: findings.append(("summary",tool.replace("_"," ").title(),str(summary),"Use this as a prompt for exploration rather than a verdict.",item))
    return findings[:12]

def generate_analysis_view():
    DASHBOARD_DIR.mkdir(parents=True,exist_ok=True)
    files=db.get_all_files()
    cards=[]
    for item in files:
        findings=collect_findings(item)
        if not findings: continue
        text=read_text(item)
        blocks=[]
        for kind,heading,observation,why,_ in findings:
            passage=excerpt(text, observation[:30])
            blocks.append(f'<div class="finding"><div class="label">{esc(heading)}</div><h3>{esc(observation)}</h3><div class="why"><strong>Why it might matter:</strong> {esc(why)}</div><div class="passage">{esc(passage)}</div><a class="link" href="{esc(reader_name(item))}">Open the writing →</a></div>')
        cards.append(f'<article class="card"><h2>{esc(title_for(item))}</h2><div class="meta">{item.get("word_count",0):,} words · {esc(item.get("status","seedling"))}</div>{"".join(blocks)}</article>')
    body=f'''<div class="eyebrow">Analysis</div><h1 class="title">What the writing is doing.</h1><p class="lede">The analysis engines look for patterns. This page puts those patterns back beside the writing so you can decide whether they matter.</p><div class="card strength"><strong>How to use this:</strong> Keep what is useful. Ignore what isn't. A finding is an invitation to look, not an instruction to rewrite.</div>{"".join(cards) or '<div class="card"><p class="empty">No saved analysis results yet. Run analysis on a piece of writing and come back here.</p></div>'}'''
    out=DASHBOARD_DIR/"analysis.html";out.write_text(page(body),encoding="utf-8");return str(out)

__all__=["generate_analysis_view"]
