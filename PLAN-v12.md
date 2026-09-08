# The Audhd Scribbler — V12 Execution Plan

> **Authoritative spec:** `SPEC-v12.md` (verbatim from the uploaded master plan)
> **Status:** Planning (locked, ready for execution)
> **Date:** 2026-09-08
> **Codename:** "The Writing App"
> **Previous plans:** `PLAN-v10.md` (delivered), `PLAN-v11.md` (superseded by SPEC-v12)
> **Platform:** Standalone Windows desktop app (pywebview + WebView2, no browser, no web server)

---

## 0. How to Read This Plan

`SPEC-v12.md` is **what** we are building — the writer's vision, the principles, the definition of done.

`PLAN-v12.md` (this document) is **how** we are building it — the concrete file paths, DB schema, API methods, UI components, and test gates for each phase.

The spec defines 10 phases. This plan expands each into 2-5 sub-phases with concrete deliverables. Total: **38 sub-phases**.

Every sub-phase ends with a test gate. No sub-phase ships without its test passing.

---

## 1. Architectural Decisions (Locked)

These decisions are made up-front to avoid rework:

### 1.1 Editor: Markdown textarea + preview, NOT contenteditable rich-text

- **Source of truth:** Markdown text in a `<textarea>`.
- **Preview:** Rendered HTML on a `<div>`, toggled by a button (not live).
- **Reasoning:** Textarea is rock-solid. No edge cases with `execCommand`, no cursor jump on re-render, no format-loss on paste. Markdown is portable, version-controllable, and exportable. The existing Reader already renders paragraphs from plain text — we reuse that code.
- **Formatting commands:** Toolbar buttons insert Markdown syntax (`**bold**`, `*italic*`, `# heading`, `> quote`) at the cursor position. No rich-text DOM manipulation.
- **Trade-off accepted:** Writers who need a WYSIWYG rich-text editor (Word-style) will not get one in v12. This is deliberate — see SPEC §6.1 "Avoid turning it into a desktop publishing system."

### 1.2 Project model: Single project per folder, SQLite-backed

- **Project folder:** `~/Documents/Audhd Scribbler Projects/<project-name>/`
- **Database:** `<project-folder>/project.scribbler` (SQLite file)
- **Manuscript files:** `<project-folder>/manuscript/<part>/<chapter>.md` (Markdown files on disk, mirrored in DB)
- **Reasoning:** The writer can always see where their work physically lives (SPEC §37). The DB is the index; the .md files are the source of truth. If the DB is corrupted, the .md files can be re-imported.
- **Multiple projects:** The app opens one project at a time. A project picker on launch (SPEC §37).

### 1.3 Analysis tiers: Instant / Quick / Deep / Project

Per SPEC §39:
- **Instant** — Local regex/dictionary checks (spell, grammar, run-on, repetition). < 100ms. Runs live while typing.
- **Quick** — Existing lightweight analyzers (craft, voice_tense, themes, editor). < 5s. Runs on demand per chapter.
- **Deep** — LLM-powered analysis (reader_perception, voice_dna, llm_assisted_tagging). 10-60s. Runs on demand, never live.
- **Project** — Whole-manuscript analysis (compare_chapters, compare_emotional_arcs, synthesis across all chapters). 30s-5min. Runs on demand, shows progress.

### 1.4 Canon vs Possibility: 4-tier status system

Per SPEC §29:
- `author_confirmed` — Writer deliberately saved this (manuscript text, manual tags, profile fields).
- `suggested` — Machine-detected with high confidence (spaCy NER characters, theme keywords).
- `possible` — Lower-confidence inference (LLM relationships, brain-dump-derived themes).
- `contradiction` — Detected inconsistency (continuity issues, conflicting character ages).

Every DB row that represents a claim about the story has a `provenance` column with one of these values. The UI visually distinguishes them (solid border = confirmed, dashed = suggested, dotted = possible, red = contradiction).

### 1.5 No new analysis engines

Per SPEC §56: "Do not build… dozens of new AI analysis engines."

The 19 existing analysis tools are sufficient. v12 **integrates** them into the editor and development areas — it does not create new ones. The only new "analysis" is the live writing-quality layer (spell/grammar/style), which is a different category (SPEC §45: "Spelling / Grammar / AI Analysis Must Be Separate").

---

## 2. Database Schema (Full v12)

All in a single SQLite file per project. Existing tables preserved; new tables added.

### 2.1 New tables

