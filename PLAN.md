# The Audhd Scribbler v2 — Build Plan

## What we're building

A standalone Windows desktop app. No web server, no browser tab, no port. A native window with a calm, AUDHD-friendly UI. All intelligence is local and deterministic — no AI calls for core functionality. Optional AI key for extra analysis only. Delivered as either an installer (.exe) or a portable folder.

## Technology Stack

| Layer | Choice | Why |
|-------|--------|-----|
| **Window** | pywebview 5.x | Native Win32 window via WebView2 (preinstalled on Win10/11). No browser dependency. |
| **Frontend** | Vanilla HTML/CSS/JS (no framework) | At ~8 views and ~40KB JS, a framework adds build complexity without payoff. |
| **Backend** | Existing `scribbler/` package, lightly refactored | 100% reuse of tagger, analyzers, search, db, safety, export. |
| **Bridge** | pywebview `js_api` (direct Python↔JS, no HTTP) | Methods called as `window.pywebview.api.method_name()`. Promisified automatically. Runs on worker thread. |
| **Build** | PyInstaller (`--onedir`) + Inno Setup | `--onedir` avoids extracting 12MB spaCy model on every launch. |
| **Python** | 3.11 (not 3.14) | pywebview + spaCy + PyInstaller all stable here. |

## Project Structure

```
audhd-scribbler-v2/
├── main.py                          # Single entry point
├── requirements.txt
├── build/
│   ├── scribbler.spec               # PyInstaller spec
│   ├── build_exe.bat                # ONE-COMMAND rebuild
│   ├── build_installer.bat          # build_exe + Inno Setup
│   └── windows.iss                  # Inno Setup script
├── assets/
│   ├── ui/
│   │   ├── index.html               # SPA shell
│   │   ├── styles/
│   │   │   ├── tokens.css           # Color palette, fonts, spacing
│   │   │   ├── base.css             # Reset, typography, layout
│   │   │   ├── components.css       # Buttons, cards, file lists, chips
│   │   │   ├── timers.css           # The thinking overlay
│   │   │   └── audhd.css            # Reduced motion, focus rings
│   │   ├── app/
│   │   │   ├── app.js               # Router + state
│   │   │   ├── api.js               # Wraps window.pywebview.api
│   │   │   ├── timer.js             # Thinking-timer controller
│   │   │   └── views/
│   │   │       ├── home.js
│   │   │       ├── inbox.js         # Tagging only
│   │   │       ├── manuscript.js    # Analysis only
│   │   │       ├── search.js        # Tag interrogation
│   │   │       ├── exports.js       # Native save dialogs
│   │   │       └── settings.js      # AI provider/key
│   │   ├── fonts/                   # Inter, Source Serif 4, JetBrains Mono
│   │   └── icons/                   # Inline SVG sprite
│   └── models/
│       └── en_core_web_sm/          # spaCy model, bundled
└── scribbler/                       # Existing engines (reused)
    ├── config.py
    ├── tagger.py
    ├── analysis_catalog.py
    ├── analysis_suite.py
    ├── analyzers/                   # All 12 analyzer modules
    ├── writer_intelligence.py
    ├── search.py
    ├── db.py
    ├── safety.py
    ├── export.py
    ├── llm.py
    ├── settings.py
    ├── file_io.py
    ├── feedback.py
    └── api.py                       # NEW — pywebview Api class
```

## What stays, what changes, what's new

