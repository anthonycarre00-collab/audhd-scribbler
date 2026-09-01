// The Audhd Scribbler v2 — Frontend controller
// Routes between views, manages state, wraps pywebview API calls

let DATA = { files: [], tools: {}, catalog: {} };
let currentView = 'home';
let operationCancelled = false;
let timerInterval = null;
let timerStart = null;
let messageInterval = null;
const calmingMessages = [
  "Reading your words carefully…",
  "Looking for patterns…",
  "This is the slow, careful part.",
  "Thank you for waiting.",
  "Almost there…"
];

// ── PYWEBVIEW API WRAPPER ──────────────────────────────────────────

let apiReady = false;
window.addEventListener('pywebviewready', () => { apiReady = true; load(); });

function waitForApi() {
  return new Promise(resolve => {
    if (apiReady) return resolve();
    window.addEventListener('pywebviewready', () => resolve());
  });
}

async function call(method, ...args) {
  await waitForApi();
  try {
    return await window.pywebview.api[method](...args);
  } catch (e) {
    console.error(`API ${method} failed:`, e);
    throw new Error(e.message || String(e));
  }
}

// ── STATE ──────────────────────────────────────────────────────────

async function load() {
  try {
    const status = await call('get_status');
    document.getElementById('statusText').textContent = status.llm || 'Ready';
    document.getElementById('statusDot').style.color = status.ok ? 'var(--success)' : 'var(--danger)';

    const filesResp = await call('list_files');
    DATA.files = filesResp.files || [];

    const toolsResp = await call('get_tools');
    DATA.tools = toolsResp.tools || {};
    DATA.catalog = toolsResp.catalog || {};

    updateNavCounts();
    if (currentView) navigate(currentView);
  } catch (e) {
    setStatus('Could not load: ' + e.message);
  }
}

function updateNavCounts() {
  const inboxCount = DATA.files.filter(f => ['raw-dumps','triage'].includes(f.folder)).length;
  const msCount = DATA.files.filter(f => ['chapters','drafts','final'].includes(f.folder)).length;
  document.getElementById('inboxCount').textContent = inboxCount || '';
  document.getElementById('msCount').textContent = msCount || '';
}

// ── NAVIGATION ─────────────────────────────────────────────────────

function navigate(view) {
  currentView = view;
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === view));
  const content = document.getElementById('content');
  content.className = 'content';
  content.classList.add(view === 'inbox' ? 'zone-inbox' : view === 'manuscript' ? 'zone-manuscript' : '');

  switch(view) {
    case 'home': renderHome(); break;
    case 'inbox': renderInbox(); break;
    case 'manuscript': renderManuscript(); break;
    case 'search': renderSearch(); break;
    case 'exports': renderExports(); break;
    case 'settings': renderSettings(); break;
  }
}

// ── STATUS & TOAST ─────────────────────────────────────────────────

function setStatus(text) {
  document.getElementById('statusText').textContent = text;
}

function showToast(text, duration = 3000) {
  const toast = document.getElementById('toast');
  toast.textContent = text;
  toast.style.display = 'block';
  toast.style.opacity = '1';
  setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.style.display = 'none', 300); }, duration);
}

// ── THINKING TIMER ─────────────────────────────────────────────────

function startTimer(title) {
  operationCancelled = false;
  const overlay = document.getElementById('thinkingOverlay');
  document.getElementById('thinkingTitle').textContent = title || 'Working…';
  document.getElementById('thinkingStep').textContent = '';
  document.getElementById('thinkingTimer').textContent = '00:00';
  document.getElementById('thinkingMessage').textContent = calmingMessages[0];
  overlay.style.display = 'flex';

  timerStart = Date.now();
  let msgIdx = 0;
  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - timerStart) / 1000);
    const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
    const ss = String(elapsed % 60).padStart(2, '0');
    document.getElementById('thinkingTimer').textContent = `${mm}:${ss}`;
  }, 1000);
  messageInterval = setInterval(() => {
    msgIdx = (msgIdx + 1) % calmingMessages.length;
    const msgEl = document.getElementById('thinkingMessage');
    msgEl.style.opacity = '0';
    setTimeout(() => { msgEl.textContent = calmingMessages[msgIdx]; msgEl.style.opacity = '1'; }, 400);
  }, 8000);
}

function updateTimerStep(step, total, message) {
  if (total > 1) {
    document.getElementById('thinkingStep').textContent = `Step ${step} of ${total} · ${message}`;
  } else {
    document.getElementById('thinkingStep').textContent = message;
  }
}

