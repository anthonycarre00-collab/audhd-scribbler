#!/usr/bin/env python3
"""Writer-first static workspace for The Audhd Scribbler.

Keeps the existing SQLite/indexing system but presents it as a calm writer's
workspace. Everything is local HTML; no server is required.
"""
import html
import json
import re
import webbrowser
from collections import Counter
from datetime import datetime
from pathlib import Path

from .. import db
from ..config import PROJECT_ROOT, DASHBOARD_DIR, STATUSES


CSS = r'''
:root{--paper:#fbfaf7;--paper2:#f3f0e9;--ink:#24282b;--muted:#73766f;--line:#ddd8ce;--accent:#476b70;--accent2:#c78b5b;--soft:#e9efed;--warm:#f5eadf;--white:#fffefa;--shadow:0 8px 30px rgba(35,38,36,.07);--serif:Georgia,'Times New Roman',serif;--sans:Inter,'Segoe UI',Arial,sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 var(--sans)}a{color:inherit}.shell{display:grid;grid-template-columns:220px 1fr;min-height:100vh}.side{position:sticky;top:0;height:100vh;background:#f0eee8;border-right:1px solid var(--line);padding:30px 18px;display:flex;flex-direction:column}.brand{font:700 22px/1.05 var(--serif);margin:0 0 6px}.tagline{font-size:12px;color:var(--muted);margin-bottom:30px}.nav a{display:block;padding:10px 12px;margin:2px 0;text-decoration:none;border-radius:8px;color:#535751}.nav a:hover,.nav a.active{background:var(--white);color:var(--accent);box-shadow:0 1px 4px #0000000b}.side-foot{margin-top:auto;font-size:11px;color:var(--muted);line-height:1.5}.main{max-width:1180px;width:100%;padding:38px 44px 70px;margin:auto}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;margin-bottom:34px}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:1.8px;color:var(--accent);font-weight:700}.title{font:700 38px/1.08 var(--serif);margin:6px 0}.lede{color:var(--muted);max-width:700px}.search{width:330px;background:var(--white);border:1px solid var(--line);border-radius:10px;padding:12px 14px;font:14px var(--sans);outline:none}.search:focus{border-color:var(--accent)}.grid{display:grid;gap:18px}.two{grid-template-columns:1.25fr .75fr}.three{grid-template-columns:repeat(3,1fr)}.panel{background:var(--white);border:1px solid var(--line);border-radius:13px;padding:23px;box-shadow:var(--shadow)}.panel h2{font:700 21px var(--serif);margin:0 0 5px}.panel h3{font-size:12px;text-transform:uppercase;letter-spacing:1.2px;color:var(--muted);margin:0 0 12px}.sub{font-size:13px;color:var(--muted);margin:0 0 18px}.hero{background:linear-gradient(135deg,#eef2ef,#f8eee6);border:1px solid #d9d9d1;border-radius:16px;padding:27px}.hero h2{font:700 26px var(--serif);margin:3px 0 8px}.btn{display:inline-block;border:1px solid var(--accent);color:var(--accent);padding:9px 14px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;background:transparent}.btn.primary{background:var(--accent);color:white}.btn.warm{border-color:var(--accent2);color:#895b36}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:17px}.stat{padding:17px 18px;background:var(--white);border:1px solid var(--line);border-radius:12px}.stat b{display:block;font:700 27px var(--serif);color:var(--accent)}.stat span{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}.item{padding:14px 0;border-bottom:1px solid var(--line)}.item:last-child{border-bottom:0}.item a{text-decoration:none}.item-title{font-weight:650}.item-meta{font-size:12px;color:var(--muted);margin-top:3px}.pill{display:inline-block;border-radius:999px;padding:3px 9px;font-size:11px;background:var(--soft);color:var(--accent);margin:2px 3px 2px 0}.pill.warm{background:var(--warm);color:#895b36}.status{font-size:11px;padding:4px 8px;border-radius:999px;background:#e9ece9;color:#5f665f}.status-seedling{background:#eee6d9}.status-growing{background:#e4eee8}.status-shaping{background:#dce8e7}.status-polishing{background:#d4e0df}.status-resting{background:#e8e5df}.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}.filecard{padding:17px;border:1px solid var(--line);border-radius:11px;background:var(--white)}.filecard:hover{box-shadow:var(--shadow)}.filecard h3{font:700 18px var(--serif);margin:0 0 6px}.excerpt{font:14px/1.55 var(--serif);color:#555a55;margin:12px 0}.bar{height:6px;background:#e6e3dc;border-radius:99px;overflow:hidden}.bar i{display:block;height:100%;background:var(--accent);border-radius:99px}.table{width:100%;border-collapse:collapse}.table td,.table th{padding:10px 8px;border-bottom:1px solid var(--line);text-align:left}.table th{font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}.notice{padding:15px 17px;background:var(--warm);border:1px solid #ead9c9;border-radius:10px}.empty{color:var(--muted);font-style:italic}.prose{font:18px/1.85 var(--serif);max-width:760px}.prose p{margin:0 0 1.2em}.reader{max-width:920px;margin:auto}.reader-head{border-bottom:1px solid var(--line);padding-bottom:25px;margin-bottom:34px}.reader-head h1{font:700 42px/1.1 var(--serif);margin:7px 0 12px}.reader-meta{color:var(--muted);font-size:13px}.focus .side,.focus .reader-tools{display:none}.focus .shell{display:block}.focus .main{max-width:820px;padding-top:70px}.focus .prose{font-size:20px;line-height:1.95}.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:25px}.small{font-size:12px;color:var(--muted)}.timeline{border-left:2px solid var(--line);margin-left:10px;padding-left:25px}.event{position:relative;padding:0 0 24px}.event:before{content:'';position:absolute;left:-32px;top:7px;width:10px;height:10px;border-radius:50%;background:var(--accent);border:3px solid var(--paper)}.event strong{font:700 18px var(--serif)}.mobile-nav{display:none}@media(max-width:850px){.shell{grid-template-columns:1fr}.side{display:none}.mobile-nav{display:block;padding:12px 18px;background:#f0eee8;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:3}.main{padding:25px 18px}.top{display:block}.search{width:100%;margin-top:18px}.two,.three{grid-template-columns:1fr}.title{font-size:31px}}
'''