```sql
-- Project metadata (one row)
CREATE TABLE project (
    id              INTEGER PRIMARY KEY DEFAULT 1,
    name            TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    last_opened_at  TEXT,
    last_chapter_id INTEGER,
    theme           TEXT DEFAULT 'dark',
    schema_version  INTEGER DEFAULT 12
);

-- Manuscript tree (replaces ad-hoc files for v12)
CREATE TABLE manuscript_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id       INTEGER,                    -- NULL for top-level (Part)
    type            TEXT NOT NULL,              -- book|part|chapter|scene
    title           TEXT NOT NULL,
    slug            TEXT,                       -- filename-safe
    sort_order      INTEGER DEFAULT 0,
    content         TEXT,                       -- Markdown (chapters/scenes only)
    word_count      INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'seedling',    -- seedling|growing|shaping|polishing|resting
    created_at      TEXT NOT NULL,
    updated_at      TEXT,
    last_opened_at  TEXT,
    FOREIGN KEY (parent_id) REFERENCES manuscript_items(id) ON DELETE CASCADE
);
CREATE INDEX idx_ms_parent ON manuscript_items(parent_id, sort_order);

-- Brain dumps (Inbox)
CREATE TABLE brain_dumps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT,
    content         TEXT NOT NULL,
    word_count      INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    tagged_at       TEXT,
    tags            TEXT,                       -- JSON: {characters:[], places:[], themes:[], ...}
    status          TEXT DEFAULT 'unprocessed', -- unprocessed|tagged|promoted|archived
    promoted_to     INTEGER,                    -- manuscript_items.id if promoted
    FOREIGN KEY (promoted_to) REFERENCES manuscript_items(id)
);

-- Character profiles
CREATE TABLE characters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    aliases         TEXT,                       -- JSON array
    role            TEXT,                       -- family|friend|professional|self|other
    age             TEXT,
    occupation      TEXT,
    background      TEXT,
    physical        TEXT,
    personality     TEXT,                       -- JSON array of traits
    voice           TEXT,                       -- JSON: {style, vocabulary, mannerisms, expressions}
    motivation      TEXT,                       -- JSON: {wants, needs, fears, objectives}
    arc_summary     TEXT,
    arc_structure   TEXT,                       -- JSON: {beginning, pressure, change, end}
    notes           TEXT,
    provenance      TEXT DEFAULT 'author_confirmed',
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

-- Place profiles
CREATE TABLE places (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    type            TEXT,                       -- domestic|geographic|institutional|imagined
    location        TEXT,
    description     TEXT,
    atmosphere      TEXT,
    sensory_signature TEXT,                     -- JSON array
    history         TEXT,
    significance    TEXT,
    notes           TEXT,
    provenance      TEXT DEFAULT 'author_confirmed',
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

-- Theme profiles
CREATE TABLE themes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    category        TEXT,                       -- AUDHD|craft|story|personal
    definition      TEXT,                       -- writer's own definition
    related_ideas   TEXT,                       -- JSON array
    symbols         TEXT,                       -- JSON array
    motifs          TEXT,                       -- JSON array
    evolution       TEXT,                       -- how the theme develops across the book
    notes           TEXT,
    provenance      TEXT DEFAULT 'author_confirmed',
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

-- Story / narrative arcs
CREATE TABLE arcs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    type            TEXT,                       -- main_plot|subplot|relationship|mystery|thematic|emotional
    purpose         TEXT,
    beginning       TEXT,
    climax          TEXT,
    resolution      TEXT,
    turning_points  TEXT,                       -- JSON array of {description, chapter_id}
    major_beats     TEXT,                       -- JSON array
    notes           TEXT,
    provenance      TEXT DEFAULT 'author_confirmed',
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

-- Relationships (between characters)
CREATE TABLE relationships (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    character_a_id  INTEGER NOT NULL,
    character_b_id  INTEGER NOT NULL,
    relation_type   TEXT,                       -- spouse|parent-child|sibling|friend|rival|mentor|other
    history         TEXT,
    current_state   TEXT,
    conflicts       TEXT,
    key_scenes      TEXT,                       -- JSON array of chapter_ids
    notes           TEXT,
    provenance      TEXT DEFAULT 'author_confirmed',
    created_at      TEXT NOT NULL,
    updated_at      TEXT,
    FOREIGN KEY (character_a_id) REFERENCES characters(id),
    FOREIGN KEY (character_b_id) REFERENCES characters(id)
);

-- Scenes (lightweight, optional)
CREATE TABLE scenes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id      INTEGER NOT NULL,
    title           TEXT,
    summary         TEXT,
    place_id        INTEGER,
    time_marker     TEXT,
    purpose         TEXT,
    emotional_beat  TEXT,
    arc_id          INTEGER,
    char_start      INTEGER,                    -- offset in chapter content
    char_end        INTEGER,
    provenance      TEXT DEFAULT 'author_confirmed',
    FOREIGN KEY (chapter_id) REFERENCES manuscript_items(id),
    FOREIGN KEY (place_id) REFERENCES places(id),
    FOREIGN KEY (arc_id) REFERENCES arcs(id)
);

-- Notes (attachable to anything)
CREATE TABLE notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type     TEXT NOT NULL,              -- passage|paragraph|chapter|character|place|theme|arc|relationship
    target_id       INTEGER,                    -- ID of the target (or chapter_id for passage/paragraph)
    target_chapter  INTEGER,                    -- for passage/paragraph notes
    target_paragraph INTEGER,
    content         TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    provenance      TEXT DEFAULT 'author_confirmed'
);

-- Analysis findings (first-class objects, SPEC §21)
CREATE TABLE analysis_findings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type     TEXT NOT NULL,              -- chapter|passage|character|theme|place|arc|manuscript
    source_id       INTEGER,                    -- ID of the source
    source_chapter  INTEGER,
    source_paragraph INTEGER,
    tool            TEXT NOT NULL,              -- craft|editor|memory_truth|emotional_beats|...
    category        TEXT NOT NULL,              -- rhythm|defensive_register|memory_uncertainty|...
    observation     TEXT NOT NULL,
    evidence        TEXT,
    why_it_matters  TEXT,
    suggested_improvement TEXT,
    status          TEXT DEFAULT 'open',        -- open|dealt_with|dismissed
    provenance      TEXT DEFAULT 'suggested',
    created_at      TEXT NOT NULL,
    resolved_at     TEXT
);
CREATE INDEX idx_findings_source ON analysis_findings(source_type, source_id);
CREATE INDEX idx_findings_status ON analysis_findings(status);

-- Version history (manuscript snapshots)
CREATE TABLE version_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id      INTEGER NOT NULL,
    content         TEXT NOT NULL,
    word_count      INTEGER,
    saved_at        TEXT NOT NULL,
    reason          TEXT,                       -- autosave|manual|pre_analysis|pre_destructive
    FOREIGN KEY (chapter_id) REFERENCES manuscript_items(id)
);

-- Writing sessions (lightweight, for "you wrote N words today" — NOT productivity scoring)
CREATE TABLE writing_sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_date    TEXT NOT NULL,
    chapter_id      INTEGER,
    words_written   INTEGER DEFAULT 0,
    duration_seconds INTEGER DEFAULT 0,
    FOREIGN KEY (chapter_id) REFERENCES manuscript_items(id)
);
```