function stopTimer() {
  clearInterval(timerInterval);
  clearInterval(messageInterval);
  document.getElementById('thinkingOverlay').style.display = 'none';
}

function cancelOperation() {
  operationCancelled = true;
  stopTimer();
  setStatus('Stopped. Your work is saved.');
}

// Progress callback from Python
window.__scribblerProgress__ = function(step, total, message) {
  updateTimerStep(step, total, message);
};

// ── HOME VIEW ──────────────────────────────────────────────────────

function renderHome() {
  const inboxFiles = DATA.files.filter(f => ['raw-dumps','triage'].includes(f.folder));
  const msFiles = DATA.files.filter(f => ['chapters','drafts','final'].includes(f.folder));
  const untagged = inboxFiles.filter(f => f.status === 'unindexed').length;

  let suggestion = '';
  if (untagged > 0) {
    suggestion = `<div class="card"><h3>Suggested next</h3><p class="muted">You have ${untagged} untagged brain dump(s).</p><button class="btn-primary" onclick="navigate('inbox')">Preview tags</button></div>`;
  } else if (msFiles.length > 0) {
    suggestion = `<div class="card"><h3>Suggested next</h3><p class="muted">You have ${msFiles.length} manuscript file(s) ready for analysis.</p><button class="btn-primary" onclick="navigate('manuscript')">Open Analysis Suite</button></div>`;
  } else {
    suggestion = `<div class="card"><h3>Suggested next</h3><p class="muted">Drop some brain dumps into the Inbox to get started.</p><button class="btn-primary" onclick="navigate('inbox')">Open Inbox</button></div>`;
  }

  document.getElementById('content').innerHTML = `
    <div class="view active">
      <div class="view-header"><h1>Your writing workshop</h1><p class="lead">Two deliberately separate worlds: <b>Inbox</b> for messy material and tagging; <b>Manuscript</b> for actual drafts and analysis. Scribbler never decides that a brain dump is a draft.</p></div>
      <div class="grid-3">
        <div class="card"><h3>01 · Scribble Inbox</h3><p class="muted">${inboxFiles.length} file(s)</p><p>Brain dumps, fragments, notes. Tag to organise, not to judge.</p><button class="btn-secondary" onclick="navigate('inbox')">Open Inbox</button></div>
        <div class="card"><h3>02 · Manuscript</h3><p class="muted">${msFiles.length} file(s)</p><p>Chapters and drafts. This is the only material analysis touches.</p><button class="btn-secondary" onclick="navigate('manuscript')">Open Manuscript</button></div>
        <div class="card"><h3>03 · Search</h3><p>Find every scene mentioning a character, place, or theme.</p><button class="btn-secondary" onclick="navigate('search')">Open Search</button></div>
      </div>
      ${suggestion}
      <div class="card"><h3>The rule that keeps Scribbler sane</h3><p><b>Tagging organises raw material. Analysis examines writing.</b> They are separate operations, separate screens.</p></div>
    </div>`;
}

// ── INBOX VIEW (tagging) ───────────────────────────────────────────

function renderInbox() {
  const files = DATA.files.filter(f => ['raw-dumps','triage'].includes(f.folder));
  document.getElementById('content').innerHTML = `
    <div class="view active zone-inbox">
      <div class="view-header"><h1>Scribble Inbox</h1><p class="lead">Brain dumps, voice-to-text, fragments. Nothing here is treated as a manuscript.</p></div>
      <div class="dropzone" id="inboxDrop" onclick="importFiles('raw-dumps')">
        <div class="dropzone-icon">📂</div><div class="dropzone-text">Drop .txt or .md files here</div><div class="dropzone-hint">or click to browse</div>
      </div>
      <div class="card">
        <h3>Your brain dumps</h3>
        <div class="filelist" id="inboxList">${renderFileList(files, 'inbox')}</div>
      </div>
      <div class="actions">
        <button class="btn-secondary" onclick="previewTags()">Preview tags</button>
        <button class="btn-primary" onclick="applyTags()">Apply tags to selected</button>
      </div>
      <div class="card" id="tagResults" style="display:none"><h3>Tagging results</h3><div id="tagResultsContent"></div></div>
    </div>`;

  // Drag-drop
  const dz = document.getElementById('inboxDrop');
  dz.ondragover = (e) => { e.preventDefault(); dz.classList.add('dragover'); };
  dz.ondragleave = () => dz.classList.remove('dragover');
  dz.ondrop = async (e) => {
    e.preventDefault(); dz.classList.remove('dragover');
    const paths = [...e.dataTransfer.files].map(f => f.path);
    if (paths.length) await doImport('raw-dumps', paths);
  };
}

