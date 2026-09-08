# The Audhd Scribbler — v12 Plan

**Status:** Planning (architectural redesign)
**Date:** 2026-09-08
**Codename:** "The Writing App"
**Previous plans:** `PLAN-v10.md` (delivered), `PLAN-v11.md` (polish-only, superseded by this plan)
**Platform:** Standalone Windows desktop app (pywebview + WebView2, no browser, no web server)

---

## 0. The Shift

v10 and v11 kept the app as a **tool suite** — import files, tag them, analyse them, export. The writer writes *somewhere else* (Word, Google Docs, a notes app) and brings the text in for processing.

v12 changes the contract: **the writer writes here**. The app becomes a Scrivener-like writing environment with the AUDHD-focused analysis tools living inside it, available live while writing or on demand.

Everything built in v10/v11 stays. The 19 analysis tools, the tagger, the reader, the relationship map, the emotional-arc comparison, the exports — all preserved and integrated into the new structure. What changes is the **centre of gravity**: instead of the Manuscript view being a list of imported files, it becomes the writing surface itself.

---

## PART 1 — ARCHITECTURE OVERVIEW

### 1.1 The four pillars

```
┌─────────────────────────────────────────────────────────┐
│                    THE WRITING APP                       │
├──────────────┬──────────────┬──────────────┬───────────┤
│  1. EDITOR   │  2. BINDER   │ 3. PROFILES  │ 4. TOOLS  │
│              │              │              │           │
│ The writing  │ The project  │ Characters,  │ Live +    │
│ surface      │ tree         │ places,      │ saved     │
│              │              │ themes, arcs │ analysis  │
└──────────────┴──────────────┴──────────────┴───────────┘
```

1. **Editor** — a real text editor with autosave, word count, focus mode, inline live-analysis markers.
2. **Binder** — a Scrivener-like project tree: Manuscript → Parts → Chapters → Scenes. Plus separate sections for Characters, Places, Themes, Research, Trash.
3. **Profiles** — dedicated cards for each character/place/theme with structured fields, cross-references, and arc tracking.
4. **Tools** — the 19 existing analysis tools (saved, on-demand) PLUS new live tools (spell, grammar, run-on sentences, repetition) that run while writing.

### 1.2 What stays, what changes, what's new

| Component | v10/v11 status | v12 action |
|-----------|----------------|------------|
| 19 analysis tools | ✅ Exists | Keep, integrate into editor sidebar |
| Tagger (spaCy + LLM) | ✅ Exists | Keep, runs automatically on editor content |
| Tag occurrence index + FTS5 | ✅ Exists | Keep, extend to new content types |
| Reader view | ✅ Exists | Becomes the Editor (read + write) |
| Relationship map | ✅ Exists | Keep, surface from Characters section |
| Emotional arc comparison | ✅ Exists | Keep, surface from Chapters section |
| Synthesis report | ✅ Exists | Keep, generates after saved analysis |
| Exports (DOCX/MD/TXT/analysis/tag index) | ✅ Exists | Keep, add "export manuscript" (concatenated chapters) |
| Inbox (brain dumps) | ✅ Exists | Becomes a Binder section, not a separate view |
| Manuscript (imported files) | ✅ Exists | Becomes the Binder's Manuscript section |
| Search | ✅ Exists | Becomes global Cmd/Ctrl+F, searches everything |
| Home view | ✅ Exists | Becomes the Dashboard |
| Settings | ✅ Exists | Keep, add editor preferences |
| **Editor** | ❌ New | **Build** — the writing surface |
| **Binder** | ❌ New | **Build** — project tree |
| **Character profiles** | ❌ New | **Build** — structured cards |
| **Place profiles** | ❌ New | **Build** — structured cards |
| **Theme profiles** | ❌ New | **Build** — structured cards |
| **Live analysis** | ❌ New | **Build** — spell/grammar/run-on/repetition |
| **Scene cards** | ❌ New | **Build** — corkboard view |
| **Dark theme** | ❌ Missing | **Build** — default dark |
| **App icon** | ❌ Missing | **Build** — custom .ico |

### 1.3 File structure changes