### 2.2 Existing tables (preserved, extended)

- `files` — kept for backward compat during migration. After migration, all v11 files become `manuscript_items` or `brain_dumps`.
- `tag_occurrences` — `file_path` column now stores `chapter:<id>` or `dump:<id>` for new items.
- `analysis_results` / `analysis_history` — `file_path` now stores `chapter:<id>`.
- `file_content_fts` — `file_path` now stores `chapter:<id>`.
- `characters` / `places` tables (old) — data migrated into the new `characters` / `places` profile tables, then old tables archived.

### 2.3 Migration

`scribbler/project/migration.py`:
1. Detect v11 DB (presence of `files` table with data, absence of `manuscript_items`).
2. Create v12 tables.
3. For each `files` row:
   - If folder is `raw-dumps`/`triage` → create a `brain_dumps` row.
   - If folder is `chapters`/`drafts`/`final` → create a `manuscript_items` row (type=chapter).
4. Migrate `characters` / `places` old tables into new profile tables (name only; writer fills in the rest).
5. Update `tag_occurrences.file_path` and `analysis_results.file_path` to new IDs.
6. Mark migration complete in `project.schema_version`.
7. Backup the old DB as `project.scribbler.v11.bak`.

---

## 3. File Structure (Full v12)

```
audhd-scribbler/
├── main.py                              (updated: project picker, icon, window config)
├── assets/
│   ├── ui/
│   │   └── index.html                   (rewritten: 3-column layout, grouped sidebar)
│   └── icons/
│       ├── app.ico                      (new: multi-res Windows icon)
│       ├── app.png                      (new: 256×256 PNG)
│       └── app.svg                      (new: SVG source)
├── scribbler/
│   ├── api.py                           (extended: ~30 new methods)
│   ├── db.py                            (extended: v12 schema, migration)
│   ├── config.py                        (extended: dark palette, editor defaults)
│   ├── passage.py                       (exists: used by editor for live analysis)
│   ├── tagger.py                        (exists: called on editor save)
│   ├── search.py                        (exists: extended for project-wide search)
│   ├── synthesis.py                     (exists)
│   ├── export.py                        (exists: extended for manuscript/project export)
│   ├── relationship_map.py              (exists)
│   ├── emotional_arc_comparison.py      (exists)
│   ├── feedback.py                      (exists)
│   ├── llm.py                           (exists)
│   ├── settings.py                      (exists: extended for project prefs)
│   ├── safety.py                        (exists: extended for version snapshots)
│   ├── file_io.py                       (exists)
│   ├── analysis_catalog.py              (exists)
│   ├── analysis_suite.py                (exists)
│   ├── writer_intelligence.py           (exists)
│   ├── passage.py                       (exists)
│   │
│   ├── project/                         (NEW — project management)
│   │   ├── __init__.py
│   │   ├── manager.py                   (open, create, list recent projects)
│   │   ├── migration.py                 (v11 → v12 migration)
│   │   └── backup.py                    (version snapshots, crash recovery)
│   │
│   ├── editor/                          (NEW — the writing surface)
│   │   ├── __init__.py
│   │   ├── writer.py                    (textarea logic, Markdown insertion, find/replace)
│   │   ├── autosave.py                  (debounced save + version snapshot)
│   │   ├── live_checks.py               (spell, grammar, run-on, repetition, style)
│   │   └── preview.py                   (Markdown → HTML rendering)
│   │
│   ├── manuscript/                      (NEW — manuscript tree)
│   │   ├── __init__.py
│   │   ├── tree.py                      (CRUD for parts/chapters/scenes)
│   │   └── export.py                    (concatenate chapters → MD/DOCX/PDF)
│   │
│   ├── profiles/                        (NEW — character/place/theme/arc/relationship cards)
│   │   ├── __init__.py
│   │   ├── characters.py
│   │   ├── places.py
│   │   ├── themes.py
│   │   ├── arcs.py
│   │   └── relationships.py
│   │
│   ├── findings/                        (NEW — analysis findings as first-class objects)
│   │   ├── __init__.py
│   │   ├── manager.py                   (CRUD, status transitions, "things to look at")
│   │   └── search.py                    (search findings by category/source/status)
│   │
│   ├── notes/                           (NEW — contextual notes)
│   │   ├── __init__.py
│   │   └── manager.py                   (attach notes to any object)
│   │
│   ├── search/                          (NEW — unified project-wide search)
│   │   ├── __init__.py
│   │   └── unified.py                   (search manuscript, dumps, profiles, findings, notes)
│   │
│   ├── timeline/                        (NEW — lightweight timeline)
│   │   ├── __init__.py
│   │   └── builder.py                   (from time_markers + chapter order)
│   │
│   └── analyzers/                       (exists — 19 tools, unchanged)
│       └── ...
│
├── build/
│   ├── scribbler.spec                   (updated: icon, new asset dirs)
│   └── windows.iss                      (updated: icon)
│
└── .github/workflows/
    └── windows-package.yml              (unchanged)
```

---

## 4. UI Layout (Full v12)

