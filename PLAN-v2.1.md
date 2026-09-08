# The Audhd Scribbler v2.1 — Polish & Update Plan

## Overview

The app works but needs three major upgrades: smarter tagging, a document reader with passage-level navigation, and saved/exportable analysis results with clickable links to the source text.

---

## PART 1: TAGGING IMPROVEMENTS

### 1.1 Fix latent bug: AI flag hardcoded to false
- `previewTags()` and `applyTags()` in the UI both pass `false` for AI
- Fix: pass actual AI availability status so LLM-assisted tagging works when configured

### 1.2 AI-assisted entity recognition
- Extend `llm_assisted_tagging()` to also extract typed entities:
  - persons (with role: family/friend/professional)
  - places (with type: domestic/geographic)
  - objects, relationships, emotional beats, time markers
- Merge LLM entities with rule-based (dedupe, prefer LLM-typed)
- Only runs when AI is configured; falls back to rule-based

### 1.3 Better disambiguation (rule-based, always on)
- Add STOPLIST for characters (don't tag "masking" or "kitchen" as a person)
- Add THEME_AS_PLACE_STOP (don't tag "burnout" as a place)
- Add `_classify_entity(name, context_sentence)` — uses preceding verb/preposition to guess type

### 1.4 New tag types
| Tag | Source | Why useful |
|-----|--------|-----------|
| relationships | LLM | "Mom and Dad" → spouses |
| emotional_beats | LLM + register | "masking collapse" → high intensity |
| time_markers | regex | "summer of 1994", "the day after" |
| objects | spaCy + LLM | recurring items (blue coat, tea pot) |

### 1.5 Editable tag preview (review before save)
- `tag_preview` caches results server-side
- UI renders chips as removable (× to delete) with "add tag" input per category
- `save_tag_edits(edits)` persists corrected tags without re-running detection
- User controls what gets saved, not the machine

### 1.6 Tag occurrence index (new DB table)
```sql
CREATE TABLE tag_occurrences (
  id INTEGER PRIMARY KEY,
  file_path TEXT, tag_type TEXT, tag_value TEXT,
  paragraph INTEGER, char_start INTEGER, char_end INTEGER,
  snippet TEXT
);
```
- Populated during `tag_file()` by scanning paragraphs once
- Makes search O(index) instead of re-reading files every query
- Powers "click a tag → see every paragraph where it appears"

### 1.7 Full-text search (SQLite FTS5)
```sql
CREATE VIRTUAL TABLE file_content_fts USING fts5(
  file_path UNINDEXED, filename UNINDEXED, body
);
```
- Populated during tagging
- Powers "search for any word across all documents"
- Returns paragraph + character offsets for highlighting

---

## PART 2: SEARCH + DOCUMENT READER

### 2.1 Document reader view (new)
- New view `reader` that shows the full text of a file
- Each paragraph wrapped in `<div id="para-N" data-para="N">`
- Search terms highlighted with `<mark>` tags
- Click a paragraph → scroll to it smoothly
- Sidebar shows the file's tags as chips; clicking a chip highlights all matching paragraphs

### 2.2 Click search result → jump to passage
- Search excerpts become clickable: "¶5 ...Nathan was sitting in the kitchen... → open"
- Click calls `openReader(path, term, paragraph)` → navigates to reader view
- Reader scrolls to ¶5, highlights "Nathan" in all paragraphs

### 2.3 Free-text search (not just tag search)
- New input: "Search inside documents…"
- Calls `search_full_text(query)` which uses FTS5 (or Python loop as fallback)
- Returns matches with paragraph numbers + snippets
- Each result clickable → opens reader at that paragraph

### 2.4 Improved tag search
- Switch `find_tag_in_file()` to word-boundary regex (stops "mom" matching "moment")
- Widen snippets to ±120 chars (or full sentence)
- Return char_start/char_end for precise highlighting
- Show "5 of 23 excerpts" with "show all" toggle
- Combine tag + text search: "refine within results" input filters excerpts live

### 2.5 Tag index export
Three formats, all from the tag_occurrences table:
- **CSV** — one row per occurrence (filename, tag_type, tag_value, paragraph, snippet). Opens in Excel.
- **JSON** — nested structure for re-import or version control
- **Markdown** — tags as `#hashtag` inline with the text, plus a tag index appendix. Searchable in any text editor.

---

## PART 3: ANALYSIS IMPROVEMENTS

### 3.1 Wire synthesis report into UI
- `synthesis.generate()` exists but is never called from `api.py`
- Add to `analyze()`: after all tools run, generate synthesis, save to DB, return to UI
- New `renderSynthesis(syn)` UI card placed ABOVE per-tool results:
  - Voice consistency
  - Narrator distance
  - Recurring signals across tools
  - Top 5 things to notice (clickable → jumps to the source observation)
  - AUDHD-aware notes
  - What this does NOT mean (anti-anxiety framing)

### 3.2 Structured locations on observations
- Add `loc` field to every observation (parallel to human-readable `location`):
  ```python
  "loc": {
    "kind": "paragraph_range",  # or sentence_range, paragraph_list, whole_chapter
    "paragraphs": [7, 9],       # 1-based, inclusive
    "sentences": [14, 19],      # when applicable
    "evidence_quote": "..."     # 1-2 sentence excerpt
  }
  ```
- Update all 12 analyzers to compute `loc` from the paragraphs/sentences they already iterate
- Backward-compatible: if `loc` is missing, UI shows the text `location` without click-to-jump

### 3.3 Click analysis observation → jump to passage
- Observation cards become clickable when `loc` exists
- "I noticed 3 long sentences in ¶7-9" → click → reader opens, scrolls to ¶7, highlights ¶7-9
- "Defensive register (4 instances)" → click → reader highlights all 4 paragraphs with defensive language
- "whole chapter" observations → reader opens at ¶1 with a banner

### 3.4 Analysis history view
- DB already stores history (`analysis_history` table, populated silently)
- New `get_saved_analysis(path)` API returns all stored results for a file
- New UI: "📚 History" button on each manuscript file row
- Shows table: tool | last_run timestamp | prior_runs count
- Click a row → re-renders the saved result card
- No need to re-run analysis to see previous results

### 3.5 Analysis export
- `export.export_analysis_report()` exists but is never called
- New `export_analysis(path, save_path, fmt)` API method
- Two formats:
  - **Markdown** — full report with synthesis at top, all observations with `[¶7-9]` anchors, evidence quotes
  - **JSON** — full data structure for round-tripping
- New UI card in Export view: "Export analysis results" with MD/JSON buttons

### 3.6 Observation quality improvements
- Add `evidence_quote` — 1-2 sentence excerpt showing the pattern in context
- Add `why_it_matters` — one sentence tying the observation to memoir craft
- Drop `slice(0,5)` — show all observations (card scrolls)
- Example: "I noticed 3 long sentences (¶7-9) averaging 42 words. *In memoir, a monotonous rhythm at the climax can flatten the emotional peak.* Evidence: 'The years that followed were a blur of masking and meltdowns and I would sit in my room...'"

### 3.7 Two new analysis tools
| Tool | What it does |
|------|-------------|
| `memory_truth` | Detects memory-uncertainty language ("I think", "as far as I remember"), absolute claims ("always", "never"), unverifiable internal states attributed to others |
| `emotional_beats` | Locates named vs shown emotions, tracks whether each scene has an emotional turn, flags scenes where stated emotion differs from scene register |

---

## PART 4: ARCHITECTURE CHANGES

### 4.1 New files
| File | Purpose |
|------|---------|
| `scribbler/passage.py` | Shared paragraph/sentence indexer. `build_index(text)` returns paragraph + sentence offsets. Used by analyzers (for `loc`) and reader view (for highlighting). |
| `scribbler/analyzers/memory_truth.py` | New tool |
| `scribbler/analyzers/emotional_beats.py` | New tool |

### 4.2 New API methods
| Method | Purpose |
|--------|---------|
| `get_file_body(path)` | Returns paragraph-split body + meta for reader view |
| `search_full_text(query)` | Free-text content search via FTS5 |
| `search_tags_with_excerpts(tag_type, value)` | Combined search + excerpts in one call |
| `save_tag_edits(edits)` | Persist user-corrected tags |
| `get_saved_analysis(path)` | Return all stored analysis results for a file |
| `list_analysis_history(path, tool)` | Return analysis history |
| `export_tag_index(format, include_excerpts)` | Export tag index as CSV/JSON/MD |
| `export_analysis(path, save_path, fmt)` | Export analysis results as MD/JSON |

### 4.3 New UI functions
| Function | Purpose |
|----------|---------|
| `renderReader(path, highlight_terms, jump_to)` | Document reader view |
| `openReader(path, term, paragraph)` | Click handler from search/analysis |
| `runFullTextSearch()` | Free-text search handler |
| `renderTagEditor(preview_data)` | Editable chip UI for tag preview |
| `saveTagEdits()` | Sends edited tags to API |
| `renderSynthesis(syn)` | Synthesis report card |
| `renderObservation(file, tool, o)` | Single observation with click-to-jump |
| `renderAnalysisHistory(path)` | History list view |
| `exportTagIndex(format)` | Trigger tag index export |
| `exportAnalysis(path, fmt)` | Trigger analysis export |

### 4.4 Database changes
- New table: `tag_occurrences` (paragraph-level tag positions)
- New table: `file_content_fts` (FTS5 full-text search)
- New columns on `files`: `relationships`, `emotional_beats`, `time_markers`, `objects`
- Wire up orphaned `characters` and `places` tables (add `upsert_character`, `upsert_place`)
- Migration helper: `_migrate(conn)` with `ALTER TABLE` guarded by `PRAGMA table_info`

### 4.5 Files to modify
| File | Changes |
|------|---------|
| `scribbler/tagger.py` | AI entity extraction, new tag types, populate tag_occurrences + FTS + characters/places tables |
| `scribbler/search.py` | Word-boundary regex, char offsets, `search_text_in_all_files()` |
| `scribbler/db.py` | New tables, new columns, migration, new helpers |
| `scribbler/api.py` | 8 new methods, fix AI flag, wire synthesis into analyze() |
| `scribbler/export.py` | Tag index export (CSV/JSON/MD), analysis export with synthesis |
| `scribbler/feedback.py` | Accept `loc`, `evidence_quote`, `why_it_matters` in format_flag() |
| `scribbler/analyzers/craft.py` | Build passage index, pass `loc` to all observations |
| `scribbler/analyzers/editor.py` | Use `re.finditer` for paragraph-located observations |
| `scribbler/analyzers/voice_tense.py` | Add paragraph numbers to tense shifts |
| `scribbler/analysis_suite.py` | Replace "whole chapter" with computed paragraph lists |
| `scribbler/analysis_catalog.py` | Add `memory_truth` and `emotional_beats` |
| `scribbler/config.py` | Add STOPLIST_CHARACTERS, TIME_MARKER_PATTERNS |
| `assets/ui/index.html` | New reader view, search improvements, synthesis card, history view, export cards, editable tags |

---

## PART 5: IMPLEMENTATION ORDER

| Phase | What | Why first |
|-------|------|-----------|
| 1 | Fix AI flag bug + wire synthesis into analyze() | 5 min fix, immediate quality boost |
| 2 | `passage.py` indexer | Foundation for reader + observation locations |
| 3 | `get_file_body` API + `renderReader` UI | The headline feature — see your document in-app |
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
| 14 | Two new analysis tools | memory_truth, emotional_beats |

Phases 1-3 deliver the biggest visible wins in the shortest time. Phases 4-7 complete the "search → see → jump" loop. Phases 8-14 add depth.
