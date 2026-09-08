# The Audhd Scribbler — v10 Plan

**Status:** Planning (locked, ready for execution)
**Date:** 2026-09-08
**Platform:** Standalone Windows desktop app (pywebview + WebView2, no browser, no web server)
**Owner:** Anthony Carré
**Previous plan:** `PLAN-v2.1.md` (kept for history)

---

## 0. Why this plan exists

The v2 desktop app **works** — import, tag, analyze, search, export, delete all function.
But four gaps keep it from being the memoir companion it should be:

1. **Tagging is shallow.** spaCy NER + keyword lists catch obvious entities but
   can't disambiguate "Mom" (person) from "moments" (not), can't tell a place from
   a theme, and can't tell when "the kitchen" is being used as an emotional container
   rather than a location. AI help is wired but never invoked from the UI.
2. **Tag results are not durable.** They live in YAML frontmatter and a DB row, but
   there is no paragraph-level index, no full-text search, and no export of the
   tag index. Every search re-reads every file.
3. **Search doesn't link to the document.** The Search view returns excerpt snippets
   but clicking does nothing — the user has to manually open the file and scroll.
4. **Analysis results vanish.** The DB stores them silently but the UI never surfaces
   history, never exports results, and never lets the user click an observation to
   see it in context.

This plan closes all four gaps with 14 phases, ordered so the biggest visible wins
land first.

---

## PART 1 — TAGGING IMPROVEMENTS

### 1.1 Fix the AI flag that's hardcoded to false
- **Bug:** `previewTags()` and `applyTags()` in `assets/ui/index.html` both pass
  `false` for the `ai` parameter. Even when the user has configured Z.ai CLI, the
  LLM-assisted tagger never runs.
- **Fix:** Pass the real AI availability status (already computed in
  `get_status()`). When AI is configured, `tag_preview` should run the LLM pass
  for entity extraction and theme enrichment.

### 1.2 AI-assisted entity recognition
- Extend `llm_assisted_tagging()` in `scribbler/tagger.py` so the LLM returns typed
  entities, not just theme guesses:
  - `persons` — with role tags (`family`/`friend`/`professional`/`self`/`other`)
  - `places` — with type (`domestic`/`geographic`/`institutional`/`imagined`)
  - `objects` — recurring items (blue coat, tea pot, the red notebook)
  - `relationships` — pairs of persons with relation (`spouse`, `parent-child`, `rival`)
  - `emotional_beats` — single-sentence emotional turns, with intensity 1-3
  - `time_markers` — `summer of 1994`, `the day after`, `two weeks before`
- Merge LLM output with rule-based output: dedupe by lowercased name, prefer the
  LLM-typed version when both detect the same string.
- Only runs when AI is configured. Falls back to rule-based otherwise — never
  fails the whole tagging step if the LLM call errors out.

### 1.3 Better disambiguation (rule-based, always on)
- Add `STOPLIST_CHARACTERS` in `scribbler/config.py`:
  common words spaCy mis-typing as `PERSON` (e.g. `masking`, `kitchen`, `diagnosis`,
  `Moments`, `Burnout`, `Stimming`).
- Add `THEME_AS_PLACE_STOP`: themes that look place-y but aren't (`burnout`,
  `meltdown`, `shutdown`, `recovery`).
- Add `_classify_entity(name, context_sentence)` in `tagger.py`: uses the preceding
  verb/preposition ("at X", "to X", "X said", "X's mother") to guess whether a
  bare capitalized token is a person, place, or other.

### 1.4 New tag types (stored in DB + YAML frontmatter)
| Tag | Source | Why useful |
|-----|--------|-----------|
| `relationships` | LLM | "Mom and Dad" → spouses; powers a relationship map |
| `emotional_beats` | LLM + register | High-intensity turns; the spine of a memoir scene |
| `time_markers` | regex + LLM | "summer of 1994" → chronological anchoring |
| `objects` | spaCy + LLM | Recurring physical items (motifs in disguise) |