Three-column layout with a grouped sidebar:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  [icon] Audhd Scribbler — <Project Name>     [◐] [✎ Note] [🔍] [Ready]  │  ← topbar
├────────────────┬──────────────────────────────────────┬─────────────────┤
│                │                                      │                 │
│  WRITE          │                                      │  Context Panel  │
│  ◌ Home         │                                      │  ─────────────  │
│  ✉ Inbox (3)    │       # Chapter 3                   │  In this passage:│
│  📄 Manuscript  │                                      │  👤 Sarah        │
│  📖 Reader      │       Sarah was sitting at the      │  👤 David        │
│                │       kitchen table when I came       │  📍 Kitchen      │
│  DEVELOP        │       downstairs. The morning        │  🎭 Memory       │
│  👤 Characters  │       light filtered through...      │  ─────────────  │
│  📍 Places      │                                      │  🔬 Live (2)    │
│  🎭 Themes      │       ⚠ long sentence (¶2)          │  ⚠ ¶2 run-on    │
│  📈 Arcs        │       ⚠ repeated "very" (¶3)        │  ⚠ ¶3 repeat    │
│  🔗 Relationships│                                     │  ─────────────  │
│                │                                      │  📝 Notes (1)   │
│  UNDERSTAND     │                                      │  "Check Sarah's │
│  🔬 Analysis    │                                      │   age here"     │
│  🔍 Search      │                                      │                 │
│  📅 Timeline    │                                      │                 │
│  📊 Compare     │                                      │                 │
│                │                                      │                 │
│  OUTPUT         │                                      │                 │
│  ⬇ Export       │                                      │                 │
│  📁 Project     │                                      │                 │
│  ⚙ Settings     │                                      │                 │
│                │                                      │                 │
├────────────────┤                                      │                 │
│  1,247 words    │  [Write] [Preview] [Focus] [Check]  │  [Collapse ▸]   │
│  autosaved 2s   │  [Undo] [Redo] [B] [I] [H] [❝] [🔍] │                 │
└────────────────┴──────────────────────────────────────┴─────────────────┘
```

### 4.1 Three modes (SPEC §31)

- **Write mode** — Sidebar visible, context panel hidden, editor full width.
- **Develop mode** — Sidebar + editor + context panel (shows characters/places/themes in current passage).
- **Analyse mode** — Sidebar + editor + findings panel (shows live checks + saved findings).

### 4.2 Focus mode (SPEC §32)

- Hides sidebar, topbar, context panel.
- Editor centred at ~720px width.
- Word count in bottom-right corner (toggleable).
- ESC to exit.

### 4.3 Dark theme (default)

Per SPEC §46. Tokens:

| Token | Dark (default) | Light (override) |
|-------|----------------|------------------|
| `--paper` | `#1A1816` | `#FAF7F2` |
| `--panel` | `#242120` | `#FFFFFF` |
| `--ink` | `#E8E2D6` | `#2E2A26` |
| `--muted` | `#8A8278` | `#7A7268` |
| `--line` | `#3A3530` | `#E8E2D6` |
| `--accent` | `#D4A574` (terracotta) | `#C89B6B` |
| `--accent-2` | `#8FB4A4` (sage) | `#6B8E7F` |

---

## 5. Sub-Phase Breakdown

The spec defines 10 phases. Each is broken into sub-phases below.

### SPEC PHASE 1 — WRITING FOUNDATION

**Goal:** The user can actually write a chapter comfortably.

#### Sub-phase 1.1 — Project foundation
- New files: `scribbler/project/__init__.py`, `manager.py`, `migration.py`
- New DB tables: `project`, `manuscript_items`, `brain_dumps`, `version_history`, `writing_sessions`
- New API methods: `create_project(name, path)`, `open_project(path)`, `list_recent_projects()`, `get_project_info()`
- Migration: v11 → v12 (import existing files as manuscript_items + brain_dumps)
- **Test gate:** Create project, reopen, verify tree is empty. Migrate a v11 DB, verify all files appear.

#### Sub-phase 1.2 — Manuscript tree
- New files: `scribbler/manuscript/__init__.py`, `tree.py`
- New API methods: `get_manuscript_tree()`, `create_chapter(parent_id, title)`, `create_part(title)`, `rename_item(id, title)`, `move_item(id, new_parent, sort_order)`, `delete_item(id)`, `duplicate_item(id)`
- UI: Tree view in sidebar (collapsible parts, drag-to-reorder, right-click context menu)
- **Test gate:** Create part, create chapter, rename, move, duplicate, delete. Verify tree persists across reopen.

#### Sub-phase 1.3 — Editor (write mode)
- New files: `scribbler/editor/__init__.py`, `writer.py`, `preview.py`
- New API methods: `get_chapter_content(id)`, `save_chapter_content(id, content)`
- UI: Textarea + status bar (word count, save status) + toolbar (Bold, Italic, Heading, Quote)
- Markdown insertion at cursor position
- **Test gate:** Write 1000 words, verify autosave, reopen, verify content persists.

#### Sub-phase 1.4 — Autosave + version history
- New files: `scribbler/editor/autosave.py`, `scribbler/project/backup.py`
- Debounced save (2s after last keystroke)
- Version snapshot every 5 minutes during active writing, plus before destructive operations
- Status bar: `saving…` → `autosaved 2s ago` → `autosaved 5m ago`
- Crash recovery: on chapter open, if newer version_history row exists, offer to restore
- **Test gate:** Write, force-close (simulate crash), reopen, verify recovery prompt. Verify version history retains last 20 snapshots per chapter.

#### Sub-phase 1.5 — Find/replace + focus mode + word count
- UI: Find/replace overlay (Ctrl+F / Ctrl+H)
- UI: Focus mode toggle (Ctrl+E) — hides sidebar + context panel
- UI: Live word/character/paragraph count in status bar
- **Test gate:** Find a word, replace, verify count updates. Enter focus mode, verify distraction-free, ESC exits.

#### Sub-phase 1.6 — Reader ↔ Editor connection
- Reader view now opens any chapter in the Editor (one click)
- Editor's "Open in Reader" button opens the current chapter read-only with highlighting
- Both share the same passage/location system (paragraph numbers)
- **Test gate:** Open chapter in Editor, click "Open in Reader", verify same paragraph scroll position. Click a search result, verify it opens in Editor at the right paragraph.

---

### SPEC PHASE 2 — WRITING QUALITY

**Goal:** The user can improve prose without leaving the editor.

