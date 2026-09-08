# Audhd Scribbler — V12.1 FINAL BUILD HANDOFF
## Make the Existing V12 Feel Like One Proper Writing App

**Audience:** Z AI / implementation agent  
**Starting point:** Current `main` branch of `audhd-scribbler`  
**Baseline:** V10 functionality + current V12 implementation  
**Important:** V11 was not a completed release. Useful V11 ideas have been incorporated into V12/V12.1 where appropriate.  
**Status:** **Ready for implementation**  
**Rule:** Audit first, then begin coding if the plan is safe. Do not pause for approval unless there is a genuine architectural conflict, data-loss risk, or a requirement that cannot be implemented safely.

---

# 0. PURPOSE

The current V12 build has crossed the threshold from an analysis toolkit into a real writing application.

It now contains substantial functionality around:

- projects
- manuscript structure
- writing/editor
- autosave/version history
- dark theme
- live writing checks
- grammar checks
- characters
- places
- themes
- arcs
- relationships
- scenes
- timeline
- findings
- unified search
- Reader
- Inbox
- Browse Tags
- Tag Map
- existing analysis tools

The problem is no longer primarily missing functionality.

The problem is **integration**.

The application can still feel like a collection of tools rather than one coherent writing environment.

V12.1 exists to fix that.

The central target is:

> **The writer writes. Scribbler remembers, organises, connects and points things out. The writer remains in control.**

The target experience:

**WRITE → NOTICE → UNDERSTAND → DEVELOP → REVISE → KEEP WRITING**

---

# 1. NON-NEGOTIABLE STARTING RULE

## V10/V12 functionality must be preserved

Before changing an existing subsystem, establish whether the desired improvement can be added around it.

Do not replace a working V10/V12 implementation simply because a different implementation looks cleaner.

Do not perform a broad rewrite.

Do not throw away functioning analysis, tagging, search, Reader, project or profile functionality.

Prefer:

**existing capability → small safe extension → better integration**

over:

**new subsystem → migration → duplicated logic → increased risk**

---

# 2. FIRST TASK — AUDIT THE ACTUAL REPOSITORY

Before editing code, inspect the current `main` branch.

Do not rely on the old V12 plan or on commit messages as proof that a feature is fully working.

Audit:

1. actual application entry point
2. actual UI loaded by `main.py`
3. active API layer
4. V10 legacy DB access
5. V12 project-local DB
6. project manager
7. manuscript tree
8. editor
9. Reader
10. search
11. tags and tag editing
12. characters
13. places
14. themes
15. arcs
16. relationships
17. scenes
18. timeline
19. findings
20. live writing checks
21. grammar checking
22. backups/snapshots
23. version history
24. import/export
25. build/installer
26. current tests
27. real end-to-end navigation

Create a concise implementation map:

| Area | Current implementation | Working? | Problem | V12.1 action |
|---|---|---|---|---|

Then proceed directly into implementation if no genuine blocker exists.

**Do not stop after the audit merely to ask whether to continue.**

---

# 3. CURRENT PRODUCT MENTAL MODEL

Keep the latest two-pipeline organisation because it is useful:

## MEMORY

The messy material.

- Inbox
- Browse Tags
- Tag Map

## CRAFT

The writing and story development.

- Manuscript
- Reader
- Findings
- Characters
- Places
- Themes
- Arcs
- Relationships
- Timeline
- Compare

## SHARED

Cross-project functions.

- Search
- Export
- Settings

This structure should stay unless actual UI testing proves a better arrangement is needed.

---

# 4. THE MANUSCRIPT IS THE CENTRE

This is the most important V12.1 principle.

The Editor is not another module beside Characters, Themes and Analysis.

It is the centre to which those things connect.

The desired relationship is:

**MANUSCRIPT PASSAGE**

↔ Characters  
↔ Places  
↔ Themes  
↔ Arcs  
↔ Relationships  
↔ Notes  
↔ Analysis Findings  
↔ Tags  
↔ Timeline

Everything important should eventually lead back to actual writing.

---

# 5. PRIORITY 1 — MAKE THE EDITOR THE CENTRE

The current Editor exists and is usable.

V12.1 should make it the place where Scribbler's intelligence becomes useful.

The writer should not have to abandon the manuscript to understand relevant story information.

---

# 6. CONTEXT PANEL — "WHAT'S CONNECTED TO THIS?"

Add a user-controlled contextual panel.