```
audhd-scribbler/
├── main.py                          (updated — window config, icon)
├── assets/
│   ├── ui/
│   │   └── index.html               (rewritten — new layout)
│   └── icons/
│       ├── app.ico                  (new — multi-res Windows icon)
│       └── app.png                  (new — 256×256 PNG)
├── scribbler/
│   ├── api.py                       (extended — ~20 new methods)
│   ├── db.py                        (extended — ~8 new tables)
│   ├── config.py                    (extended — dark palette, editor defaults)
│   ├── passage.py                   (exists — used by editor for live analysis)
│   ├── tagger.py                    (exists — called on editor save)
│   ├── search.py                    (exists — extended for global search)
│   ├── synthesis.py                 (exists)
│   ├── export.py                    (exists — extended for manuscript export)
│   ├── relationship_map.py          (exists)
│   ├── emotional_arc_comparison.py  (exists)
│   ├── editor/                      (NEW — the writing surface)
│   │   ├── __init__.py
│   │   ├── live_analysis.py         (spell, grammar, run-on, repetition)
│   │   ├── autosave.py              (debounced save to DB)
│   │   └── manuscript_export.py     (concatenate chapters → DOCX/MD)
│   ├── binder/                      (NEW — project tree)
│   │   ├── __init__.py
│   │   ├── tree.py                  (hierarchical project structure)
│   │   └── migration.py             (import existing files into binder)
│   ├── profiles/                    (NEW — character/place/theme cards)
│   │   ├── __init__.py
│   │   ├── characters.py
│   │   ├── places.py
│   │   ├── themes.py
│   │   └── arcs.py                  (character arc + theme arc tracking)
│   └── analyzers/                   (exists — 19 tools, unchanged)
│       └── ...
├── build/
│   ├── scribbler.spec               (updated — icon, new asset dirs)
│   └── windows.iss                  (updated — icon)
└── .github/workflows/
    └── windows-package.yml          (unchanged)
```

---

## PART 2 — THE EDITOR (Writing Surface)

### 2.1 Editor requirements

The editor is the heart of v12. It must be:
- **Fast** — no lag when typing in a 10,000-word chapter.
- **Autosaving** — debounce 2 seconds after last keystroke, save to DB.
- **Live-analysis-aware** — show inline markers for issues without blocking typing.
- **Distraction-free** — focus mode hides everything except the text.
- **Word-counting** — live word/character/paragraph count in the status bar.
- **Format-aware** — supports Markdown (headings, bold, italic, blockquotes) rendered on save.

### 2.2 Technical approach

Use a `<textarea>` with a synchronised preview `<div>`, NOT a contenteditable rich-text editor. Reasons:
- Textarea is rock-solid, no edge cases with formatting commands.
- Markdown is the source of truth — portable, version-controllable, exportable.
- Preview is rendered on save (or on a toggle), not live (avoids cursor jump issues).
- The existing reader view already renders paragraphs from plain text — we reuse that code.

**Editor layout:**
```
┌─────────────────────────────────────────────────┐
│  ch-03.md · 1,247 words · autosaved 2s ago      │  ← status bar
├─────────────────────────────────────────────────┤
│                                                  │
│   # Chapter 3                                    │
│                                                  │
│   Mom was sitting at the kitchen table           │  ← textarea
│   when I came downstairs. The morning            │     (monospace or
│   light filtered through the yellow              │      serif, user choice)
│   curtains and I remember thinking               │
│   that this was the last normal                  │
│   morning we would have for a while.             │
│                                                  │
│   ⚠ run-on sentence (¶2)                        │  ← inline markers
│   ⚠ repeated word "very" (¶3)                   │
│                                                  │
├─────────────────────────────────────────────────┤
│  [✎ Write] [👁 Preview] [🎯 Focus] [🔬 Analyse] │  ← mode bar
└─────────────────────────────────────────────────┘
```

### 2.3 Editor modes

1. **Write mode** (default) — textarea + status bar + inline markers. Sidebar visible.
2. **Preview mode** — rendered Markdown (headings, bold, italic, blockquotes, paragraphs). Read-only.
3. **Focus mode** — textarea only, sidebar and topbar hidden. ESC to exit.
4. **Analyse mode** — saved analysis runs and displays inline (observations appear as margin notes next to the paragraphs they reference).

### 2.4 Autosave

- Debounce 2 seconds after the last keystroke.
- Save to `binder_items` table (new — see Part 3) with `content` column.
- Status bar shows: `saving…` → `autosaved 2s ago` → `autosaved 5m ago`.
- On app launch, if a binder item has unsaved changes (crash recovery), offer to restore.

### 2.5 Live analysis (inline markers)

A new module `scribbler/editor/live_analysis.py` runs after each autosave (debounced). It does NOT use the heavy 19-tool suite — those are for saved analysis. Live analysis is lightweight and fast:

| Check | How | Marker |
|-------|-----|--------|
| Spell check | `pyspellchecker` library (already pure-Python, no external deps) | Red squiggle under misspelled word |
| Run-on sentence | Sentence > 45 words OR > 3 clauses (regex on `,` `;` `—`) | Yellow bar in left margin next to paragraph |
| Repeated word | Same word 3+ times in one paragraph (excluding stopwords) | Yellow underline |
| Double space | `  ` (two+ spaces) | Grey highlight |
| Trailing whitespace | Lines ending with space/tab | Grey highlight |
| Passive voice (simple) | `was/were/been + past participle` regex | Blue underline |
| Filter words | Existing FILTER_WORDS list | Grey underline |
| Weak words | Existing WEAK_WORDS list | Grey underline |

