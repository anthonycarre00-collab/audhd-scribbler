# The Audhd Scribbler — v11 Plan

**Status:** Planning (locked, ready for execution)
**Date:** 2026-09-08
**Platform:** Standalone Windows desktop app (pywebview + WebView2, no browser, no web server)
**Owner:** Anthony Carré
**Previous plan:** `PLAN-v10.md` (delivered — see commits `0814f3d` through `6089cc3`)

---

## 0. Why this plan exists

v10 delivered all 15 phases — tagging, search, reader, analysis, exports, history, editable tags, AI entities, new tag types, two new analysis tools, relationship map, and emotional-arc comparison. **All 295 tests pass and the Windows build is green.**

But the user's feedback is clear: **the app is OK, not brilliant**. The pieces work individually but the *flow* between them is broken for an AUDHD writer who needs the tool to do the organisational thinking for them. Specific pain points:

1. **The Reader view is hidden** — buried as the 5th sidebar item, with no surface area anywhere else pointing to it. The user lands on Home, doesn't know Reader exists, and the deep-links from search/analysis click into a view they've never seen.
2. **Search isn't working properly** — there are two separate search inputs (free-text and tag), results don't persist when navigating away, and there's no way to search *analysis observations* — only file content and tags.
3. **The tagging → manuscript flow is two silos** — Inbox tags never suggest themselves onto Manuscript files, and Manuscript analysis observations never become searchable artefacts the way tags do.
4. **No dark theme** — the Warm Linen palette is fine but the app should default to dark (less eye strain for long writing sessions, calmer for an AUDHD brain).
5. **No app icon** — the .exe currently ships without one; the window title bar shows the default webview icon.
6. **The "flow" isn't writer-shaped** — a writer's flow is: *dump → tag → find → re-read → analyse → fix → re-search*. The current app supports each step individually but doesn't connect them.

This plan closes those gaps with **six focused workstreams**. No new analysis tools, no new tag types, no new visualisations. Just polish, flow, and discoverability.

---

## PART 1 — DARK THEME (DEFAULT)

### 1.1 Add a dark palette
Replace the `:root` token block with a `prefers-color-scheme: dark` default and a manual light override. Tokens:

| Token | Dark (default) | Light (override) |
|-------|----------------|------------------|
| `--paper` | `#1A1816` | `#FAF7F2` |
| `--panel` | `#242120` | `#FFFFFF` |
| `--ink` | `#E8E2D6` | `#2E2A26` |
| `--muted` | `#8A8278` | `#7A7268` |
| `--line` | `#3A3530` | `#E8E2D6` |
| `--soft` | `#2E2A26` | `#F2EDE3` |
| `--inbox-accent` | `#8FB4A4` | `#6B8E7F` |
| `--inbox-soft` | `#2A3833` | `#E8EFE9` |
| `--inbox-deep` | `#A8C4B8` | `#4A6B5C` |
| `--ms-accent` | `#D4A574` | `#C89B6B` |
| `--ms-soft` | `#3A2E22` | `#F5EBDD` |
| `--ms-deep` | `#E8B888` | `#8E6A42` |
| `--success` | `#8FB4A4` | `#7A9B7E` |
| `--warning` | `#D4A574` | `#D4A574` |
| `--danger` | `#C49084` | `#B07A6A` |

### 1.2 Theme toggle in the topbar
- New `◐ Theme` button next to Quick Note.
- Cycles: `dark → light → dark`.
- Preference saved to `settings.json` via `set_setting("theme", "dark"|"light")`.
- On load, the saved theme is applied before the first paint (no flash).

### 1.3 Reader view tweaks for dark
- `mark` highlight uses `rgba(212,165,116,0.30)` on dark (was `0.45` — too bright on dark bg).
- `.reader-para:hover` uses `#2E2A26` (was `var(--soft)` — barely visible on dark).
- `.para-highlight` animation uses `rgba(212,165,116,0.20)` on dark.

### 1.4 SVG chart tweaks for dark
- Map view: edge lines use `#5A544A` on dark (was `var(--muted)` — too low contrast).
- Compare view: grid lines use `#3A3530` on dark; curves brighten slightly.

