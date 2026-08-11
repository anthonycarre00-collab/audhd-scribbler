# The Audhd Scribbler

A calm, writer-first workspace for messy memoir material. It keeps the useful tagging, SQLite index and analysis machinery underneath, but the main experience is now about **writing, finding, organising and understanding your material** rather than staring at a dashboard of statistics.

## Windows only

This package is now Windows-only. Mac launchers/installers have been removed.

## Install

1. Download the repository as a ZIP and extract it.
2. Double-click **`INSTALL-Windows.bat`**.
3. The installer creates the local environment, installs dependencies and prepares the project.
4. Double-click **`SCRIBBLER-Windows.bat`** whenever you want to use Scribbler.

You do **not** need to open a terminal or remember commands.

The installer can use Windows Package Manager to install a supported Python version if Python is not already available. Internet access is required for the first installation because Python packages and the language model are downloaded.

## The workspace

The new browser-based workspace is deliberately writer-first:

- **Home** — continue where you left off, recent material and three useful things worth looking at.
- **Writing** — browse the actual material, with excerpts, status and metadata.
- **Organise** — a simple view of raw/early material and the current project shape.
- **Explore** — see recurring people and themes without turning everything into a chart.
- **Analyse** — existing craft, voice, character, continuity, theme and editor analysis remains available.
- **Manuscript** — see chapter/draft material as an emerging book.
- **Search** — search names, places, themes, eras, statuses and the text itself, then open the actual writing.

### Focus Mode

Open any piece of writing from the workspace and use **Focus** to strip away the application chrome and read the prose cleanly.

### Scribble Inbox

Raw dumps are treated as material, not failures. You can leave things messy, develop them later, or simply keep them around until you know what they are.

## What stays underneath

The existing system is deliberately retained rather than rebuilt:

- SQLite metadata/index
- automatic tagging
- characters, places, eras, themes, sensory details, emotional register and beats
- search by tags
- tag coverage reports
- six analysis engines
- local exports
- archive instead of destructive deletion
- optional LLM assistance

Your prose is not automatically rewritten or reorganised.

## Analysis philosophy

Analysis is intended to help you notice things in your own writing, not grade you. The existing feedback system remains strengths-first and optional: describe what was noticed, explain why it might matter, then let the writer decide what to do.

## Daily workflow

1. Drop `.txt` or `.md` material into **`raw-dumps`**.
2. Open Scribbler and tag the material.
3. Open the **workspace/dashboard**.
4. Browse, search, read and organise when useful.
5. Move material into chapters/drafts/final as the manuscript develops.
6. Run analysis on material when you actually want it.
7. Export clean Word/Markdown/plain-text copies when needed.

There is no required rigid workflow. The folders and statuses are there to externalise working memory, not to tell you that you're behind.

## Statuses

- **seedling** — raw material
- **growing** — being developed
- **shaping** — structural work
- **polishing** — close to finished
- **resting** — deliberately left alone for a while

## Privacy

Your writing and SQLite database are local files. If you enable an external LLM provider, the relevant text is sent to that provider for processing. Otherwise Scribbler does not need to send your writing anywhere.

Keep this repository private if it contains personal memoir material.

## Project folders

```text
audhd-scribbler/
├── INSTALL-Windows.bat
├── SCRIBBLER-Windows.bat
├── raw-dumps/
├── triage/
├── chapters/
├── characters/
├── places/
├── themes/
├── research/
├── comps/
├── drafts/
├── final/
├── archive/
├── data/
└── scribbler/
```

## Design rule

**Write first. Organise when useful. Analyse when curious.**

The tool exists to reduce working-memory load and make your own material easier to find and understand. It is not a productivity coach and it does not decide what your memoir should be.
