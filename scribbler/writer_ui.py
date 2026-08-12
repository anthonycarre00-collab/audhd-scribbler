"""Writer-first UI layer.

Kept separate from the dashboard generator so the presentation layer can evolve
without changing the underlying tagging/analysis engines.
"""
import json
from . import webapp, safety

ANALYSIS_TOOLS = [
    ("craft", "Craft & Rhythm", "Draft", "Sentence rhythm, balance and craft signals."),
    ("voice", "Voice & Tense", "Draft", "Narrative voice, tense consistency and distance."),
    ("characters", "Characters & Relationships", "Draft", "Character presence, relationships and trajectory signals."),
    ("continuity", "Continuity & Timeline", "Draft", "Chronology, recurring facts and continuity signals."),
    ("themes", "Themes & Emotional Arc", "Draft", "Recurring themes, motifs and emotional movement."),
    ("editor", "Editorial / Memoir Patterns", "Near-final", "Clarity, redundancy and memoir-specific editorial signals."),
]


def install():
    """Install the staged UI and add pre-change snapshots to mutating actions."""
    original_tag = webapp.ScribblerHandler._tag
    original_analyze = webapp.ScribblerHandler._analyze

    def safe_tag(handler):
        safety.project_snapshot("before-tag")
        return original_tag(handler)

    def safe_analyze(handler):
        safety.project_snapshot("before-analysis")
        return original_analyze(handler)

    webapp.ScribblerHandler._tag = safe_tag
    webapp.ScribblerHandler._analyze = safe_analyze
    webapp.inject_controls = inject_controls