---

## PART 2 — APP ICON

### 2.1 Commission a custom icon
A single SVG source, rasterised to `.ico` (multi-resolution: 16, 32, 48, 64, 128, 256) and `.png` (256×256) for the build pipeline.

**Concept:** A fountain pen nib forming the lower curve of a brain, with a small spark/star at the top-right — "messy but genius, captured". Warm terracotta (`#C89B6B`) on a dark charcoal (`#1A1816`) background, matching the dark theme.

The icon needs to read at 16×16 (taskbar) as well as 256×256 (installer hero). The pen-nib shape is the dominant element; the brain curve and spark are detail that emerges at larger sizes.

### 2.2 Wire the icon into the build
- Save `assets/icons/app.ico` (multi-resolution Windows icon).
- Save `assets/icons/app.png` (256×256 PNG for the spec).
- Update `build/scribbler.spec`:
  ```python
  exe = EXE(
      ...
      name='AudhdScribbler',
      icon='assets/icons/app.ico',
      ...
  )
  ```
- Update `build/windows.iss`:
  ```ini
  SetupIconFile=assets\icons\app.ico
  ```
- Update `main.py` to pass `icon` to `webview.create_window()`:
  ```python
  window = webview.create_window(
      title="The Audhd Scribbler",
      html=html_string,
      js_api=api,
      icon=os.path.join(SCRIPT_DIR, "assets", "icons", "app.ico"),
      ...
  )
  ```

### 2.3 Favicon in the HTML
- Inline a base64-encoded 32×32 PNG as `<link rel="icon">` in the HTML `<head>` so the title bar shows it even in dev mode.

---

## PART 3 — READER VIEW DISCOVERABILITY

### 3.1 Move Reader up in the sidebar
Current order: `Home, Inbox, Manuscript, Search, Reader, Map, Compare, Export, Settings`
New order: `Home, Inbox, Manuscript, Reader, Search, Map, Compare, Export, Settings`

Reader is now the 4th item, immediately after Manuscript — the natural place a writer goes after running analysis or before searching.

### 3.2 Surface Reader from the Manuscript file list
Every manuscript file row gets an `📖 Open in Reader` button next to the existing `📚 History` button. One click opens the file in the Reader view, no search required.

### 3.3 Surface Reader from the Inbox file list
Every brain dump file row gets the same `📖 Open in Reader` button. Writers often want to re-read a brain dump before deciding whether to promote it to a chapter.

### 3.4 Make the Reader the default deep-link target
Currently `openReader()` exists but is only called from search results and analysis observations. After this change:
- Clicking any tag chip anywhere → opens Reader with that tag highlighted.
- Clicking any file row → opens Reader at paragraph 1.
- The Home view's "Suggested next" card includes `📖 Read your latest brain dump` when there's an untagged dump in the Inbox.

### 3.5 Reader sidebar improvements
- Add a "Recent files" rail at the top of the Reader view (last 5 files opened) so writers don't have to scroll the full file list every time.
- Track last-opened file in `settings.json` and re-open it automatically when the user navigates to Reader (if they were there before).

---

## PART 4 — SEARCH THAT ACTUALLY WORKS

### 4.1 Unified search bar
Replace the two-card Search view (free-text + tag) with a **single search bar at the top** that does both:

```
[ search: ___________________________ ] [🔍]
                                       ↑
                          searches tags AND full text simultaneously
```

- Typing a query hits both `search_full_text` and `search_tags_with_excerpts` (across all tag types).
- Results are de-duplicated by file_path and merged.
- Each result shows: filename, match type (`tag: character = Mom` or `text: "kitchen"`), paragraph number, snippet.
- All excerpts remain clickable → open Reader.

### 4.2 Search within analysis results (NEW)
Add a third search mode: **search analysis observations**.

- New API method `search_observations(query)`:
  - Iterates `analysis_results` table for all files.
  - For each stored result, walks `observations` list and matches `query` against `category`, `formatted`, `observation`, `evidence_quote`, `why_it_matters`.
  - Returns matches with: `file_path`, `filename`, `tool`, `category`, `formatted`, `evidence_quote`, `loc` (paragraph numbers).