### 1.5 Editable tag preview (review before save)
- `tag_preview` already caches results server-side keyed by file path.
- UI renders chips as removable (× to delete) with an "add tag" input per category.
- New API method `save_tag_edits(path, edits)` persists corrected tags without
  re-running detection — the user's edits are authoritative.
- This is critical for memoir work where the AI will always miss emotional nuance.

### 1.6 Tag occurrence index (new DB table)
```sql
CREATE TABLE tag_occurrences (
  id          INTEGER PRIMARY KEY,
  file_path   TEXT NOT NULL,
  tag_type    TEXT NOT NULL,    -- characters|places|themes|era|...
  tag_value   TEXT NOT NULL,    -- "Mom", "kitchen", "masking"
  paragraph   INTEGER,          -- 1-based
  char_start  INTEGER,
  char_end    INTEGER,
  snippet     TEXT              -- ±80 chars around match
);
CREATE INDEX idx_occ_file   ON tag_occurrences(file_path);
CREATE INDEX idx_occ_tag    ON tag_occurrences(tag_type, tag_value);
```
- Populated during `tag_file()` by scanning paragraphs once per file.
- Makes search O(index) instead of re-reading every file on every query.
- Powers "click a tag → see every paragraph where it appears".

### 1.7 Full-text search (SQLite FTS5)
```sql
CREATE VIRTUAL TABLE file_content_fts USING fts5(
  file_path  UNINDEXED,
  filename   UNINDEXED,
  body,
  tokenize='porter unicode61'
);
```
- Populated during tagging.
- Powers "search for any word across all documents" with proper stemming.
- Returns paragraph + character offsets for highlighting.
- Graceful fallback: if FTS5 unavailable (older SQLite), fall back to Python
  substring loop over `files.body`.

---

## PART 2 — SEARCH + DOCUMENT READER

### 2.1 Document reader view (new top-level view)
- New sidebar entry: **Reader** (between Manuscript and Search).
- New view function `renderReader(path, opts)`:
  - Header: filename, word count, tag chips for the file (clickable to filter).
  - Body: full text, each paragraph wrapped in
    `<div id="para-N" data-para="N" class="paragraph">…</div>`.
  - Right rail: tag chips for this file, grouped by type. Clicking a chip
    highlights all matching paragraphs with `<mark>` and scrolls to the first.
  - Optional `jump_to` parameter: opens the reader pre-scrolled to a paragraph.
  - Optional `highlight` parameter: a list of terms to highlight on load.
- New API method `get_file_body(path)` returns:
  ```python
  { "path": ..., "filename": ..., "meta": {...yaml...},
    "paragraphs": ["...", "...", ...],     # 1-indexed via [0] padding
    "word_count": N, "tags": {...} }
  ```

### 2.2 Click search result → jump to passage
- Every excerpt in the Search view becomes clickable.
- Click handler calls `openReader(path, term, paragraph)`:
  ```js
  window.pywebview.api.get_file_body(path).then(body => {
    showView('reader');
    renderReader(body, { jump_to: paragraph, highlight: [term] });
  });
  ```
- Reader scrolls smoothly to `#para-N`, term highlighted with `<mark>` in every
  paragraph where it appears.

### 2.3 Free-text search (not just tag search)
- New input on the Search view: "Search inside documents…"
- Calls new API `search_full_text(query)`:
  - Uses FTS5 if available; falls back to Python loop.
  - Returns matches grouped by file: `[{ path, filename, matches: [{ paragraph, char_start, char_end, snippet }] }]`.
  - Each match is clickable → opens reader at that paragraph with the term highlighted.

### 2.4 Improved tag search
- Switch `find_tag_in_file()` to word-boundary regex `\b{value}\b` (stops "mom"
  matching "moment").