function renderFileList(files, scope) {
  if (!files.length) return '<div class="empty">Nothing here yet.</div>';
  return files.map(f => `
    <div class="filerow">
      <input type="checkbox" data-s="${scope}" value="${esc(f.path)}">
      <div class="file-info"><div class="file-name">${esc(f.filename)}</div><div class="file-meta">${f.word_count||0} words · ${esc(f.status)}${f.last_analyzed?' · analysed':''}</div></div>
      <span class="file-folder">${esc(f.folder)}</span>
      <button class="btn-delete" onclick="deleteFile('${esc(f.path)}')">Delete</button>
    </div>`).join('');
}

function selected(scope) {
  return [...document.querySelectorAll(`input[data-s="${scope}"]:checked`)].map(x => x.value);
}

async function importFiles(destination) {
  try {
    const result = await window.pywebview.api.pick_open_files();
    if (result && result.paths && result.paths.length) {
      await doImport(destination, result.paths);
    }
  } catch (e) { showToast('Could not open file dialog'); }
}

async function doImport(destination, paths) {
  setStatus('Importing…');
  const result = await call('import_files', destination, paths);
  if (result.ok) {
    showToast(result.message);
    await load();
  } else {
    showToast(result.error || 'Import failed');
  }
}

async function previewTags() {
  const paths = selected('inbox');
  if (!paths.length) return showToast('Select one or more brain dumps first');
  startTimer('Previewing tags');
  const result = await call('tag_preview', paths, false);
  stopTimer();
  if (result.ok) {
    const content = result.preview.map(p => `
      <div class="result-card">
        <div class="result-head"><div><h3>${esc(p.filename)}</h3></div></div>
        <div class="kv-grid">
          <div class="kv-item"><span class="kv-label">Voice</span><strong>${esc(p.voice||'—')}</strong></div>
          <div class="kv-item"><span class="kv-label">Era</span><strong>${esc(p.era||'—')}</strong></div>
          <div class="kv-item"><span class="kv-label">Emotion</span><strong>${esc(p.emotional_register||'—')}</strong></div>
        </div>
        <div style="margin-top:12px"><strong>Themes</strong><div class="chips">${(p.themes||[]).map(t=>`<span class="chip chip-theme">${esc(t)}</span>`).join('')}</div></div>
        <div><strong>Characters</strong><div class="chips">${(p.characters||[]).map(c=>`<span class="chip chip-character">${esc(c)}</span>`).join('')}</div></div>
        <div><strong>Places</strong><div class="chips">${(p.places||[]).map(p=>`<span class="chip chip-place">${esc(p)}</span>`).join('')}</div></div>
        <div><strong>Sensory</strong><div class="chips">${(p.sensory||[]).map(s=>`<span class="chip chip-sensory">${esc(s)}</span>`).join('')}</div></div>
      </div>`).join('');
    document.getElementById('tagResults').style.display = 'block';
    document.getElementById('tagResultsContent').innerHTML = content;
    setStatus('Tag preview ready');
  } else { showToast(result.error); }
}

async function applyTags() {
  const paths = selected('inbox');
  if (!paths.length) return showToast('Select one or more brain dumps first');
  startTimer('Tagging ' + paths.length + ' brain dump(s)');
  const result = await call('tag_files', paths, false);
  stopTimer();
  if (result.ok) {
    showToast(`Tagged ${result.tagged.length} file(s)`);
    await load();
    renderInbox();
  } else { showToast(result.error); }
}

// ── MANUSCRIPT VIEW (analysis) ────────────────────────────────────

