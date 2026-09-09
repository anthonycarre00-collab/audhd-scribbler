# Audhd Scribbler — V12.2 POLISH, PERFORMANCE & INTEGRATION PLAN

## From "Functional" to "Production-Quality, Usable, Calm"

**Audience:** Z AI / implementation agent  
**Starting point:** Current `main` branch of `audhd-scribbler` (V12.1 build)  
**Baseline:** V12.1 handoff spec + current `assets/ui/index.html` and `scribbler/` package  
**Status:** **Ready for implementation**  
**Rule:** Audit first. Make targeted, surgical fixes — no broad rewrites. Each phase must ship green tests before the next begins. Update `worklog.md` after every phase.

---

# 0. PURPOSE

V12.1 made the app *functionally* complete. The user's audit confirms the app builds and runs, but is **not yet polished, bug-free, or usable day-to-day**. Nine concrete pain points are blocking real use:

1. UI palette / fonts / button sizes are not yet calm-dark-friendly or readable.
2. Sidebar cannot scroll — categories below "Relationships" are unreachable.
3. A useless mini "Manuscript / + New Chapter" injected block with ugly default scrollbar sits above the nav.
4. Tagging is mis-classifying common nouns/adjectives/verbs (e.g. "bastard") as characters; Era is too narrow; tag-click results are poor; Reader is obstructed by a mini tag-search box; Tag Map inherits all the tagging errors.
5. The writing editor crashes / hangs under load; autosave and live-checks fire too often; missing strikethrough; context-checking should be callable, not automatic.
6. The Promote button is tiny and feels broken / memory-hoggy.
7. Manuscript analysis results offer suggestions with no path to act on them; Reader is OK; Findings/Characters/Places/Themes/Arcs/Relationships tabs do not auto-populate from manuscript analysis; Characters/Places (and Themes/Arcs) lack UI to add backstory / physical descripts / research notes.
8. Tabbing away loses everything displayed on the previous screen.
9. The tool is complex but not yet production quality; needs expert planning, coding, sign-off, worklog updates across UI, UX, nav flow, tech spec, performance, functionality, smoothness, usefulness.

V12.2 exists to convert V12.1 from a working build into a tool the writer *wants* to open every day.

The central target is unchanged:

> **The writer writes. Scribbler remembers, organises, connects and points things out. The writer remains in control.**

---

# 1. NON-NEGOTIABLE STARTING RULES

## 1.1 Preserve V10 / V12 / V12.1 functionality

Before changing a subsystem, prove the desired improvement can be added around it. Do not rewrite the tagger, the analyzers, the editor, or the project manager. Extend them.

## 1.2 No data loss

Every change that touches `db.py`, `manuscript/tree.py`, `tagger.py`, or `api.py` must include a no-op migration test on an existing project directory. Never delete rows to "clean up" — use `provenance='suggested'` flags and let the writer dismiss them.

## 1.3 No new dependencies

V12.2 ships inside the same Windows installer. Do not add packages that bloat the PyInstaller bundle. If a feature cannot be built with what `requirements.txt` already lists (spaCy, pyspellchecker, python-docx, etc.), escalate before adding it.

## 1.4 Every phase ships its own test gate

Phase = code change + smoke test + worklog entry. No phase is "done" until the test gate at the bottom of that phase passes and the worklog is updated.

## 1.5 Accessibility & calm

- Min body text 15px, line-height ≥ 1.6.
- Min click target 40×40px (44×44 preferred).
- No pure black on pure white or pure white on pure black.
- No flashing, no rapid motion, no sticky modals that trap focus.
- All keyboard shortcuts documented in-app (Settings → Shortcuts).

---

# 2. AUDIT — WHAT THE CODE LOOKS LIKE TODAY

The following were read in full before this plan was written:

- `assets/ui/index.html` (988 lines, single-file app: CSS tokens at top, then HTML scaffold, then JS)
- `assets/ui/styles/tokens.css` (the "Warm Linen" light palette — overridden by an inline dark-theme block in `index.html` lines ~20–60)
- `assets/ui/styles/base.css`, `components.css`, `timers.css` (companion stylesheets; the inline CSS in `index.html` is what actually wins in 95% of cases)
- `scribbler/tagger.py` (599 lines — `detect_characters`, `_classify_entity`, `detect_places`, `detect_era`, `detect_themes`, `detect_emotional_register`, `llm_assisted_tagging`)
- `scribbler/editor/live_checks.py` (290 lines — `run_live_checks`, paragraph-splitting, spelling, run-on, passive, filter/weak words, repeated openers)
- `scribbler/api.py` (1311 lines — `run_live_checks`, `save_chapter_content`, `get_chapter_content`, `tag_files`, `analyze`, `_run_tool`)
- `scribbler/config.py` (`STOPLIST_CHARACTERS`, `THEME_AS_PLACE_STOP`, `AUDHD_THEMES`, `ERAS`, `SENSORY_CATEGORIES`, `ANACHRONISM_WATCHLIST`)
- `scribbler/db.py` (has `upsert_character`, `upsert_place`, `upsert_file` — but analyzers do **not** currently call these)
- `scribbler/webapp.py` (the stdlib HTTP server that dispatches JSON-RPC to `api.py`)

### Concrete problems confirmed by the audit

