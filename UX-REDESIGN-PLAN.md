# AUDHD Scribbler — Writer-First UX Redesign Plan

## Objective
Turn the existing tool from a capable analysis/dashboard utility into a pleasant writer's workspace for organising memoir material, developing a manuscript, finding material, and understanding the writing.

## Hard constraints
- Windows only. Remove Mac launch/install/support files and documentation.
- No console commands for the end user.
- Final package must be one-click install/use on Windows.
- Preserve existing writing, tagging, SQLite/data model, and analysis engines wherever possible.
- Do not automatically rewrite or reorganise the writer's prose.
- Keep the low-shame / choice-based philosophy.
- Maximum three substantial implementation passes.

## Pass 1 — Writer Workspace
- Rework the generated web UI into a coherent writer-focused application shell.
- Replace dashboard-first hierarchy with Home, Writing, Organise, Explore, Analyse, Manuscript, Search.
- Home: Continue Writing, Things Worth Looking At, recent material, project progress.
- Writing/reader view: clean prose typography, metadata sidebar, status, summary, related material, bookmark/keep-this, Focus Mode.
- Focus Mode: prose only, minimal controls, easy exit.
- Scribble Inbox: raw material cards with excerpt, metadata, word count and simple Keep / Develop / Archive actions.
- Improve visual design: editorial writing-room feel, warm restrained palette, strong typography, whitespace, fewer generic cards.

## Pass 2 — Organise & Explore
- Manuscript view: ordered chapters, parts, word counts, statuses and easy opening/reordering where current architecture permits.
- Character dossiers: appearances, timeline, associated themes and links to actual passages.
- Theme dossiers: appearances, strongest passages, related themes and useful observations.
- Timeline: visual memoir chronology linked directly to material.
- Explore views: People / Time / Themes; retain useful existing visualisations only where they answer a real writer question.
- Search: one writer-facing search entry point covering text, tags, people, places, themes, eras and statuses; results lead to actual passages.
- Saved Moments/bookmarks: lightweight collection of passages the writer wants to keep or revisit.

## Pass 3 — Analysis & Delivery
- Preserve the existing analysis engines.
- Redesign analysis presentation around: What I noticed / Why it might matter / Show me / Leave it.
- Link useful findings back to actual writing passages where possible.
- Surface strengths before criticism and retain optional low-shame language.
- Add practical dashboard prompts based on existing data.
- Remove obsolete/duplicated menu complexity where the new UI replaces it.
- Windows-only packaging: remove Mac scripts/docs; create a clean one-click Windows installer/launcher with no console or manual dependency installation.
- Update README and quick-start documentation.

## Explicit non-goals
- No Word/Google Docs clone, collaboration, AI prose-generation system, unnecessary schema/database migrations, or chart-for-everything UI.
- Do not alter the user's memoir content automatically.

## Acceptance checklist
- [ ] Writer-oriented home screen.
- [ ] Quick find/open/read material.
- [ ] Comfortable Focus Mode.
- [ ] Clear Scribble Inbox workflow.
- [ ] Search leads to real passages.
- [ ] Characters/themes/timeline are useful rather than decorative.
- [ ] Analysis explains findings and can show relevant text.
- [ ] Existing data and analyzers still work.
- [ ] Windows only.
- [ ] End user installs/runs without console commands.
- [ ] README matches actual workflow.