def inject_controls(page):
    if 'id="scribblerAppControls"' in page:
        return page
    tool_json = json.dumps(ANALYSIS_TOOLS, ensure_ascii=False)
    overlay = f'''<style>
#scribblerAppControls{{position:sticky;top:0;z-index:9999;background:#252a2b;color:#fff;padding:10px 14px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;font:13px Segoe UI,Arial,sans-serif;box-shadow:0 3px 18px rgba(0,0,0,.12)}}
#scribblerAppControls button{{border:1px solid rgba(255,255,255,.28);background:#394143;color:#fff;border-radius:7px;padding:8px 11px;cursor:pointer;font:inherit}}#scribblerAppControls button:hover{{background:#4b5557}}#scribblerAppControls .primary{{background:#476b70;border-color:#476b70}}.s-status{{margin-left:auto;opacity:.8;font-size:12px}}
.s-modal{{position:fixed;inset:0;background:rgba(20,24,24,.55);z-index:10000;display:none;align-items:center;justify-content:center;padding:24px}}.s-modal.open{{display:flex}}.s-dialog{{background:#fbfaf7;color:#252a2b;width:min(920px,96vw);max-height:90vh;overflow:auto;border-radius:14px;padding:26px;box-shadow:0 20px 70px rgba(0,0,0,.25)}}.s-dialog h2{{font:700 27px Georgia,serif;margin:0 0 7px}}.s-muted{{color:#74766f;font-size:13px}}.s-row{{display:flex;gap:12px;align-items:center;padding:11px 4px;border-bottom:1px solid #ddd8ce}}.s-row input{{width:18px;height:18px}}.s-tools{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:15px 0}}.s-toolcard{{border:1px solid #ddd8ce;border-radius:9px;padding:12px;background:#fff}}.s-toolcard small{{display:block;color:#74766f;margin-top:4px}}.s-actions{{display:flex;gap:8px;justify-content:flex-end;margin-top:20px}}.s-warning{{padding:12px;background:#fff4dc;border:1px solid #ead39b;border-radius:8px;margin:12px 0}}.s-good{{padding:11px;background:#edf3ef;border-radius:8px;margin:8px 0}}@media(max-width:650px){{.s-status{{width:100%;margin-left:0}}.s-tools{{grid-template-columns:1fr}}}}
</style>
<div id="scribblerAppControls"><button class="primary" onclick="Scribbler.importFiles()">＋ Import brain dump</button><button onclick="Scribbler.tag()">Tag brain dumps</button><button onclick="Scribbler.analyse()">Analyse drafts</button><button onclick="Scribbler.refresh()">↻ Refresh</button><button onclick="Scribbler.help()">How Scribbler works</button><span class="s-status" id="scribblerStatus">Ready</span></div>
<div class="s-modal" id="scribblerModal"><div class="s-dialog" id="scribblerDialog"></div></div><input id="scribblerUpload" type="file" multiple accept=".txt,.md,.text" style="display:none">
<script>
const SCRIBBLER_TOOLS={tool_json};
const Scribbler=(()=>{{const modal=document.getElementById('scribblerModal'),dialog=document.getElementById('scribblerDialog'),status=document.getElementById('scribblerStatus');let files=[];const esc=x=>String(x??'').replace(/[&<>\"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}}[m]));const setStatus=x=>status.textContent=x;const open=x=>{{dialog.innerHTML=x;modal.classList.add('open')}};const close=()=>modal.classList.remove('open');modal.addEventListener('click',e=>{{if(e.target===modal)close()}});
async function load(){{const r=await fetch('/api/files');const j=await r.json();files=j.files||[];return j}}
function choose(title,kind){{const rows=files.map(f=>`<label class="s-row"><input type="checkbox" data-file="${{esc(f.path)}}"><span><strong>${{esc(f.filename)}}</strong><br><span class="s-muted">${{f.word_count||0}} words · ${{esc(f.folder)}} · ${{esc(f.status)}}</span></span></label>`).join('')||'<p class="s-muted">Nothing indexed yet. Import some writing first.</p>';if(kind==='tag')open(`<h2>Tag brain dumps</h2><p class="s-muted">Tagging is for raw, messy material. It organises it without judging the quality of the writing.</p>${{rows}}<div class="s-actions"><button onclick="Scribbler.close()">Cancel</button><button class="primary" onclick="Scribbler.doTag()">Tag selected</button></div>`);else{{const cards=SCRIBBLER_TOOLS.map(t=>`<label class="s-toolcard"><input type="checkbox" class="s-tool" value="${{t[0]}}"> <strong>${{t[1]}}</strong><small>Best used on: ${{t[2]}}<br>${{t[3]}}</small></label>`).join('');open(`<h2>Analyse drafts</h2><p class="s-muted">Analysis is deliberately separate from tagging. Select actual draft/manuscript material, then choose the question you want Scribbler to investigate.</p>${{rows}}<div class="s-tools">${{cards}}</div><div class="s-warning"><strong>Run All is cautious.</strong> Some diagnostics overlap or can conflict with deliberate voice. Scribbler will not silently run every tool as though every finding were a problem.</div><div class="s-actions"><button onclick="Scribbler.close()">Cancel</button><button onclick="Scribbler.runAll()">Run recommended</button><button class="primary" onclick="Scribbler.doAnalyse()">Run selected</button></div>`)}}}}
function selected(){{return [...dialog.querySelectorAll('input[data-file]:checked')].map(x=>x.dataset.file)}}
async function importFiles(){{const i=document.getElementById('scribblerUpload');i.value='';i.onchange=async()=>{{if(!i.files.length)return;setStatus('Importing…');const fd=new FormData();[...i.files].forEach(f=>fd.append('files',f));const r=await fetch('/api/upload',{{method:'POST',body:fd}}),j=await r.json();if(!j.ok)return alert(j.error);await load();setStatus('Saved to Scribble Inbox');open(`<h2>Saved safely</h2><div class="s-good">${{j.saved.length}} file(s) imported into <strong>Scribble Inbox</strong>.<br>Your originals were not altered.</div><div class="s-actions"><button onclick="Scribbler.close()">Done</button><button class="primary" onclick="Scribbler.tag()">Tag this material</button></div>`)}};i.click()}}
async function tag(){{await load();choose('Tag','tag')}}
async function doTag(){{const p=selected();if(!p.length)return alert('Choose at least one brain dump.');if(!confirm('Tag the selected brain dumps?\n\nScribbler will create a safety snapshot first. Your writing will not be rewritten.'))return;close();setStatus('Creating safety snapshot and tagging…');const j=await (await fetch('/api/tag',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{paths:p,use_llm:true}})}})).json();setStatus(j.ok?'✓ Tagging saved':'Tagging failed');open(`<h2>${{j.ok?'Tagging saved':'Tagging failed'}}</h2><div class="s-good">${{j.tagged?.length||0}} item(s) processed. Previous project state was preserved before the operation.</div><div class="s-actions"><button onclick="Scribbler.close()">Done</button></div>`)}}
async function analyse(){{await load();choose('Analyse','analyse')}}
async function doAnalyse(){{const p=selected(),t=[...dialog.querySelectorAll('.s-tool:checked')].map(x=>x.value);if(!p.length)return alert('Choose at least one draft.');if(!t.length)return alert('Choose at least one analysis tool.');if(!confirm('Run the selected analysis on these drafts?\n\nA safety snapshot will be created first. Existing analysis results are retained in history.'))return;close();setStatus('Snapshotting and analysing…');const j=await (await fetch('/api/analyze',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{paths:p,tools:t}})}})).json();setStatus(j.ok?'✓ Analysis saved':'Analysis failed');open(`<h2>${{j.ok?'Analysis saved':'Analysis failed'}}</h2><div class="s-good">${{j.results?.length||0}} draft(s) analysed. Previous analysis results remain available in history.</div>${{j.errors?.length?'<div class="s-warning">Some items could not be analysed. Nothing was deleted.</div>':''}}<div class="s-actions"><button onclick="Scribbler.close()">Done</button><a href="analysis.html"><button>Open analysis</button></a></div>`)}}
function runAll(){{const checks=dialog.querySelectorAll('.s-tool');checks.forEach(x=>x.checked=true);alert('Recommended run selected: all currently compatible core diagnostics. Scribbler deliberately does not auto-add future specialist tools that may clash with the draft stage. Review the selected tools, then press Run selected.')}}
async function refresh(){{setStatus('Refreshing…');await fetch('/api/refresh',{{method:'POST'}});location.reload()}}
function help(){{open(`<h2>How Scribbler works</h2><p><strong>Brain dumps first.</strong> Import anything messy into Scribble Inbox. Tagging helps you find people, places, themes, eras and promising material. It does not rate your prose.</p><p><strong>Drafts later.</strong> When you promote material into a real draft/manuscript, analysis becomes useful. Choose the exact draft and the exact question you want answered.</p><p><strong>Your safety net.</strong> Before tagging or analysis, Scribbler makes a local snapshot. Analysis results are versioned rather than silently destroyed.</p><p><strong>You remain editor.</strong> Findings are evidence and prompts, not instructions. Scribbler never automatically rewrites your memoir.</p><div class="s-actions"><button onclick="Scribbler.close()">Close</button></div>`)}}
return {{importFiles,tag,doTag,analyse,doAnalyse,runAll,refresh,help,close}}}})();
</script>'''
    return page.replace('<body>', '<body>'+overlay, 1)