- UI: a checkbox `☑ Include analysis observations` under the search bar (default on).
- Results from analysis observations get a distinct badge (`🔬 analysis` vs `🏷 tag` vs `📄 text`) so the writer knows what kind of match it is.
- Clicking an analysis-observation result opens the Reader at the observation's `loc.paragraphs[0]` — same deep-link as clicking the observation in the analysis view.

### 4.3 Persist search results across navigation
Currently navigating away from Search clears the results. Fix:
- Store the last query + results in a global `lastSearch` variable.
- When the user returns to Search, restore the query in the input and re-render the results without re-running the search.
- Add a `✕ Clear` button to explicitly reset.

### 4.4 Search result density
- Show up to 12 excerpts per file (was 8).
- Add `show all (N)` toggle per file that expands inline.
- Add a `refine within results` input below the results that filters excerpts live (no new API call).

### 4.5 Search shortcuts
- `Ctrl+F` (or `Cmd+F` on Mac) when not focused on an input → focus the global search bar.
- `Esc` when focused on the search bar → clear and blur.

---

## PART 5 — TAGGING → MANUSCRIPT FLOW

### 5.1 Promote a brain dump to a chapter
Currently the writer has to: tag in Inbox → manually copy file to chapters → re-tag in Manuscript. Replace with a single `⬆ Promote to manuscript` button on each Inbox file row:
- Calls new API method `promote_to_manuscript(path)`:
  - Copies the file from `raw-dumps`/`triage` to `chapters/`.
  - Carries over all existing tags (no re-tagging needed).
  - Marks the original as `promoted` in the DB (status = `resting`, doesn't appear in Inbox counts but isn't deleted).
  - Returns the new path.
- UI shows a toast: `Promoted to chapters/<filename>. Tags preserved.`

### 5.2 Carry tags into the Manuscript view
When the Manuscript view loads, each file row shows its tag count and a chip preview (`🏷 5 tags · Mom, kitchen, masking…`). Currently the Manuscript file list shows only `word_count · status · analysed` — no tag visibility. Adding the tag chips makes the manuscript immediately scannable.

### 5.3 Re-tag button on Manuscript files
A `🔄 Re-tag` button on each manuscript file row. Calls `tag_files([path], aiAvailable)`. Useful after editing a chapter — the writer doesn't have to navigate back to Inbox to refresh tags.

### 5.4 Analysis observations become searchable tags (auto)
When analysis runs, the `memory_truth` and `emotional_beats` tools already produce `category` labels (e.g. `memory_uncertainty`, `defensive_register`, `telling_not_showing`). These should be auto-indexed as `analysis_findings` in the tag_occurrences table:
- New tag_type: `analysis_findings`
- Populated during `analyze()` by walking each tool's observations and inserting one occurrence per paragraph in `loc.paragraphs`.
- This means the unified search (Part 4) can find "every paragraph where I was defensive" by typing `defensive` — no separate "search analysis" mode needed for the common cases.

---

## PART 6 — FLOW POLISH

### 6.1 Home view redesign
The current Home shows three cards (Inbox / Manuscript / Search) and a "Suggested next" card. Redesign to a **writer-shaped dashboard**:

```
┌──────────────────────────────────────────────────────────┐
│  Welcome back. You have:                                  │
│  • 3 untagged brain dumps                                 │
│  • 2 chapters with new analysis                           │
│  • 1 chapter not analysed in 7+ days                      │
│                                                           │
│  [ 📥 Tag my brain dumps ]  [ 📄 Analyse my chapters ]   │
│  [ 📖 Read last opened ]    [ 🔍 Search everything ]     │
│                                                           │
│  ── Recent activity ──────────────────────────────────    │
│  • Tagged `kitchen-morning.md` (2 hours ago)             │
│  • Analysed `ch-03.md` with 4 tools (yesterday)          │
│  • Promoted `dump-2024-03.md` to chapters (3 days ago)   │
└──────────────────────────────────────────────────────────┘
```