#### Sub-phase 2.1 — Live checks module
- New files: `scribbler/editor/live_checks.py`
- New dependency: `pyspellchecker` (pure Python, ~5MB)
- Checks: spelling, run-on sentences (>45 words / >3 clauses), repeated words, double spaces, trailing whitespace, passive voice, filter words, weak words, sentence starters
- Each check returns: `{paragraph, char_start, char_end, message, severity, check_type}`
- Performance: only analyse current paragraph ± 2. Debounce 2s. Target < 100ms.
- **Test gate:** Feed sample text with known issues, verify all detected. Performance test: 1000 words in < 200ms.

#### Sub-phase 2.2 — Live checks UI (issue panel)
- Right rail in Analyse mode: list of live findings
- Each finding: severity icon, message, paragraph link
- Click → scroll editor to paragraph, highlight the issue
- Per-check toggles in Settings (writer can disable specific checks)
- Master "Pause live analysis" button
- **Test gate:** Write a run-on sentence, verify it appears in the panel. Click it, verify editor scrolls. Disable a check, verify it stops firing.

#### Sub-phase 2.3 — Ignore / dismiss / add to dictionary
- Right-click a finding: `Ignore`, `Dismiss`, `Add to dictionary` (spell only)
- Ignored findings stored in `analysis_findings` with status=`dismissed`
- Personal dictionary stored in `project` table (JSON column)
- **Test gate:** Dismiss a finding, verify it doesn't reappear on next check. Add a word to dictionary, verify it's no longer flagged.

#### Sub-phase 2.4 — Grammar checks (rule-based)
- New file: `scribbler/editor/grammar_checks.py`
- Rules: subject-verb agreement (simple), tense consistency within paragraph, dangling modifiers (heuristic), comma splices, missing capitalisation
- Each finding: problem, why it may be a problem, possible correction
- **Test gate:** Feed text with known grammar issues, verify detection. Verify no false positives on clean text.

---

### SPEC PHASE 3 — CHARACTERS

**Goal:** A character profile shows both what the writer says about the character and where that character actually appears.

#### Sub-phase 3.1 — Character profiles (backend)
- New files: `scribbler/profiles/__init__.py`, `characters.py`
- New DB table: `characters` (full structured profile)
- New API methods: `create_character(data)`, `get_character(id)`, `update_character(id, data)`, `list_characters()`, `delete_character(id)`
- **Test gate:** CRUD operations on characters. Verify aliases are stored as JSON.

#### Sub-phase 3.2 — Character profiles (UI)
- New sidebar entry: `👤 Characters` (under DEVELOP)
- Character list view: cards with name, role, mention count
- Character profile view: structured form with all fields from SPEC §11.1
- Edit mode: inline form fields, save button
- **Test gate:** Create character "Sarah", fill in all fields, save, reopen, verify data persists.

#### Sub-phase 3.3 — Character evidence (auto-population)
- When a chapter is saved, run tagger → detect characters
- For each detected character:
  - If name matches existing character (by name or alias) → link
  - If no match → create stub character (name only, provenance=`suggested`)
- `characters` table gains `appearances` column (JSON: `[{chapter_id, paragraph, snippet}]`)
- UI: Character profile shows "Appears in N passages across M chapters" with clickable list
- **Test gate:** Write a chapter mentioning "Sarah", save, verify Sarah's profile shows the appearance. Click the appearance, verify it opens the editor at that paragraph.

#### Sub-phase 3.4 — Character arc workspace
- Character profile gains "Arc" tab
- Structured fields: beginning, pressure, change, end (SPEC §13)
- Plus: emotional state, key decisions, turning points, unresolved threads
- Per-character emotional arc chart (valence of scenes where they appear)
- **Test gate:** Fill in arc fields, save, verify chart renders using existing emotional-arc analysis.

#### Sub-phase 3.5 — Relationships
- New DB table: `relationships`
- New file: `scribbler/profiles/relationships.py`
- UI: `🔗 Relationships` sidebar entry
- Relationship list: pairs of characters with relation type
- Relationship detail: notes, key scenes, emotional changes
- Existing relationship map (`relationship_map.py`) now surfaces from this section
- **Test gate:** Create relationship between Sarah and David, verify it appears on the map. Click the map edge, verify it opens the relationship detail.

---

### SPEC PHASE 4 — PLACES / THEMES

**Goal:** The writer can investigate an idea, place or theme and immediately reach the relevant writing.

#### Sub-phase 4.1 — Place profiles
- New files: `scribbler/profiles/places.py`
- New DB table: `places`
- UI: `📍 Places` sidebar entry
- Place profile: name, type, description, atmosphere, sensory signature (chips), history, significance
- Auto-population: tagger detects places → link or create stub
- "Appears in" section with clickable passages
- **Test gate:** Create place "Kitchen", write chapter mentioning kitchen, verify appearance links.

#### Sub-phase 4.2 — Theme profiles
- New files: `scribbler/profiles/themes.py`
- New DB table: `themes`
- UI: `🎭 Themes` sidebar entry
- Theme profile: name, category, writer's definition, related ideas, symbols, motifs, evolution
- "Supporting passages" + "Contradictory passages" sections
- Theme density heatmap (which chapters lean heaviest on this theme)
- **Test gate:** Create theme "Masking", associate passages, verify density chart renders.

---

### SPEC PHASE 5 — ARCS / STRUCTURE

**Goal:** The writer can understand the shape of the story without constructing a complicated planning system.

#### Sub-phase 5.1 — Story / narrative arcs
- New DB table: `arcs`
- New file: `scribbler/profiles/arcs.py`
- UI: `📈 Arcs` sidebar entry
- Arc types: main_plot, subplot, relationship, mystery, thematic, emotional
- Arc fields: title, purpose, beginning, turning points, climax, resolution, related chapters
- **Test gate:** Create arc "Sarah's acceptance", connect to chapters, save, verify.