**Performance**: live analysis only runs on the current paragraph + the 2 paragraphs before and after (not the whole document). This keeps it fast even in 10k-word chapters.

**Toggle**: each check can be turned on/off in Settings → Editor preferences. A master `Pause live analysis` button in the status bar.

### 2.6 Word count + progress tracking

- Live word count in the status bar.
- Optional **session target** (e.g. "write 500 words this session") — shows progress bar.
- Optional **chapter target** (e.g. "this chapter should be ~3000 words") — shows progress against target.
- Daily word count logged to `writing_sessions` table (new) — powers the Dashboard's "you wrote N words today" card.

### 2.7 New files

| File | Purpose |
|------|---------|
| `scribbler/editor/__init__.py` | Package init |
| `scribbler/editor/live_analysis.py` | `run_live_analysis(text, cursor_paragraph)` → list of markers |
| `scribbler/editor/autosave.py` | `save_binder_item(item_id, content)` — debounced DB write |
| `scribbler/editor/manuscript_export.py` | `export_manuscript(format, include_synthesis)` — concatenate all chapters in order |

### 2.8 New API methods

| Method | Purpose |
|--------|---------|
| `get_binder_item_content(item_id)` | Returns the current content of a binder item |
| `save_binder_item(item_id, content)` | Saves content (autosave) |
| `run_live_analysis(item_id, cursor_offset)` | Returns markers for the current view |
| `set_editor_preferences(prefs)` | Saves editor preferences (font, size, live checks on/off) |
| `get_editor_preferences()` | Returns saved preferences |
| `log_writing_session(word_count_delta)` | Logs a writing session for the dashboard |

---

## PART 3 — THE BINDER (Project Tree)

### 3.1 Binder structure

Scrivener-like hierarchical tree:

```
📁 My Memoir
├── 📄 Manuscript
│   ├── 📁 Part One: Childhood
│   │   ├── 📄 Ch 01: The Kitchen
│   │   ├── 📄 Ch 02: The Porch
│   │   └── 📄 Ch 03: The Phone Call
│   ├── 📁 Part Two: Adolescence
│   │   ├── 📄 Ch 04: High School
│   │   └── 📄 Ch 05: Diagnosis
│   └── 📄 Part Three: Adulthood
│       └── 📄 Ch 06: Unmasking
├── 📄 Inbox (brain dumps)
│   ├── 📄 dump-2024-03-15.md
│   └── 📄 dump-2024-03-22.md
├── 👤 Characters
│   ├── 👤 Mom
│   ├── 👤 Dad
│   └── 👤 Nathan
├── 📍 Places
│   ├── 📍 The Kitchen
│   └── 📍 The Porch
├── 🎭 Themes
│   ├── 🎭 Masking
│   └── 🎭 Memory
├── 📚 Research
│   └── 📄 autism-stats.md
└── 🗑 Trash
```

### 3.2 Binder item types

| Type | Icon | Content | Children |
|------|------|---------|----------|
| `project` | 📁 | (none — root) | Yes |
| `folder` | 📁 | (none) | Yes |
| `chapter` | 📄 | Markdown text | No |
| `scene` | 📄 | Markdown text | No |
| `brain_dump` | 📄 | Markdown text | No |
| `character` | 👤 | Structured profile (see Part 4) | No |
| `place` | 📍 | Structured profile (see Part 5) | No |
| `theme` | 🎭 | Structured profile (see Part 6) | No |
| `research` | 📄 | Markdown text | No |
| `trash` | 🗑 | (none — holds deleted items) | Yes |

### 3.3 Database schema

New table `binder_items`:

```sql
CREATE TABLE binder_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id   INTEGER,              -- NULL for top-level
    type        TEXT NOT NULL,        -- folder|chapter|scene|brain_dump|character|place|theme|research|trash
    title       TEXT NOT NULL,
    slug        TEXT,                 -- URL-safe filename for export
    sort_order  INTEGER DEFAULT 0,   -- ordering within parent
    content     TEXT,                 -- markdown text (for chapters/scenes/dumps/research) or JSON (for profiles)
    word_count  INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'seedling',  -- seedling|growing|shaping|polishing|resting
    created_at  TEXT NOT NULL,
    updated_at  TEXT,
    metadata    TEXT,                 -- JSON: { tags: {...}, analysis: {...}, etc. }
    FOREIGN KEY (parent_id) REFERENCES binder_items(id) ON DELETE CASCADE
);
CREATE INDEX idx_binder_parent ON binder_items(parent_id, sort_order);
CREATE INDEX idx_binder_type ON binder_items(type);
```

### 3.4 Migration from v11