### Keep unchanged
- config.py, tagger.py, analysis_catalog.py, analysis_suite.py, analyzers/*, writer_intelligence.py, search.py, db.py, safety.py, export.py, file_io.py, feedback.py

### Change
1. tagger._get_spacy() — load from assets/models/en_core_web_sm/ (bundled)
2. llm._try_openai_package — remove pip fallback
3. settings.SETTINGS_PATH — resolve to %LOCALAPPDATA% when frozen
4. export.py — add export_chapter_comparison()

### Delete
- webapp.py, ScribblerWindows.py, release_ui.py, release_runtime.py

### New
- main.py (pywebview entry point)
- scribbler/api.py (Api class replacing webapp.py)
- assets/ui/* (real HTML/CSS/JS files)

## The Api class

| Method | Purpose |
|--------|---------|
| list_files() | Returns all files with metadata |
| get_tools() | Returns the 17-tool catalog |
| import_files(destination, file_paths) | Native file dialog → copies to project folder |
| save_note(title, text) | Quick note → raw-dumps |
| tag_preview(paths, use_ai) | Preview tags without applying |
| tag_files(paths, use_llm) | Apply tags — pushes step progress |
| analyze(paths, tools) | Run analysis — pushes step progress |
| compare_chapters(paths) | Cross-chapter voice drift + pacing |
| search_tags(tag_type, value) | Search by character/place/theme |
| search_multi(filters) | Multi-tag AND search |
| find_in_file(path, tag_type, value) | Paragraph-level evidence |
| tag_coverage(path) | Full-document coverage proof |
| get_tag_values(tag_type) | Populate filter dropdowns |
| export_file(path, kind, save_path) | Native save dialog → docx/md/txt |
| delete_file(path) | Move to archive |
| backup(save_path) | Native save dialog → ZIP |
| set_ai_provider(provider, api_key) | Settings |
| get_ai_status() | Returns llm_status() |
| pick_open_files() | Wraps pywebview file dialog |
| pick_save_path(default_name) | Wraps pywebview save dialog |

## UI Design — "Warm Linen" palette

```css
--paper:      #FAF7F2   (warm cream background)
--panel:      #FFFFFF   (white card surface)
--ink:        #2E2A26   (warm dark brown-gray)
--muted:      #7A7268   (warm gray)
--line:       #E8E2D6   (warm beige border)
--inbox-accent:  #6B8E7F (muted sage — tagging zone)
--ms-accent:     #C89B6B (warm terracotta — analysis zone)
```

### Typography
- Body: Inter 16px
- Headings: Source Serif 4 18-30px
- Timer: JetBrains Mono 56px
- Never below 13px

### The Thinking Timer
- 56px mono elapsed timer (never countdown)
- 10px pulsing dot (2.4s cycle, not spinner)
- Calming messages cycle every 8s: "Reading your words carefully…" → "Looking for patterns…" → "This is the slow, careful part."
- Cancel always safe: "Stop — your work is saved"
- Respects prefers-reduced-motion

## UI Views

### Home
- Counts: "12 brain dumps · 4 chapters · 23 analyses run"
- Suggested next step with one button
- Recent activity

### Inbox (sage zone — tagging only)
- Drop zone (drag-drop + click)
- File list with checkboxes
- Preview tags + Apply tags
- Results as color-coded editable chips

### Manuscript (terracotta zone — analysis only)
- Drop zone
- File list with checkboxes
- "Ask your manuscript" query box
- 17 tools grouped into 4 collapsible categories
- "Recommended set" pre-selected (8 tools)
- Results as plain-language findings (summary first, evidence second, JSON collapsed)

### Search
- Filter by character, place, theme, era, mood, status
- Multi-tag AND search
- Paragraph-level evidence with context

### Export & Backup
- Export one file → choose format → native save dialog
- Backup entire project → native save dialog → ZIP

### Quick Note (overlay)
- Slides in from right (400px, doesn't cover screen)
- Auto-saves draft every 30s

### Settings
- AI provider selection
- API key entry + test
- Clearly marked "optional"

## Analysis Suite — 17 existing + 5 new

### Existing (keep all 17)
craft, voice, characters, continuity, themes, editor, repetition, pacing, structure, memoir, reader, research, cadence, motifs, anchors, voice_dna, reader_perception

### New Tier-1 memoir tools (all deterministic)
1. Scene vs Summary — per-paragraph classification + ratio per chapter
2. Show vs Tell — emotion labels vs embodied showing
3. Narrator Reliability — self-criticism, deflection, disclosure, withholding
4. Stakes & Significance — want/desire, fear/loss, cost, transformation
5. Emotional Register — emotion families (grief, shame, joy, anger, fear, tenderness, relief, longing, numbness)

### Cross-chapter consistency
Manuscript Arc Mapper aggregates per-chapter signatures:
- Voice drift vector
- Narrator-distance arc
- Emotional arc
- Theme arc
- Scene:summary ratio
- Stakes density
- Character presence arc
- Pacing curve

## Build Order (10 phases)

| Phase | Focus | Deliverable |
|-------|-------|-------------|
| 1 | Spike: main.py + Api + stub HTML | Window opens, shows file list |
| 2 | Inbox: import, tag preview, tag files | Can import and tag |
| 3 | Thinking timer | Timer shows during long ops |
| 4 | Analysis: tools, run, results | Can run all tools |
| 5 | Chapter Compare | Cross-chapter drift |
| 6 | Search | Tag interrogation |
| 7 | Native save dialogs | Exports go where user chooses |
| 8 | Settings | AI provider/key |
| 9 | Bundle spaCy + fonts | No runtime downloads |
| 10 | PyInstaller + Inno Setup | Working .exe + installer |

## Key constraints

- Standalone Windows app, no web server
- All intelligence local (deterministic, no AI for core)
- Optional AI key for extra analysis only
- Large well-designed timers
- Tagging and analysis completely separate
- Uploads and exports kept separate
- Documents up to 10k words (tagging), 60k words (analysis)
- Cross-chapter consistency tracking
- Results exportable and fully interrogatable
- AUDHD-friendly UI: calm, sleek, clearly explained
- Memory/RAM efficient — no hogs