#### Sub-phase 5.2 — Scenes (lightweight)
- New DB table: `scenes`
- A chapter can contain scenes (optional — writer can ignore)
- Scene: title, summary, place, time, purpose, emotional beat, related arc, char range
- UI: Scene markers in the editor gutter (click to view/edit scene metadata)
- **Test gate:** Create scene in a chapter, verify it appears in the gutter. Click, verify metadata form.

#### Sub-phase 5.3 — Timeline
- New files: `scribbler/timeline/__init__.py`, `builder.py`
- Builds timeline from: chapter order + time_markers (existing) + scene time fields
- UI: `📅 Timeline` sidebar entry
- Timeline view: chapters in order, with time markers and detected sequence problems
- "Does my story make sense when I put it in order?" — surfaces continuity issues
- **Test gate:** Create chapters with time markers, verify timeline renders. Introduce a sequence problem (e.g. "two weeks later" before "yesterday"), verify it's flagged.

---

### SPEC PHASE 6 — INTEGRATED ANALYSIS

**Goal:** Analysis becomes part of the writing process rather than a separate destination.

#### Sub-phase 6.1 — Analysis findings as first-class objects
- New DB table: `analysis_findings`
- New files: `scribbler/findings/__init__.py`, `manager.py`
- When `analyze()` runs, each observation becomes a row in `analysis_findings`
- Fields: source, tool, category, observation, evidence, location, why_it_matters, suggested_improvement, status
- Status: open / dealt_with / dismissed
- **Test gate:** Run analysis on a chapter, verify findings appear in DB. Mark one as "dealt_with", verify it's filtered from the "open" list.

#### Sub-phase 6.2 — "Things Worth Looking At" panel
- New API method: `get_things_to_look_at()` — returns top N open findings across the project, prioritised by severity
- UI: Panel in the Home view + a dedicated section in Analyse mode
- Shows: chapter, category, observation (one line each)
- Click → open the finding detail → click → open the passage in the editor
- **Test gate:** Run analysis on 3 chapters, verify "Things to Look At" shows the top findings. Click through to the passage.

#### Sub-phase 6.3 — Contextual analysis (scope-aware)
- Selecting a passage in the editor → "Analyse passage" button
- Right-click a chapter in the tree → "Analyse chapter"
- From a character profile → "Analyse character" (runs character-related tools on chapters where they appear)
- From a theme → "Analyse theme" (runs themes tool on associated chapters)
- All use the existing 19 tools — no new engines
- **Test gate:** Select a paragraph, run "Analyse passage", verify findings are scoped to that paragraph. Run "Analyse character" on Sarah, verify only chapters where she appears are analysed.

#### Sub-phase 6.4 — Analysis ↔ Notes bridge
- Any finding can be converted to a note: "Keep as note"
- Creates a `notes` row attached to the same target as the finding
- The finding's status becomes `dealt_with` (with a link to the note)
- **Test gate:** Convert a finding to a note, verify note appears in the notes panel and the finding is marked dealt_with.

---

### SPEC PHASE 7 — UNIFIED SEARCH / MEMORY

**Goal:** The writer can remember something vaguely and find it.

#### Sub-phase 7.1 — Unified search backend
- New files: `scribbler/search/__init__.py`, `unified.py`
- Searches across: manuscript text, brain dumps, characters, places, themes, arcs, relationships, notes, analysis findings
- Uses FTS5 for text, LIKE for structured fields
- Returns grouped results: `{manuscript: [...], dumps: [...], characters: [...], ...}`
- **Test gate:** Index a project with diverse content, search "kitchen", verify results from multiple categories.

#### Sub-phase 7.2 — Unified search UI
- Global search overlay (Ctrl+F or topbar search button)
- Search bar + results grouped by type
- Each result: type icon, title, snippet, click → open in the right view
- Recent searches stored in memory (not persisted)
- **Test gate:** Search "Sarah", verify results include chapters, character profile, relationships, notes, findings.

---

### SPEC PHASE 8 — DEEP INTEGRATION

**Goal:** The application behaves like one coherent system rather than a collection of modules.

#### Sub-phase 8.1 — Editor ↔ Development linking (context panel)
- Right rail in Develop mode shows: characters/places/themes/arcs in the current passage
- Detected by running a lightweight tagger on the current paragraph (debounced)
- Click a character → open their profile
- Click a place → open its profile
- Click a theme → open its profile
- **Test gate:** Write "Sarah was in the kitchen", verify Sarah and Kitchen appear in the context panel. Click Sarah, verify her profile opens.

#### Sub-phase 8.2 — Development → Manuscript linking
- From character profile: "Show passages" → list of appearances, each clickable → opens editor
- From place profile: "Show scenes" → list of scenes set in this place
- From theme profile: "Show passages" → supporting + contradictory passages
- From arc: "Show chapters" → chapters connected to this arc
- From finding: "Open passage" → editor at the finding's location
- **Test gate:** From Sarah's profile, click "Show passages", verify list renders, click one, verify editor opens at the right paragraph.

#### Sub-phase 8.3 — Brain dump → Development
- When a brain dump is tagged, detected entities (Sarah, hospital, trauma) appear as suggestions
- Writer can click "Save as character note" → creates a note attached to Sarah's profile
- Writer can click "Save as theme note" → creates a note attached to the theme
- Original brain dump is preserved unchanged
- **Test gate:** Tag a brain dump mentioning Sarah, verify suggestion appears. Click "Save as character note", verify note appears on Sarah's profile.

#### Sub-phase 8.4 — Selection-based tools
- Selecting text in the editor shows a floating toolbar: Check spelling, Check grammar, Analyse, Find similar, Add note, Tag, Link to character, Link to theme
- "Link to character" → picker → creates a note linking the passage to the character
- **Test gate:** Select a sentence, verify floating toolbar. Click "Add note", verify note is created attached to that paragraph.