`scribbler/binder/migration.py` handles importing existing files:
- For each file in `raw-dumps/` or `triage/`: create a `brain_dump` binder item under `Inbox`.
- For each file in `chapters/`/`drafts/`/`final/`: create a `chapter` binder item under `Manuscript`.
- Carry over all tags from the `files` table into `binder_items.metadata`.
- Mark old `files` table rows as `migrated = 1` (new column) so they don't appear in the old views.
- The old file folders stay on disk — the binder items reference them by `slug` for export compatibility.

**Migration is automatic on first launch of v12.** A one-time dialog explains what happened and offers to open the Binder view.

### 3.5 Binder UI

A tree view in the left sidebar (replacing the current nav). Collapsible folders, drag-to-reorder, right-click for context menu (New, Rename, Delete, Move to Trash, Duplicate, Export).

```
┌─────────────────┬──────────────────────────────┐
│  📁 My Memoir   │                              │
│  ├📄 Manuscript │                              │
│  │ ├📁 Part One │       (editor or             │
│  │ │ ├📄 Ch 01  │        profile view          │
│  │ │ └📄 Ch 02  │        here)                 │
│  │ └📁 Part Two │                              │
│  ├📄 Inbox (3)  │                              │
│  ├👤 Characters │                              │
│  ├📍 Places     │                              │
│  ├🎭 Themes     │                              │
│  ├📚 Research   │                              │
│  └🗑 Trash      │                              │
├─────────────────┤                              │
│  🔍 Search      │                              │
│  📈 Compare     │                              │
│  🕸 Map         │                              │
│  ⬇ Export       │                              │
│  ⚙ Settings     │                              │
└─────────────────┴──────────────────────────────┘
```

The bottom section (Search, Compare, Map, Export, Settings) are **global tools** that work across the whole project — they stay as nav items below the binder.

### 3.6 New files

| File | Purpose |
|------|---------|
| `scribbler/binder/__init__.py` | Package init |
| `scribbler/binder/tree.py` | `get_tree()`, `create_item()`, `move_item()`, `delete_item()`, `rename_item()` |
| `scribbler/binder/migration.py` | `migrate_v11_to_v12()` — one-time import |

### 3.7 New API methods

| Method | Purpose |
|--------|---------|
| `get_binder_tree()` | Returns the full tree (nested dict) |
| `create_binder_item(parent_id, type, title)` | Creates a new item, returns its ID |
| `move_binder_item(item_id, new_parent_id, sort_order)` | Drag-and-drop reorder |
| `rename_binder_item(item_id, new_title)` | Rename |
| `delete_binder_item(item_id)` | Move to Trash (soft delete) |
| `permanently_delete_binder_item(item_id)` | Hard delete |
| `duplicate_binder_item(item_id)` | Copy an item |

---

## PART 4 — CHARACTER PROFILES

### 4.1 Profile structure

Each character is a binder item of type `character` with structured content (JSON in `binder_items.content`):

```json
{
  "name": "Mom",
  "aliases": ["Mother", "Mum"],
  "role": "family",
  "description": "A woman holding everything together by a thread.",
  "physical": "Silver-streaked hair, always an apron, hands that smell of coffee.",
  "personality": ["anxious", "loving", "reserved", "stubborn"],
  "background": "Grew up on a farm, married young, sacrificed her career for the family.",
  "arc_summary": "From holding the family together to finally letting go.",
  "goals": ["Keep the family safe", "Hide her own struggles"],
  "fears": ["That Nathan will end up like his father"],
  "relationships": [
    { "other": "Nathan", "relation": "parent-child", "notes": "Tense but loving" },
    { "other": "Dad", "relation": "spouse", "notes": "Estranged by Chapter 3" }
  ],
  "first_appearance": "Ch 01",
  "tags": ["masking", "burnout"]
}
```

### 4.2 Character profile UI

A dedicated card view (not the editor) with structured fields:

```
┌─────────────────────────────────────────────────────┐
│  👤 Mom                              [✎ Edit] [🔗]  │
├─────────────────────────────────────────────────────┤
│  Aliases: Mother, Mum                               │
│  Role: Family                                        │
│  First appears: Ch 01                                │
│                                                      │
│  ── Description ──                                   │
│  A woman holding everything together by a thread.    │
│                                                      │
│  ── Physical ──                                      │
│  Silver-streaked hair, always an apron, hands that   │
│  smell of coffee.                                    │
│                                                      │
│  ── Personality ──                                   │
│  [anxious] [loving] [reserved] [stubborn]           │
│                                                      │
│  ── Arc ──                                           │
│  From holding the family together to finally         │
│  letting go.                                         │
│  [📈 View arc chart]                                 │
│                                                      │
│  ── Goals ──                                         │
│  • Keep the family safe                              │
│  • Hide her own struggles                            │
│                                                      │
│  ── Fears ──                                         │
│  • That Nathan will end up like his father           │
│                                                      │
│  ── Relationships ──                                 │
│  Nathan (parent-child) — Tense but loving            │
│  Dad (spouse) — Estranged by Chapter 3               │
│                                                      │
│  ── Appears in ──                                    │
│  Ch 01 (¶1, ¶4, ¶7)  Ch 02 (¶3)  Ch 03 (¶1-5)      │
│  [📂 Open all in Reader]                             │
└─────────────────────────────────────────────────────┘
```

