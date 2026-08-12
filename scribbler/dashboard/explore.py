#!/usr/bin/env python3
"""Writer-focused exploration pages.

Uses the existing indexed metadata and prose. No schema changes and no
automatic rewriting of the writer's material.
"""
import html
import re
from collections import Counter, defaultdict
from pathlib import Path

from .. import db
from ..config import PROJECT_ROOT, DASHBOARD_DIR


def esc(value):
    return html.escape(str(value or ""), quote=True)


def title_for(item):
    return Path(item.get("filename", "Untitled")).stem.replace("_", " ").replace("-", " ").strip().title()


def reader_name(item):
    return "reader_" + re.sub(r"[^A-Za-z0-9_-]+", "_", item.get("filename", "file")) + ".html"


def text_for(item):
    path = Path(item.get("path", ""))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if text.startswith("---"):
        match = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.S)
        if match:
            text = text[match.end():]
    text = re.sub(r"<!-- SCRIBBLER SUMMARY[\s\S]*?-->", "", text)
    return text.strip()


CSS = r'''
:root{--paper:#fbfaf7;--ink:#252a2b;--muted:#74766f;--line:#ddd8ce;--accent:#476b70;--warm:#f5eadf;--white:#fffefa;--soft:#e9efed;--serif:Georgia,'Times New Roman',serif;--sans:Inter,'Segoe UI',Arial,sans-serif;--shadow:0 8px 30px rgba(35,38,36,.06)}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 var(--sans)}a{color:inherit}.shell{min-height:100vh}.topbar{border-bottom:1px solid var(--line);background:#f0eee8;padding:16px 28px;display:flex;align-items:center;gap:20px}.brand{font:700 19px var(--serif)}.topbar a{text-decoration:none;color:#59605b;font-size:13px}.main{max-width:1180px;margin:auto;padding:38px 42px 70px}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:1.8px;color:var(--accent);font-weight:700}.title{font:700 40px/1.08 var(--serif);margin:6px 0}.lede{color:var(--muted);max-width:720px}.tabs{display:flex;gap:6px;margin:28px 0;border-bottom:1px solid var(--line);padding-bottom:10px}.tabs a{padding:8px 13px;border-radius:8px;text-decoration:none}.tabs a:hover{background:var(--white)}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.panel{background:var(--white);border:1px solid var(--line);border-radius:13px;padding:22px;box-shadow:var(--shadow)}.panel h2{font:700 23px var(--serif);margin:0 0 4px}.sub{font-size:13px;color:var(--muted)}.item{padding:16px 0;border-bottom:1px solid var(--line)}.item:last-child{border-bottom:0}.item-title{font-weight:700}.meta{font-size:12px;color:var(--muted);margin:3px 0 9px}.tag{display:inline-block;background:var(--soft);color:var(--accent);padding:3px 8px;border-radius:999px;font-size:11px;margin:2px}.passage{margin:10px 0;padding:13px 15px;background:#f7f3eb;border-left:3px solid #c9b49d;font:15px/1.65 var(--serif);color:#454947}.more{font-size:12px;color:var(--accent);font-weight:650;text-decoration:none}.timeline{position:relative;margin-top:28px;padding-left:34px}.timeline:before{content:'';position:absolute;left:10px;top:4px;bottom:4px;width:2px;background:var(--line)}.era{position:relative;margin:0 0 24px}.era:before{content:'';position:absolute;left:-29px;top:5px;width:10px;height:10px;border-radius:50%;background:var(--accent);border:3px solid var(--paper)}.era h3{font:700 21px var(--serif);margin:0}.era-count{font-size:12px;color:var(--muted)}.era-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px;margin-top:10px}.mini{background:var(--white);border:1px solid var(--line);border-radius:10px;padding:12px}.mini a{text-decoration:none}.empty{color:var(--muted);font-style:italic}.bar{height:7px;background:#e7e3dc;border-radius:99px;overflow:hidden;margin-top:7px}.bar i{display:block;height:100%;background:var(--accent)}@media(max-width:800px){.main{padding:25px 18px}.grid{grid-template-columns:1fr}.topbar{padding:13px 18px;flex-wrap:wrap}.title{font-size:32px}}
'''