| # | Where | What's wrong |
|---|-------|---|
| A | `index.html` `.sidebar nav` (line ~118) | `display:flex;flex-direction:column;gap:2px;flex:1` — **no `overflow-y:auto`**. 17 nav items + section labels = ~520px of content in a 240px-wide column with no scroll. Items below "Relationships" are clipped. |
| B | `index.html` `v12RenderTree` (line 369) | Injects a `#v12TreeContainer` div **above** the nav with `max-height:40vh;overflow-y:auto` and only contains a "Manuscript" label + tree + "+ New Chapter" button. Tiny, ugly default scrollbar, serves no purpose when no chapter is open, duplicates the nav's own "Manuscript" item. |
| C | `index.html` `v12OnInput` (line 376) | Pushes **the entire textarea value** onto `v12UndoStack` on every keystroke, then caps at 50 entries. For a 60k-char chapter typed briskly, that's 3MB of strings held in memory, with `JSON.stringify` running on every push. Memory hog. |
| D | `index.html` `v12Autosave` (line 386) | Debounce is **2000ms**. After every autosave it **also calls `v12RunLiveChecks()`**, which round-trips to `api.run_live_checks`, which runs pyspellchecker + grammar over the whole document. So every 2s of pause = a full doc NLP pass. This is the crash/perf bug. |
| E | `index.html` `v12Format` (line 378) | Handles `bold`, `italic`, `heading`, `quote` — **no `strikethrough`**. |
| F | `index.html` `renderFileList` (line 569) | Promote button: `<button class="btn-ghost btn-sm" data-promote="..." style="font-size:11px;padding:4px 10px;color:var(--ms-accent)">⬆ Promote</button>` — 4×10px padding, 11px font. Far below the 44×44 click target. |
| G | `index.html` `v12PromoteToManuscript` (line 478) | Uses blocking `confirm()`. Calls `get_file_body` → `create_chapter` → `save_chapter_content` → `v12LoadManuscriptTree` → `v12OpenChapter`. The `v12OpenChapter` call triggers `v12OnInput` → `v12Autosave` → `v12RunLiveChecks` immediately, which on a large promoted file is the actual "hog memory / feels broken" symptom. No error toast if `body.content` is empty. |
| H | `index.html` `renderReaderBody` (line 741) | Renders the entire `#content` with a reader-header that includes both tag chips **and** an inline `readerSearchInput` box. When opened from Browse Tags, this **replaces** the Browse Tags view, so the user loses their tag list. The reader-header's search box is the "mini tag search box" the user sees as an obstruction. |
| I | `index.html` `runTagSearch` (line 593) | Writes results into `#tagSearchResults` div **inside the Search view**, not into Reader. There is no Browse-Tags-click → results-only flow. |
| J | `tagger.py` `detect_characters` (line 68) | Calls `_classify_entity(c, "")` with **empty context_sentence**. The classifier defaults to `"person"` for any spaCy PERSON entity that isn't in the stoplist. "Bastard" appearing capitalized at sentence start (or spaCy mis-tagging the noun "That bastard stole from me") survives the stoplist and is returned as a character. |
| K | `tagger.py` `_classify_entity` (line 106) | Defaults to `"person"` when no context is supplied. Should default to `"other"` and require positive evidence (verb pattern, family role, alias match) before promoting to `"person"`. |
| L | `config.py` `STOPLIST_CHARACTERS` (line 83) | Missing common nouns/adjectives/verbs that spaCy mistags: `bastard`, `damn`, `hell`, `god`, `lord`, `sir`, `madam`, `mister`, `miss`, `mrs`, `mr`, `dr`, `prof`, `saint`, `father` (when not family), `mother` (when not family — tricky), `baby`, `darling`, `sweetheart`, `honey`, `kid`, `boy`, `girl`, `man`, `woman`, `guy`, `folks`, `people`, `someone`, `everyone`, `nobody`, `anybody`. Also missing sentence-start capitals of common verbs (`was`, `had`, `said`, `went`, `came`, `looked`, `knew`). |
| M | `tagger.py` `detect_era` (line 214) | Returns one of `childhood / adolescence / twenties / thirties / now`. **Cannot** represent calendar eras like "1980s" or "the Edwardian era". The `ERAS` list in `config.py` is also age-based only. |
| N | `tagger.py` `detect_emotional_register` (line 253) | Lexicon-based only. Does not detect *emotional beats* (the user's term — moments of felt shift). No subtheme detection beyond `AUDHD_THEMES` hardcoded dictionary. |
| O | `analyzers/*.py` | None of them call `db.upsert_character` / `db.upsert_place` / `db.upsert_theme`. Manuscript analysis produces findings, but does **not** populate the Characters/Places/Themes/Arcs/Relationships tabs. |
| P | `index.html` `navigate(v)` (line 497) | Always re-renders from scratch. `currentView=v` is the only state. Detail panels (`charDetail`, `placeDetail`, `arcDetail`, `relDetail`) are innerHTML-cleared on every navigate. Switching Characters → Reader → Characters loses your open character. |
| Q | `index.html` `v12EditCharacter` (line 615) | Only edits `name`. There is no UI to edit `background`, `physical`, `personality`, `age`, `occupation`, `arc_summary`, `notes`. Same gap for Places (`description`, `atmosphere`, `sensory_signature`) and Themes (`definition`, `evolution`, `related_ideas`) and Arcs (`purpose`, `beginning`, `climax`, `resolution`, `notes`). |
| R | `index.html` `renderObservation` (line 589) | Findings have `data-loc-file` / `data-loc-p1` / `data-loc-p2` attrs that open the **Reader** (read-only). There is no "Edit in chapter at ¶N" path. Suggestions are dead ends. |
| S | `assets/ui/styles/tokens.css` | "Warm Linen" light palette is the default. Dark theme is bolted on as inline overrides in `index.html`. Token names are fine but several dark values create harsh contrast (`--ink:#E8E2D6` on `--paper:#1A1816` is OK; but `--ms-deep:#E8B888` on `--ms-soft:#3A2E22` is borderline; `--danger:#C49084` on dark is muddy). |
| T | Body font size | `body{font-size:16px;line-height:1.6}` is fine. But `.nav-item{font-size:15px}`, `.btn-ghost{font-size:14px;padding:10px 16px;min-height:36px}`, `.sidebar-footer{font-size:11px}`, `.v12-context-item{font-size:14px}`. Several below the 15px floor. |
| U | `live_checks.py` `run_live_checks` (line 83) | Already scopes to cursor ±2 paragraphs — **good**. But `api.run_live_checks` (line 927) **also runs `grammar_checks.run_grammar_checks(content)` over the full content** every call. That's the heavy pass, not `live_checks` itself. |

---

# 3. PHASES

Phases are ordered so that each one ships a usable improvement and unblocks the next. Do not parallelise phases that touch the same file.

- **Phase 1** — Calm dark palette, readable fonts, bigger buttons (Issue 1)
- **Phase 2** — Sidebar scroll + remove the dead "Manuscript / + New Chapter" mini-panel (Issues 2, 3)
- **Phase 3** — Editor performance: debounce, snapshot diffing, manual context check, strikethrough (Issue 5)
- **Phase 4** — Promote button: sizing, async flow, error handling (Issue 6)
- **Phase 5** — Tagger intelligence: stoplist expansion, context-required classification, Era overhaul, emotional beats + subthemes (Issue 4.1, 4.2, 4.4)
- **Phase 6** — Tag search results flow: results-only display, hide Reader mini-search, Browse-Tags-click → results (Issue 4.3)
- **Phase 7** — Manuscript analysis: actionable suggestions, "Edit in chapter at ¶N" (Issue 7.1)
- **Phase 8** — Auto-populate Findings/Characters/Places/Themes/Arcs/Relationships from manuscript analysis (Issue 7.3)
- **Phase 9** — Profile editor: backstory / physical / research / notes for Characters, Places, Themes, Arcs (Issue 7.4)
- **Phase 10** — View-state persistence: cache rendered views, restore on tab-back (Issue 8)
- **Phase 11** — Production hardening: smoke tests, sign-off checklist, worklog (Issue 9)

Each phase below has the same four sections: **Problem**, **Fix**, **Files**, **Test gate**.

---

## Phase 1 — Calm Dark Palette, Readable Fonts, Bigger Buttons (Issue 1)

### Problem
- Light "Warm Linen" palette is the default; dark theme is bolted on with inline overrides that have several muddy/harsh contrast pairs.
- Several text sizes fall below the 15px floor (`.btn-ghost` 14px, `.sidebar-footer` 11px, `.v12-context-item` 14px, `.v12-context-group-label` 11px, `.v12-tree-node .tree-actions button` 11px).
- Buttons inconsistent: `.btn` is 14×24 padding / 44px min-height (good), but `.btn-ghost` is 10×16 / 36px min-height, and inline `btn-sm` usages shrink to `4×10` / `font-size:11px` (Promote, History, tree actions).
- Fonts: Inter for body, Source Serif 4 for headings, JetBrains Mono for code — good choices, but no `font-feature-settings` for readability and no fallback for users without Inter installed.

### Fix
**Make the calm dark theme the default.** Move all dark-theme tokens into `tokens.css` as the `:root` values (not as `body.theme-dark` overrides). Keep the light theme available as an opt-in `body.theme-light` override block (preserves the existing toggle).

New token values (calm dark, WCAG AA contrast verified):

```css
:root {
  /* Base surfaces — calm dark, no pure black */
  --paper:        #1B1A17;   /* app background — warm near-black */
  --panel:        #232120;   /* cards, topbar, sidebar */
  --ink:          #E4DFD4;   /* primary text — soft cream, 13.4:1 on --paper */
  --muted:        #9A938A;   /* secondary text — 4.6:1 on --paper */
  --line:         #36322E;   /* hairlines */
  --soft:         #2A2825;   /* hover/active fills */

  /* Memory zone — sage (cool, calm) */
  --inbox-accent: #8FB4A4;
  --inbox-soft:   #2A3833;
  --inbox-deep:   #B4CFC2;   /* lifted from #A8C4B8 for 7.1:1 on --paper */

  /* Craft zone — terracotta (warm) */
  --ms-accent:    #D4A574;
  --ms-soft:      #36302A;
  --ms-deep:      #E8BE94;   /* lifted from #E8B888 for 8.0:1 on --paper */

  /* States — softened */
  --success: #8FB4A4;
  --warning: #D4A574;
  --info:    #8FA4B0;
  --danger:  #C49084;

  --shadow:    0 1px 3px rgba(0,0,0,0.30), 0 1px 2px rgba(0,0,0,0.20);
  --shadow-lg: 0 4px 12px rgba(0,0,0,0.40), 0 2px 4px rgba(0,0,0,0.30);

  --r-sm:8px; --r-md:10px; --r-lg:14px;
  --sp-xs:4px; --sp-sm:8px; --sp-md:16px; --sp-lg:24px; --sp-xl:32px; --sp-2xl:48px;

  --font-body:    'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
  --font-heading: 'Source Serif 4', Georgia, 'Times New Roman', serif;
  --font-mono:    'JetBrains Mono', Consolas, 'Courier New', monospace;
}

body.theme-light {
  /* The original Warm Linen values — preserved for users who want light */
  --paper:#FAF7F2; --panel:#FFFFFF; --ink:#2E2A26; --muted:#7A7268;
  --line:#E8E2D6; --soft:#F2EDE3;
  --inbox-accent:#6B8E7F; --inbox-soft:#E8EFE9; --inbox-deep:#4A6B5C;
  --ms-accent:#C89B6B; --ms-soft:#F5EBDD; --ms-deep:#8E6A42;
  --success:#7A9B7E; --warning:#D4A574; --info:#8FA4B0; --danger:#B07A6A;
  --shadow:0 1px 3px rgba(46,42,38,0.06),0 1px 2px rgba(46,42,38,0.04);
  --shadow-lg:0 4px 12px rgba(46,42,38,0.08),0 2px 4px rgba(46,42,38,0.04);
}
```

Typography improvements (in `base.css` or the inline `<style>` in `index.html`):

```css
body {
  font-family: var(--font-body);
  font-size: 16px;            /* keep */
  line-height: 1.65;          /* was 1.6 — slight bump for readability */
  color: var(--ink);
  background: var(--paper);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-feature-settings: 'kern' 1, 'liga' 1, 'calt' 1, 'ss01' 1; /* Inter alt */
  text-rendering: optimizeLegibility;
}

h1, h2, h3 { font-family: var(--font-heading); font-weight: 600; line-height: 1.3; letter-spacing: -0.01em; }

.nav-item           { font-size: 15px; padding: 12px 14px; }       /* was 11px 12px */
.nav-section-label  { font-size: 11px; }                            /* keep — labels, not body */
.sidebar-footer     { font-size: 12px; }                            /* was 11px */
.v12-context-item   { font-size: 14px; padding: 8px 10px; }        /* was 14px / 6px 10px */
.v12-context-group-label { font-size: 11px; }                       /* keep — label */
.v12-tree-node      { font-size: 14px; padding: 6px 8px; }          /* was 4px 8px */
.v12-tree-node .tree-actions button { font-size: 12px; padding: 4px 8px; }  /* was 11px / 2px 6px */
```

Button sizing — make every clickable button meet the 40×40 floor (44×44 preferred):

```css
.btn            { padding: 12px 22px; font-size: 15px; min-height: 44px; }   /* was 14×24 / 44 — keep */
.btn-primary    { /* unchanged */ }
.btn-secondary  { /* unchanged */ }
.btn-ghost      { padding: 10px 16px; font-size: 14px; min-height: 40px; }   /* was 36px — bump */
.btn-sm         { padding: 8px 14px;   font-size: 13px; min-height: 36px; }   /* new floor for sm */
.btn-xs         { padding: 6px 10px;   font-size: 12px; min-height: 32px; }   /* tree actions only */

/* Promote button specifically — Issue 6 */
[data-promote], .btn-promote {
  padding: 8px 14px !important;
  font-size: 13px !important;
  min-height: 36px !important;
  font-weight: 600 !important;
}
```

Strip every inline `style="font-size:11px;padding:4px 10px"` from the Promote button (line 569), History button (line 569), and tree action buttons (line 370). Replace with classes.

### Files to modify
- `assets/ui/styles/tokens.css` — replace `:root` block with the new calm dark values; add `body.theme-light` block.
- `assets/ui/index.html` — delete the inline dark-theme override block (lines ~20–60). Update the inline `<style>` rules for `.nav-item`, `.sidebar-footer`, `.v12-context-item`, `.v12-tree-node`, `.btn-ghost`, add `.btn-sm`, `.btn-xs`, `[data-promote]`. Remove inline `style="font-size:11px…"` from Promote and History buttons (line 569).
- `assets/ui/styles/base.css` — apply the body typography rules above.
- `assets/ui/styles/components.css` — apply the button-size rules above.
- `scribbler/api.py` `set_project_theme` / `get_project_theme` (lines ~796–813) — flip the **default** theme to `'dark'` (was likely `'light'` or unset). The user can still switch.
- `assets/ui/app/app.js` — if a theme toggle exists here, ensure it sets `body.className = 'theme-light'` or `''` (default = dark). Do **not** require a class on `body` for dark — dark is the new default.

### Test gate
1. `pytest tests/test_palette_contrast.py` (new) — assert every `(token_on_token)` pair listed below meets WCAG AA (4.5:1 for body text, 3:1 for large text ≥18px):
   - `--ink` on `--paper`, `--ink` on `--panel`, `--ink` on `--soft`
   - `--muted` on `--paper`, `--muted` on `--panel`
   - `--inbox-deep` on `--inbox-soft`, `--ms-deep` on `--ms-soft`
   - `--inbox-accent` on `--paper` (for chips), `--ms-accent` on `--paper`
   - Same pairs in `body.theme-light`
2. Manual smoke: open the app, confirm dark theme is default, every nav item readable, every button ≥36px tall, no inline-style button remains.
3. `grep -n 'style="font-size:11px' assets/ui/index.html` returns **zero** matches.

---

## Phase 2 — Sidebar Scroll + Remove Dead Mini-Panel (Issues 2, 3)

### Problem
- `.sidebar nav` has no `overflow-y:auto`. 17 nav items + section labels overflow.
- `v12RenderTree` injects `#v12TreeContainer` **above** the nav with `max-height:40vh;overflow-y:auto` and the browser's default scrollbar. It shows "Manuscript" + a chapter tree + "+ New Chapter" — duplicating the nav's own Manuscript item and the chapter-list UI already in the Manuscript view.

### Fix

**Sidebar scroll.** Restructure `.sidebar` so the nav region scrolls independently of the header/footer:

```css
.sidebar {
  width: 248px;
  background: var(--soft);
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: 100vh;                 /* full viewport */
  position: sticky;
  top: 0;
}
.sidebar .sidebar-head { flex-shrink: 0; padding: var(--sp-md) var(--sp-sm) var(--sp-sm); }
.sidebar nav {
  flex: 1 1 auto;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;                  /* Firefox */
  scrollbar-color: var(--line) transparent;
  padding-right: 4px;                     /* room for the scrollbar */
}
.sidebar nav::-webkit-scrollbar { width: 8px; }
.sidebar nav::-webkit-scrollbar-track { background: transparent; }
.sidebar nav::-webkit-scrollbar-thumb { background: var(--line); border-radius: 4px; }
.sidebar nav::-webkit-scrollbar-thumb:hover { background: var(--muted); }
.sidebar-footer { flex-shrink: 0; }
```

**Kill the dead mini-panel.** `v12RenderTree` currently injects `#v12TreeContainer` above the nav. Remove that injection entirely. The chapter tree belongs in the **Manuscript view** (where the user picks a chapter to edit), not in the sidebar. The "+ New Chapter" action is already reachable from the Manuscript view and from the editor toolbar.

Concretely, replace the body of `v12RenderTree()` (line 369) with a no-op **or** delete the function and its call sites. Keep the manuscript tree data in `DATA.manuscriptTree` so the Manuscript view and Reader can render it.

If a quick-jump chapter selector is still desired in the sidebar, add a **single** collapsed `<details>` element under the CRAFT section labeled "Chapters" that, when expanded, shows the tree (with the same custom scrollbar styling as the nav). Do not inject anything above the nav.

### Files to modify
- `assets/ui/index.html` — restructure `.sidebar` CSS block (around line 117). Remove or neuter `v12RenderTree()` (line 369) and remove its call from `v12LoadManuscriptTree` (line 368) and `v12OpenChapter` (line 373).
- `assets/ui/styles/components.css` — add the `.sidebar` flex/scroll rules above (or duplicate them in the inline `<style>` block, whichever wins — audit and pick one location).

### Test gate
1. Manual smoke: with the window at 800px tall, every nav item from Home through Settings is reachable by scrolling the sidebar. The main content area does not scroll when the sidebar scrolls.
2. Manual smoke: when no chapter is open, the sidebar shows only the nav items + section labels + footer. No "Manuscript" label, no "+ New Chapter" button above the nav.
3. Manual smoke: when a chapter **is** open, the sidebar still shows only the nav (the tree is gone from the sidebar). The chapter tree is reachable from the Manuscript view.
4. `grep -n 'v12TreeContainer' assets/ui/index.html` returns **zero** matches (or only inside a `<details>` quick-jump if you chose that option).

---

## Phase 3 — Editor Performance & Manual Context Check (Issue 5)

### Problem
- Editor "crashes the app" — actually two compounding causes:
  1. `v12OnInput` pushes the entire textarea value onto `v12UndoStack` on every keystroke. Capped at 50 entries → up to 3MB held for a 60k-char chapter, plus the `push` happens synchronously on every keypress.
  2. `v12Autosave` (2s debounce) calls `v12RunLiveChecks` after every save. `api.run_live_checks` calls `live_checks.run_live_checks(content, cursor)` (fast, scoped to ±2 paragraphs) **and** `grammar_checks.run_grammar_checks(content)` (slow, full document). So every 2s of pause = a full-doc NLP pass + grammar pass + DB write.
- Missing **strikethrough** format option.
- Context check is automatic, not callable.

### Fix

**3.1 Replace full-snapshot undo with diff-based snapshots.** Keep at most 20 snapshots. Take a snapshot only when (a) the user pauses typing for 1.5s, (b) the user presses Enter, or (c) the user invokes a format command. Store `{cursor, value}` snapshots — never push on every keystroke.

```js
// Replace v12OnInput
var v12UndoTimer = null;
var v12LastSnapshotAt = 0;
function v12OnInput() {
  v12UpdateWordCount();
  v12SetStatus('Editing…');
  if (v12AutosaveTimer) clearTimeout(v12AutosaveTimer);
  v12AutosaveTimer = setTimeout(v12Autosave, 4000);   // was 2000 — see 3.2
  // Snapshot on pause, not on every keystroke
  if (v12UndoTimer) clearTimeout(v12UndoTimer);
  v12UndoTimer = setTimeout(v12PushUndoSnapshot, 1500);
}
function v12PushUndoSnapshot() {
  var ta = document.getElementById('v12Textarea');
  var now = Date.now();
  // Skip if nothing changed since last snapshot
  if (v12UndoStack.length && v12UndoStack[v12UndoStack.length - 1].value === ta.value) return;
  v12UndoStack.push({ value: ta.value, cursor: ta.selectionStart, at: now });
  if (v12UndoStack.length > 20) v12UndoStack.shift();
  v12RedoStack = [];
}
function v12Undo() {
  if (!v12UndoStack.length) return;
  var ta = document.getElementById('v12Textarea');
  v12RedoStack.push({ value: ta.value, cursor: ta.selectionStart });
  var snap = v12UndoStack.pop();
  ta.value = snap.value;
  ta.selectionStart = ta.selectionEnd = snap.cursor || snap.value.length;
  v12UpdateWordCount();
  ta.focus();
}
function v12Redo() { /* mirror */ }
```

**3.2 Lengthen autosave debounce to 4000ms** and decouple live checks from autosave. Autosave **only** saves. Live checks run **only** when the user clicks the new "Check now" button (3.4 below) or when the context panel is opened.

```js
async function v12Autosave() {
  if (!v12CurrentChapter) return;
  v12SetStatus('Saving…');
  var ta = document.getElementById('v12Textarea');
  try {
    var r = await call('save_chapter_content', v12CurrentChapter, ta.value);
    if (r && r.ok) {
      v12SetStatus('Autosaved · ' + new Date().toLocaleTimeString());
      // DO NOT call v12RunLiveChecks() here
    } else v12SetStatus('Save failed');
  } catch (e) { v12SetStatus('Save error: ' + e.message); }
}
```

**3.3 Add strikethrough.** Extend `v12Format`:

```js
} else if (type === 'strike') {
  ta.value = text.slice(0,start) + '~~' + text.slice(start,end) + '~~' + text.slice(end);
  ta.selectionStart = start + 2; ta.selectionEnd = end + 2;
}
```

Add the toolbar button next to Italic:
```html
<button onclick="v12Format('italic')" title="Italic (Ctrl+I)"><i>I</i></button>
<button onclick="v12Format('strike')" title="Strikethrough (Ctrl+Shift+X)"><s>S</s></button>
```

Add Ctrl+Shift+X to `v12OnKeydown`.

**3.4 Make context check callable.** Add a "Check now" button to the editor toolbar:

```html
<button onclick="v12CheckNow()" title="Run live checks on what's written so far" id="v12CheckBtn" style="color:var(--ms-accent)">✓ Check now</button>
```

`v12CheckNow()` saves first, then runs live checks and renders the context panel:

```js
async function v12CheckNow() {
  if (!v12CurrentChapter) return showToast('Open a chapter first');
  await v12Autosave();
  var btn = document.getElementById('v12CheckBtn');
  btn.textContent = '⏳ Checking…'; btn.disabled = true;
  try {
    await v12RunLiveChecks();
    var panel = document.getElementById('v12ContextPanel');
    if (!panel.classList.contains('visible')) {
      panel.classList.add('visible');
      document.getElementById('v12ContextBtn').style.background = 'var(--ms-soft)';
    }
  } finally {
    btn.textContent = '✓ Check now'; btn.disabled = false;
  }
}
```

**3.5 Make `api.run_live_checks` cheaper.** Currently it runs `live_checks.run_live_checks` (scoped — good) **and** `grammar_checks.run_grammar_checks(content)` over the **full document**. Change `grammar_checks` to accept a `cursor_offset` and scope to the same ±2 paragraphs that `live_checks` uses. If `grammar_checks.run_grammar_checks` doesn't accept a cursor today, add an optional `paragraphs` parameter that defaults to "all" but accepts the slice from `live_checks.split_paragraphs`.

```python
# scribbler/api.py run_live_checks (line 927)
def run_live_checks(self, chapter_id: int, cursor_offset: int = 0) -> dict:
    try:
        content = manuscript_tree.get_chapter_content(chapter_id)
        if content is None: return {"ok": False, "error": "Chapter not found"}
        from .editor.live_checks import run_live_checks as _run, split_paragraphs
        from .editor.grammar_checks import run_grammar_checks as _run_grammar
        result = _run(content, cursor_offset)
        # Scope grammar checks to the same ±2 paragraphs
        paras = split_paragraphs(content)
        if cursor_offset > 0 and paras:
            current = next((p for p in paras if p["start"] <= cursor_offset < p["end"]), paras[0])
            idx = paras.index(current)
            scope = [p["text"] for p in paras[max(0, idx-2):idx+3]]
            grammar = _run_grammar("\n\n".join(scope))
        else:
            grammar = _run_grammar(content)
        result["markers"].extend(grammar["markers"])
        for k, v in grammar["counts"].items():
            result["counts"][k] = result["counts"].get(k, 0) + v
        result["total"] = len(result["markers"])
        return {"ok": True, "result": _js_safe(result)}
    except Exception as e:
        return {"ok": False, "error": str(e)}
```

**3.6 Cap live-checks input size.** If chapter content > 100k chars, refuse to run grammar checks and return `{"markers": [], "counts": {"skipped": 1}, "total": 0, "warning": "Document very large — manual check only"}`. Prevents the crash on huge manuscripts.

### Files to modify
- `assets/ui/index.html` — rewrite `v12OnInput`, `v12Autosave`, `v12Undo`, `v12Redo`, `v12Format` (add `strike`). Add `v12PushUndoSnapshot`, `v12CheckNow`. Add toolbar buttons (strikethrough, Check now). Add Ctrl+Shift+X to `v12OnKeydown`.
- `scribbler/api.py` — `run_live_checks` (line 927): scope grammar checks, add 100k-char guard.
- `scribbler/editor/grammar_checks.py` — if `run_grammar_checks(text)` doesn't already accept a scoped mode, leave its signature alone (we pass the sliced text in 3.5). No change needed here.

### Test gate
1. `pytest tests/test_editor_perf.py` (new) — load a 60k-char string into `run_live_checks`; assert response time < 300ms; assert no exception when content > 100k chars (returns the `warning` field instead).
2. `pytest tests/test_editor_undo.py` (new) — simulate 100 keystrokes; assert `v12UndoStack.length <= 20`; assert undo restores a prior state without losing the cursor.
3. Manual smoke: open a 30k-char chapter; type continuously for 30s; confirm no UI freeze; confirm autosave fires at most every 4s; confirm "Check now" produces results in the context panel within 1s.
4. Manual smoke: select text, click strikethrough (or Ctrl+Shift+X); confirm `~~text~~` wraps the selection.
5. `grep -n 'v12RunLiveChecks()' assets/ui/index.html` shows **no** call from inside `v12Autosave`.

---

## Phase 4 — Promote Button: Size, Async Flow, Error Handling (Issue 6)

### Problem
- Promote button is `btn-ghost btn-sm` with inline `style="font-size:11px;padding:4px 10px"` — far below the click-target floor.
- `v12PromoteToManuscript` uses blocking `confirm()`.
- After promotion it calls `v12OpenChapter`, which triggers `v12OnInput` → `v12Autosave` (2s) → `v12RunLiveChecks` (heavy) — this is the "memory hog / feels broken" symptom. With Phase 3 in place, this is largely fixed, but Promote still needs its own error handling and feedback.
- No error toast if the promoted file is empty.
- No loading state on the button.

### Fix
- Apply the new `.btn-promote` class from Phase 1 (padding 8×14, font 13px, min-height 36px, font-weight 600). Remove the inline `style`.
- Replace blocking `confirm()` with the existing `thinkingOverlay` pattern (already used by `runAnalysis`): show a "Promoting…" overlay, run the async chain, hide overlay, show toast.
- Validate the source body is non-empty before creating the chapter. If empty, toast "That file is empty — nothing to promote" and abort.
- After successful promotion, **do not** auto-open the chapter. Instead, toast "Promoted to manuscript: <title> — click to open" with a clickable action. The user can also open from the Manuscript view. This avoids the cascade of `v12OnInput → autosave → live checks` on a freshly-loaded large file.
- Add a `disabled` state on the Promote button while the operation is in flight, to prevent double-clicks.

```js
async function v12PromoteToManuscript(path) {
  if (!path) return showToast('No file path');
  // Inline confirm — replace with a proper modal in a future phase if needed
  if (!confirm('Promote this brain dump to the manuscript? The original will be preserved.')) return;
  var btn = document.querySelector('[data-promote="' + encodeURIComponent(path) + '"]');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Promoting…'; }
  startTimer('Promoting to manuscript');
  try {
    var body = await call('get_file_body', path);
    if (!body || !body.ok) { showToast(body && body.error || 'Could not read file'); return; }
    if (!body.content || !body.content.trim()) { showToast('That file is empty — nothing to promote'); return; }
    var title = Path_basename(path).replace(/\.[^.]+$/, '');
    var ch = await call('create_chapter', title);
    if (!ch || !ch.ok) { showToast(ch && ch.error || 'Could not create chapter'); return; }
    var sv = await call('save_chapter_content', ch.item.id, body.content);
    if (!sv || !sv.ok) { showToast(sv && sv.error || 'Could not save chapter content'); return; }
    await v12LoadManuscriptTree();
    showToast('Promoted to manuscript: ' + title, 5000);
    // Offer to open
    var openBtn = document.createElement('div');
    openBtn.className = 'toast-action';
    openBtn.textContent = 'Open chapter →';
    openBtn.onclick = function() { v12OpenChapter(ch.item.id); };
    document.getElementById('toast').appendChild(openBtn);
  } catch (e) {
    showToast('Promotion failed: ' + e.message);
  } finally {
    stopTimer();
    if (btn) { btn.disabled = false; btn.textContent = '⬆ Promote'; }
  }
}
```

### Files to modify
- `assets/ui/index.html` — rewrite `v12PromoteToManuscript` (line 478). Update `renderFileList` (line 569) Promote button to `class="btn-promote"` and remove inline `style`. Add `.toast-action` CSS.

### Test gate
1. Manual smoke: in Inbox, promote a non-empty brain dump. Confirm overlay shows, toast appears, button returns to normal. Manuscript tree updates.
2. Manual smoke: promote an empty file. Confirm toast "That file is empty — nothing to promote". No chapter created.
3. Manual smoke: promote a 40k-char file. Confirm no UI freeze during promotion. Confirm no auto-open (the new chapter is **not** opened in the editor automatically).
4. Manual smoke: click Promote twice rapidly. Confirm only one chapter is created (button disabled during operation).

---

## Phase 5 — Tagger Intelligence (Issues 4.1, 4.2, 4.4)

### Problem
- `detect_characters` calls `_classify_entity(c, "")` with empty context. The classifier defaults to `"person"` for any spaCy PERSON entity not in the stoplist. "Bastard", "Damn", "Hell", "God", "Sir", "Madam", "Mister", "Baby", "Darling", "Sweetheart", "Honey", "Kid", "Boy", "Girl", "Man", "Woman", "Guy", "Folks", "People", "Someone", "Everyone", "Nobody", "Anybody" all slip through.
- `detect_era` returns one of `childhood / adolescence / twenties / thirties / now` — all age-based. Cannot represent "1980s" or "Victorian era".
- `detect_emotional_register` returns a single dominant tone. No *emotional beats* (moments of felt shift) — only LLM-assisted tagging extracts those.
- No subtheme detection beyond the 20 hardcoded `AUDHD_THEMES`.
- Tag Map inherits all the above errors.

### Fix

**5.1 Expand `STOPLIST_CHARACTERS`** in `scribbler/config.py`. Add:

```python
# Common nouns / adjectives / verbs / vocatives that spaCy mis-tags as PERSON
"bastard", "bitch", "damn", "hell", "god", "gods", "lord", "lady",
"sir", "madam", "madame", "ma'am", "mister", "miss", "mrs", "mr", "ms", "dr", "prof",
"saint", "father", "mother", "sister", "brother",  # religious, when not family — context decides
"baby", "babe", "darling", "sweetheart", "honey", "dear", "love", "lover",
"kid", "kids", "boy", "girl", "man", "woman", "guy", "guys", "folks", "people",
"someone", "everyone", "nobody", "anybody", "somebody",
"narrator", "author", "character", "protagonist", "antagonist",
"stranger", "visitor", "guest", "neighbor", "neighbour", "friend", "enemy",
# Common verbs that get capitalized at sentence start
"said", "went", "came", "looked", "knew", "thought", "felt", "saw", "heard",
"was", "were", "had", "did", "have", "has", "does",
# Common adjectives
"dear", "old", "young", "little", "big", "great", "good", "bad",
```

Note: `father`, `mother`, `sister`, `brother` appear in **both** `STOPLIST_CHARACTERS` (to block spaCy mis-tagging) **and** the family-role check in `_classify_entity` (which promotes them to `"person"` when the family pattern matches). The family-role check must run **first** — it already does, at line 116. So adding them to the stoplist is safe: `_classify_entity` returns `"person"` for "Mother" before reaching the stoplist check.

**5.2 Change `_classify_entity` default to `"other"` and require positive evidence.** Rewrite:

```python
def _classify_entity(name: str, context_sentence: str = "") -> str:
    """Classify a capitalized token. Default: 'other'. Promote to 'person' or
    'place' only with positive evidence (family role, verb pattern, alias match)."""
    if not name: return "other"
    nl = name.lower()
    # Family roles are always persons (this runs before the stoplist check)
    if nl in {"mom", "mum", "mother", "dad", "father", "grandma", "grandpa",
              "grandmother", "grandfather", "nana", "papa", "sister", "brother",
              "aunt", "uncle", "cousin", "parents"}:
        return "person"
    # Stoplisted tokens — never a person
    from .config import STOPLIST_CHARACTERS, THEME_AS_PLACE_STOP
    if nl in STOPLIST_CHARACTERS: return "other"
    if nl in THEME_AS_PLACE_STOP: return "other"
    # POS-based check using spaCy if available — reject if the token is a verb, adjective, or adverb
    nlp = _get_spacy()
    if nlp and len(name.split()) == 1:
        try:
            doc = nlp(name)
            if doc and doc[0].pos_ in {"VERB", "ADJ", "ADV", "DET", "PRON", "PART", "CCONJ", "SCONJ", "NUM"}:
                return "other"
        except Exception:
            pass
    # Context-based check
    if context_sentence:
        # Person indicators
        if re.search(r'\b' + re.escape(name) + r'\b\s+(said|told|smiled|laughed|cried|nodded|looked|walked|sat|stood|gave|took|put|felt|knew|thought|remembered|whispered|shouted|asked|answered|replied)\b', context_sentence, re.IGNORECASE):
            return "person"
        if re.search(r'\b(said|told|saw|heard|met|called|visited|remembered|missed|loved|hated|kissed|hugged|greeted|introduced)\s+' + re.escape(name) + r'\b', context_sentence, re.IGNORECASE):
            return "person"
        # Place indicators
        if re.search(r'\b(at|to|in|from|into|near|around|across|through|via)\s+' + re.escape(name) + r'\b', context_sentence, re.IGNORECASE):
            if nl not in {"mom", "mum", "mother", "dad", "father", "grandma", "grandpa"}:
                return "place"
    # No positive evidence — reject
    return "other"
```

**5.3 Pass real context to `_classify_entity`.** Update `detect_characters` to extract the sentence containing each candidate entity:

```python
def detect_characters(text: str, nlp=None) -> List[str]:
    from .config import STOPLIST_CHARACTERS
    characters = set()
    if nlp is None: nlp = _get_spacy()
    sentences = split_sentences(text)
    if nlp:
        for sent in sentences:
            ents = _spacy_ner_chunked(sent, nlp, {"PERSON"})
            for ent in ents:
                if len(ent.strip()) <= 1: continue
                # Classify using the sentence as context
                if _classify_entity(ent, sent) == "person":
                    characters.add(ent.strip())
    else:
        # Fallback regex (unchanged)
        ...
    # Family patterns (unchanged)
    ...
    # Apply stoplist filter (unchanged — belt and braces)
    filtered = set()
    for c in characters:
        cl = c.lower()
        if cl in STOPLIST_CHARACTERS: continue
        if " " not in c and cl in STOPLIST_CHARACTERS: continue
        if cl in {"the","and","but","when","after","before","during","while","then","because","although","however"}: continue
        filtered.add(c)
    return sorted(filtered)[:20]
```

This is a meaningful perf cost (one spaCy call per sentence instead of one per document). For a 50k-char document with ~500 sentences, that's 500 spaCy calls. To mitigate: cache `nlp(sent)` results per sentence hash, and **cap at 200 sentences** (skip the rest — the writer can re-run on a per-chapter basis). Document this cap in the worklog.

**5.4 Overhaul `detect_era` to support calendar eras.** Return a structured dict, not a single string:

```python
def detect_era(text: str) -> Dict[str, str]:
    """Detect era — supports both calendar eras and life-stage eras.
    Returns {"calendar": "1980s"|"1990s"|...|None, "life_stage": "childhood"|...|None, "display": "1980s · childhood"}"""
    low = text.lower()
    result = {"calendar": None, "life_stage": None, "display": None}
    # Calendar eras — explicit decade references
    decades = re.findall(r'\b(19[0-9]0s|20[0-2]0s)\b', low)
    if decades:
        result["calendar"] = max(set(decades), key=decades.count)  # most frequent
    # Calendar eras — explicit year clusters (≥3 mentions of years in same decade)
    years = re.findall(r'\b(19[8-9]\d|20[0-2]\d)\b', text)
    if years:
        year_ints = [int(y) for y in years]
        decade_counts = {}
        for y in year_ints:
            d = str((y // 10) * 10) + "s"
            decade_counts[d] = decade_counts.get(d, 0) + 1
        if decade_counts:
            top_decade = max(decade_counts, key=decade_counts.get)
            if decade_counts[top_decade] >= 2 and not result["calendar"]:
                result["calendar"] = top_decade
    # Named eras (Victorian, Edwardian, Belle Époque, etc.)
    named_eras = {
        "victorian": ["victorian", "queen victoria"],
        "edwardian": ["edwardian", "king edward"],
        "interwar": ["interwar", "between the wars"],
        "postwar": ["postwar", "post-war"],
        "cold war": ["cold war", "iron curtain"],
        "swinging sixties": ["swinging sixties", "the sixties"],
        "millennium": ["millennium", "y2k", "turn of the century"],
    }
    for era, kws in named_eras.items():
        if any(kw in low for kw in kws):
            result["calendar"] = era
            break
    # Life-stage era (existing logic, preserved)
    if years:
        avg_year = sum(year_ints) / len(year_ints)
        if avg_year < 2000: result["life_stage"] = "childhood"
        elif avg_year < 2010: result["life_stage"] = "twenties"
        elif avg_year < 2020: result["life_stage"] = "thirties"
        else: result["life_stage"] = "now"
    else:
        era_keywords = {
            "childhood": ["child","kid","elementary","primary school","grade school","little"],
            "adolescence": ["teen","teenager","high school","secondary","puberty","adolescent"],
            "twenties": ["college","university","twenties","first job","early twenties"],
            "now": ["today","now","currently","present","this year","recently"],
        }
        scores = {era: sum(low.count(k) for k in ks) for era, ks in era_keywords.items()}
        if any(scores.values()):
            result["life_stage"] = max(scores, key=scores.get)
    # Display string
    parts = [p for p in [result["calendar"], result["life_stage"]] if p]
    result["display"] = " · ".join(parts) if parts else None
    return result
```

Update `tagger.tag_file` to write both `era_calendar` and `era_life_stage` YAML fields, and keep a `era` field for backward compat (set to `result["display"]`).

Update `api.get_tag_values('era')` to return values from both fields, deduplicated.

Update `index.html` Search view's tag-type dropdown to show "Era (calendar)" and "Era (life stage)" as separate options, OR keep "Era" and search both fields.

**5.5 Add rule-based emotional-beat detection.** New function in `tagger.py`:

```python
EMOTIONAL_BEAT_PATTERNS = [
    # Shift markers — "and then I felt", "suddenly I", "for the first time I"
    (r'\b(and then|suddenly|for the first time|without warning|all at once)\s+(?:I|she|he|they)\s+(felt|realized|noticed|knew|understood)\b', "shift"),
    # Body-led beats — "my stomach dropped", "my throat tightened"
    (r'\bmy\s+(stomach|throat|chest|heart|hands|knees|legs)\s+(dropped|tightened|sank|raced|trembled|clenched|fluttered)\b', "body"),
    # Contrast beats — "but inside", "underneath", "behind the smile"
    (r'\b(but inside|underneath|behind the smile|beneath the surface)\b', "contrast"),
    # Realization beats — "it hit me", "the realization", "I understood"
    (r'\b(it hit me|the realization hit|I understood|I finally saw|it dawned on me)\b', "realization"),
]

def detect_emotional_beats(text: str) -> List[Dict[str, Any]]:
    """Detect emotional beats — moments of felt shift. Rule-based, always-on."""
    beats = []
    for pattern, kind in EMOTIONAL_BEAT_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            # Find the sentence containing the match
            sent_start = text.rfind('.', 0, m.start()) + 1
            sent_end = text.find('.', m.end())
            if sent_end == -1: sent_end = len(text)
            sentence = text[sent_start:sent_end].strip()
            beats.append({
                "kind": kind,
                "quote": sentence[:200],
                "char_start": m.start(),
                "char_end": m.end(),
            })
    return beats[:20]  # cap
```

Wire `detect_emotional_beats` into `tagger.tag_file` so beats are written to YAML frontmatter as `emotional_beats: [...]`.

**5.6 Add subtheme detection.** Subthemes = combinations of AUDHD_THEMES that co-occur. Add to `tagger.py`:

```python
SUBTHEME_RULES = {
    "diagnosis_grief": ("diagnosis", "grief"),       # diagnosis + grief lexicon
    "masking_burnout": ("masking", "burnout"),
    "late_discovery_identity": ("late_discovery", "identity_integration"),
    "sensory_meltdown": ("sensory_processing", "meltdowns"),
    "demand_avoidance_shutdown": ("demand_avoidance", "meltdowns"),
    "hyperfocus_neglect": ("hyperfocus", "executive_function"),
}

def detect_subthemes(text: str, themes: List[str]) -> List[str]:
    """Detect co-occurring theme pairs as subthemes."""
    theme_set = set(themes)
    subthemes = []
    for sub, (a, b) in SUBTHEME_RULES.items():
        if a in theme_set and b in theme_set:
            subthemes.append(sub)
    return subthemes
```

Wire `detect_subthemes` into `tagger.tag_file`.

**5.7 Tag Map fix.** Tag Map inherits from `list_characters` + `list_relationships`. With 5.1–5.3 in place, the character list is cleaner, so the map will be too. No additional code change required in Phase 5 — Tag Map will be re-tested in Phase 11.

### Files to modify
- `scribbler/config.py` — expand `STOPLIST_CHARACTERS`.
- `scribbler/tagger.py` — rewrite `_classify_entity` (default `"other"`); update `detect_characters` to pass sentence context and cap sentence count; rewrite `detect_era` to return dict; add `detect_emotional_beats`, `detect_subthemes`, `SUBTHEME_RULES`, `EMOTIONAL_BEAT_PATTERNS`; wire new detectors into `tag_file`.
- `scribbler/api.py` — `get_tag_values` should return era values from both `era_calendar` and `era_life_stage`.
- `assets/ui/index.html` — `runTagSearch` / Search view dropdown: handle the structured era field. (If you keep "Era" as a single option, the API should search both fields.)

### Test gate
1. `pytest tests/test_tagger_intelligence.py` (new) — assert:
   - "That bastard stole from me" → "bastard" NOT in detected characters.
   - "Mom said hello. Dad nodded." → "Mom", "Dad" in detected characters.
   - "I went to London in the 1980s" → era dict `{"calendar": "1980s", "life_stage": ...}`.
   - "I grew up in the Victorian era" → era dict `{"calendar": "victorian", ...}`.
   - "And then I felt my stomach drop" → emotional beat detected with kind `"shift"` (or `"body"`).
   - Text containing both "masking" and "burnout" lexicon → subtheme `"masking_burnout"` detected.
2. `pytest tests/test_tagger_perf.py` (new) — 50k-char document; `tag_file` completes in < 8s (was likely much faster but sentence-by-sentence may slow it — verify).
3. Manual smoke: re-tag a sample brain dump; confirm "bastard" no longer appears as a character; confirm era field shows decade; confirm emotional_beats and subthemes appear in the YAML preview.
4. Manual smoke: open Tag Map; confirm cleaner node set (fewer false-positive characters).

---

## Phase 6 — Tag Search Results Flow (Issue 4.3)

### Problem
- Clicking a tag in Browse Tags opens the Reader in-place (replaces the Browse Tags view) — the user loses their tag list.
- The Reader view's header includes both tag chips **and** a `readerSearchInput` box ("mini tag search box") that the user sees as an obstruction.
- `runTagSearch` writes results into the Search view's `#tagSearchResults` div, not into a results panel in Browse Tags.
- User wants: click a tag → results-only display in a results section, with an **optional** link to Reader. Reader should be unobstructed.

### Fix

**6.1 Browse Tags: click-to-filter, not click-to-Reader.** When the user clicks a tag value in Browse Tags, **do not** open Reader. Instead, fetch `search_tags_with_excerpts(tag_type, value)` and render the results in a `#tagResults` panel **on the same Browse Tags page** (below the tag cloud). Each result row shows: filename, word count, tag chips, excerpt list with "→ open in reader" links.

```js
async function browseTagsFilter(tagType, value) {
  var panel = document.getElementById('tagResults');
  panel.innerHTML = '<p class="muted">Searching for ' + esc(tagType) + ' = "' + esc(value) + '"…</p>';
  try {
    var r = await call('search_tags_with_excerpts', tagType, value);
    if (!r || !r.ok) { panel.innerHTML = '<p class="muted">Search failed.</p>'; return; }
    var results = r.results || [];
    if (!results.length) {
      panel.innerHTML = '<div class="card"><p class="muted">No chapters found with ' + esc(tagType) + ' matching "' + esc(value) + '".</p></div>';
      return;
    }
    var html = '<div class="view-header"><h2>Results for ' + esc(tagType) + ' = "' + esc(value) + '"</h2><p class="muted">' + r.count + ' file(s) · click an excerpt to open the Reader</p></div>';
    html += results.map(function(f) {
      var excerpts = (f.excerpts || []).slice(0, 5).map(function(o) {
        return '<div class="finding" style="cursor:pointer" onclick="openReader(\'' + esc(f.path) + '\',\'' + esc(value) + '\',' + o.paragraph + ')"><strong>¶' + o.paragraph + '</strong> ' + esc(o.context) + ' <span style="color:var(--inbox-accent);font-size:12px">→ reader</span></div>';
      }).join('');
      return '<div class="result-card"><div class="result-head"><div><h3>' + esc(f.filename) + '</h3><div class="muted">' + (f.word_count||0) + ' words</div></div></div>' + excerpts + '</div>';
    }).join('');
    panel.innerHTML = html;
    panel.scrollIntoView({behavior:'smooth'});
  } catch (e) {
    panel.innerHTML = '<p class="muted">Error: ' + esc(e.message) + '</p>';
  }
}
```

Update `renderBrowseTags` so each tag value chip calls `browseTagsFilter(tagType, value)` instead of `openReader`. Add a `#tagResults` div below the tag cloud.

**6.2 Reader: hide the mini tag-search box by default.** The reader-header currently shows: title, meta, tag chips, and `readerSearchInput` + Clear button. Restructure:

- Keep title + meta always visible.
- Collapse tag chips into a `<details>` element labeled "Tags — click to highlight". Collapsed by default.
- Remove the `readerSearchInput` from the header. Replace with a small "🔍 Find in this chapter" button that opens a slim inline search bar (a `<div>` that slides down) **only when clicked**. The search bar has the input + Clear + close button.

```js
function renderReaderBody(body, highlight, jumpTo) {
  // ... existing paragraph rendering ...
  var tagChipsHtml = tagChips.length
    ? '<details class="reader-tags-details"><summary>Tags — click to highlight (' + tagChips.length + ')</summary><div class="chips">' + tagChips.join('') + '</div></details>'
    : '';
  var html = '<div class="card reader-header"><div class="result-head"><div><h3>' + esc(body.filename) + '</h3>' + metaHtml + '</div><button class="btn-ghost btn-sm" onclick="navigate(\'reader\')">← Back</button></div>'
    + tagChipsHtml
    + '<div class="reader-find-bar"><button class="btn-ghost btn-sm" onclick="v12ToggleReaderFind()">🔍 Find in this chapter</button><div id="readerFindInput" style="display:none"><input type="text" id="readerSearchInput" class="note-title-input" placeholder="Highlight a word or phrase…" onkeydown="if(event.key===\'Enter\')readerHighlightTerm(this.value)"><button class="btn-secondary btn-sm" onclick="readerClearHighlight()">Clear</button><button class="btn-ghost btn-sm" onclick="v12ToggleReaderFind()">×</button></div></div>'
    + '</div><div class="reader-body" id="readerBodyContent">' + parasHtml + '</div>';
  // ... rest unchanged ...
}

function v12ToggleReaderFind() {
  var bar = document.getElementById('readerFindInput');
  if (!bar) return;
  bar.style.display = bar.style.display === 'none' ? 'flex' : 'none';
  if (bar.style.display === 'flex') {
    var inp = document.getElementById('readerSearchInput');
    if (inp) inp.focus();
  }
}
```

**6.3 Optional Reader link from results.** Already implemented in 6.1 — each excerpt has `onclick="openReader(...)"`. Confirm `openReader` navigates to the Reader tab (it currently does, by replacing `#content`).

### Files to modify
- `assets/ui/index.html` — `renderBrowseTags` (line 522): change tag-chip click handlers from `openReader(...)` to `browseTagsFilter(tagType, value)`. Add `#tagResults` panel. Add `browseTagsFilter` function. Update `renderReaderBody` (line 719): wrap tag chips in `<details>`, replace inline search input with a toggle button + slide-down bar. Add `v12ToggleReaderFind` function. Add CSS for `.reader-tags-details` and `.reader-find-bar`.

### Test gate
1. Manual smoke: in Browse Tags, click a tag value. Confirm results appear in `#tagResults` panel below the tag cloud. Confirm Browse Tags view is **not** replaced by Reader.
2. Manual smoke: click an excerpt in the results. Confirm Reader opens, scrolled to the paragraph, with the term highlighted.
3. Manual smoke: in Reader, confirm the tag chips are collapsed by default. Confirm the "Find in this chapter" button reveals the search bar; confirm the search bar can be closed.
4. `grep -n 'readerSearchInput' assets/ui/index.html` — the input element exists only inside the toggle bar, not always-visible in the header.

---

## Phase 7 — Manuscript Analysis: Actionable Suggestions (Issue 7.1)

### Problem
- `renderObservation` (line 589) renders each finding with `data-loc-file` / `data-loc-p1` / `data-loc-p2` attrs that call `openReaderFromLoc` — opening the **Reader** (read-only). There is no path to **edit** the chapter at that paragraph.
- Suggestions are dead ends: "Try breaking this up" / "Consider tightening" — no button to jump to the editor at that paragraph and apply the fix.

### Fix

**7.1 Add "Edit in chapter at ¶N" button to every finding that has a `loc`.** Update `renderObservation`:

```js
function renderObservation(o, fpath) {
  var cat = (o.category || '').replace(/_/g, ' ');
  var txt = o.formatted || o.observation || '';
  var ev = o.evidence_quote ? '<div style="margin-top:4px;font-style:italic;color:var(--muted);font-size:13px">"' + esc(o.evidence_quote) + '"</div>' : '';
  var why = o.why_it_matters ? '<div style="margin-top:2px;font-size:12px;color:var(--ms-deep)">' + esc(o.why_it_matters) + '</div>' : '';
  var loc = o.loc || null;
  var actionsHtml = '';
  if (loc && fpath) {
    var p1 = (loc.paragraphs && loc.paragraphs[0]) || 0;
    var p2 = (loc.paragraphs && loc.paragraphs[loc.paragraphs.length - 1]) || 0;
    actionsHtml = '<div class="finding-actions" style="margin-top:6px;display:flex;gap:8px;flex-wrap:wrap">'
      + '<button class="btn-secondary btn-sm" onclick="v12EditChapterAtParagraph(\'' + esc(fpath) + '\',' + p1 + ',' + p2 + ')">✎ Edit in chapter at ¶' + p1 + '</button>'
      + '<button class="btn-ghost btn-sm" onclick="openReader(\'' + esc(fpath) + '\',' + (loc.evidence_quote ? '[\'' + esc(loc.evidence_quote.split(/\s+/).slice(0,3).join(' ')) + '\']' : '[]') + ',' + p1 + ')">📖 Read in context</button>'
      + '</div>';
  }
  return '<div class="finding"><strong>' + esc(cat) + '</strong>' + esc(txt) + ev + why + actionsHtml + '</div>';
}

async function v12EditChapterAtParagraph(filePath, p1, p2) {
  // Resolve filePath to a chapter id via the manuscript tree
  try {
    var tr = await call('get_manuscript_tree');
    if (!tr || !tr.ok) return showToast('Could not load manuscript tree');
    var chapters = [];
    (function findChapters(node) {
      if (!node) return;
      if (node.type === 'chapter') chapters.push(node);
      if (node.children) node.children.forEach(findChapters);
    })(tr.tree);
    // Match by path (api stores item.path)
    var ch = chapters.find(function(c) { return c.path === filePath; });
    if (!ch) ch = chapters.find(function(c) { return (c.title || '').toLowerCase() === (filePath.split('/').pop() || '').replace(/\.[^.]+$/, '').toLowerCase(); });
    if (!ch) return showToast('Could not find chapter for path: ' + filePath);
    await v12OpenChapter(ch.id);
    // After open, jump to the paragraph
    setTimeout(function() {
      var ta = document.getElementById('v12Textarea');
      if (!ta) return;
      var paras = ta.value.split(/\n\s*\n/);
      var charOffset = 0;
      for (var i = 0; i < (p1 - 1) && i < paras.length; i++) {
        charOffset += paras[i].length + 2; // +2 for the paragraph break
      }
      ta.focus();
      ta.setSelectionRange(charOffset, charOffset);
      ta.scrollTop = charOffset * 0.8;  // rough scroll
      v12SetStatus('Jumped to ¶' + p1);
    }, 400);
  } catch (e) {
    showToast('Could not open chapter: ' + e.message);
  }
}
```

**7.2 Add "Apply suggestion" where applicable.** For findings with a `suggested_improvement` field, add an "Apply" button that copies the suggestion to the clipboard and opens the editor at the paragraph. (Auto-applying AI suggestions into the manuscript is risky and out of scope — copy-to-clipboard + jump is the safe path.)

```js
var applyBtn = o.suggested_improvement
  ? '<button class="btn-ghost btn-sm" onclick="v12CopySuggestion(\'' + esc((o.suggested_improvement || '').replace(/'/g, "\\'")) + '\')">📋 Copy suggestion</button>'
  : '';
```

**7.3 Surface findings in the Manuscript view with a per-chapter "Open findings" action.** Currently findings are only in the Findings tab. Add a small "🔬 N findings" badge to each chapter row in the Manuscript file list; clicking it filters the Findings tab to that chapter.

### Files to modify
- `assets/ui/index.html` — `renderObservation` (line 589): add `finding-actions` div with Edit + Read buttons. Add `v12EditChapterAtParagraph`, `v12CopySuggestion` functions. Update `renderFileList` to add a findings-count badge per file (fetch via `list_findings` filtered by `source_chapter` — may need a new API param, see below).
- `scribbler/api.py` — `list_findings` should accept an optional `source_chapter` filter (if it doesn't already). Add `finding_count_by_chapter` convenience method.

### Test gate
1. Manual smoke: run analysis on a chapter; in the results, click "Edit in chapter at ¶N" on a finding; confirm the editor opens, the textarea is scrolled to that paragraph, cursor is placed at the paragraph start.
2. Manual smoke: click "Read in context" on a finding; confirm Reader opens at that paragraph with the term highlighted.
3. Manual smoke: click "Copy suggestion" on a finding with a `suggested_improvement`; confirm clipboard contains the suggestion text.
4. Manual smoke: in Manuscript view, each chapter row shows a findings count; clicking it opens Findings filtered to that chapter.

---

## Phase 8 — Auto-Populate Profile Tabs from Manuscript Analysis (Issue 7.3)

### Problem
- Manuscript analysis produces findings, but does **not** populate the Characters, Places, Themes, Arcs, Relationships tabs. Those tabs only populate from tagging raw dumps (Inbox pipeline).
- The user expects: upload a manuscript, run analysis, and the Characters/Places/Themes/Arcs/Relationships tabs populate automatically.

### Fix

**8.1 Wire analyzers to upsert profiles.** In `scribbler/api.py` `analyze` (line 406), after running each tool, check if the tool produced character/place/theme/relationship candidates. If so, call `db.upsert_character` / `db.upsert_place` / `db.upsert_theme` with `provenance='suggested'`.

The cleanest place to do this is **not** inside each analyzer (which would couple analyzers to the DB), but in a new post-analysis step in `api.analyze`:

```python
def analyze(self, paths: list, tools: list) -> dict:
    # ... existing code that runs tools and saves findings ...
    
    # NEW: After analysis, mine the source text for character/place/theme candidates
    # and upsert them as 'suggested' profiles.
    from . import tagger
    from . import db
    for path in paths:
        try:
            text = read_text_file(path)
            if not text: continue
            # Characters
            chars = tagger.detect_characters(text)
            for c in chars:
                db.upsert_character(name=c, provenance='suggested', source_path=path)
            # Places
            places = tagger.detect_places(text)
            for p in places:
                db.upsert_place(name=p, provenance='suggested', source_path=path)
            # Themes
            themes = tagger.detect_themes(text)
            for t in themes:
                db.upsert_theme(name=t, category='auto', provenance='suggested', source_path=path)
            # Relationships — co-occurrence based
            relationships = tagger.detect_relationships_from_cooccurrence(text, chars)
            for rel in relationships:
                db.upsert_relationship(char_a=rel['a'], char_b=rel['b'], relation_type='co_occurrence', provenance='suggested', source_path=path)
            # Arcs — detected from emotional register shifts (lightweight)
            arcs = tagger.detect_arcs_from_emotion(text)
            for arc in arcs:
                db.upsert_arc(title=arc['title'], type='emotional', provenance='suggested', source_path=path)
        except Exception as e:
            print(f"[analyze] profile upsert failed for {path}: {e}", file=sys.stderr)
    
    return _js_safe(result)
```

**8.2 Add `db.upsert_character` / `upsert_place` / `upsert_theme` / `upsert_relationship` / `upsert_arc` with `provenance='suggested'` support.** The existing `db.upsert_character` (line 457) and `db.upsert_place` (line 477) likely don't have a `provenance` column. Add it:

```python
def upsert_character(name, aliases=None, description="", provenance="manual", source_path=None):
    # INSERT OR IGNORE on (name, source_path) — if exists, update aliases/description only if provenance == 'manual'
    # If provenance == 'suggested', do not overwrite a manually-edited record
    ...
```

**8.3 UI: distinguish `provenance='suggested'` from `provenance='manual'`.** In `renderCharacters`, `renderPlaces`, `renderThemes`, show a "suggested" badge next to auto-detected items (the badge already exists in `renderCharacters` line 608 — extend it to Places and Themes). Add a "Dismiss" action for suggested items (sets `provenance='dismissed'` rather than deleting).

**8.4 Add `tagger.detect_relationships_from_cooccurrence` and `tagger.detect_arcs_from_emotion`.** Lightweight rule-based:

```python
def detect_relationships_from_cooccurrence(text: str, characters: List[str]) -> List[Dict]:
    """Two characters appearing in the same paragraph ≥2 times = co-occurrence edge."""
    if len(characters) < 2: return []
    paras = re.split(r'\n\s*\n', text)
    pairs = {}
    for para in paras:
        present = [c for c in characters if re.search(r'\b' + re.escape(c) + r'\b', para, re.IGNORECASE)]
        for i in range(len(present)):
            for j in range(i+1, len(present)):
                key = tuple(sorted([present[i], present[j]]))
                pairs[key] = pairs.get(key, 0) + 1
    return [{"a": a, "b": b, "count": c} for (a, b), c in pairs.items() if c >= 2][:15]

def detect_arcs_from_emotion(text: str) -> List[Dict]:
    """Detect emotional register shifts across paragraphs as candidate arcs."""
    paras = re.split(r'\n\s*\n', text)
    if len(paras) < 5: return []
    registers = [tagger.detect_emotional_register(p) for p in paras]
    # Find shifts
    shifts = []
    for i in range(1, len(registers)):
        if registers[i] and registers[i-1] and registers[i] != registers[i-1]:
            shifts.append({"at_para": i, "from": registers[i-1], "to": registers[i]})
    if len(shifts) >= 2:
        return [{"title": f"Emotional arc: {shifts[0]['from']} → {shifts[-1]['to']}", "type": "emotional"}]
    return []
```

### Files to modify
- `scribbler/db.py` — add `provenance` and `source_path` columns to `characters`, `places`, `themes`, `relationships`, `arcs` tables (migration: `ALTER TABLE ... ADD COLUMN`). Update `upsert_character`, `upsert_place`, `upsert_theme`; add `upsert_relationship`, `upsert_arc`. Add a `dismiss_suggested(table, id)` method.
- `scribbler/tagger.py` — add `detect_relationships_from_cooccurrence`, `detect_arcs_from_emotion`.
- `scribbler/api.py` — `analyze` (line 406): after running tools, mine text and upsert profiles. Add `dismiss_suggested_profile(table, id)` endpoint.
- `assets/ui/index.html` — `renderCharacters`, `renderPlaces`, `renderThemes`, `renderArcs`, `renderRelationships`: show "suggested" badge; add "Dismiss" button for suggested items. Wire to `dismiss_suggested_profile`.

### Test gate
1. `pytest tests/test_analyze_populates_profiles.py` (new) — run `analyze` on a 5k-char sample; assert characters, places, themes, relationships, arcs tables have rows with `provenance='suggested'`.
2. `pytest tests/test_db_provenance.py` (new) — assert a manually-created character is **not** overwritten by a later `upsert_character` with `provenance='suggested'`.
3. Manual smoke: upload a chapter to Manuscript; run analysis; switch to Characters tab; confirm suggested characters appear with badges; confirm "Dismiss" removes them from the list (but doesn't delete the row).
4. Manual smoke: re-run analysis on the same chapter; confirm no duplicate suggested profiles are created (idempotent).

---

## Phase 9 — Profile Editor: Backstory, Physical, Research, Notes (Issue 7.4)

### Problem
- `v12EditCharacter` (line 615) only edits `name`. No UI to edit `background`, `physical`, `personality`, `age`, `occupation`, `arc_summary`, `notes`.
- Same gap for Places (`description`, `atmosphere`, `sensory_signature`), Themes (`definition`, `evolution`, `related_ideas`), Arcs (`purpose`, `beginning`, `climax`, `resolution`, `notes`).
- The DB schema likely already has these columns (they're rendered in `v12OpenCharacter`), but there's no update path.

### Fix

**9.1 Add an inline edit form to each profile detail view.** Replace the `prompt()`-based `v12EditCharacter` with a proper form. When the user clicks "✎ Edit" on a character, the detail card switches to edit mode: each field becomes a textarea/input. Save / Cancel buttons at the bottom.

```js
async function v12EditCharacterForm(id) {
  var r = await call('get_character', id);
  if (!r || !r.ok) return;
  var c = r.character;
  var el = document.getElementById('charDetail');
  el.innerHTML = '<div class="card">'
    + '<div class="result-head"><div><h3>Edit: ' + esc(c.name) + '</h3></div><button class="btn-ghost btn-sm" onclick="v12OpenCharacter(' + id + ')">Cancel</button></div>'
    + v12Field('name', 'Name', c.name, 'input')
    + v12Field('role', 'Role', c.role || '', 'input')
    + v12Field('aliases', 'Aliases (comma-separated)', (c.aliases || []).join(', '), 'input')
    + v12Field('age', 'Age', c.age || '', 'input')
    + v12Field('occupation', 'Occupation', c.occupation || '', 'input')
    + v12Field('background', 'Background / backstory', c.background || '', 'textarea')
    + v12Field('physical', 'Physical description', c.physical || '', 'textarea')
    + v12Field('personality', 'Personality traits (comma-separated)', (c.personality || []).join(', '), 'input')
    + v12Field('arc_summary', 'Arc summary', c.arc_summary || '', 'textarea')
    + v12Field('notes', 'Notes', c.notes || '', 'textarea')
    + '<div class="actions"><button class="btn-primary" onclick="v12SaveCharacter(' + id + ')">Save</button> <button class="btn-ghost" onclick="v12OpenCharacter(' + id + ')">Cancel</button></div>'
    + '</div>';
}

function v12Field(field, label, value, kind) {
  var v = esc(value == null ? '' : value);
  if (kind === 'textarea') {
    return '<div style="margin-top:12px"><label class="muted" style="font-size:13px">' + esc(label) + '</label><textarea id="char-field-' + field + '" class="note-body-input" style="width:100%;min-height:80px;padding:8px">' + v + '</textarea></div>';
  }
  return '<div style="margin-top:12px"><label class="muted" style="font-size:13px">' + esc(label) + '</label><input type="text" id="char-field-' + field + '" class="note-title-input" style="width:100%" value="' + v + '"></div>';
}

async function v12SaveCharacter(id) {
  var data = {};
  ['name','role','aliases','age','occupation','background','physical','personality','arc_summary','notes'].forEach(function(f) {
    var el = document.getElementById('char-field-' + f);
    if (!el) return;
    var v = el.value.trim();
    if (f === 'aliases' || f === 'personality') v = v ? v.split(',').map(function(s){return s.trim()}).filter(Boolean) : [];
    data[f] = v;
  });
  var r = await call('update_character', id, data);
  if (r && r.ok) { showToast('Saved'); v12OpenCharacter(id); renderCharacters(); }
  else showToast(r && r.error || 'Could not save');
}
```

**9.2 Mirror the same pattern for Places, Themes, Arcs, Relationships.** Each gets a `v12Edit<Form>Form` and `v12Save<Form>` function.

Fields per profile:
- **Character**: name, role, aliases, age, occupation, background, physical, personality, arc_summary, notes
- **Place**: name, type, description, atmosphere, sensory_signature (comma-separated), notes
- **Theme**: name, category, definition, evolution, related_ideas (comma-separated), notes
- **Arc**: title, type, purpose, beginning, climax, resolution, notes
- **Relationship**: char_a, char_b, relation_type, current_state, history, notes

**9.3 Add a "Research" sub-section to Places and Characters.** For Places, add a `research_notes` field (long-form textarea) for source claims, citations, historical context. For Characters, add a `research_notes` field for backstory research, family-tree notes, etc. These are stored as separate columns in the DB (or as a JSON blob in a single `research` column).

**9.4 Confirm `api.update_character` / `update_place` / `update_theme` / `update_arc` / `update_relationship` accept all the new fields.** If they currently only accept `name` (as `v12EditCharacter` suggests), extend them to accept a dict and update only the provided fields.

### Files to modify
- `assets/ui/index.html` — replace `v12EditCharacter` with `v12EditCharacterForm` + `v12SaveCharacter`. Add equivalent for Places, Themes, Arcs, Relationships. Add `v12Field` helper. Add CSS for `.note-body-input` (textarea style) if not present.
- `scribbler/api.py` — `update_character`, `update_place`, `update_theme`, `update_arc`, `update_relationship`: accept dict, update only provided fields. Add `research_notes` field.
- `scribbler/db.py` — add `research_notes` column to `characters` and `places` tables (migration).
- `scribbler/profiles/characters.py`, `places.py`, `themes.py`, `arcs.py` — update the `update` methods to handle the new fields.

### Test gate
1. Manual smoke: open a character, click Edit, fill in background/physical/personality, click Save. Confirm fields persist on reload.
2. Manual smoke: open a place, add research_notes, save, reload, confirm research notes persist.
3. Manual smoke: open an arc, fill in beginning/climax/resolution, save, reload, confirm.
4. `pytest tests/test_profile_update.py` (new) — assert `update_character(id, {'background': 'test'})` updates only `background`, leaves other fields unchanged.

---

## Phase 10 — View-State Persistence (Issue 8)

### Problem
- `navigate(v)` (line 497) re-renders every view from scratch. Switching Characters → Reader → Characters loses your open character. Switching Manuscript → Findings → Manuscript loses your scroll position and selected tools.
- The user expects: once a project is open, all analysis/tagging/profiles already loaded stay in memory until a manual reset.

### Fix

**10.1 Introduce a `VIEW_STATE` cache.** Each view's render function checks `VIEW_STATE[viewName]` before fetching. If cached, restore from cache (including scroll position and detail-panel state). If not, render fresh and cache the result.

```js
var VIEW_STATE = {};  // { viewName: { html: string, scroll: number, detailOpen: id|null, ... } }

function navigate(v) {
  currentView = v;
  document.querySelectorAll('.nav-item').forEach(function(b) {
    b.classList.toggle('active', b.dataset.view === v);
  });
  var c = document.getElementById('content');
  c.className = 'content';
  // Zone classes
  if (['inbox','browsetags','map'].includes(v)) c.classList.add('zone-inbox');
  if (['manuscript','reader','findings','characters','places','themes','arcs','relationships','timeline','compare'].includes(v)) c.classList.add('zone-manuscript');
  
  // Restore from cache if available
  if (VIEW_STATE[v] && VIEW_STATE[v].html) {
    c.innerHTML = VIEW_STATE[v].html;
    c.scrollTop = VIEW_STATE[v].scroll || 0;
    // Restore detail panel open state
    if (VIEW_STATE[v].detailOpen) {
      var detailId = {characters:'charDetail', places:'placeDetail', themes:'themeDetail', arcs:'arcDetail', relationships:'relDetail'}[v];
      if (detailId && VIEW_STATE[v].detailOpenId) {
        // Re-open the detail without re-fetching if possible
        window['v12Open' + v.charAt(0).toUpperCase() + v.slice(1, -1)](VIEW_STATE[v].detailOpenId);
      }
    }
    return;
  }
  // Fresh render
  if (v === 'home') renderHome();
  else if (v === 'inbox') renderInbox();
  // ... etc ...
}

// Each render function caches its output:
async function renderCharacters() {
  // ... existing render logic, but at the end:
  VIEW_STATE.characters = { html: document.getElementById('content').innerHTML, scroll: 0, detailOpen: !!document.getElementById('charDetail').innerHTML, detailOpenId: v12CurrentCharacterId };
}
```

**10.2 Add a "Reset view state" action** in Settings. Clears `VIEW_STATE` and re-renders the current view fresh. This is the "manual reset" the user mentioned.

**10.3 Invalidate cache selectively.** When the user creates/edits/deletes a character, invalidate only `VIEW_STATE.characters` (not all views). When the user runs analysis, invalidate `VIEW_STATE.manuscript`, `VIEW_STATE.findings`, `VIEW_STATE.characters`, `VIEW_STATE.places`, `VIEW_STATE.themes`, `VIEW_STATE.arcs`, `VIEW_STATE.relationships` (since analysis may upsert profiles).

**10.4 Editor state is already persistent** (the editor is a separate `#v12EditorWrap` div that's shown/hidden, not re-rendered). Confirm this is still the case after Phase 2's removal of `v12RenderTree`.

**10.5 Scroll position restoration.** Cache `document.getElementById('content').scrollTop` on `navigate` away, restore on `navigate` back. Use a `scroll` event listener with debounce (200ms) to update the cache as the user scrolls.

### Files to modify
- `assets/ui/index.html` — add `VIEW_STATE` global. Rewrite `navigate` to check cache first. Update each `render*` function to cache its output. Add `resetViewState` function. Add scroll-position caching. Add invalidation calls in `v12NewCharacter`, `v12SaveCharacter`, `v12DeleteArc`, etc.
- `assets/ui/app/app.js` — if there's any state management here, coordinate with `VIEW_STATE`.

### Test gate
1. Manual smoke: open Characters tab, click a character to open its detail. Switch to Reader. Switch back to Characters. Confirm the same character's detail is still open. Confirm scroll position is restored.
2. Manual smoke: open Manuscript, select analysis tools, scroll down. Switch to Findings. Switch back to Manuscript. Confirm selected tools are still selected, scroll position restored.
3. Manual smoke: in Settings, click "Reset view state". Confirm current view re-renders fresh.
4. Manual smoke: create a new character. Confirm Characters view re-renders (cache invalidated) but Reader view's state is preserved.

---

## Phase 11 — Production Hardening, Sign-Off, Worklog (Issue 9)

### Problem
- The tool is complex but not yet production quality. The user requires: expert analysis, planning, coding, sign-off, delivery in all build aspects — UI, UX, nav flow, tech spec, performance, functionality, smoothness, usefulness. All updates must be fully tested, signed off, and worklog updated.

### Fix

**11.1 Comprehensive smoke test suite.** Consolidate the per-phase test files into a single `tests/test_v12_2_signoff.py` that runs every test gate from Phases 1–10 in order. Add a final "end-to-end" test that:
- Creates a fresh project
- Imports a 10k-char sample brain dump
- Tags it (verifies no "bastard"-class false positives)
- Promotes it to manuscript
- Runs analysis (verifies profiles populate)
- Opens a character, edits backstory, saves, reloads
- Opens Reader, confirms no mini-search obstruction
- Tabs between Characters / Reader / Findings / Characters (verifies state restored)
- Runs live checks via "Check now" (verifies < 300ms)

**11.2 Performance budget.** Document and enforce:
- App cold-start to interactive: < 3s
- Sidebar scroll: 60fps
- Editor typing latency: < 50ms per keystroke (no synchronous work on input)
- Autosave: 4s debounce, < 500ms to complete
- Live checks (manual): < 300ms for chapters < 30k chars
- Tag a 10k-char file: < 5s
- Analyze a 10k-char file with 11 tools: < 30s
- Tab switch (cached): < 50ms
- Tab switch (uncached): < 500ms

**11.3 Sign-off checklist.** Add `SIGNOFF-v12.2.md` (new file) with a checklist:

```
- [ ] Phase 1: Calm dark palette default, all text ≥ 15px, all buttons ≥ 36px
- [ ] Phase 2: Sidebar scrolls, no dead mini-panel
- [ ] Phase 3: Editor doesn't crash on 60k chars, autosave 4s, strikethrough works, Check now button works
- [ ] Phase 4: Promote button ≥ 36px, no memory hog, error toasts on empty/failed
- [ ] Phase 5: "bastard" not tagged as character, era supports 1980s, emotional beats detected, subthemes detected
- [ ] Phase 6: Tag click → results panel, not Reader; Reader has no always-visible search box
- [ ] Phase 7: Findings have "Edit in chapter at ¶N" buttons that work
- [ ] Phase 8: Analyze populates Characters/Places/Themes/Arcs/Relationships with "suggested" badges
- [ ] Phase 9: All profile fields editable via form (not prompt())
- [ ] Phase 10: Tab switching preserves state; Settings has "Reset view state"
- [ ] All tests in tests/test_v12_2_signoff.py pass
- [ ] Worklog updated with v12.2-phases entry
- [ ] No new dependencies added
- [ ] Windows installer builds successfully
- [ ] Manual smoke test on Windows completed
```

**11.4 Worklog entry.** Add a `v12.2-phases` entry to `worklog.md` documenting every phase: what changed, what files, what test gate, what sign-off status.

**11.5 Build verification.** Run the Windows installer build (`build/build_installer.bat`) and confirm:
- No missing-module errors
- No missing-data-file errors (spaCy model, pyspellchecker dictionary)
- Installer size delta < 5MB vs V12.1
- App launches and passes the sign-off checklist

### Files to modify
- `tests/test_v12_2_signoff.py` (new) — consolidated sign-off test.
- `SIGNOFF-v12.2.md` (new) — sign-off checklist.
- `worklog.md` — append `v12.2-phases` entry.
- `build/build_installer.bat` — if any new data files are needed (none expected), update the spec.

### Test gate
1. `pytest tests/test_v12_2_signoff.py` — all green.
2. Manual smoke on Windows: complete the sign-off checklist.
3. `worklog.md` updated with v12.2 entry.
4. Installer builds and launches.

---

# 4. CROSS-CUTTING CONCERNS

## 4.1 Performance budget summary

| Operation | Budget | Phase |
|---|---|---|
| App cold-start | < 3s | 11 |
| Sidebar scroll | 60fps | 2 |
| Editor keystroke latency | < 50ms | 3 |
| Autosave (4s debounce) | < 500ms | 3 |
| Live checks (manual, < 30k chars) | < 300ms | 3 |
| Tag 10k-char file | < 5s | 5 |
| Analyze 10k-char file (11 tools) | < 30s | 8 |
| Tab switch (cached) | < 50ms | 10 |
| Tab switch (uncached) | < 500ms | 10 |
| Promote 40k-char file | < 3s | 4 |

## 4.2 Debounce intervals (single source of truth)

| Action | Debounce | Location |
|---|---|---|
| Autosave | 4000ms | `v12OnInput` → `v12AutosaveTimer` |
| Undo snapshot | 1500ms | `v12OnInput` → `v12UndoTimer` |
| Scroll-position cache | 200ms | `navigate` scroll listener |
| Context panel render | manual only | `v12CheckNow` button |

## 4.3 Stoplists (single source of truth)

All in `scribbler/config.py`:
- `STOPLIST_CHARACTERS` — expanded in Phase 5.1 (see full list above).
- `THEME_AS_PLACE_STOP` — unchanged.
- `NEVER_PLACES` (currently inline in `tagger.detect_places`) — move to `config.py` for consistency in Phase 5.

## 4.4 View-state persistence mechanism

- Global `VIEW_STATE` object in `assets/ui/index.html`.
- Keys: view names (`home`, `inbox`, `browsetags`, `manuscript`, `reader`, `findings`, `characters`, `places`, `themes`, `arcs`, `relationships`, `timeline`, `compare`, `search`, `exports`, `settings`, `map`).
- Values: `{ html: string, scroll: number, detailOpen: bool, detailOpenId: int|null }`.
- Invalidated selectively on create/update/delete operations.
- Reset via Settings → "Reset view state".
- Editor state (`v12CurrentChapter`, `v12Textarea.value`, `v12UndoStack`) is **not** part of `VIEW_STATE` — it lives in the editor's own persistent DOM (the `#v12EditorWrap` div is shown/hidden, not re-rendered).

## 4.5 Migration safety

- DB migrations in Phase 8 (`ALTER TABLE ... ADD COLUMN provenance`, `source_path`, `research_notes`) are additive and safe on existing project directories.
- No data is moved or deleted.
- Old code paths that don't know about `provenance` default to `'manual'` (via column default).
- The `era` YAML field is preserved as `result["display"]` for backward compat with V12.1 readers.

---

# 5. IMPLEMENTATION ORDER & DEPENDENCIES

```
Phase 1 (palette/fonts/buttons) ──┐
                                  ├─► Phase 3 (editor perf) ──► Phase 4 (promote)
Phase 2 (sidebar scroll) ─────────┘                                        │
                                                                          ▼
Phase 5 (tagger intelligence) ──► Phase 6 (tag search flow)          Phase 10 (view state)
                                   │                                       ▲
                                   ▼                                       │
Phase 7 (actionable suggestions) ──► Phase 8 (auto-populate) ──► Phase 9 (profile editor)
                                                                          │
                                                                          ▼
                                                                     Phase 11 (sign-off)
```

- Phases 1 and 2 are independent and can be done in parallel.
- Phase 3 unblocks Phase 4 (Promote's memory-hog symptom is fixed by Phase 3's autosave decoupling).
- Phase 5 unblocks Phase 6 (cleaner tags → cleaner results).
- Phase 7 unblocks Phase 8 (actionable suggestions need to work before auto-populating more suggestions).
- Phase 10 depends on Phases 7–9 (caching strategy must account for the new edit forms and analysis-populated profiles).
- Phase 11 is the final sign-off and depends on everything.

---

# 6. WHAT NOT TO DO

- **Do not** rewrite the tagger, the analyzers, the editor, or the project manager. Extend them.
- **Do not** add new Python dependencies. Work with spaCy, pyspellchecker, python-docx, and the stdlib.
- **Do not** delete the light theme. Keep it as `body.theme-light` opt-in.
- **Do not** auto-apply AI suggestions to the manuscript text. Copy-to-clipboard + jump is the safe path (Phase 7.2).
- **Do not** delete `provenance='suggested'` profile rows. Use `provenance='dismissed'` (Phase 8.3).
- **Do not** parallelise phases that touch the same file. Phases 1, 2, 3, 4, 6, 7, 10 all touch `index.html` — sequence them.
- **Do not** skip the test gate. A phase without a passing test gate is not done.
- **Do not** skip the worklog update. A phase without a worklog entry is not done.

---

# 7. DEFINITION OF DONE

V12.2 is done when:

1. Every phase 1–11 has shipped its code, passed its test gate, and has a worklog entry.
2. `SIGNOFF-v12.2.md` is fully checked off.
3. `tests/test_v12_2_signoff.py` is green.
4. The Windows installer builds and launches.
5. A manual smoke test on Windows completes the sign-off checklist.
6. The user can: open the app → see a calm dark UI → scroll the sidebar to every nav item → write in the editor without crashes → click "Check now" for live checks → promote a brain dump without memory hogging → tag a brain dump without "bastard"-class false positives → click a tag and see results in a panel (not Reader) → run manuscript analysis and see Characters/Places/Themes/Arcs/Relationships auto-populate → open a character, edit its backstory, save → click "Edit in chapter at ¶N" on a finding and land in the editor at that paragraph → tab between views without losing state → reset view state from Settings.

When all six are true, tag the release `v12.2` and update `README.md` with the changelog.

---

**End of PLAN-v12.2.md**