The `🔗` button links the character to the relationship map. The `📈 View arc chart` button opens a per-character emotional arc chart (valence of scenes where they appear). The `📂 Open all in Reader` button opens a multi-file reader view with all their appearances highlighted.

### 4.3 Auto-population

When the writer tags a chapter, the tagger detects characters. If a detected character name matches an existing profile's `name` or `aliases`, the chapter is auto-linked to that profile. If no match exists, a stub profile is created (name only) and flagged for the writer to fill in.

### 4.4 Character arc tracking

For each character, track their emotional presence across chapters:
- For each chapter where the character appears, compute the average valence of paragraphs containing them.
- Plot as a line chart (chapter on X, valence on Y).
- This is a per-character slice of the existing emotional arc comparison.

---

## PART 5 — PLACE PROFILES

### 5.1 Profile structure

```json
{
  "name": "The Kitchen",
  "type": "domestic",
  "description": "The emotional centre of the house. Where news lands.",
  "sensory_signature": ["coffee", "burnt toast", "yellow curtains", "cold floor"],
  "emotional_register": "tense, domestic, charged",
  "chapters": ["Ch 01", "Ch 03", "Ch 07"],
  "notes": "The kitchen changes meaning across the book — from safe to threatening."
}
```

### 5.2 Place profile UI

Similar card structure to characters, with:
- A **sensory signature** chip list (the smells/sounds/textures associated with this place).
- A **map of appearances** (which chapters, which paragraphs).
- A **place density chart** (how often the place appears across the manuscript timeline).

---

## PART 6 — THEME PROFILES

### 6.1 Profile structure

```json
{
  "name": "Masking",
  "category": "AUDHD",
  "description": "The performance of normalcy that exhausts the narrator.",
  "manifestations": [
    "Forcing eye contact", "Scripting conversations", "Suppressing stims"
  ],
  "chapters": ["Ch 01", "Ch 04", "Ch 06"],
  "evolution": "From unconscious habit to conscious refusal.",
  "related_themes": ["identity_integration", "burnout"]
}
```

### 6.2 Theme profile UI

Card with:
- Manifestations chip list.
- Evolution text field (how the theme develops across the book).
- Related themes (linked chips → jump to those profiles).
- **Theme density heatmap** across chapters (which chapters lean heaviest on this theme).

---

## PART 7 — LIVE ANALYSIS TOOLS

### 7.1 The live analysis panel

A collapsible right rail in the editor, showing live markers as the writer types:

```
┌──────────────────────────┐
│  🔬 Live (3 issues)      │
├──────────────────────────┤
│  ⚠ ¶2 Run-on sentence    │
│    (47 words, 4 clauses) │
│    [click to jump]       │
│                          │
│  ⚠ ¶3 Repeated: "very"   │
│    (3 times)             │
│    [click to jump]       │
│                          │
│  ⚠ ¶4 Passive voice      │
│    "was followed"        │
│    [click to jump]       │
└──────────────────────────┘
```

Clicking a marker scrolls the editor to the paragraph and highlights the issue.

### 7.2 Live checks (new module)

`scribbler/editor/live_analysis.py`:

| Function | Check | Source |
|----------|-------|--------|
| `check_spelling(text)` | Misspelled words | `pyspellchecker` (add to requirements.txt) |
| `check_run_on_sentences(text)` | Sentences > 45 words OR > 3 clause-separators | Regex |
| `check_repeated_words(text)` | Same word 3+ times in a paragraph | Counter (exclude stopwords) |
| `check_double_spaces(text)` | `  ` anywhere | Regex |
| `check_trailing_whitespace(text)` | Lines ending with space/tab | Regex |
| `check_passive_voice(text)` | `was/were/been + past participle` | Regex |
| `check_filter_words(text)` | Existing FILTER_WORDS list | Existing |
| `check_weak_words(text)` | Existing WEAK_WORDS list | Existing |
| `check_sentence_starters(text)` | Same opener 3+ times in a row | Regex |

Each function returns a list of `{ paragraph, char_start, char_end, message, severity }` markers.

### 7.3 Performance budget