Primary heading:

> **What's connected to this?**

The panel can show, where relevant:

### Characters

Sarah  
David

### Places

Kitchen

### Themes

Memory  
Family

### Arc

Sarah — Acceptance

### Notes

2

### Things worth looking at

1

Every item is clickable.

The panel should use existing data wherever possible.

**Do not build a knowledge graph.**

---

# 7. CONTEXT MUST BE RELEVANT, NOT EXHAUSTIVE

The contextual panel should answer:

> **What is useful to me right now?**

It must not become a second information-management screen.

Prioritise:

1. current selected passage
2. current paragraph
3. current chapter
4. known entities in/near the passage
5. related saved tags
6. relevant notes
7. relevant findings

Do not display every character, place, theme and analysis result in the entire project.

If there is nothing relevant:

> **Nothing connected yet.**

That is perfectly acceptable.

---

# 8. CONTEXT FOLLOWS THE CURSOR / SELECTION

Context can initially use practical deterministic matching:

- current paragraph
- selected text
- character names
- character aliases
- place names
- theme names
- nearby tags
- nearby finding locations
- chapter-level associations

A reliable deterministic first version is preferable to speculative AI.

Refresh after sensible events:

- cursor/selection changes where practical
- save
- explicit context refresh

Do not run expensive LLM analysis on every cursor movement.

---

# 9. CONTEXT PANEL MUST BE USER-CONTROLLED

The context panel should not automatically take over the writing surface.

Default:

**closed or compact**

Button:

**Context**

When opened, it occupies a small right rail.

When closed, the Editor gets the space back.

Remember the user's preference where practical.

---

# 10. EDITOR MODES

Use the same Editor.

Provide lightweight modes:

## Write

Maximum writing space.

## Develop

Writing + contextual story information.

## Analyse

Writing + analysis findings.

Do not create separate editor implementations.

---

# 11. FOCUS MODE

Focus Mode should genuinely minimise distraction.

Hide:

- sidebar
- context panel
- non-essential tools

Keep:

- editor
- necessary navigation
- optional status/count

Exit must always be obvious.

---

# 12. EDITOR NAVIGATION MUST BE LOCATION-SAFE

Every important feature should be able to open a specific manuscript location.

These must work:

- Character → passage
- Place → passage
- Theme → passage
- Arc → scene/chapter
- Relationship → relevant scene
- Timeline → chapter
- Search → passage
- Finding → evidence
- Reader → Editor
- Tag → passage

If a target is paragraph 8, the Editor should land at paragraph 8.

If a finding has character offsets, highlight that range when practical.

Avoid all incorrect-ID / empty-target failures.

---

# 13. SHARED LOCATION MODEL

Reader and Editor should agree on:

- project
- chapter
- paragraph
- character offset
- selection range

Do not maintain separate incompatible location systems.

This is one of the highest-value technical cleanups in V12.1.

---

# 14. READER VS EDITOR

Keep the distinction clear.

## Reader

Read / inspect / investigate.

## Editor

Write / revise.

They should share navigation and location.

Do not create two competing manuscript systems.

---

# 15. PRIORITY 2 — MAKE DEVELOPMENT PAGES EVIDENCE-BASED

Characters, Places, Themes and Arcs are now real features.

V12.1 must make them useful in relation to the actual manuscript.

A profile without evidence is just a form.

---

# 16. CHARACTER PAGE

Structure:

## Profile

- name
- aliases
- role
- age
- occupation
- background
- physical
- personality
- voice
- motivation

## Development

- arc
- relationships
- notes

## Evidence

Show where the character appears:

- chapter
- paragraph
- snippet

Click → Editor/Reader at the correct passage.

## Analysis

Show relevant saved findings where appropriate.

The user should be able to compare:

> **What I say this character is**

with:

> **What the manuscript actually shows.**

---

# 17. PLACE PAGE

Structure:

## Profile

- location
- description
- atmosphere
- sensory signature
- history
- significance

## Evidence

Where this place appears.

## Related

- characters
- themes
- scenes
- notes

Every useful item leads back to the manuscript.

---

# 18. THEME PAGE

Structure:

## Definition

Writer's own definition.

## Evidence

Relevant manuscript passages.

## Counter-evidence

Only where reliable evidence exists.

Counter-evidence must not be presented as fact merely because an algorithm found something vaguely related.

## Related

- characters
- places
- scenes
- motifs
- notes
- findings