function renderManuscript() {
  const files = DATA.files.filter(f => ['chapters','drafts','final'].includes(f.folder));
  const tools = DATA.tools || {};
  const catalog = DATA.catalog || {};
  const order = ['craft','voice','characters','continuity','themes','editor','repetition','pacing','structure','memoir','reader','research','cadence','motifs','anchors','voice_dna','reader_perception'];
  const groups = {'Prose':[], 'Story':[], 'Structure':[], 'Editorial':[], 'Accuracy':[], 'Writer':[], 'Memoir':[]};
  order.forEach(k => { if (tools[k]) { const g = tools[k].group||'Other'; (groups[g]||(groups[g]=[])).push(k); } });

  const toolGrid = Object.entries(groups).filter(([g,ks])=>ks.length).map(([group, keys]) => `
    <div style="margin-bottom:16px"><strong>${group}</strong>
    <div class="tool-grid" style="margin-top:8px">${keys.map(k => {
      const t = tools[k], c = catalog[k]||{};
      return `<div class="tool-card" id="tool-${k}" onclick="toggleTool('${k}')">
        <input type="checkbox" class="toolbox" value="${k}" onchange="event.stopPropagation(); this.closest('.tool-card').classList.toggle('selected',this.checked)">
        <div class="tool-body"><div class="tool-title">${esc(t.title)}</div><div class="tool-meta">${esc(c.stage||'draft')} · ${esc(t.purpose||'')}</div></div>
      </div>`;
    }).join('')}</div></div>`).join('');

  document.getElementById('content').innerHTML = `
    <div class="view active zone-manuscript">
      <div class="view-header"><h1>Manuscript</h1><p class="lead">Chapters and drafts. Importing here makes material eligible for analysis.</p></div>
      <div class="dropzone" id="msDrop" onclick="importFiles('chapters')">
        <div class="dropzone-icon">📂</div><div class="dropzone-text">Drop .txt or .md files here</div><div class="dropzone-hint">or click to browse</div>
      </div>
      <div class="card"><h3>Your manuscript</h3><div class="filelist" id="msList">${renderFileList(files, 'analysis')}</div></div>
      <div class="card"><h3>Choose analysis tools</h3>
        <div class="actions"><button class="btn-secondary btn-sm" onclick="selectRecommended()">Use recommended</button><button class="btn-ghost btn-sm" onclick="selectAllTools()">Select all</button><button class="btn-ghost btn-sm" onclick="clearTools()">Clear</button></div>
        ${toolGrid}
      </div>
      <div class="actions"><button class="btn-primary" onclick="runAnalysis()">Run selected</button></div>
      <div id="analysisResults"></div>
    </div>`;

  const dz = document.getElementById('msDrop');
  dz.ondragover = (e) => { e.preventDefault(); dz.classList.add('dragover'); };
  dz.ondragleave = () => dz.classList.remove('dragover');
  dz.ondrop = async (e) => { e.preventDefault(); dz.classList.remove('dragover'); const paths = [...e.dataTransfer.files].map(f=>f.path); if (paths.length) await doImport('chapters', paths); };
}

function toggleTool(k) {
  const card = document.getElementById('tool-'+k);
  const cb = card.querySelector('input');
  cb.checked = !cb.checked;
  card.classList.toggle('selected', cb.checked);
}
function selectRecommended() { clearTools(); ['craft','voice','characters','continuity','themes','editor','repetition','pacing','cadence'].forEach(k => { const cb = document.querySelector(`.toolbox[value="${k}"]`); if (cb) { cb.checked = true; cb.closest('.tool-card').classList.add('selected'); } }); }
function selectAllTools() { document.querySelectorAll('.toolbox').forEach(cb => { cb.checked = true; cb.closest('.tool-card').classList.add('selected'); }); }
function clearTools() { document.querySelectorAll('.toolbox').forEach(cb => { cb.checked = false; cb.closest('.tool-card').classList.remove('selected'); }); }

async function runAnalysis() {
  const paths = selected('analysis');
  const tools = [...document.querySelectorAll('.toolbox:checked')].map(x => x.value);
  if (!paths.length) return showToast('Select one or more manuscript files first');
  if (!tools.length) return showToast('Choose at least one analysis tool');
  startTimer(`Analysing ${paths.length} file(s) with ${tools.length} tool(s)`);
  const result = await call('analyze', paths, tools);
  stopTimer();
  if (result.ok) {
    const html = result.results.flatMap(r => Object.entries(r.results).map(([k,v]) => renderResult(r.filename, k, v))).join('') || '<div class="empty">No results returned.</div>';
    document.getElementById('analysisResults').innerHTML = html;
    setStatus(result.message);
  } else { showToast(result.error); }
}