- Live analysis runs debounced (2s after last keystroke).
- Only analyses the current paragraph ± 2 paragraphs (not the whole document).
- Target: < 100ms per run on a typical paragraph.
- If slow, fall back to on-save-only analysis (configurable in Settings).

### 7.4 New dependency

`pyspellchecker` — pure Python, no system dictionaries required. Adds ~5MB to the bundle. Bundled English dictionary.

---

## PART 8 — SAVED ANALYSIS (Integration)

### 8.1 The 19 tools stay

No changes to the existing analysis tools. They run on demand via the `🔬 Analyse` button in the editor mode bar.

### 8.2 Analyse mode

When the writer clicks `🔬 Analyse`:
1. The current binder item's content is saved.
2. The selected tools run (writer picks from the existing tool picker).
3. Results display in the right rail (replacing live analysis).
4. Observations are clickable → jump to the paragraph in the editor.
5. Synthesis report appears at the top of the rail.

### 8.3 Analysis history per item

Each binder item remembers its analysis history (already in DB via `analysis_history`). The `📚 History` button (existing) opens a list of prior runs.

### 8.4 Cross-item analysis

The existing `compare_emotional_arcs` and `compare_chapters` work on multiple binder items (chapters). No changes needed — just wire the UI to select chapters from the binder instead of from the old file list.

---

## PART 9 — VISUALISATIONS

### 9.1 Relationship map (existing — surface from Characters)

Clicking `🕸 Map` in the bottom nav opens the existing relationship map. No changes to the backend. The UI is restyled for the dark theme.

### 9.2 Emotional arc comparison (existing — surface from Manuscript)

Clicking `📈 Compare` in the bottom nav opens the existing arc comparison. Chapter selection now comes from the binder tree instead of the old file list.

### 9.3 NEW: Character arc chart

Per-character emotional arc across chapters. Accessed from a character profile's `📈 View arc chart` button.

- X axis: chapters (in order).
- Y axis: average valence of paragraphs where the character appears.
- Single line, single character.
- Markers show which chapter had the highest/lowest emotional presence.

### 9.4 NEW: Theme density heatmap

Per-theme density across chapters. Accessed from a theme profile's `📊 View density` button.

- X axis: chapters.
- Y axis: theme density (mentions per 1000 words).
- Heatmap cells coloured by intensity.

### 9.5 NEW: Manuscript structure map

A bird's-eye view of the whole manuscript:

```
Ch 01 ████████████ 3,200w  😊 +0.4
Ch 02 ██████████████████ 4,800w  😐 +0.1
Ch 03 ██████████ 2,100w  😢 -0.3
Ch 04 ██████████████ 3,600w  😊 +0.2
Ch 05 ████████████████████████ 6,100w  😢 -0.5
Ch 06 ██████████████ 3,400w  😊 +0.6
```

Each row is a chapter, with a word-count bar and an emoji representing the average valence. Clicking a row opens the chapter in the editor. Accessed from the Dashboard.

---

## PART 10 — UI/UX OVERHAUL

### 10.1 Dark theme (default)

As specified in PLAN-v11 Part 1. Tokens:

| Token | Dark (default) |
|-------|----------------|
| `--paper` | `#1A1816` |
| `--panel` | `#242120` |
| `--ink` | `#E8E2D6` |
| `--muted` | `#8A8278` |
| `--line` | `#3A3530` |
| `--accent` (terracotta) | `#D4A574` |
| `--accent-2` (sage) | `#8FB4A4` |

Light theme available via toggle in topbar. Preference saved to `settings.json`.

### 10.2 App icon

Custom SVG → `.ico` (multi-res: 16/32/48/64/128/256). Concept: a fountain pen nib forming the lower curve of a brain, with a spark at top-right. Wired into:
- `main.py` (pywebview window icon)
- `build/scribbler.spec` (PyInstaller exe icon)
- `build/windows.iss` (Inno Setup installer icon)
- HTML `<link rel="icon">` (title bar favicon)

