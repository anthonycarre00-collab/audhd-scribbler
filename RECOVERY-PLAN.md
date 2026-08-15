# Scribbler Recovery Plan — Functional Wiring Pass

## Source of truth
Reuse the existing engines and decisions already present in repository history; do not redesign the product or invent replacement workflows.

Reference commits:
- `80024a17d425c9dfd1364db79c122fed444005be` — locked tagging/manuscript safety/analysis workflow.
- `53bc06d14cf3eeb1a3328ebadbd25d5318b8aaae` — mature tagging/search/coverage workflow.
- `b53a90633913a5db6debb5b2b8f2ad3449ce78b6` — voice, motif, cadence, structural-anchor and chapter-comparison intelligence.
- `b13eceafb8c9a13855948826b74dcac2ed7cddd3` — file visibility/read/delete workflow.

## Locked workflow
1. **Scribble Inbox / Tagging**: raw brain dumps and quick notes only. Import, preview tags, apply tags, search/filter tagged material. No writing-quality analysis here.
2. **Manuscript / Analysis**: chapters, drafts and final material only. Select manuscript files, select individual analysis tools, run one tool or a compatible group, view results/history. No tagging action here.
3. **Safety / Export**: explicit save confirmations, snapshots, project backup, non-overwriting exports.

## Functional repair
- Replace the shallow `analysis_suite.py` dispatch with real deterministic implementations for the six previously stubbed tools, reusing `writer_intelligence` metrics where appropriate.
- Keep the established analyzers (`craft`, `voice_tense`, `characters`, `continuity`, `themes`, `editor`) intact.
- Keep `writer_intelligence.py` intact and wire its real functions directly.
- Every visible analysis tool must map to an executable function. No catalogue-only/stub tools.
- Analysis results must render as readable findings/metrics/evidence, not only raw JSON.
- Add per-tool Run action plus Run Recommended and Run All; Run All warns and uses the existing compatibility guidance.
- Add analysis history viewing using existing database history functions.

## UI repair
- One workspace; no overlay UI and no prompt-based import destinations.
- Separate Inbox controls from Manuscript/Analysis controls visually and behaviourally.
- Dedicated tag preview/results area inside Inbox.
- Dedicated analysis results area inside Analysis.
- Real upload dialogs for Inbox vs Chapter vs Draft; no destination prompts.
- Quick Note saves directly into Inbox.
- No header buttons that do nothing.

## Safety
- Never analyse raw-dump/Inbox files.
- Never tag manuscript files.
- Snapshot before import/tag/analysis/note/metadata changes.
- Preserve analysis history.
- Never silently overwrite exported files.

## Release gate
Before packaging:
- compile all Python modules;
- import all analyzers and writer-intelligence modules;
- start the server and verify `/api/status`, `/api/files`, `/api/tools`;
- execute each analysis tool against a known sample text and assert non-empty result;
- verify tag-preview and tag paths reject manuscript files;
- verify analysis rejects Inbox files;
- verify quick note and import destinations;
- package and launch the frozen Windows executable.

No new feature scope is permitted in this pass. This is a recovery, wiring, reliability and presentation pass only.
