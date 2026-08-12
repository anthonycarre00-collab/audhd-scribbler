#!/usr/bin/env python3
"""Writer-first static workspace for The Audhd Scribbler."""
import html
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from .. import db
from ..config import PROJECT_ROOT, DASHBOARD_DIR

CSS = r'''
:root{--paper:#fbfaf7;--ink:#252a2b;--muted:#74766f;--line:#ddd8ce;--accent:#476b70;--warm:#f5eadf;--soft:#e9efed;--white:#fffefa;--shadow:0 8px 30px rgba(35,38,36,.06);--serif:Georgia,'Times New Roman',serif;--sans:Inter,'Segoe UI',Arial,sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 var(--sans)}a{color:inherit}.shell{display:grid;grid-template-columns:220px 1fr;min-height:100vh}.side{position:sticky;top:0;height:100vh;background:#f0eee8;border-right:1px solid var(--line);padding:30px 18px;display:flex;flex-direction:column}.brand{font:700 22px/1.05 var(--serif)}.tagline{font-size:12px;color:var(--muted);margin:6px 0 30px}.nav a{display:block;padding:10px 12px;margin:2px 0;text-decoration:none;border-radius:8px;color:#535751}.nav a:hover{background:var(--white);color:var(--accent)}.side-foot{margin-top:auto;font-size:11px;color:var(--muted)}.main{max-width:1180px;width:100%;padding:38px 44px 70px;margin:auto}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;margin-bottom:30px}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:1.8px;color:var(--accent);font-weight:700}.title{font:700 38px/1.08 var(--serif);margin:6px 0}.lede{color:var(--muted);max-width:700px}.search{width:330px;background:var(--white);border:1px solid var(--line);border-radius:10px;padding:12px 14px;font:14px var(--sans)}.grid{display:grid;gap:18px}.two{grid-template-columns:1.25fr .75fr}.three{grid-template-columns:repeat(3,1fr)}.panel,.hero,.stat,.filecard{background:var(--white);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow)}.panel{padding:23px}.hero{padding:27px;background:linear-gradient(135deg,#eef2ef,#f8eee6)}.panel h2,.hero h2{font:700 22px var(--serif);margin:0 0 5px}.sub{font-size:13px;color:var(--muted)}.btn{display:inline-block;border:1px solid var(--accent);color:var(--accent);padding:8px 13px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;background:transparent;cursor:pointer}.btn.primary{background:var(--accent);color:white}.stat{padding:17px 18px}.stat b{display:block;font:700 27px var(--serif);color:var(--accent)}.stat span{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}.item{padding:14px 0;border-bottom:1px solid var(--line)}.item:last-child{border:0}.item a{text-decoration:none}.item-title{font-weight:650}.item-meta{font-size:12px;color:var(--muted);margin-top:3px}.pill,.status{display:inline-block;border-radius:999px;padding:3px 9px;font-size:11px;background:var(--soft);color:var(--accent);margin:2px}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}.filecard{padding:17px}.filecard h3{font:700 18px var(--serif);margin:0 0 5px}.excerpt{font:14px/1.55 var(--serif);color:#555a55;margin:12px 0}.bar{height:6px;background:#e6e3dc;border-radius:99px;overflow:hidden}.bar i{display:block;height:100%;background:var(--accent)}.table{width:100%;border-collapse:collapse}.table td,.table th{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left}.table th{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}.notice{padding:15px 17px;background:var(--warm);border:1px solid #ead9c9;border-radius:10px}.empty{color:var(--muted);font-style:italic}.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:25px}.prose{font:18px/1.85 var(--serif);max-width:760px}.prose p{margin:0 0 1.2em}.reader-head{border-bottom:1px solid var(--line);padding-bottom:25px;margin-bottom:34px}.reader-head h1{font:700 42px/1.1 var(--serif);margin:7px 0 12px}.reader-meta{color:var(--muted);font-size:13px}.focus .side{display:none}.focus .shell{display:block}.focus .main{max-width:820px;padding-top:70px}.focus .prose{font-size:20px;line-height:1.95}.focus .reader-tools{display:none}.results-empty{grid-column:1/-1}@media(max-width:850px){.shell{grid-template-columns:1fr}.side{display:none}.main{padding:25px 18px}.top{display:block}.search{width:100%;margin-top:18px}.two,.three{grid-template-columns:1fr}.title{font-size:31px}}
'''