### 10.3 Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [icon] Audhd Scribbler          [◐ Theme] [✎ Note] [Ready] │  ← topbar
├──────────────┬──────────────────────────────┬───────────────┤
│              │                              │               │
│  📁 Manuscript│                              │  🔬 Live (3)  │
│  ├📁 Part One │       # Chapter 3            │  ⚠ ¶2 run-on │
│  │ ├📄 Ch 01  │                              │  ⚠ ¶3 repeat │
│  │ └📄 Ch 02  │       Mom was sitting at the │  ⚠ ¶4 passive│
│  ├📄 Inbox (3)│       kitchen table when I   │               │
│  ├👤 Characters│      came downstairs...      │  ── or ──     │
│  ├📍 Places   │                              │               │
│  ├🎭 Themes   │                              │  ✦ Synthesis  │
│  ├📚 Research │                              │  Voice: ...   │
│  └🗑 Trash    │                              │  Distance:... │
│              │                              │               │
│  ───────────  │                              │               │
│  🔍 Search    │                              │               │
│  📈 Compare   │                              │               │
│  🕸 Map       │                              │               │
│  ⬇ Export     │                              │               │
│  ⚙ Settings   │                              │               │
└──────────────┴──────────────────────────────┴───────────────┘
```

Three columns: Binder (left, 240px), Editor (centre, flexible), Analysis rail (right, 280px, collapsible).

### 10.4 Focus mode

`🎯 Focus` hides the binder and analysis rail, leaving only the editor centred at a comfortable reading width (~720px). ESC exits.

### 10.5 Dashboard (replaces Home)

Opened on app launch. Shows:
- Greeting + word count today.
- 4 action buttons: `Continue writing`, `Tag brain dumps`, `Analyse chapters`, `Search everything`.
- Recent activity feed (from `activity_log`).
- Manuscript structure map (Part 9.5).

### 10.6 Global search

`Ctrl+F` opens a search overlay (not a separate view). Searches:
- Binder item titles.
- Binder item content (FTS5).
- Tags.
- Analysis observations.

Results grouped by type, each clickable → opens the item in the editor at the match location.

### 10.7 Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New quick note |
| `Ctrl+F` | Global search |
| `Ctrl+R` | Toggle reader/preview mode |
| `Ctrl+E` | Focus mode |
| `Ctrl+S` | Force save (autosave still runs) |
| `Ctrl+Enter` | Run saved analysis on current item |
| `Ctrl+1`-`8` | Jump to binder sections |
| `Ctrl+Shift+↑`/`↓` | Move item up/down in binder |
| `Esc` | Close overlay / exit focus mode |

---

## PART 11 — DATABASE CHANGES

### 11.1 New tables

```sql
-- Binder tree (replaces files table for v12 items)
CREATE TABLE binder_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id   INTEGER,
    type        TEXT NOT NULL,
    title       TEXT NOT NULL,
    slug        TEXT,
    sort_order  INTEGER DEFAULT 0,
    content     TEXT,
    word_count  INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'seedling',
    created_at  TEXT NOT NULL,
    updated_at  TEXT,
    metadata    TEXT,
    FOREIGN KEY (parent_id) REFERENCES binder_items(id) ON DELETE CASCADE
);

-- Writing sessions (for the dashboard)
CREATE TABLE writing_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT NOT NULL,           -- YYYY-MM-DD
    item_id     INTEGER,
    word_count_start INTEGER,
    word_count_end INTEGER,
    duration_seconds INTEGER,
    FOREIGN KEY (item_id) REFERENCES binder_items(id)
);