The real question is:

> **Is this theme genuinely present in the writing?**

---

# 19. ARC PAGE

Structure:

## Intended arc

- beginning
- pressure
- turning points
- major beats
- climax
- resolution

## Actual evidence

Which chapters/scenes support the arc.

## Analysis

Relevant emotional and structural findings.

The writer should be able to move between:

**planned arc ↔ actual manuscript**

easily.

---

# 20. RELATIONSHIPS

Relationship pages should show:

- characters
- type
- history
- current state
- conflicts
- important scenes
- relevant passages
- emotional movement
- notes

Existing relationship-map functionality remains useful as an overview.

Do not spend V12.1 building a more sophisticated graph.

---

# 21. PRIORITY 3 — IMPROVE LIVE WRITING CHECKS

The current live checker is a good foundation.

Existing checks include:

- spelling
- run-on sentences
- repeated words
- double spaces
- passive construction
- filter words
- weak words
- repeated sentence openings

Do not replace this with an enormous external grammar system.

---

# 22. SEPARATE ERRORS FROM SUGGESTIONS

## Errors

Use for likely mechanical problems:

- spelling
- deterministic grammar issue
- obvious punctuation problem

## Suggestions

Use for:

- long sentences
- repetition
- possible passive voice
- weak words
- filter words
- repeated sentence openers
- density/readability signals

Important:

**"really" is not an error.**

**"felt" is not an error.**

These may be deliberate choices.

---

# 23. LIVE CHECK UX

Use:

- subtle marker/underline
- small count
- Context panel
- click to inspect

Avoid:

- modal popups
- constant interruptions
- aggressive red markings for suggestions
- rewriting text automatically

The writer must always be able to ignore the system and continue writing.

---

# 24. IGNORE / DISMISS

Support simple actions:

**Ignore this**

**Ignore this type**

**Dismiss**

A lightweight per-project ignore mechanism is enough.

Do not build an elaborate machine-learning feedback system unless later proven necessary.

---

# 25. SPELLCHECK QUALITY

Use the current offline mechanism.

Improve handling of:

- proper names
- character names
- place names
- fictional words
- contractions
- apostrophes

Provide Add/Ignore where practical.

Do not promise Grammarly-level correctness.

---

# 26. GRAMMAR QUALITY

Keep the current rule-based grammar layer.

Use wording such as:

> **Possible grammar issue**

rather than:

> **Grammar error**

unless the rule is genuinely deterministic.

Show:

**What it noticed**

**Possible correction**

The writer decides.

---

# 27. PRIORITY 4 — ANALYSIS IN THE WRITING FLOW

The current analysis suite is already large.

Do not create another collection of AI tools.

Instead, expose existing analysis in the places the writer needs it.

---

# 28. ANALYSE SELECTION

Editor:

Select text

→ **Analyse selection**

Use the existing analysis tools appropriate to that context.

Results are saved.

---

# 29. ANALYSE CHAPTER

Editor:

**Analyse chapter**

Use the existing analysis engine(s).

Results feed the existing Findings system.

The editor must remain usable while deeper analysis runs.

---

# 30. FINDINGS PRESENTATION

Do not dump JSON.

Use:

## Things worth looking at

Each finding should show:

- What I noticed
- Evidence
- Why it might matter
- Possible improvement
- Open passage

Actions:

- Keep
- Dismiss
- Turn into note
- Dealt with where appropriate

---

# 31. ANALYSIS FINDINGS ARE NOT TAGS

Hard rule.

Do not convert analysis findings into permanent user tags automatically.

A tag means:

> **Writer-approved organisation**

A finding means:

> **Scribbler thinks this may be worth looking at**

Keep these distinct.

---

# 32. FINDINGS → NOTES

Allow:

**Make note**

Example:

Finding:

> Possible continuity problem.

Writer note:

> Check why David already knows this here.

This is useful and straightforward.

Do not build project-management software around it.

---

# 33. PRIORITY 5 — SEARCH SHOULD FEEL LIKE MEMORY

Search is not primarily a database function.

It is an answer to:

> **"I remember something. Where is it?"**

---

# 34. SEARCH ACROSS THE WHOLE PROJECT

Search:

- manuscript text
- brain dumps
- tags
- characters
- places
- themes
- arcs
- relationships
- scenes
- notes
- analysis findings

The writer should not need to know where the information is stored.

---