def esc(s):
    return html.escape(str(s or ""), quote=True)


def clean_text(path):
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    # Strip YAML frontmatter added by the tagger.
    if text.startswith("---"):
        m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.S)
        if m:
            text = text[m.end():]
    return text.strip()


def title_for(f):
    return Path(f.get("filename", "Untitled")).stem.replace("_", " ").replace("-", " ").strip().title()


def reader_name(f):
    return "reader_" + re.sub(r"[^a-zA-Z0-9_-]+", "_", f.get("filename", "file")) + ".html"


def write_page(path, title, body, extra_class=""):
    html_doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · The Audhd Scribbler</title><style>{CSS}</style></head><body class="{extra_class}"><div class="shell"><aside class="side"><div class="brand">The Audhd<br>Scribbler</div><div class="tagline">A calm place for messy writing.</div><nav class="nav"><a href="dashboard.html">Home</a><a href="dashboard.html#writing">Writing</a><a href="dashboard.html#organise">Organise</a><a href="dashboard.html#explore">Explore</a><a href="dashboard.html#analyse">Analyse</a><a href="manuscript.html">Manuscript</a><a href="dashboard.html#search">Search</a></nav><div class="side-foot">Your writing stays on this computer.<br><br>Generated {datetime.now().strftime('%d %b %Y')}</div></aside><div class="mobile-nav"><a href="dashboard.html">← Scribbler</a></div><main class="main">{body}</main></div></body></html>'''
    path.write_text(html_doc, encoding="utf-8")


def generate():
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    files = db.get_all_files()
    stats = db.get_stats()
    # Generate readable local pages for every indexed file.
    for f in files:
        p = PROJECT_ROOT / Path(f.get("path", "")) if not Path(f.get("path", "")).is_absolute() else Path(f.get("path"))
        if not p.exists():
            continue
        text = clean_text(p)
        paragraphs = [x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()]
        body = f'''<div class="reader-tools toolbar"><a class="btn" href="dashboard.html">← Back to workspace</a><button class="btn" onclick="document.body.classList.toggle('focus')">Focus</button></div><div class="reader-head"><div class="eyebrow">{esc(f.get('folder','writing'))}</div><h1>{esc(title_for(f))}</h1><div class="reader-meta">{f.get('word_count',0):,} words · {esc(f.get('era') or 'era not tagged')} · <span class="status status-{esc(f.get('status','seedling'))}">{esc(f.get('status','seedling'))}</span></div><div class="actions">{''.join('<span class="pill">'+esc(x)+'</span>' for x in (f.get('themes') or [])[:8])}</div></div><div class="prose">{''.join('<p>'+esc(x).replace('\n','<br>')+'</p>' for x in paragraphs)}</div>'''
        write_page(DASHBOARD_DIR / reader_name(f), title_for(f), body)

    # Search index uses metadata + a bounded excerpt; actual reading remains in local reader pages.
    search_rows=[]
    for f in files:
        p=Path(f.get('path',''))
        if not p.is_absolute(): p=PROJECT_ROOT/p
        text=clean_text(p) if p.exists() else ''
        search_rows.append({'name':title_for(f),'file':reader_name(f),'folder':f.get('folder',''),'status':f.get('status','seedling'),'era':f.get('era',''),'characters':f.get('characters') or [],'places':f.get('places') or [],'themes':f.get('themes') or [],'text':text[:12000].lower(),'excerpt':re.sub(r'\s+',' ',text)[:260]})

    statuses=Counter(f.get('status','seedling') for f in files)
    chars=Counter(c for f in files for c in (f.get('characters') or []))
    themes=Counter(t for f in files for t in (f.get('themes') or []))
    folders=Counter(f.get('folder','') for f in files)
    chapters=[f for f in files if f.get('folder') in ('chapters','drafts','final')]
    raw=[f for f in files if f.get('folder') in ('raw-dumps','triage')]
    recent=sorted(files,key=lambda x:x.get('last_modified') or '',reverse=True)[:5]
    uncategorised=[f for f in files if f.get('folder') in ('raw-dumps','triage') and not (f.get('themes') or f.get('characters') or f.get('places'))]
    seedling=[f for f in files if f.get('status')=='seedling']

    continue_file = recent[0] if recent else None
    continue_html = '<div class="empty">Drop some writing into <b>raw-dumps</b> and tag it. The workspace will take it from there.</div>'
    if continue_file:
        continue_html=f'''<div class="eyebrow">Continue where you left off</div><h2>{esc(title_for(continue_file))}</h2><p class="sub">{continue_file.get('word_count',0):,} words · {esc(continue_file.get('status','seedling'))}</p><p class="excerpt">{esc(re.sub(r'\s+',' ',clean_text(Path(continue_file.get('path',''))))[:280])}</p><a class="btn primary" href="{esc(reader_name(continue_file))}">Open this writing →</a>'''

    worthwhile=[]
    if uncategorised: worthwhile.append(("Loose material",f"You have {len(uncategorised)} piece(s) of raw material with little or no tagging.","Open the Scribble Inbox"))
    if seedling: worthwhile.append(("Fresh material",f"{len(seedling)} piece(s) are still at seedling stage. Nothing is wrong with that.","Browse fresh writing"))
    repeated=[c for c,n in chars.most_common() if n>=3]
    if repeated: worthwhile.append(("A person keeps appearing",f"{repeated[0]} appears across {chars[repeated[0]]} pieces of writing.","Explore people"))
    if not worthwhile: worthwhile=[("You're in decent shape","Nothing is urgently demanding attention. You can simply write.","Open your recent material")]

    recent_html=''.join(f'''<div class="item"><a href="{esc(reader_name(f))}"><div class="item-title">{esc(title_for(f))}</div><div class="item-meta">{f.get('word_count',0):,} words · {esc(f.get('folder',''))} · {esc(f.get('status','seedling'))}</div></a></div>''' for f in recent)
    worth_html=''.join(f'''<div class="item"><div class="item-title">{esc(a)}</div><div class="item-meta">{esc(b)}</div><div style="margin-top:7px"><a href="#writing" class="btn">{esc(c)} →</a></div></div>''' for a,b,c in worthwhile[:3])
    status_html=''.join(f'<span class="pill">{esc(k)} · {v}</span>' for k,v in statuses.items())
    file_cards=''.join(f'''<article class="filecard"><h3><a href="{esc(reader_name(f))}" style="text-decoration:none">{esc(title_for(f))}</a></h3><div class="item-meta">{f.get('word_count',0):,} words · {esc(f.get('folder',''))}</div><p class="excerpt">{esc(re.sub(r'\s+',' ',clean_text(Path(f.get('path',''))))[:180])}</p><span class="status status-{esc(f.get('status','seedling'))}">{esc(f.get('status','seedling'))}</span></article>''' for f in files)
    people_html=''.join(f'<div class="item"><div class="item-title">{esc(c)}</div><div class="item-meta">{n} piece(s)</div></div>' for c,n in chars.most_common(12)) or '<p class="empty">No characters tagged yet.</p>'
    themes_html=''.join(f'<div class="item"><div class="item-title">{esc(t)}</div><div class="bar" style="margin-top:7px"><i style="width:{max(8,int(n/max(themes.values())*100)) if themes else 0}%"></i></div><div class="item-meta">{n} piece(s)</div></div>' for t,n in themes.most_common(10)) or '<p class="empty">No themes tagged yet.</p>'

    js_data=json.dumps(search_rows,ensure_ascii=False).replace('</','<\\/')
    dashboard_body=f'''<section class="top"><div><div class="eyebrow">Your writing workspace</div><h1 class="title">A place for the messy bits.</h1><p class="lede">Write first. Organise when useful. Explore what keeps turning up. The Scribbler remembers the things you don't want to keep in your head.</p></div><input id="searchBox" class="search" placeholder="Search your writing…" oninput="searchWriting(this.value)"></section>