def esc(value):
    return html.escape(str(value or ''),quote=True)

def title_for(item):
    return Path(item.get('filename','Untitled')).stem.replace('_',' ').replace('-',' ').strip().title()

def reader_name(item):
    return 'reader_'+re.sub(r'[^A-Za-z0-9_-]+','_',item.get('filename','file'))+'.html'

def content_for(path):
    try:text=Path(path).read_text(encoding='utf-8',errors='replace')
    except Exception:return ''
    if text.startswith('---'):
        m=re.match(r'^---\s*\n.*?\n---\s*\n',text,re.S)
        if m:text=text[m.end():]
    return re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->','',text).strip()

def page(title,body):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · The Audhd Scribbler</title><style>{CSS}</style></head><body><div class="shell"><aside class="side"><div class="brand">The Audhd<br>Scribbler</div><div class="tagline">A calm place for messy writing.</div><nav class="nav"><a href="dashboard.html">Home</a><a href="dashboard.html#writing">Writing</a><a href="dashboard.html#organise">Organise</a><a href="explore.html">Explore</a><a href="analysis.html">Analyse</a><a href="manuscript.html">Manuscript</a><a href="dashboard.html#search">Search</a></nav><div class="side-foot">Your writing stays on this computer.<br><br>Generated {datetime.now().strftime('%d %b %Y')}</div></aside><main class="main">{body}</main></div></body></html>'''

def generate():
    DASHBOARD_DIR.mkdir(parents=True,exist_ok=True)
    files=db.get_all_files(); stats=db.get_stats()
    chapters=[f for f in files if f.get('folder') in ('chapters','drafts','final')]
    raw=[f for f in files if f.get('folder') in ('raw-dumps','triage')]
    recent=sorted(files,key=lambda x:x.get('last_modified') or '',reverse=True)[:6]
    chars=Counter(c for f in files for c in (f.get('characters') or [])); themes=Counter(t for f in files for t in (f.get('themes') or []))
    statuses=Counter(f.get('status','seedling') for f in files); folders=Counter(f.get('folder','') for f in files)
    index=[]
    for f in files:
        p=Path(f.get('path','')); p= p if p.is_absolute() else PROJECT_ROOT/p; text=content_for(p) if p.exists() else ''
        index.append({'name':title_for(f),'file':reader_name(f),'folder':f.get('folder',''),'status':f.get('status','seedling'),'era':f.get('era',''),'characters':f.get('characters') or [],'places':f.get('places') or [],'themes':f.get('themes') or [],'text':text[:10000].lower(),'excerpt':re.sub(r'\s+',' ',text)[:260]})
    if recent:
        f=recent[0]; text=content_for(f.get('path','')); continue_html=f'''<div class="eyebrow">Continue where you left off</div><h2>{esc(title_for(f))}</h2><p class="sub">{f.get('word_count',0):,} words · {esc(f.get('status','seedling'))}</p><p class="excerpt">{esc(re.sub(r'\s+',' ',text)[:280])}</p><a class="btn primary" href="{esc(reader_name(f))}">Open this writing →</a>'''
    else:continue_html='<p class="empty">No writing is indexed yet. Drop material into raw-dumps and tag it.</p>'
    worthwhile=[]; loose=[f for f in raw if not(f.get('themes') or f.get('characters') or f.get('places'))]; seedlings=[f for f in files if f.get('status')=='seedling']
    if loose:worthwhile.append(('Loose material',f'{len(loose)} piece(s) have little or no tagging.'))
    if seedlings:worthwhile.append(('Fresh material',f'{len(seedlings)} piece(s) are still seedling material.'))
    if chars:
        n,c=chars.most_common(1)[0]; worthwhile.append(('A person keeps appearing',f'{n} appears in {c} piece(s).'))
    if not worthwhile:worthwhile=[('Nothing urgent','There is no need to manufacture work when nothing is asking for attention.')]
    worth_html=''.join(f'<div class="item"><div class="item-title">{esc(a)}</div><div class="item-meta">{esc(b)}</div></div>' for a,b in worthwhile[:3])
    cards=[]
    for f in files:
        p=Path(f.get('path',''));p=p if p.is_absolute() else PROJECT_ROOT/p;text=content_for(p) if p.exists() else ''
        cards.append(f'<article class="filecard"><h3><a href="{esc(reader_name(f))}" style="text-decoration:none">{esc(title_for(f))}</a></h3><div class="item-meta">{f.get("word_count",0):,} words · {esc(f.get("folder",""))}</div><p class="excerpt">{esc(re.sub(r"\s+"," ",text)[:180])}</p><span class="status">{esc(f.get("status","seedling"))}</span></article>')
    people_html=''.join(f'<div class="item"><div class="item-title">{esc(n)}</div><div class="item-meta">{c} piece(s)</div></div>' for n,c in chars.most_common(12)) or '<p class="empty">No people tagged yet.</p>'
    mt=max(themes.values()) if themes else 1; theme_html=''.join(f'<div class="item"><div class="item-title">{esc(n)}</div><div class="bar"><i style="width:{max(8,int(c/mt*100))}%"></i></div><div class="item-meta">{c} piece(s)</div></div>' for n,c in themes.most_common(10)) or '<p class="empty">No themes tagged yet.</p>'
    raw_html=''.join(f'<div class="item"><a href="{esc(reader_name(f))}"><div class="item-title">{esc(title_for(f))}</div><div class="item-meta">{f.get("word_count",0):,} words · {esc(f.get("status","seedling"))}</div></a></div>' for f in raw[:12]) or '<p class="empty">Your scribble inbox is empty.</p>'
    recent_html=''.join(f'<div class="item"><a href="{esc(reader_name(f))}"><div class="item-title">{esc(title_for(f))}</div><div class="item-meta">{f.get("word_count",0):,} words · {esc(f.get("status","seedling"))}</div></a></div>' for f in recent)
    status_html=''.join(f'<span class="pill">{esc(n)} · {c}</span>' for n,c in statuses.items()); folder_html=''.join(f'<tr><td>{esc(n)}</td><td>{c}</td></tr>' for n,c in folders.items())
    data=json.dumps(index,ensure_ascii=False)
    body=f'''<section class="top"><div><div class="eyebrow">Your writing workspace</div><h1 class="title">A place for the messy bits.</h1><p class="lede">Write first. Organise when useful. Explore what keeps turning up. The Scribbler remembers the things you don't want to keep in your head.</p></div><input id="searchBox" class="search" placeholder="Search your writing…"></section><section class="grid two"><div class="hero">{continue_html}</div><div class="panel"><div class="eyebrow">Three things worth looking at</div>{worth_html}</div></section><section class="grid three" style="margin-top:18px"><div class="stat"><b>{stats.get('total_words',0):,}</b><span>words</span></div><div class="stat"><b>{stats.get('total_files',0)}</b><span>pieces</span></div><div class="stat"><b>{len(chapters)}</b><span>chapter / draft pieces</span></div></section><section id="writing" style="margin-top:38px"><div class="eyebrow">Writing</div><h2 style="font:700 28px var(--serif);margin:4px 0">Your material</h2><p class="sub">Nothing has to be finished to belong here.</p><div class="cards">{"".join(cards)}</div></section><section id="organise" class="grid two" style="margin-top:38px"><div class="panel"><h2>Scribble Inbox</h2><p class="sub">Raw and early material. Keep it messy until you know what it is.</p>{raw_html}</div><div class="panel"><h2>Project shape</h2><p class="sub">Where your material currently lives.</p><div>{status_html}</div><table class="table" style="margin-top:14px"><tbody>{folder_html}</tbody></table></div></section><section id="explore" class="grid two" style="margin-top:38px"><div class="panel"><h2>People</h2><p class="sub">Who keeps appearing?</p>{people_html}</div><div class="panel"><h2>Themes</h2><p class="sub">What keeps coming back?</p>{theme_html}</div></section><section id="analyse" class="grid two" style="margin-top:38px"><div class="panel"><h2>Analysis</h2><p class="sub">Patterns are prompts, not verdicts.</p><div class="notice"><b>Writer-first rule:</b> analysis should point you back to the writing, not bury you in numbers.</div><p><a class="btn" href="analysis.html">Open analysis →</a></p></div><div class="panel"><h2>Recently changed</h2>{recent_html}</div></section><section id="search" class="panel" style="margin-top:38px"><h2>Search your writing</h2><p class="sub">Search names, places, themes, eras, statuses and the text itself.</p><div id="results" class="cards"><p class="empty results-empty">Start typing above.</p></div></section><footer style="margin-top:45px;color:var(--muted);font-size:12px">The Audhd Scribbler · local workspace · {datetime.now().strftime('%d %B %Y')}</footer><script>const INDEX={data};const box=document.getElementById('searchBox'),out=document.getElementById('results');box.addEventListener('input',()=>{{const q=box.value.trim().toLowerCase();if(!q){{out.innerHTML='<p class="empty results-empty">Start typing above.</p>';return}}const hits=INDEX.filter(x=>[x.name,x.folder,x.status,x.era,...x.characters,...x.places,...x.themes,x.text].join(' ').toLowerCase().includes(q));out.innerHTML=hits.length?hits.map(x=>`<article class="filecard"><h3><a href="${{x.file}}">${{x.name}}</a></h3><div class="item-meta">${{x.folder}} · ${{x.status}} · ${{x.era||'era not tagged'}}</div><p class="excerpt">${{x.excerpt}}</p><a class="btn" href="${{x.file}}">Read this →</a></article>`).join(''):'<p class="empty results-empty">Nothing found.</p>'}});</script>'''
    (DASHBOARD_DIR/'dashboard.html').write_text(page('Home',body),encoding='utf-8')
    for f in files:
        p=Path(f.get('path',''));p=p if p.is_absolute() else PROJECT_ROOT/p;text=content_for(p) if p.exists() else ''
        paras=[x.strip() for x in re.split(r'\n\s*\n',text) if x.strip()]; prose=''.join('<p>'+esc(x).replace('\n','<br>')+'</p>' for x in paras)
        body=f'''<div class="toolbar reader-tools"><a class="btn" href="dashboard.html">← Back to workspace</a><button class="btn" onclick="document.body.classList.toggle('focus')">Focus</button></div><div class="reader-head"><div class="eyebrow">{esc(f.get('folder','writing'))}</div><h1>{esc(title_for(f))}</h1><div class="reader-meta">{f.get('word_count',0):,} words · {esc(f.get('era') or 'era not tagged')} · {esc(f.get('status','seedling'))}</div></div><div class="prose">{prose}</div>'''
        (DASHBOARD_DIR/reader_name(f)).write_text(page(title_for(f),body),encoding='utf-8')
    ordered=sorted(chapters,key=lambda f:(f.get('chapter_no') if f.get('chapter_no') is not None else 9999,title_for(f)))
    rows=''.join(f'<tr><td><a href="{esc(reader_name(f))}">{esc(title_for(f))}</a></td><td>{esc(f.get("chapter_no") or "—")}</td><td>{f.get("word_count",0):,}</td><td><span class="status">{esc(f.get("status","seedling"))}</span></td><td>{esc(f.get("era") or "—")}</td></tr>' for f in ordered) or '<tr><td colspan="5" class="empty">No chapter or draft material yet.</td></tr>'
    manuscript=f'''<div class="top"><div><div class="eyebrow">The book</div><h1 class="title">Manuscript</h1><p class="lede">The emerging shape of the memoir. An overview, not a demand that everything be finished.</p></div></div><div class="panel"><table class="table"><thead><tr><th>Chapter / piece</th><th>No.</th><th>Words</th><th>Status</th><th>Era</th></tr></thead><tbody>{rows}</tbody></table></div>'''
    (DASHBOARD_DIR/'manuscript.html').write_text(page('Manuscript',manuscript),encoding='utf-8')
    return str(DASHBOARD_DIR/'dashboard.html')