# 35. SEARCH RESULTS SHOULD BE GROUPED

Example:

## Character

Sarah

## Manuscript

Chapter 2 — excerpt  
Chapter 5 — excerpt  
Chapter 9 — excerpt

## Brain dumps

Old note — excerpt

## Analysis

2 findings

This is better than one giant flat result list.

---

# 36. SEARCH RESULT ACTIONS

Every result should have a clear destination.

Examples:

- Open in Editor
- Open in Reader
- Open Character
- Open Theme
- Open Finding

The destination should match the result.

---

# 37. SEARCH STATE PERSISTENCE

When the writer searches:

**hospital**

then opens something else and returns:

- retain `hospital`
- restore results where practical
- retain useful filters

The writer should not need to remember what they were searching for.

---

# 38. BROWSE TAGS STAYS

Browse Tags is useful.

Its purpose:

> **Show me what I have tagged so I can remember what is there.**

Do not turn it into a complicated taxonomy manager.

---

# 39. TAG EDITS ARE AUTHORITATIVE

Keep:

- add
- remove
- edit
- save

Manual changes are authoritative.

Automatic re-tagging must not silently wipe them.

---

# 40. PRIORITY 6 — BRAIN DUMP → MANUSCRIPT

Memory and Craft remain separate.

But promotion should be easy.

---

# 41. PROMOTE TO MANUSCRIPT

A brain dump can be promoted.

The operation should:

1. preserve the original
2. create manuscript material
3. preserve useful tags
4. keep the source relationship
5. allow the new manuscript material to be edited independently

Do not silently turn the original dump into canon.

---

# 42. PRIORITY 7 — FIX SAFETY / SNAPSHOT ARCHITECTURE

The current implementation has had to disable snapshot functions because of database-locking/slowdown problems.

That may be an understandable temporary workaround.

It is not acceptable as the final writing-app behaviour.

---

# 43. SAFETY FIX REQUIREMENT

Find and fix the underlying cause.

Investigate:

- long-held DB connections
- snapshot timing
- locking
- autosave interaction
- unnecessary repeated snapshots

Potential practical solutions:

- separate snapshot connection
- snapshot only after save commit
- file-based backup
- sensible snapshot frequency

Do not simply remove safety functionality.

---

# 44. AUTOSAVE

A sensible pattern:

**typing**

↓

debounce

↓

save manuscript source

↓

update indexes/metadata

↓

optional version snapshot under a sensible policy

Do not snapshot on every keystroke.

Autosave should never make writing feel sluggish.

---

# 45. VERSION HISTORY

Provide:

**Version history**

with timestamps.

Actions:

**Preview**

**Restore**

Before restore:

**Create safety snapshot**

Restore must be reversible.

---

# 46. PRIORITY 8 — CLEAN UP V10 / V12 DUPLICATION

The current repository contains legacy V10 and newer V12 systems.

This is understandable during migration.

Now establish clear ownership.

---

# 47. CANONICAL DATA OWNERSHIP

Document one authoritative source for each data type.

| Data | Canonical source |
|---|---|
| Manuscript text | Markdown manuscript source |
| Brain dump | Brain-dump source file |
| Character profile | V12 character record |
| Place profile | V12 place record |
| Theme profile | V12 theme record |
| Arc | V12 arc record |
| Relationship | V12 relationship record |
| Scene | V12 scene record |
| Writer note | V12 note record |
| Manual tag | Saved user tag |
| Analysis finding | V12 finding record |
| Search index | Derived |
| Timeline derivation | Derived unless explicitly confirmed |
| Live writing check | Derived |

Do not allow two competing sources of truth to develop.

---

# 48. DO NOT MASS-REWRITE

Where old code is still needed:

- document it
- isolate it
- stop introducing new dependencies on it
- migrate gradually

Do not risk breaking working behaviour simply to make the source tree cleaner.

---

# 49. VERSION CONSISTENCY

Audit all version reporting:

- Python API
- UI
- sidebar
- executable
- installer
- tests
- project metadata

They should report the actual current version consistently.

---

# 50. PRIORITY 9 — MANUSCRIPT TREE

Keep the hierarchy lightweight:

**Book**

→ Parts

→ Chapters

→ optional Scenes

Support:

- create
- rename
- reorder
- move
- open
- duplicate
- archive/delete safely

Do not add ten organisational layers.

---

# 51. SCENES REMAIN OPTIONAL