def page(body):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Explore · The Audhd Scribbler</title><style>{CSS}</style></head><body><header class="topbar"><div class="brand">The Audhd Scribbler</div><a href="dashboard.html">Home</a><a href="manuscript.html">Manuscript</a><a href="explore.html">Explore</a><a href="analysis.html">Analysis</a></header><main class="main">{body}</main></body></html>'''


def passage_for(item):
    text = re.sub(r"\s+", " ", text_for(item)).strip()
    if not text:
        return ""
    return text[:360] + ("…" if len(text) > 360 else "")


def generate_explore():
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    files = db.get_all_files()
    people = defaultdict(list)
    themes = defaultdict(list)
    eras = defaultdict(list)

    for item in files:
        for name in item.get("characters") or []:
            people[str(name)].append(item)
        for name in item.get("themes") or []:
            themes[str(name)].append(item)
        era = item.get("era") or "Unplaced in time"
        eras[str(era)].append(item)

    person_blocks=[]
    for name, items in sorted(people.items(), key=lambda x:(-len(x[1]), x[0].lower())):
        links=[]
        for item in items[:8]:
            p=passage_for(item)
            links.append(f'<div class="item"><a class="more" href="{esc(reader_name(item))}">{esc(title_for(item))}</a><div class="passage">{esc(p)}</div></div>')
        person_blocks.append(f'<article class="panel"><h2>{esc(name)}</h2><div class="sub">Appears in {len(items)} piece(s)</div>{"".join(links)}{"<div class=\"sub\">+ %d more</div>"%(len(items)-8) if len(items)>8 else ""}</article>')

    theme_counts=Counter({k:len(v) for k,v in themes.items()})
    max_theme=max(theme_counts.values()) if theme_counts else 1
    theme_blocks=[]
    for name,count in theme_counts.most_common():
        items=themes[name]
        examples="".join(f'<div class="item"><a class="more" href="{esc(reader_name(i))}">{esc(title_for(i))}</a><div class="passage">{esc(passage_for(i))}</div></div>' for i in items[:3])
        theme_blocks.append(f'<article class="panel"><h2>{esc(name)}</h2><div class="sub">{count} piece(s)</div><div class="bar"><i style="width:{max(8,int(count/max_theme*100))}%"></i></div>{examples}</article>')

    era_blocks=[]
    for era,items in sorted(eras.items(), key=lambda x:x[0].lower()):
        cards="".join(f'<div class="mini"><a href="{esc(reader_name(i))}"><strong>{esc(title_for(i))}</strong></a><div class="meta">{i.get("word_count",0):,} words · {esc(i.get("status","seedling"))}</div></div>' for i in items)
        era_blocks.append(f'<section class="era"><h3>{esc(era)}</h3><div class="era-count">{len(items)} piece(s)</div><div class="era-list">{cards}</div></section>')

    body=f'''<div class="eyebrow">Explore</div><h1 class="title">See what keeps turning up.</h1><p class="lede">These views are here to help you notice connections. They don't decide what your memoir means — they simply make the material easier to see.</p><nav class="tabs"><a href="#people">People</a><a href="#themes">Themes</a><a href="#time">Time</a></nav><section id="people"><div class="eyebrow">People</div><h2 style="font:700 27px var(--serif);margin:5px 0">Who keeps appearing?</h2><p class="sub">Open a piece to read the actual passage rather than just looking at a count.</p><div class="grid">{"".join(person_blocks) or '<div class="panel"><p class="empty">No people have been tagged yet.</p></div>'}</div></section><section id="themes" style="margin-top:50px"><div class="eyebrow">Themes</div><h2 style="font:700 27px var(--serif);margin:5px 0">What keeps coming back?</h2><p class="sub">Frequency is only a clue. The excerpts are the useful part.</p><div class="grid">{"".join(theme_blocks) or '<div class="panel"><p class="empty">No themes have been tagged yet.</p></div>'}</div></section><section id="time" style="margin-top:50px"><div class="eyebrow">Time</div><h2 style="font:700 27px var(--serif);margin:5px 0">Where does the memoir happen?</h2><p class="sub">This uses the era information already attached to your material.</p><div class="timeline">{"".join(era_blocks) or '<p class="empty">No eras have been tagged yet.</p>'}</div></section>'''
    out=DASHBOARD_DIR/"explore.html"
    out.write_text(page(body),encoding="utf-8")
    return str(out)


__all__=["generate_explore"]