- Widen snippets to ±120 chars or full sentence (whichever is shorter).
- Return `char_start`/`char_end` for precise highlighting in the reader.
- UI: "5 of 23 excerpts" with "show all" toggle.
- UI: "refine within results" input filters excerpts live (no new API call).

### 2.5 Tag index export
Three formats, all from the `tag_occurrences` table:
- **CSV** — one row per occurrence (filename, tag_type, tag_value, paragraph, snippet).
  Opens in Excel. Best for sharing with a writing group.
- **JSON** — nested structure `{ file: { tag_type: { tag_value: [{ paragraph, snippet }] } } }`.
  Best for re-import or version control.
- **Markdown** — tags inline as `#hashtag` next to the paragraphs where they occur,
  plus a tag index appendix. Searchable in any text editor.
- New API method `export_tag_index(format, include_excerpts)` writes to a
  user-chosen save path via `pick_save_path()`.

---

## PART 3 — ANALYSIS IMPROVEMENTS

### 3.1 Wire synthesis report into the UI
- `synthesis.generate()` exists in `scribbler/synthesis.py` but is never called
  from `api.py`.
- Add to `analyze()`: after all tools run, call `synthesis.generate(file_path, results)`,
  save to DB, return to UI as part of the analysis payload.
- New UI function `renderSynthesis(syn)` renders a card placed **above** the
  per-tool results:
  - Voice consistency (one sentence)
  - Narrator distance (experiencing self ↔ narrating self)
  - Recurring signals across tools (top 3)
  - Top 5 things to notice (each clickable → jumps to the source observation)
  - AUDHD-aware notes (gentle, non-pathologizing)
  - "What this does NOT mean" anti-anxiety framing

### 3.2 Structured locations on observations
- Add a `loc` field to every observation, parallel to the human-readable `location`:
  ```python
  "loc": {
    "kind": "paragraph_range",     # paragraph_range | sentence_range | paragraph_list | whole_chapter
    "paragraphs": [7, 9],          # 1-based, inclusive
    "sentences": [14, 19],         # only when sentence_range
    "evidence_quote": "..."        # 1-2 sentence excerpt
  }
  ```
- Update all 12 analyzers to compute `loc` from the paragraphs/sentences they
  already iterate. The shared `passage.py` indexer (Phase 2) makes this uniform.
- Backward-compatible: if `loc` is missing, the UI shows the text `location`
  without a click-to-jump affordance.

### 3.3 Click analysis observation → jump to passage
- Observation cards become clickable when `loc` exists.
- "I noticed 3 long sentences in ¶7-9" → click → reader opens, scrolls to ¶7,
  highlights ¶7-9 with a soft yellow background.
- "Defensive register (4 instances)" → click → reader highlights all 4 paragraphs
  with defensive language.
- "whole chapter" observations → reader opens at ¶1 with a banner:
  "This observation applies to the whole chapter."

### 3.4 Analysis history view
- The DB already stores history silently in the `analysis_history` table.
- New API method `get_saved_analysis(path)` returns the most recent stored results
  for a file.
- New API method `list_analysis_history(path, tool=None)` returns timestamps of
  all prior runs.
- New UI: **📚 History** button on each manuscript file row.
- Click a row → re-renders the saved result card without re-running analysis.
- Useful for "did this paragraph used to be flagged as defensive?" forensics.

### 3.5 Analysis export
- `export.export_analysis_report()` exists but is never called from the UI.
- New API method `export_analysis(path, save_path, fmt)`:
  - **Markdown** — full report with synthesis at top, all observations with `[¶7-9]`
    anchors, evidence quotes, sorted by tool then severity.
  - **JSON** — full data structure for round-tripping or external tooling.
- New UI card in the Export view: "Export analysis results" with MD/JSON buttons
  per file (or "export all" for a manuscript-level bundle).

### 3.6 Observation quality improvements
- Add `evidence_quote` — 1-2 sentence excerpt showing the pattern in context.
  Critical for memoir work where the user needs to see the actual prose, not
  just a description of it.