- The four action buttons are the writer's primary paths — no thinking required.
- The "Recent activity" list pulls from the `activity_log` table (already populated).
- The counts are computed from `DATA.files` on load.

### 6.2 Sidebar count badges
Currently only Inbox and Manuscript show counts. Add:
- **Reader**: no count (it's a viewer, not a list).
- **Search**: no count.
- **Map**: shows the character count (`🕸 12`).
- **Compare**: shows the manuscript count (`📈 3`).
- **Export**: no count.

### 6.3 Topbar polish
- Replace the plain `✎ Audhd Scribbler` brand text with the new app icon (16×16) + brand text.
- Replace `Ready` status text with `Idle` / `Working…` / `Ready` states.
- Add the theme toggle button (Part 1.2).

### 6.4 Empty states
Every view currently shows "Nothing here yet." for empty states. Replace with **action-oriented empty states**:
- Inbox empty: `Your inbox is clear. Drop a brain dump here, or write a Quick Note (Ctrl+N).`
- Manuscript empty: `No chapters yet. Promote a brain dump from the Inbox, or import a draft.`
- Search no results: `No matches. Try a different word, or check that your files are tagged.`
- Reader no files: `Nothing to read yet. Import a file first.`

### 6.5 Keyboard shortcuts
- `Ctrl+N` → Quick Note (already exists as a button; add the shortcut).
- `Ctrl+F` → Focus search bar.
- `Ctrl+R` → Open Reader.
- `Ctrl+1` through `Ctrl+8` → Navigate to the 1st through 8th sidebar items.
- `Esc` → Close any open overlay (Quick Note, Thinking timer cancel).

---

## PART 7 — IMPLEMENTATION ORDER

| Phase | What | Effort | Why first |
|-------|------|--------|-----------|
| 1 | Dark theme + toggle | Small | Immediate visual upgrade; touches every view |
| 2 | App icon (SVG → .ico → wire into build) | Small | Visible in title bar, taskbar, installer; signals "real app" |
| 3 | Reader discoverability (move up, surface from file rows) | Small | Fixes the #1 user complaint |
| 4 | Unified search bar + persist results | Medium | Fixes the #2 user complaint |
| 5 | Search analysis observations (new API + UI) | Medium | Makes analysis useful long-term, not just at run time |
| 6 | Promote-to-manuscript flow | Small | Connects the two silos |
| 7 | Carry tags into Manuscript view + re-tag button | Small | Makes Manuscript self-sufficient |
| 8 | Auto-index analysis findings as searchable tags | Small | Makes the unified search even more powerful for free |
| 9 | Home view redesign | Medium | The "brilliant" first impression |
| 10 | Sidebar count badges + topbar polish | Small | Finishing touches |
| 11 | Empty states + keyboard shortcuts | Small | Polish |

Phases 1-3 deliver the biggest visible wins in the shortest time. Phases 4-8 fix the flow. Phases 9-11 make it feel finished.

---

## PART 8 — TESTING GATES

Each phase must pass:
1. **JS syntax** — `python scripts/check_html_js.py` returns PASS.
2. **Phase test** — `python scripts/phase{N}_test.py` for the new behaviour.
3. **No regressions** — `python comprehensive_test.py` (240 tests), `python scripts/pre_build_verification.py` (41 tests), and `python functional_smoke_test.py` all still pass.
4. **Manual smoke** — load the app, navigate to each view, confirm the new behaviour works end-to-end.

After all phases, push to GitHub and trigger the Windows build. Build must complete with all 14 CI steps green before sign-off.

---

## PART 9 — WHAT THIS PLAN DOES NOT DO

To stay focused and avoid over-engineering:
- **No new analysis tools** — the 19 existing tools are enough.
- **No new tag types** — the 9 existing types are enough.
- **No new visualisations** — Map and Compare are sufficient.
- **No AI changes** — the LLM integration stays as-is.
- **No database schema changes** — only one new tag_type value (`analysis_findings`) which uses the existing `tag_occurrences` table.
- **No new dependencies** — everything uses what's already in `requirements.txt`.

The plan is intentionally conservative. The goal is brilliance through polish, not through more features.