A writer must be able to work perfectly at:

**Book → Chapter**

level.

Scenes are an optional organisational/development layer.

Do not force scene planning on the user.

---

# 52. HOME — WRITER'S LAUNCHPAD

Home should help orient the writer.

Show:

### Continue writing

Last chapter / last position.

### Brain dump

Quick Note / Inbox.

### Develop

Characters / Themes / Places / Arcs.

### Understand

Open Findings / Recent Analysis.

### Search

Search everything.

Keep it calm.

No productivity scoring.

No streaks.

No achievements.

---

# 53. "THINGS WORTH LOOKING AT" ON HOME

A small number of open findings may appear.

Example:

**Things worth looking at**

- Chapter 4 — possible continuity issue
- Chapter 7 — strong emotional beat
- Chapter 9 — repetition worth reviewing

Click:

**finding → evidence → Editor**

This gives the writer a useful return path after time away.

---

# 54. UI / VISUAL STANDARD

The application should feel like a:

> **quiet, intelligent writer's workshop**

not:

> **an AI productivity dashboard**

Use:

- large clear headings
- readable typography
- generous spacing
- clear primary action
- restrained icons
- consistent controls
- compact contextual panels
- useful empty states

Avoid:

- dense boxes everywhere
- tiny controls
- excessive badges
- giant tables
- technical language
- permanent warnings
- excessive animation

---

# 55. THE EDITOR SHOULD BE THE NICEST SCREEN

The Editor should receive the highest visual attention.

Requirements:

- comfortable line width
- readable typography
- generous line spacing
- stable cursor
- minimal distraction
- clear chapter title
- unobtrusive save state
- consistent dark theme
- no unnecessary motion

The writer should actually want to write in it.

---

# 56. SIMPLE TOOLBAR

Keep a small toolbar.

Recommended:

**Undo | Redo | Bold | Italic | Heading | Quote | Find | Check | Analyse | Context**

Do not create a Word-style ribbon.

---

# 57. STATUS BAR

Useful:

- word count
- character count
- save state
- optional writing session indicator

Do not turn this into productivity pressure.

---

# 58. KEYBOARD SHORTCUTS

Keep shortcuts simple and consistent:

- Ctrl+S — save
- Ctrl+F — find/search
- Ctrl+B — bold
- Ctrl+I — italic
- Ctrl+Z — undo
- Ctrl+Y — redo
- Ctrl+E — focus mode
- Ctrl+N — Quick Note
- Esc — close current overlay/panel

Do not build a huge shortcut matrix.

---

# 59. ERROR HANDLING

Writer-facing errors must be human-readable.

Bad:

`sqlite3.OperationalError: database is locked`

Better:

> **Scribbler couldn't create a snapshot just now. Your manuscript is still saved.**

Technical detail can be available separately.

Never show raw stack traces in the normal UI.

---

# 60. NO SILENT FAILURES

Important operations must not silently swallow errors.

For save/index/backup/restore operations:

- report failure
- log failure
- preserve the source
- keep the application usable

Never say something saved when it did not.

---

# 61. EXPORT / PORTABILITY

Keep current export functionality.

At minimum:

- Markdown
- TXT
- DOCX where already supported
- analysis export
- project backup

The writer must always be able to get their work back out.

---

# 62. PROJECT BACKUP

A project backup must contain enough to reconstruct the project.

At minimum:

- manuscript
- brain dumps
- project DB
- project metadata
- character/place/theme records
- arcs/relationships/scenes
- notes
- findings
- relevant configuration

Restore must be tested.

---

# 63. TESTING PHILOSOPHY

The current automated test suite is valuable.

Keep it.

But do not confuse:

**software correctness**

with:

**good writer UX**

A feature is not done merely because its test passes.

---

# 64. MANUAL "REAL WRITER" TEST AFTER EACH MAJOR UI PHASE

This is now a mandatory gate.

After each major UI phase, spend a realistic 10–15 minutes using the feature as a writer rather than merely following scripted test clicks.

Check:

- Can I find it?
- Do I understand it?
- Is the main action obvious?
- Does it interrupt writing?
- Is there too much information?
- Does it help me or give me something else to manage?
- Can I recover my place easily?
- Does it naturally lead back to the manuscript?

The purpose is to catch problems automated tests cannot see.

---

# 65. CRITICAL JOURNEY 1 — WRITE

New/open project

→ open chapter