- Add `why_it_matters` — one sentence tying the observation to memoir craft.
  Example: "In memoir, a monotonous rhythm at the climax can flatten the emotional peak."
- Drop the `slice(0,5)` truncation — show all observations in a scrolling card.
- Example output:
  > I noticed 3 long sentences (¶7-9) averaging 42 words.
  > *In memoir, a monotonous rhythm at the climax can flatten the emotional peak.*
  > Evidence: "The years that followed were a blur of masking and meltdowns and
  > I would sit in my room..."

### 3.7 Two new analysis tools
| Tool | What it does |
|------|--------------|
| `memory_truth` | Detects memory-uncertainty language ("I think", "as far as I remember"), absolute claims ("always", "never"), unverifiable internal states attributed to others. Memoir-specific: flags places where the narrator is over-claiming certainty. |
| `emotional_beats` | Locates named vs shown emotions, tracks whether each scene has an emotional turn, flags scenes where the stated emotion differs from the scene register. |

---

## PART 4 — ARCHITECTURE CHANGES

### 4.1 New files
| File | Purpose |
|------|---------|
| `scribbler/passage.py` | Shared paragraph/sentence indexer. `build_index(text)` returns paragraph + sentence offsets. Used by analyzers (for `loc`) and reader view (for highlighting). |
| `scribbler/analyzers/memory_truth.py` | New analysis tool. |
| `scribbler/analyzers/emotional_beats.py` | New analysis tool. |

### 4.2 New API methods (all on `Api` in `scribbler/api.py`)
| Method | Purpose |
|--------|---------|
| `get_file_body(path)` | Returns paragraph-split body + meta for reader view. |
| `search_full_text(query)` | Free-text content search via FTS5 (Python fallback). |
| `search_tags_with_excerpts(tag_type, value)` | Combined search + excerpts in one call. |
| `save_tag_edits(path, edits)` | Persist user-corrected tags without re-running detection. |
| `get_saved_analysis(path)` | Return most-recent stored analysis results for a file. |
| `list_analysis_history(path, tool=None)` | Return analysis history timestamps. |
| `export_tag_index(format, include_excerpts=True)` | Export tag index as CSV/JSON/MD. |
| `export_analysis(path, save_path, fmt)` | Export analysis results as MD/JSON. |

### 4.3 New UI functions (in `assets/ui/index.html`)
| Function | Purpose |
|----------|---------|
| `renderReader(body, opts)` | Document reader view with paragraph anchors + highlights. |
| `openReader(path, term, paragraph)` | Click handler from search/analysis → opens reader. |
| `runFullTextSearch()` | Free-text search handler. |
| `renderTagEditor(preview_data)` | Editable chip UI for tag preview. |
| `saveTagEdits()` | Sends edited tags to API. |
| `renderSynthesis(syn)` | Synthesis report card (top of analysis view). |
| `renderObservation(file, tool, o)` | Single observation with click-to-jump. |
| `renderAnalysisHistory(path)` | History list view. |
| `exportTagIndex(format)` | Trigger tag index export via save dialog. |
| `exportAnalysis(path, fmt)` | Trigger analysis export via save dialog. |

### 4.4 Database changes (in `scribbler/db.py`)
- New table: `tag_occurrences` (paragraph-level tag positions, see 1.6).
- New virtual table: `file_content_fts` (FTS5 full-text search, see 1.7).
- New columns on `files`: `relationships`, `emotional_beats`, `time_markers`, `objects`.
- Wire up the orphaned `characters` and `places` tables — add `upsert_character()`
  and `upsert_place()` helpers, called from `tagger.py`.
- Migration helper: `_migrate(conn)` runs `ALTER TABLE` guarded by
  `PRAGMA table_info` so existing user DBs upgrade in place.