---

### SPEC PHASE 9 — UI / UX POLISH

**Goal:** The app looks and feels brilliant.

#### Sub-phase 9.1 — Dark theme + light toggle
- Implement the dark palette from §4.3
- Theme toggle in topbar (◐)
- Preference saved per-project in `project.theme`
- No flash on load (apply theme before first paint)
- **Test gate:** Toggle theme, verify all views respect it. Reopen project, verify theme persists.

#### Sub-phase 9.2 — Custom app icon
- SVG source: fountain pen nib + brain curve + spark (terracotta on charcoal)
- Rasterise to .ico (16/32/48/64/128/256) and .png (256)
- Wire into: main.py (pywebview icon), scribbler.spec (PyInstaller), windows.iss (Inno Setup), HTML favicon
- **Test gate:** Build the exe, verify icon appears in taskbar, title bar, installer.

#### Sub-phase 9.3 — Home view (Writer's Desk)
- Replaces the v11 Home
- "Continue writing" button (opens last chapter)
- "What's in my head?" (Quick Note + Inbox count + recent dumps)
- "Work on the story" (Manuscript + Characters + Places + Themes + Arcs)
- "Understand the work" (Recent analysis + Things to look at)
- "Search everything" (opens unified search)
- **Test gate:** Open app, verify Home shows the right counts and the "Continue writing" button opens the last chapter.

#### Sub-phase 9.4 — Empty states + keyboard shortcuts
- Every view has an action-oriented empty state (SPEC §46)
- Keyboard shortcuts: Ctrl+N (note), Ctrl+F (search), Ctrl+E (focus), Ctrl+S (force save), Ctrl+Enter (analyse), Ctrl+1-8 (nav), Esc (close overlay)
- Shortcut help overlay (Ctrl+?)
- **Test gate:** Verify each shortcut works. Verify empty states render for a fresh project.

#### Sub-phase 9.5 — Transitions + responsive layout
- Smooth transitions for: view switches, panel collapse, overlay open/close
- Responsive: sidebar collapses to icons on narrow windows, context panel hides below 1000px width
- **Test gate:** Resize the window, verify layout adapts. Open/close panels, verify transitions are smooth (no jank).

---

### SPEC PHASE 10 — SAFETY / RELEASE

**Goal:** The app is safe to trust with a manuscript.

#### Sub-phase 10.1 — Autosave + recovery testing
- Simulate crash mid-typing, verify recovery
- Simulate corrupt DB, verify .md files on disk are intact
- Verify version history retains last 20 snapshots per chapter
- **Test gate:** 9 test journeys from SPEC §52 (Write, Check, Character, Theme, Arc, Brain dump, Analysis, Search, Recovery).

#### Sub-phase 10.2 — Performance testing
- 10,000-word chapter: editor loads < 500ms, live analysis < 200ms
- 60,000-word manuscript (10 chapters × 6k): full analysis < 60s
- 100 files in project: tree loads < 1s
- **Test gate:** Performance tests pass on the test machine.

#### Sub-phase 10.3 — Full regression + Windows build
- Run all v10/v11 phase tests (updated for new file paths)
- Run comprehensive_test.py (240 tests, updated assertions)
- Run functional_smoke_test.py
- Trigger GitHub Actions Windows build
- Verify both artifacts (Installer + Portable) are produced
- Manual smoke test of the built exe
- **Test gate:** All tests green, CI green, manual smoke passes.

---

## 6. New API Methods (Full List)

### Project management
- `create_project(name, path)`
- `open_project(path)`
- `list_recent_projects()`
- `get_project_info()`
- `set_project_setting(key, value)`

### Manuscript tree
- `get_manuscript_tree()`
- `create_chapter(parent_id, title)`
- `create_part(title)`
- `rename_manuscript_item(id, title)`
- `move_manuscript_item(id, new_parent_id, sort_order)`
- `delete_manuscript_item(id)`
- `duplicate_manuscript_item(id)`

### Editor
- `get_chapter_content(id)`
- `save_chapter_content(id, content)`
- `run_live_checks(chapter_id, cursor_offset)`
- `get_version_history(chapter_id)`
- `restore_version(version_id)`
- `set_editor_preferences(prefs)`
- `get_editor_preferences()`

### Brain dumps
- `get_brain_dumps()`
- `create_brain_dump(title, content)`
- `tag_brain_dump(id, use_ai)`
- `promote_brain_dump_to_chapter(id, parent_id)`

### Characters
- `list_characters()`
- `create_character(data)`
- `get_character(id)`
- `update_character(id, data)`
- `delete_character(id)`
- `get_character_appearances(id)`

### Places
- `list_places()`
- `create_place(data)`
- `get_place(id)`
- `update_place(id, data)`
- `delete_place(id)`
- `get_place_appearances(id)`

### Themes
- `list_themes()`
- `create_theme(data)`
- `get_theme(id)`
- `update_theme(id, data)`
- `delete_theme(id)`
- `get_theme_passages(id)`

### Arcs
- `list_arcs()`
- `create_arc(data)`
- `get_arc(id)`
- `update_arc(id, data)`
- `delete_arc(id)`

### Relationships
- `list_relationships()`
- `create_relationship(data)`
- `get_relationship(id)`
- `update_relationship(id, data)`
- `delete_relationship(id)`

### Scenes
- `list_scenes(chapter_id)`
- `create_scene(data)`
- `update_scene(id, data)`
- `delete_scene(id)`

### Notes
- `get_notes(target_type, target_id)`
- `create_note(target_type, target_id, content)`
- `update_note(id, content)`
- `delete_note(id)`

### Findings
- `get_findings(source_type, source_id, status)`
- `get_things_to_look_at(limit)`
- `update_finding_status(id, status)`
- `convert_finding_to_note(finding_id)`

### Search
- `unified_search(query)`