<section class="grid two"><div class="hero">{continue_html}</div><div class="panel"><h3>Three things worth looking at</h3>{worth_html}</div></section>
<section class="grid three" style="margin-top:18px"><div class="stat"><b>{stats.get('total_words',0):,}</b><span>words</span></div><div class="stat"><b>{stats.get('total_files',0)}</b><span>pieces of writing</span></div><div class="stat"><b>{len(chapters)}</b><span>chapter / draft pieces</span></div></section>
<section id="writing" style="margin-top:38px"><div class="toolbar"><div><div class="eyebrow">Writing</div><h2 style="font:700 28px var(--serif);margin:4px 0">Your material</h2><p class="sub">Nothing has to be finished to belong here.</p></div><a class="btn warm" href="file:///{esc((PROJECT_ROOT/'raw-dumps').as_posix())}">Open scribble folder</a></div><div class="cards">{file_cards}</div></section>
<section id="organise" class="grid two" style="margin-top:38px"><div class="panel"><h2>Scribble Inbox</h2><p class="sub">Raw and early material. Keep it, develop it, or simply leave it alone.</p>{''.join(f'<div class="item"><a href="{esc(reader_name(f))}"><div class="item-title">{esc(title_for(f))}</div><div class="item-meta">{f.get("word_count",0):,} words · {esc(f.get("status","seedling"))}</div></a></div>' for f in raw[:12]) or '<p class="empty">Your inbox is empty.</p>'}</div><div class="panel"><h2>Project shape</h2><p class="sub">A quick view of where your material currently lives.</p><div>{status_html}</div><table class="table" style="margin-top:14px">{''.join(f'<tr><td>{esc(k)}</td><td>{v}</td></tr>' for k,v in folders.items())}</table></div></section>
<section id="explore" class="grid two" style="margin-top:38px"><div class="panel"><h2>People</h2><p class="sub">Who keeps appearing in the story?</p>{people_html}</div><div class="panel"><h2>Themes</h2><p class="sub">What keeps coming back?</p>{themes_html}</div></section>
<section id="analyse" class="grid two" style="margin-top:38px"><div class="panel"><h2>Analysis</h2><p class="sub">The existing analysis suite remains underneath this workspace. Run it from the Windows app menu; the results are still saved locally.</p><div class="notice"><b>Writer-first rule:</b> analysis should point you back to the writing, not bury you in numbers.</div></div><div class="panel"><h2>Recently opened / changed</h2>{recent_html}</div></section>
<section id="search" class="panel" style="margin-top:38px"><h2>Search your writing</h2><p class="sub">Search names, places, themes, eras, statuses and the text itself. Results open the actual passage.</p><div id="results" class="cards"><p class="empty">Start typing in the search box above.</p></div></section>
<footer style="margin-top:45px;color:var(--muted);font-size:12px">The Audhd Scribbler · local workspace · {esc(datetime.now().strftime('%d %B %Y'))}</footer>
<script>const INDEX={js_data};function searchWriting(q){{q=q.trim().toLowerCase();const out=document.getElementById('results');if(!q){{out.innerHTML='<p class="empty">Start typing in the search box above.</p>';return}}const hits=INDEX.filter(x=>[x.name,x.folder,x.status,x.era,...x.characters,...x.places,...x.themes,x.text].join(' ').toLowerCase().includes(q));if(!hits.length){{out.innerHTML='<p class="empty">Nothing found for “'+q.replace(/</g,'&lt;')+'”.</p>';return}}out.innerHTML=hits.map(x=>'<article class="filecard"><h3><a href="'+x.file+'">'+x.name+'</a></h3><div class="item-meta">'+x.folder+' · '+x.status+' · '+(x.era||'era not tagged')+'</div><p class="excerpt">'+x.excerpt.replace(/</g,'&lt;')+'…</p><a class="btn" href="'+x.file+'">Read this →</a></article>').join('')}}}</script>'''
    write_page(DASHBOARD_DIR/'dashboard.html','Home',dashboard_body)

    # Manuscript view.
    ordered=sorted(chapters,key=lambda f:(f.get('chapter_no') if f.get('chapter_no') is not None else 9999,title_for(f)))
    rows=''.join(f'<tr><td><a href="{esc(reader_name(f))}">{esc(title_for(f))}</a></td><td>{esc(f.get("chapter_no") or "—")}</td><td>{f.get("word_count",0):,}</td><td><span class="status status-{esc(f.get("status","seedling"))}">{esc(f.get("status","seedling"))}</span></td><td>{esc(f.get("era") or "—")}</td></tr>' for f in ordered) or '<tr><td colspan="5" class="empty">No chapter/draft material yet.</td></tr>'
    body=f'''<div class="top"><div><div class="eyebrow">The book</div><h1 class="title">Manuscript</h1><p class="lede">The emerging shape of the memoir. This is an overview, not a demand that everything be finished.</p></div></div><div class="panel"><table class="table"><thead><tr><th>Chapter / piece</th><th>No.</th><th>Words</th><th>Status</th><th>Era</th></tr></thead><tbody>{rows}</tbody></table></div>'''
    write_page(DASHBOARD_DIR/'manuscript.html','Manuscript',body)
    return str(DASHBOARD_DIR/'dashboard.html')