-- Live analysis cache (avoids re-running on every keystroke)
CREATE TABLE live_analysis_cache (
    item_id     INTEGER NOT NULL,
    paragraph   INTEGER NOT NULL,
    check_type  TEXT NOT NULL,
    char_start  INTEGER,
    char_end    INTEGER,
    message     TEXT,
    severity    TEXT,
    PRIMARY KEY (item_id, paragraph, check_type, char_start),
    FOREIGN KEY (item_id) REFERENCES binder_items(id) ON DELETE CASCADE
);
```

### 11.2 Existing tables

- `files` — kept for backward compat; marked `migrated = 1` after binder import.
- `tag_occurrences` — extended: `file_path` column now stores `binder_item_id` (as string) for new items. Old rows unchanged.
- `analysis_results` / `analysis_history` — `file_path` column now stores `binder_item_id`. Old rows unchanged.
- `file_content_fts` — `file_path` now stores `binder_item_id`. Old rows unchanged.

### 11.3 Migration

`scribbler/binder/migration.py`:
1. Create `binder_items` table.
2. For each row in `files`:
   - Determine binder type (brain_dump if folder is raw-dumps/triage; chapter if chapters/drafts/final).
   - Create a binder item under the appropriate parent (Inbox or Manuscript).
   - Copy `content` from disk, `word_count`, `status`, `metadata` (tags).
   - Update `tag_occurrences.file_path` and `analysis_results.file_path` to the new binder item ID.
3. Mark all `files` rows as `migrated = 1`.
4. Log to `activity_log`.

Migration runs automatically on first v12 launch. Takes < 5 seconds for a typical project.

---

## PART 12 — IMPLEMENTATION ORDER

| Phase | What | Effort | Depends on |
|-------|------|--------|------------|
| 1 | Dark theme + app icon | Small | Nothing |
| 2 | DB schema: `binder_items`, `writing_sessions`, `live_analysis_cache` | Small | Nothing |
| 3 | Binder backend (`tree.py`, `migration.py`) + migration | Medium | Phase 2 |
| 4 | Binder UI (tree sidebar, context menus, drag-reorder) | Medium | Phase 3 |
| 5 | Editor (textarea, autosave, word count, status bar) | Medium | Phase 4 |
| 6 | Editor modes (Write, Preview, Focus, Analyse) | Small | Phase 5 |
| 7 | Live analysis module (`live_analysis.py`) + right rail | Medium | Phase 5 |
| 8 | Spell check (`pyspellchecker` integration) | Small | Phase 7 |
| 9 | Character profiles (backend + UI) | Medium | Phase 4 |
| 10 | Place profiles | Medium | Phase 4 |
| 11 | Theme profiles | Medium | Phase 4 |
| 12 | Auto-population (tagger → profiles) | Small | Phase 9-11 |
| 13 | Character arc chart | Small | Phase 9 |
| 14 | Theme density heatmap | Small | Phase 11 |
| 15 | Manuscript structure map (Dashboard) | Small | Phase 5 |
| 16 | Dashboard (replaces Home) | Medium | Phase 15 |
| 17 | Global search overlay | Medium | Phase 4 |
| 18 | Keyboard shortcuts + polish | Small | All |
| 19 | Migration testing + v11 compat | Small | All |
| 20 | Full test sweep + Windows build | Small | All |

**Phases 1-6 are the minimum viable writing app.** Phases 7-12 add the live tools and profiles. Phases 13-17 add the visualisations and dashboard. Phases 18-20 are polish and ship.

---

## PART 13 — TESTING STRATEGY

### 13.1 Per-phase tests

Each phase gets a `scripts/phase{N}_test.py` that tests the new behaviour in isolation.

### 13.2 Integration tests

- `scripts/test_binder_migration.py` — creates v11-style files, runs migration, verifies binder tree.
- `scripts/test_editor_autosave.py` — simulates typing, verifies DB save.
- `scripts/test_live_analysis.py` — feeds sample text, verifies markers.
- `scripts/test_profiles.py` — creates character/place/theme profiles, verifies cross-references.

### 13.3 Regression tests

- `comprehensive_test.py` (240 tests) — must still pass (with updated assertions for new file paths).
- `functional_smoke_test.py` — must still pass.
- All v10 phase tests (`phase1` through `phase15`) — must still pass.

### 13.4 Performance tests

- Type 1000 words in the editor → live analysis must complete in < 200ms per run.
- Open a 10,000-word chapter → editor must load in < 500ms.
- Run all 19 analysis tools on a 10,000-word chapter → must complete in < 60s.
- Migrate a project with 100 files → must complete in < 10s.

### 13.5 Build test

- GitHub Actions Windows build must complete with all 14 CI steps green.
- Both artifacts (Installer + Portable) must be produced.
- Manual smoke test of the built exe: create a project, write a chapter, run analysis, export.

---

## PART 14 — RISKS AND MITIGATIONS

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Editor textarea is too basic for serious writers | Medium | High | Markdown is the source of truth; preview mode shows rendered output. Rich-text can come in v13. |
| Live analysis is too slow on long chapters | Medium | Medium | Only analyse current paragraph ± 2. Debounce 2s. Fall back to on-save-only if slow. |
| Binder migration corrupts existing data | Low | High | Migration is non-destructive (old `files` table kept). Backup DB before migration. Reversible. |
| `pyspellchecker` dictionary is too basic | Medium | Low | Writer can add custom words to a personal dictionary (stored in settings). |
| UI feels cramped with 3 columns | Medium | Medium | Analysis rail is collapsible. Focus mode hides both rails. |
| Too many features for one release | High | High | Phased delivery — Phases 1-6 are MVP, rest can follow. Each phase is independently shippable. |
| Dark theme contrast issues | Low | Low | Test with WCAG contrast checker. Provide light fallback. |

---

## PART 15 — WHAT THIS PLAN DOES NOT DO

To stay focused:
- **No rich-text editor** — Markdown textarea only. Rich-text (bold/italic buttons, image embedding) is v13.
- **No real-time collaboration** — single-user desktop app.
- **No cloud sync** — local only. Backup/export is manual.
- **No version control UI** — writers who want VCS can use git externally.
- **No mobile app** — desktop only.
- **No AI writing assistant** — the LLM is for analysis, not for generating prose. This is a firm line.
- **No new analysis tools** — the 19 existing tools are sufficient. New live checks (spell/grammar/run-on) are lightweight utilities, not analysis tools.

---

## PART 16 — DELIVERY

- All changes on `main` branch.
- Each phase = one commit.
- After Phase 20, push to GitHub and trigger the Windows build.
- Worklog updated in `worklog.md` after each phase.
- No code is shipped without all testing gates green.

**Estimated total effort**: 20 phases, ~2-3x the v10 scope. The MVP (Phases 1-6) is roughly equivalent to v10 in effort. The full plan is achievable in a focused sprint.