### Timeline
- `get_timeline()`
- `get_continuity_issues()`

### Export
- `export_manuscript(format, include_synthesis)` (concatenate all chapters)
- `export_project_backup(path)` (ZIP of project folder)

---

## 7. New Dependencies

| Package | Purpose | Size | Reason |
|---------|---------|------|--------|
| `pyspellchecker` | Spell checking | ~5MB | Pure Python, offline, no system dictionary dependency |
| `markdown` | Markdown → HTML rendering for preview | ~500KB | Standard, well-maintained |
| `pillow` | Icon rasterisation (SVG → PNG → ICO) | ~5MB | Already a transitive dep; explicit for icon generation |

No other new dependencies. Everything else uses what's already in `requirements.txt`.

---

## 8. Testing Strategy

### 8.1 Per-sub-phase tests

Each sub-phase gets `scripts/subphase_{N.M}_test.py` testing the new behaviour in isolation.

### 8.2 Journey tests (SPEC §52)

`scripts/journey_test_{1-9}.py` — the 9 critical user journeys from the spec. These matter more than unit tests (SPEC §52: "These journeys matter more than simply accumulating hundreds of isolated tests").

### 8.3 Regression tests

- `comprehensive_test.py` — updated for v12 file paths, must still pass.
- `functional_smoke_test.py` — updated, must still pass.
- All v10/v11 phase tests — updated for new API, must still pass.

### 8.4 Performance tests

- `scripts/perf_editor.py` — type 1000 words, verify < 200ms live analysis.
- `scripts/perf_large_manuscript.py` — 60k words across 10 chapters, verify < 60s analysis.
- `scripts/perf_migration.py` — migrate a v11 project with 100 files, verify < 10s.

---

## 9. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Editor textarea too basic for serious writers | Medium | High | Markdown is portable; preview mode shows rendered output. Rich-text explicitly deferred (SPEC §6.1). |
| Live analysis too slow on long chapters | Medium | Medium | Only analyse current paragraph ± 2. Debounce 2s. Fall back to on-save-only if slow. |
| Project migration corrupts existing data | Low | High | Migration is non-destructive (old DB backed up). .md files on disk are the ultimate source of truth. |
| Too many features for one release | High | High | 38 sub-phases, each independently shippable. MVP = Sub-phases 1.1-1.6 (writing foundation). |
| DB schema too complex | Medium | Medium | All tables are independent; no joins across more than 2 tables. SQLite handles this fine. |
| Context panel is distracting | Medium | Low | Defaults to hidden. Writer enables via "Develop" mode. Collapsible. |
| Dark theme contrast issues | Low | Low | Test with WCAG contrast checker. Light fallback always available. |
| Writer feels locked in | Low | Medium | .md files on disk are always readable. Export to MD/TXT/DOCX/PDF. Project folder is transparent. |

---

## 10. Delivery Order (Summary)

| Sub-phase | What | Effort | MVP? |
|-----------|------|--------|------|
| 1.1 | Project foundation + migration | Medium | ✅ |
| 1.2 | Manuscript tree | Medium | ✅ |
| 1.3 | Editor (write mode) | Medium | ✅ |
| 1.4 | Autosave + version history | Medium | ✅ |
| 1.5 | Find/replace + focus + word count | Small | ✅ |
| 1.6 | Reader ↔ Editor connection | Small | ✅ |
| 2.1 | Live checks module | Medium | |
| 2.2 | Live checks UI | Small | |
| 2.3 | Ignore / dismiss / dictionary | Small | |
| 2.4 | Grammar checks | Medium | |
| 3.1 | Character profiles backend | Medium | |
| 3.2 | Character profiles UI | Medium | |
| 3.3 | Character evidence (auto) | Medium | |
| 3.4 | Character arc workspace | Small | |
| 3.5 | Relationships | Medium | |
| 4.1 | Place profiles | Medium | |
| 4.2 | Theme profiles | Medium | |
| 5.1 | Story arcs | Small | |
| 5.2 | Scenes | Small | |
| 5.3 | Timeline | Medium | |
| 6.1 | Findings as first-class objects | Medium | |
| 6.2 | "Things to Look At" panel | Small | |
| 6.3 | Contextual analysis (scope-aware) | Medium | |
| 6.4 | Analysis ↔ Notes bridge | Small | |
| 7.1 | Unified search backend | Medium | |
| 7.2 | Unified search UI | Small | |
| 8.1 | Editor ↔ Development linking | Medium | |
| 8.2 | Development → Manuscript linking | Small | |
| 8.3 | Brain dump → Development | Small | |
| 8.4 | Selection-based tools | Small | |
| 9.1 | Dark theme | Small | |
| 9.2 | App icon | Small | |
| 9.3 | Home (Writer's Desk) | Medium | |
| 9.4 | Empty states + shortcuts | Small | |
| 9.5 | Transitions + responsive | Small | |
| 10.1 | Autosave + recovery testing | Small | |
| 10.2 | Performance testing | Small | |
| 10.3 | Full regression + Windows build | Small | |

**MVP (Sub-phases 1.1–1.6):** A usable writing environment. The writer can create a project, write chapters, autosave, find/replace, focus mode. This alone is a meaningful upgrade over v11.

**Full v12:** All 38 sub-phases. The complete writing app described in the spec.

---

## 11. What This Plan Does Not Do

Per SPEC §56, explicitly excluded:
- No full Scrivener clone
- No full Microsoft Word clone
- No rich-text (WYSIWYG) editor — Markdown textarea + preview only
- No cloud sync or collaboration
- No AI writing assistant / autonomous rewriting
- No new analysis engines (the 19 existing tools are sufficient)
- No graph database
- No vector/RAG infrastructure
- No productivity scoring / streaks / badges
- No mobile app

The goal is a focused, brilliant writing environment that connects the existing capabilities — not a kitchen sink.