function renderResult(file, tool, data) {
  const title = (DATA.tools[tool]||{}).title || tool;
  if (data.error) return `<div class="result-card"><div class="result-head"><div><h3>${esc(file)}</h3><div class="muted">${esc(title)}</div></div><span class="result-badge">error</span></div><p class="muted">${esc(data.error)}</p></div>`;
  const items = prettyResult(data);
  return `<div class="result-card">
    <div class="result-head"><div><h3>${esc(file)}</h3><div class="muted">${esc(title)}</div></div><span class="result-badge">saved</span></div>
    ${items.filter(x=>typeof x.value!=='object').slice(0,6).map(x=>`<div class="kv-item" style="display:inline-block;margin:4px"><span class="kv-label">${esc(x.label)}</span><strong>${esc(String(x.value))}</strong></div>`).join('')}
    ${items.filter(x=>typeof x.value==='object').slice(0,5).map(x=>`<div class="finding"><strong>${esc(x.label)}</strong>${esc(JSON.stringify(x.value,null,2))}</div>`).join('')}
    ${data.summary ? `<div class="notice">${esc(data.summary)}</div>` : ''}
    ${data.observations ? data.observations.slice(0,5).map(o => `<div class="finding"><strong>${esc((o.category||'').replace(/_/g,' ' '))}</strong>${esc(o.formatted||o.observation||'')}</div>`).join('') : ''}
    ${data.strengths ? `<div class="finding"><strong>Strengths</strong>${data.strengths.map(s=>`<div>• ${esc(s)}</div>`).join('')}</div>` : ''}
    <details><summary>Full evidence (JSON)</summary><div class="json-viewer">${esc(JSON.stringify(data,null,2))}</div></details>
  </div>`;
}

function prettyResult(data) {
  let flat = [];
  function walk(v, path='') {
    if (v == null) return;
    if (Array.isArray(v)) { if (v.length && typeof v[0]==='object') flat.push({label:path, value:v}); return; }
    if (typeof v === 'object') { for (const [k,x] of Object.entries(v)) { if (k==='analysis'||k==='observations'||k==='strengths'||k==='summary') continue; walk(x, path?path+' · '+k:k); } }
    else flat.push({label:path, value:v});
  }
  walk(data);
  return flat.slice(0, 15);
}

// ── SEARCH VIEW ───────────────────────────────────────────────────

function renderSearch() {
  document.getElementById('content').innerHTML = `
    <div class="view active">
      <div class="view-header"><h1>Search</h1><p class="lead">Find every scene mentioning a character, place, or theme across all tagged files.</p></div>
      <div class="card">
        <h3>Search by tag</h3>
        <div class="grid-2">
          <div><label class="muted">Tag type</label><select id="searchTagType" class="note-title-input" onchange="loadTagValues()">
            <option value="characters">Character</option><option value="places">Place</option><option value="themes">Theme</option>
            <option value="era">Era</option><option value="emotional_register">Emotional Register</option><option value="status">Status</option>
          </select></div>
          <div><label class="muted">Value</label><input type="text" id="searchValue" class="note-title-input" placeholder="Type or pick a value" list="tagValueList"></div>
        </div>
        <datalist id="tagValueList"></datalist>
        <div class="actions"><button class="btn-primary" onclick="runSearch()">Search</button></div>
      </div>
      <div id="searchResults"></div>
    </div>`;
  loadTagValues();
}

async function loadTagValues() {
  const tagType = document.getElementById('searchTagType').value;
  try {
    const result = await call('get_tag_values', tagType);
    const list = document.getElementById('tagValueList');
    list.innerHTML = (result.values||[]).map(v => `<option value="${esc(v.value)}">${esc(v.value)} (${v.count})</option>`).join('');
  } catch(e) {}
}

async function runSearch() {
  const tagType = document.getElementById('searchTagType').value;
  const value = document.getElementById('searchValue').value.trim();
  if (!value) return showToast('Enter a value to search for');
  startTimer('Searching for ' + value);
  const result = await call('search_tags', tagType, value);
  stopTimer();
  if (result.ok) {
    const html = result.results.length ? result.results.map((f,i) => `
      <div class="result-card">
        <div class="result-head"><div><h3>${esc(f.filename||'unknown')}</h3><div class="muted">${f.word_count||0} words · ${esc(f.status||'')}</div></div></div>
        ${(f.characters||[]).length ? `<div><strong>Characters:</strong> ${f.characters.map(c=>`<span class="chip chip-character">${esc(c)}</span>`).join('')}</div>` : ''}
        ${(f.themes||[]).length ? `<div><strong>Themes:</strong> ${f.themes.map(t=>`<span class="chip chip-theme">${esc(t)}</span>`).join('')}</div>` : ''}
      </div>`).join('') : '<div class="empty">No files found matching your search.</div>';
    document.getElementById('searchResults').innerHTML = html;
    setStatus(`Found ${result.count} file(s)`);
  } else { showToast(result.error); }
}

// ── EXPORT VIEW ───────────────────────────────────────────────────

function renderExports() {
  const files = DATA.files.filter(f => ['chapters','drafts','final'].includes(f.folder));
  document.getElementById('content').innerHTML = `
    <div class="view active">
      <div class="view-header"><h1>Export & Backup</h1><p class="lead">Outputs only. Nothing here imports or changes your writing.</p></div>
      <div class="card"><h3>Export one manuscript file</h3>
        <div class="filelist">${renderFileList(files, 'export')}</div>
        <div class="actions" style="margin-top:12px">
          <button class="btn-secondary btn-sm" onclick="exportFile('docx')">Export as DOCX</button>
          <button class="btn-secondary btn-sm" onclick="exportFile('md')">Export as Markdown</button>
          <button class="btn-secondary btn-sm" onclick="exportFile('txt')">Export as Plain text</button>
        </div>
      </div>
      <div class="card"><h3>Back up the whole project</h3><p class="muted">Creates a ZIP with your writing folders, database, and project manifest. You choose where it lands.</p>
        <button class="btn-primary" onclick="backupProject()">Choose location & create backup ZIP</button>
      </div>
    </div>`;
}

async function exportFile(kind) {
  const paths = selected('export');
  if (!paths.length) return showToast('Select one file first');
  try {
    const saveResult = await window.pywebview.api.pick_save_path(`export.${kind}`);
    if (!saveResult || !saveResult.path) return;
    startTimer('Exporting');
    const result = await call('export_file', paths[0], kind, saveResult.path);
    stopTimer();
    if (result.ok) { showToast('Export created at: ' + result.path); }
    else { showToast(result.error); }
  } catch(e) { showToast('Export cancelled'); }
}

async function backupProject() {
  try {
    const saveResult = await window.pywebview.api.pick_save_path('Scribbler-Backup.zip');
    if (!saveResult || !saveResult.path) return;
    startTimer('Creating backup');
    const result = await call('backup_project', saveResult.path);
    stopTimer();
    if (result.ok) { showToast('Backup created at: ' + result.path); }
    else { showToast(result.error); }
  } catch(e) { showToast('Backup cancelled'); }
}

// ── SETTINGS VIEW ─────────────────────────────────────────────────

function renderSettings() {
  document.getElementById('content').innerHTML = `
    <div class="view active">
      <div class="view-header"><h1>Settings</h1><p class="lead">Optional AI configuration. All core analysis works without AI.</p></div>
      <div class="card" id="settingsCard"><p class="muted">Loading…</p></div>
    </div>`;
  loadSettings();
}

async function loadSettings() {
  try {
    const status = await call('get_ai_status');
    document.getElementById('settingsCard').innerHTML = `
      <h3>AI Status</h3><p>${esc(status.status)}</p>
      <div style="margin-top:16px"><strong>AI is optional.</strong> All 17 analysis tools and the tagger work fully without AI. Only reader perception and LLM-assisted tagging summaries use it.</div>`;
  } catch(e) { document.getElementById('settingsCard').innerHTML = '<p>Could not load settings.</p>'; }
}

// ── QUICK NOTE ────────────────────────────────────────────────────

function openQuickNote() { document.getElementById('noteOverlay').style.display = 'flex'; document.getElementById('noteBody').focus(); }
function closeQuickNote() { document.getElementById('noteOverlay').style.display = 'none'; document.getElementById('noteTitle').value = ''; document.getElementById('noteBody').value = ''; }

async function saveNote() {
  const title = document.getElementById('noteTitle').value.trim();
  const text = document.getElementById('noteBody').value.trim();
  if (!text) return showToast('Write something first');
  const result = await call('save_note', title, text);
  if (result.ok) { closeQuickNote(); showToast('Saved to Inbox'); await load(); }
  else { showToast(result.error); }
}

// ── DELETE ────────────────────────────────────────────────────────

async function deleteFile(path) {
  if (!confirm('Move this file to archive? You can recover it later.')) return;
  const result = await call('delete_file', path);
  if (result.ok) { showToast(result.message); await load(); navigate(currentView); }
  else { showToast(result.error); }
}

// ── UTILITIES ─────────────────────────────────────────────────────

function esc(s) { return String(s??'').replace(/[&<>"']/g, m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