→ write

→ autosave

→ close

→ reopen

→ text intact

→ continue writing

Must work reliably.

---

# 66. CRITICAL JOURNEY 2 — WRITE + CONTEXT

Open chapter

→ write passage mentioning Sarah and Kitchen

→ Context

→ Sarah/Kitchen appear if recognised

→ click Sarah

→ character opens

→ return to manuscript

→ correct chapter/location retained.

---

# 67. CRITICAL JOURNEY 3 — LIVE CHECK

Write:

- misspelling
- long sentence
- repeated word

→ subtle markers appear

→ inspect marker

→ understand why it appears

→ dismiss

→ marker disappears

→ manuscript text remains unchanged unless writer edits it.

---

# 68. CRITICAL JOURNEY 4 — ANALYSIS

Select passage

→ Analyse

→ result saved

→ finding appears

→ evidence visible

→ Open passage

→ Editor reaches correct location

→ Make note

→ finding status remains under writer control.

---

# 69. CRITICAL JOURNEY 5 — CHARACTER

Open character

→ see profile

→ see appearances

→ click appearance

→ correct passage opens

→ return to character.

---

# 70. CRITICAL JOURNEY 6 — THEME

Open theme

→ see definition

→ see evidence

→ inspect related passage

→ return.

---

# 71. CRITICAL JOURNEY 7 — BRAIN DUMP

Quick Note

→ Inbox

→ Detect tags

→ manually edit

→ save

→ Browse Tags

→ select saved tag

→ open occurrence

→ correct passage opens.

---

# 72. CRITICAL JOURNEY 8 — PROMOTION

Brain dump

→ Promote to Manuscript

→ original remains

→ manuscript copy exists

→ useful tags retained

→ new manuscript content can be edited independently.

---

# 73. CRITICAL JOURNEY 9 — SEARCH

Search:

**hospital**

→ grouped results

→ manuscript

→ brain dump

→ character/profile

→ analysis

→ open relevant destination

→ return

→ search remains.

---

# 74. CRITICAL JOURNEY 10 — RECOVERY

Write significant material

→ save

→ backup

→ simulate interruption

→ reopen

→ latest safe state available.

---

# 75. CRITICAL JOURNEY 11 — MIGRATION

Use an actual older project.

→ migrate

→ verify manuscript

→ verify brain dumps

→ verify tags

→ verify analysis history

→ verify profiles

→ verify backup

→ continue writing.

---

# 76. PERFORMANCE TARGETS

Normal writing must feel immediate.

Target:

- chapter opening: fast
- editing: no perceptible lag
- local checks: near-instant
- search: fast for normal projects
- profile opening: fast
- analysis: asynchronous
- heavy analysis: does not freeze the Editor

Do not optimise for theoretical giant projects before normal writing is excellent.

---

# 77. AI PERFORMANCE POLICY

AI should not be required for ordinary writing.

Local/non-LLM functionality should cover:

- editing
- saving
- navigation
- search
- spelling
- basic grammar
- live checks

LLM use remains appropriate for:

- deeper analysis
- existing AI-assisted tagging
- deeper interpretation

Deep work should be explicit and asynchronous.

---

# 78. NO AUTOMATIC CANON CHANGES

AI must never silently:

- change manuscript text
- change character facts
- change relationships
- change themes
- change arcs
- delete material
- turn suggestions into confirmed facts

Writer action is always required.

---

# 79. NO AUTOMATIC ANALYSIS TAGGING

Analysis findings must not become user tags automatically.

Keep the distinction:

**Tag = writer-approved organisational fact**

**Finding = machine interpretation**

If a writer wants a finding preserved as a tag, that should be an explicit action.

---

# 80. IMPLEMENTATION ORDER

| Phase | Work | Priority |
|---|---|---|
| 0 | Audit current V12 + source-of-truth map | Critical |
| 1 | Editor/context integration | Critical |
| 2 | Shared Reader ↔ Editor location/navigation | Critical |
| 3 | Character/Place/Theme/Arc evidence integration | Critical |
| 4 | Live-check UX + error/suggestion separation | High |
| 5 | Analysis from selection/chapter + Findings | High |
| 6 | Findings → Notes | High |
| 7 | Search grouping + context persistence | High |
| 8 | Brain dump → Manuscript polish | High |
| 9 | Snapshot/backup architecture fix | Critical |
| 10 | V10/V12 source-of-truth cleanup | High |
| 11 | Home/navigation/visual polish | Medium |
| 12 | Full journey testing + release hardening | Critical |