### 4.5 Files to modify
| File | Changes |
|------|---------|
| `scribbler/tagger.py` | AI entity extraction, new tag types, populate `tag_occurrences` + FTS + characters/places tables |
| `scribbler/search.py` | Word-boundary regex, char offsets, `search_text_in_all_files()` |
| `scribbler/db.py` | New tables, new columns, migration, new helpers |
| `scribbler/api.py` | 8 new methods, fix AI flag, wire synthesis into `analyze()` |
| `scribbler/export.py` | Tag index export (CSV/JSON/MD), analysis export with synthesis |
| `scribbler/feedback.py` | Accept `loc`, `evidence_quote`, `why_it_matters` in `format_flag()` |
| `scribbler/analyzers/craft.py` | Build passage index, pass `loc` to all observations |
| `scribbler/analyzers/editor.py` | Use `re.finditer` for paragraph-located observations |
| `scribbler/analyzers/voice_tense.py` | Add paragraph numbers to tense shifts |
| `scribbler/analysis_suite.py` | Replace "whole chapter" with computed paragraph lists |
| `scribbler/analysis_catalog.py` | Add `memory_truth` and `emotional_beats` |
| `scribbler/config.py` | Add `STOPLIST_CHARACTERS`, `TIME_MARKER_PATTERNS`, `THEME_AS_PLACE_STOP` |
| `assets/ui/index.html` | New reader view, search improvements, synthesis card, history view, export cards, editable tags |

---

## PART 5 — IMPLEMENTATION ORDER

| Phase | What | Why this order |
|-------|------|----------------|
| 1 | Fix AI flag bug + wire synthesis into `analyze()` | 5-min fix, immediate quality boost |
| 2 | `passage.py` indexer | Foundation for reader + observation locations |
| 3 | `get_file_body` API + `renderReader` UI | Headline feature — see your document in-app |
| 4 | Tag occurrence index + FTS5 in DB | Makes search fast and enables export |
| 5 | Click search result → jump to reader | Connects search to the document |
| 6 | Free-text search | Search by any word, not just tags |
| 7 | Structured `loc` on observations (craft + editor first) | Enables click analysis → jump to passage |
| 8 | Analysis export (MD/JSON) | Save and share results |
| 9 | Analysis history view | See previous runs without re-running |
| 10 | Tag index export (CSV/JSON/MD) | Searchable tags outside the app |
| 11 | Editable tag preview | User controls what gets saved |
| 12 | AI entity extraction | Smarter tagging when AI configured |
| 13 | New tag types (relationships, time markers, etc.) | Richer metadata |
| 14 | Two new analysis tools (`memory_truth`, `emotional_beats`) | Depth for memoir specifically |

Phases 1-3 deliver the biggest visible wins in the shortest time.
Phases 4-7 complete the "search → see → jump" loop.
Phases 8-14 add depth.

---

## PART 6 — TESTING GATES

Each phase must pass these checks before the next phase starts:

1. **Syntax** — `python -m py_compile` on every modified `.py` file.
2. **Smoke** — `python -c "from scribbler.api import Api; Api()"` must not raise.
3. **Node check** — `node --check assets/ui/index.html` (extracts the script block).
   Actually we'll use `python scripts/check_html_js.py` which parses the HTML and
   lints the embedded `<script>` block.
4. **Functional** — for phases that touch the API, run
   `python scripts/phase{N}_test.py` which calls each new API method against a
   fixture file and asserts the shape of the response.
5. **Integration** — at the end, run `python comprehensive_test.py` (existing
   240-test suite) and confirm zero regressions.

---

## PART 7 — DELIVERY

- All changes committed to `main` on the existing private GitHub repo.
- Each phase = one commit with a clear message.
- After Phase 14, push the GitHub Actions workflow run to build a fresh
  Windows `.exe` + Inno Setup installer.
- Worklog updated in `worklog.md` after each phase.
- No code is shipped without all testing gates green.
