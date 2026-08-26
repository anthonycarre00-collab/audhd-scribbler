# Scribbler — Tagging, Manuscript Safety & Analysis Plan

## Locked workflow
1. IMPORT / SCRIBBLE INBOX — raw brain dumps only. Tagging helps organise material; it does not judge draft quality.
2. DEVELOP / MANUSCRIPT — selected material becomes chapters/drafts. Writing is never overwritten by tagging or analysis.
3. ANALYSE — deliberate analysis of selected draft/manuscript files only. Never silently analyse the Inbox.

## Data safety
- Never overwrite original imported prose during tagging or analysis.
- Before any operation that changes a manuscript or project metadata, create a timestamped local snapshot/backup.
- Every user-initiated save/change gets a visible confirmation: what changed, where it was saved, and when.
- Keep analysis results versioned rather than silently replacing the previous result; allow comparison/history.
- Database uses WAL plus periodic SQLite backup.
- Provide a clear "Project Safety" status and one-click backup/export from the UI.
- Failed writes must not remove or replace the previous good version.
- Destructive actions require explicit confirmation.

## Analysis UX
Each analysis method gets its own card/button with:
- plain-English purpose
- recommended stage (draft / near-final / final)
- what it looks at
- what it does NOT look at
- expected time/cost if AI-backed
- Run button
- last-run timestamp
- view previous result

A separate "Run Recommended" and "Run All" action is available, but Run All warns that some analyses overlap or depend on other outputs. It runs independent tools first and dependent/interpretive tools only when their prerequisites exist.

## Analysis suite additions to investigate/implement only where technically reliable
- Developmental / structure: overall arc, opening/hook, chapter purpose, scene vs summary balance, pacing, repetition.
- Character: arc/trajectory, relationship dynamics, character voice distinction, presence/absence tracking.
- Memoir-specific: reflection vs event balance, narrator distance, emotional arc, thematic coherence, memory/claim uncertainty flags.
- Continuity: chronology, ages, places, recurring facts, unresolved threads.
- Prose/craft: voice, sentence rhythm, dialogue, show-vs-tell, cliché/overused language, repetition.
- Editorial: clarity, redundancy/compression, line-edit signals, copy-edit signals.
- Reader experience: opening promise, engagement drops, confusion points, emotional peaks/valleys.
- Research/fact flags: claims that may need verification, without pretending the tool can prove facts.

## Important restraint
Do not add dozens of shallow AI buttons. Prefer a smaller set of high-value, evidence-linked analyses. Every finding should point to the relevant passage/chapter where possible. Analysis suggests; the writer decides. It never rewrites the manuscript automatically.