---

# 81. IMPLEMENTATION STYLE

Work in coherent commits.

Suggested commit sequence:

1. `v12.1 audit and source-of-truth map`
2. `v12.1 editor context integration`
3. `v12.1 reader editor navigation`
4. `v12.1 evidence integration`
5. `v12.1 live check UX`
6. `v12.1 analysis integration`
7. `v12.1 search UX`
8. `v12.1 brain dump manuscript flow`
9. `v12.1 safety fixes`
10. `v12.1 source-of-truth cleanup`
11. `v12.1 UI polish`
12. `v12.1 release hardening`

Do not mix unrelated architectural changes into one large commit.

---

# 82. TEST GATE AFTER EVERY PHASE

After each phase:

1. Python syntax
2. JavaScript syntax
3. targeted tests
4. full regression suite
5. UI smoke test
6. relevant critical journey
7. manual writer usability check for major UI changes

No phase should knowingly leave the application broken.

---

# 83. DO NOT GAME THE TESTS

Never:

- weaken assertions
- delete tests because behaviour is inconvenient
- hard-code fake results
- pretend a save succeeded
- swallow important failures merely to keep tests green
- create non-functional UI placeholders
- mark a feature complete when only its backend works

Tests protect the product.

---

# 84. WHAT COUNTS AS DONE

A feature is not done because:

- a button exists
- an API exists
- a database table exists
- a test passes

It is done when:

> **A normal writer can use it without needing to understand how Scribbler works internally.**

---

# 85. THE "SECOND BRAIN" TEST

For every V12.1 change, ask:

> **Does this remove something the writer has to remember or organise?**

Good examples:

Search removes remembering where something is.

Tags remove remembering which files contain something.

Character evidence removes remembering every passage involving a character.

Theme evidence removes remembering where a theme appears.

Findings remove remembering what the analysis previously noticed.

Notes remove remembering future fixes.

Context removes the need to jump between screens.

---

# 86. THE "DON'T ANNOY THE WRITER" TEST

Do not create:

- constant popups
- endless warnings
- forced categorisation
- repeated tagging
- intrusive AI
- unnecessary modal dialogs
- information overload

The writer must be able to ignore Scribbler and simply write.

That is a feature.

---

# 87. THE "ONE APP" TEST

At any point, ask:

> **Does this feel like part of the same writing application?**

A writer should not mentally switch between:

- “the character tool”
- “the analysis tool”
- “the tag tool”
- “the search tool”

They should feel:

> **“I'm in my book, and Scribbler is helping me.”**

---

# 88. FINAL PRODUCT STANDARD

The final experience should be:

**I am writing.**

Scribbler knows:

- who is in the passage
- where the scene is
- what themes are involved
- what arc is relevant
- what I have previously noted
- what analysis has noticed
- what old ideas might connect

I can inspect any of these with one click.

Then:

**I return to writing.**

That is the product.

---

# 89. FINAL DEFINITION OF V12.1

V12.1 succeeds when Scribbler genuinely feels like:

> **“This is where I write my book.”**

rather than:

> **“This is an AI analysis toolkit that happens to contain an editor.”**

The Editor is the centre.

The manuscript is authoritative.

The Inbox is the external memory.

Search is retrieval.

Characters, places, themes, arcs and relationships are development tools.

Reader is the inspection surface.

Analysis is interpretation.

Live checks are quiet assistance.

AI is the assistant.

The writer remains the author.

---

# 90. FINAL INSTRUCTION TO Z AI

**Start by auditing the current `main` branch.**

Do not assume the old V12 plan matches the code.

Identify what is working.

Preserve it.

Fix only what needs fixing.

Then begin implementation in the order specified.

**Do not wait for approval after the audit unless you encounter:**

- a genuine data-loss risk
- an architectural conflict that prevents safe implementation
- a requirement that cannot be implemented with the current technology
- a dependency/security problem requiring a real decision

Otherwise:

**audit → implement → test → inspect → continue.**

Do not invent another major feature set.

Do not turn V12.1 into V13.

Do not build speculative infrastructure.

Make the existing application work together.

The highest-value outcome is not another clever feature.

It is this:

> **When the writer is writing, Scribbler already has the relevant context one click away.**

That is V12.1.

**Make it feel like one writing tool.**
