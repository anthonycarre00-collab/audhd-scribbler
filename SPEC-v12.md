# The Audhd Scribbler — V12 Master Spec

> **Source document:** `The Audhd Scribbler — V12 Master Plan.docx` (uploaded 2026-09-08)
> **Status:** Authoritative — replaces all prior v12 planning drafts
> **Date:** 2026-09-08
> **Platform:** Standalone Windows desktop application — pywebview + WebView2
> **Owner:** Anthony Carré
> **Foundation:** V10 delivered + V11 consolidated plan

---

## Purpose

Transform Audhd Scribbler from an intelligent writing-organising tool into a complete, approachable writing application.

---

## 0. V12 — The Bigger Vision

V11's objective is to make Scribbler feel like an external brain for a writer.

V12 takes that one step further.

The application becomes the place where the writer can:

- capture ideas
- write actual prose
- organise manuscripts
- build characters
- develop relationships
- track character arcs
- develop themes
- map places
- examine emotional beats
- analyse prose
- check grammar and spelling
- identify sentences that need attention
- search everything
- understand how different pieces of the work connect
- revise
- and ultimately finish the book

The result should feel like a proper writing application, while retaining the unusual intelligence already present in Scribbler.

The target is not to reproduce every feature of Scrivener.

The target is:

> The simplicity and accessibility of a good writing app + the organisational power of a lightweight Scrivener + Scribbler's existing intelligent analysis and memory system.

---

## 1. The V12 Design Principle

The application should be built around one central idea:

> Everything belongs to the writing project, but everything has a different job.

There are four major layers:

1. **WRITE** — Where the writer actually writes.
2. **ORGANISE** — Where material is arranged into manuscript structure and working sections.
3. **DEVELOP** — Where characters, places, themes, arcs, relationships and other story elements are developed.
4. **UNDERSTAND** — Where Scribbler analyses the writing and explains what it sees.

These must not become four disconnected applications. They all operate on the same underlying project.

---

## 2. The Core V12 Workflow

The writer's complete workflow becomes:

```
CAPTURE → WRITE → ORGANISE → DEVELOP → ANALYSE → CHECK → REVISE → WRITE AGAIN
```

This should work in both directions.

For example:
- Character → Character profile → Related passages → Reader → Analysis → Revision
- Manuscript passage → Detected character → Character profile → Arc → Related scenes
- Brain dump → Tag → Develop → Promote → Manuscript → Analyse

Nothing important should become an isolated island.

---

## 3. The New V12 Application Structure

The main navigation should evolve from the V11 structure.

A possible primary structure:

**WRITE**
- Home
- Inbox
- Manuscript
- Reader

**DEVELOP**
- Characters
- Places
- Themes
- Arcs
- Relationships

**UNDERSTAND**
- Analysis
- Search
- Timeline / Structure
- Compare

**OUTPUT**
- Export
- Project / Settings

The exact labels can be refined during UI implementation, but the conceptual grouping should remain.

The navigation should be visually obvious and friendly rather than resembling an enterprise application.

---

## 4. Home — The Writer's Desk

Home should become the writer's starting point rather than a statistics dashboard.

The opening screen should immediately provide:

**Continue writing**
- last manuscript opened
- last chapter
- last reading position
- last edited location

Primary button: **Continue writing**

**What's in my head?**
- Quick Note
- Inbox
- recent brain dumps

**Work on the story**
- Manuscript
- Characters
- Places
- Themes
- Arcs

**Understand the work**
- Recent analysis
- Things worth looking at
- unresolved issues
- recent discoveries

**Search everything**
One global search.

The Home screen should feel like: "Here is my writing life. Where do I want to go?"

Not: "Here are twelve metrics about my productivity."

---

## 5. The Manuscript — A Real Writing Environment

This is the largest new capability in V12. The Manuscript must become a genuine writing workspace.

### 5.1 Basic structure

Provide a simple manuscript tree:

```
Book
├── Part One
│   ├── Chapter 1
│   ├── Chapter 2
│   └── Chapter 3
└── Part Two
    ├── Chapter 4
    └── Chapter 5
```

The writer should be able to:
- create chapter
- rename chapter
- reorder chapter
- create section
- rename section
- move chapter
- duplicate chapter
- delete/archive chapter
- open chapter in editor

Do not attempt to replicate every Scrivener organisational feature. The structure should remain understandable.

---

## 6. The Writing Editor

The writing editor needs to be substantially better than the current Reader.

Reader and Editor should remain conceptually distinct:
- **Reader** — Read and investigate.
- **Editor** — Write and revise.

But they should share the same passage/location system.

### 6.1 Editor essentials

The editor should support sensible basic writing functions:
- normal paragraphs
- headings
- bold
- italic
- underline where useful
- block quote
- lists
- undo/redo
- copy/paste
- select all
- find
- replace
- keyboard shortcuts
- word count
- character count
- paragraph count
- basic navigation

Avoid turning it into a desktop publishing system.

### 6.2 Comfortable writing surface

The writing area should be large and calm. The writer should be able to hide distractions.

Potential modes:
- **Focus** — Large writing area with minimal UI.
- **Normal** — Writing area + useful contextual tools.
- **Inspect** — Writing area + analysis/context panel.

The default should favour writing.

---

## 7. Live Writing Tools

One of V12's most important ideas:

> The writer shouldn't always have to leave the editor to use Scribbler's intelligence.

Provide an optional contextual tools panel.

Possible tools:
- **Spelling** — Identify likely spelling errors.
- **Grammar** — Identify grammar problems.
- **Sentence length** — Highlight unusually long sentences.
- **Sentence structure** — Identify overly complicated or awkward construction.
- **Repetition** — Identify repeated words or phrases.
- **Passive voice** — Flag potential passive constructions.
- **Telling / showing** — Use the existing analysis capability where appropriate.
- **Emotional register** — Highlight passages with notable emotional register.
- **Voice** — Surface potential voice inconsistencies.
- **Readability** — Identify passages that may be unusually dense.
- **Dialogue** — Potential dialogue issues.
- **Clichés / repeated expressions** — Flag likely repetition or cliché usage.
- **Continuity** — Surface relevant continuity issues already known by Scribbler.

These should not rewrite the manuscript automatically.

The writer gets: **Notice → Explain → Locate → Decide**

rather than: AI → Rewrite my book

---

## 8. Live vs Saved Analysis

V12 should support two modes.

**LIVE** — Fast lightweight checks while writing.
Examples: spelling, grammar, sentence length, repetition, basic style warnings.

These should not require a full manuscript analysis.

**DEEP ANALYSIS** — Existing Scribbler analysis engines run against:
- paragraph
- passage
- chapter
- selected chapters
- whole manuscript

Results are saved.

The writer can therefore ask:
- "Analyse this paragraph now."
- "Run the full chapter analysis and save the findings."

This distinction prevents the application from constantly running expensive/deep analysis.

---

## 9. The Writing Toolbar

The editor should have a very simple toolbar.

Possible arrangement:
```
Undo | Redo | Bold | Italic | Heading | Quote | Find | Check | Analyse
```

Then contextual tools can appear in a secondary panel.

Avoid a giant Microsoft Word-style ribbon. The interface should remain writer-friendly.

---

## 10. Spelling and Grammar

V12 should introduce a proper writing-quality layer.

### 10.1 Spell checking

The editor should identify likely spelling mistakes.

Potential implementation should favour:
- local/offline checking where practical
- existing libraries/dependencies where possible
- no unnecessary cloud requirement

The writer can:
- ignore
- replace
- add to dictionary

### 10.2 Grammar checking

Grammar checking should identify likely issues rather than pretending to be infallible.

Each finding should provide:
- Problem
- Why it may be a problem
- Possible correction

The writer chooses whether to change it.

### 10.3 Writing-quality checks

Additional lightweight checks:
- very long sentence
- sentence fragment
- repeated word
- repeated phrase
- excessive adverbs
- excessive passive construction
- paragraph density
- repeated sentence openings
- dialogue punctuation
- possible cliché
- inconsistent tense

These should be configurable rather than forced on the writer.

---

## 11. Characters — A Full Development Area

Characters should become a first-class part of the application. Each character gets a dedicated profile.

### 11.1 Character profile

Possible sections:

**Identity**
- name, aliases, age, occupation, background, physical description

**Personality**
- traits, strengths, weaknesses, fears, desires, values, contradictions

**Voice**
- speech style, vocabulary, mannerisms, recurring expressions

**Motivation**
- wants, needs, fears, objectives

**Relationships**
- Connected characters.

**Arc**
- Character development over the manuscript.

**Evidence**
- Actual manuscript passages involving the character.

**Notes**
- Writer's free-form development notes.

---

## 12. Character Evidence

The profile must not become a manually maintained biography that quickly becomes obsolete.

Scribbler should connect the profile to actual writing.

Example:
```
Character: Sarah
  Appears in 17 passages
  4 chapters
  3 major emotional beats
  Connected to 5 characters
```

Clicking any item opens Reader/Editor at the relevant passage.

The writer can therefore compare:
- What I say Sarah is
- against
- How Sarah actually behaves in the manuscript

That is exactly the kind of intelligence Scribbler should provide.

---

## 13. Character Arc System

Each important character should have an arc workspace.

Possible structure:
```
Beginning → Pressure → Change → End
```
- What does the character believe?
- What challenges that belief?
- What happens?
- What has changed?

The system should also support:
- emotional state
- key decisions
- turning points
- relationships
- unresolved threads
- important scenes

Existing emotional-arc analysis should feed into this rather than being duplicated.

---

## 14. Relationships

Relationships become a first-class development tool.

Each relationship can contain:
- characters involved
- nature of relationship
- history
- current state
- conflicts
- dependencies
- key scenes
- emotional changes

Existing relationship-map functionality should become a useful interface rather than merely a visualisation.

The writer should be able to click: **Sarah → David**

and immediately see:
- relationship notes
- relevant passages
- emotional changes
- analysis
- key events

---

## 15. Places

Places receive their own section.

A place profile could contain:
- name, location, description, atmosphere, sensory details, history, significance, associated characters, associated themes, scenes

And importantly: **Where does this place actually appear?**

The writer can jump directly to passages. This helps continuity as well as creative development.

---

## 16. Themes

Themes become another first-class development object.

A theme could contain:
- theme name, writer's definition, related ideas, characters, places, scenes, symbols, motifs, supporting passages, contradictory passages, analysis findings

The system should help the writer discover:

> "I thought this was a theme, but am I actually writing it?"

That is far more useful than simply counting theme mentions.

---

## 17. Story / Narrative Arcs

V12 should support story arcs independently from character arcs.

Possible arc types:
- main plot
- subplot
- relationship arc
- mystery
- thematic arc
- emotional arc

Each arc contains:
- title, purpose, beginning, turning points, major beats, climax, resolution, related chapters, related characters, related themes

The writer should be able to map an arc without having to construct a complicated plotting database.

---

## 18. Timeline and Continuity

A lightweight timeline becomes extremely useful once characters, places and manuscript structure exist.

The timeline can surface:
- dates
- time markers
- chapter events
- character ages
- locations
- sequence problems

Existing time_markers and continuity functionality should be reused.

The goal is not a cinematic timeline editor. It is:

> "Does my story make sense when I put it in order?"

---

## 19. Analysis Suite — V12 Expansion

The existing analysis suite remains. V12 does not throw it away. Instead, analysis becomes integrated into writing.

Existing capabilities such as:
- memory analysis
- emotional beats
- relationship mapping
- emotional arc comparison
- continuity
- voice
- themes
- sensory analysis
- other existing analysis tools

should become available from:
- Analysis section
- manuscript
- selected passage
- character
- theme
- place
- arc

---

## 20. Contextual Analysis

If the writer selects a passage containing a character, the analysis panel can offer: **Analyse character**

If they select a scene: **Analyse scene**

If they select a chapter: **Analyse chapter**

If they select the manuscript: **Analyse manuscript**

The same underlying analysis engines should operate at different scopes.

This is an important way of getting much more value from the existing system without creating 50 new tools.

---

## 21. Analysis Findings as First-Class Objects

Analysis findings should remain distinct from author-approved tags. But they should become easier to manage.

Every finding should contain:
- source
- analysis tool
- category
- observation
- evidence
- location
- why it matters
- suggested improvement
- status

Possible status:
- Open
- Dealt with
- Dismissed

The writer remains in control.

---

## 22. The "Things to Look At" Panel

The application should maintain a concise list of useful observations.

For example:
```
Things worth looking at

Chapter 4 — Potentially defensive dialogue in Sarah's confrontation.
Chapter 7 — Repeated references to the same sensory motif.
Chapter 9 — Possible continuity conflict involving the timeline.
Chapter 11 — Strong emotional beat worth preserving.
```

This is much more useful than making the writer read an enormous AI report.

---

## 23. Search Everything

V11's unified search becomes even more important.

V12 Search searches:
- manuscript text
- brain dumps
- tags
- characters
- places
- themes
- arcs
- relationships
- analysis observations
- analysis suggestions
- notes

A search for "kitchen" might return:
- Chapter 3 passage
- Brain dump
- Place: Kitchen
- Character: Sarah
- Theme: memory
- Analysis observation

Everything should lead back to the relevant context.

---

## 24. The Knowledge Model

V12 should establish relationships between existing concepts.

Conceptually:
```
MANUSCRIPT
  contains: CHAPTERS
    contain: PASSAGES / SCENES
      which can relate to:
        CHARACTERS, PLACES, THEMES, ARCS, RELATIONSHIPS, TIME, ANALYSIS, TAGS
```

This is not a reason to build a massive graph database. The application can continue using the existing SQLite architecture. The important thing is that the UI understands these relationships.

---

## 25. Important Architectural Rule

Do not create a separate database system for every new feature. Extend the existing model carefully.

The architecture should remain approximately:
```
Stored source material → Project entities → Analysis → Interpretation → UI
```

- The manuscript remains authoritative.
- Analysis remains interpretation.
- Writer-entered information remains authoritative where explicitly saved.
- AI suggestions remain suggestions.

---

## 26. Editor ↔ Development Linking

This is where V12 can become genuinely special.

While writing a passage, the writer should be able to see:
```
Characters in this passage: Sarah, David
Places: Kitchen
Themes: Memory, Family
Arc: Sarah's acceptance arc
Analysis: 2 things worth looking at
```

Clicking any of these opens the corresponding development panel. The writer never has to leave the manuscript just to understand its context.

---

## 27. Development → Manuscript Linking

The reverse must work too.

- From a character profile: Show passages
- From a theme: Show passages
- From a place: Show scenes
- From an arc: Show chapters
- From an analysis issue: Open passage

Everything eventually leads back to the writing.

---

## 28. Brain Dump → Development

The Inbox remains the messy zone. But V12 allows a brain dump to become useful development material.

For example, a dump contains:
> "Sarah probably hates hospitals because of what happened when…"

Scribbler may identify:
- Sarah
- hospital
- trauma
- possible character motivation
- possible theme

The writer can then deliberately save those as:
- Character note
- Theme note
- Brain dump tag

Nothing should be silently promoted into canon.

---

## 29. Canon vs Possibility

This becomes increasingly important in a full writing application.

The system should distinguish:
- **Author confirmed** — Something the writer has deliberately established.
- **Suggested** — AI inference or automatic detection.
- **Possible** — An idea in the writer's notes.
- **Contradiction** — Something potentially inconsistent.

This prevents the AI from accidentally becoming the author.

---

## 30. Scenes

V12 should introduce lightweight scene support.

A chapter can contain scenes. Each scene can have:
- title, summary, characters, place, time, purpose, emotional beat, related arc, manuscript passage

The writer should be able to work without scenes if they don't want them. Scenes are an organisational aid, not a mandatory methodology.

---

## 31. Writing Modes

Provide three useful working modes:
- **Write** — Maximum writing space.
- **Develop** — Writing + relevant story information.
- **Analyse** — Writing + findings/evidence.

This allows the same manuscript to support different cognitive modes without forcing the writer to jump between unrelated screens.

---

## 32. Focus Mode

A genuine distraction-free writing mode should be available.

Hide: sidebar, unnecessary metadata, analysis, development tools.

Keep: manuscript, editor, essential navigation, word count if desired.

Exit easily.

---

## 33. Writer-Friendly Word Count

Word count should be available but not treated as a productivity score.

Show useful contextual information: current selection, current scene, current chapter, manuscript.

Avoid: streaks, achievement systems, guilt-inducing goals.

Optional writing targets may be added later, but they are not core V12.

---

## 34. Version History / Safety

A real writing application needs stronger protection against accidental damage.

At minimum:
- automatic save
- safe writes
- backup before destructive operations
- manuscript history
- restore previous version where practical

Existing analysis history must remain separate from manuscript history. Do not allow an analysis operation to overwrite source material.

---

## 35. Import / Export

Support straightforward manuscript workflows.

**Import:** Markdown, TXT, common existing formats where current infrastructure supports them.

**Export:** Markdown, TXT, HTML, PDF where practical, DOCX if a suitable existing dependency/workflow is acceptable.

The core project should remain portable. The writer must never feel locked into Scribbler.

---

## 36. Projects

V12 should eventually treat the work as a project, not merely a folder of files.

A project contains:
- manuscript, brain dumps, characters, places, themes, arcs, relationships, analysis, settings, backups

This makes the architecture much closer to a real writing application.

However: Do not build cloud accounts, online collaboration or synchronisation into V12. Local-first is an advantage.

---

## 37. Project Open / New Project

Provide: New Project, Open Project, Recent Projects.

A project should have a clear folder structure on disk. The user should always be able to understand where their work physically lives.

---

## 38. Autosave and Recovery

Writing software cannot afford fragile saving.

Implement:
- frequent autosave
- safe temporary write
- recovery after crash
- backup/version protection
- clear saved/unsaved status

The writer should never wonder: "Did it save?"

---

## 39. AI Cost / Performance Principle

Do not run expensive AI analysis continuously. Use tiers:

1. **Instant** — Local/simple: spelling, basic grammar, sentence length, repetition, simple style checks.
2. **Quick** — Existing lightweight analysis.
3. **Deep** — LLM-powered analysis.
4. **Project** — Large manuscript analysis.

The UI should clearly communicate what is happening.

---

## 40. Analysis Should Never Block Writing

If a deep analysis is running, the editor remains usable.

Show: "Analysing Chapter 4…"

rather than freezing the application. Results appear when ready.

---

## 41. Contextual Tool Dock

A compact right-hand panel could contain:

Tools: Check, Analyse, Characters, Themes, Places, Arcs, Notes.

The panel should change according to what the writer is doing. This avoids putting every possible feature permanently on screen.

---

## 42. Selection-Based Tools

Selecting text should expose useful actions:
- Check spelling
- Check grammar
- Analyse
- Find similar
- Add note
- Tag
- Link to character
- Link to theme

This creates a powerful connection between writing and organisation.

---

## 43. Notes

V12 should provide simple contextual notes.

A note can attach to: passage, paragraph, chapter, character, place, theme, arc.

Example: "Need to explain why David already knows this."

The note is for the writer, not an AI-generated task-management system.

---

## 44. Analysis + Notes

An AI finding should optionally be turned into a writer note.

Example:
```
Analysis: Possible continuity issue.
Writer: Keep as note → "Check whether Sarah was already in Bogotá here."
```

This is a useful bridge between AI interpretation and human work.

---

## 45. Spelling / Grammar / AI Analysis Must Be Separate

Do not create one giant "AI writing assistant". They have different purposes:

- **Spell checker** — Correctness.
- **Grammar checker** — Construction.
- **Style checker** — Craft.
- **Story analysis** — Meaning.
- **Character analysis** — Psychology/development.
- **Structural analysis** — Story.

This separation makes the system much easier to understand.

---

## 46. UI Principle — Big, Clear, Friendly

V12 should feel significantly more approachable than a conventional writing application.

**Use:**
- large clear section headings
- generous spacing
- obvious primary buttons
- simple language
- restrained icons
- readable panels
- minimal nested menus
- dark mode by default
- optional light mode

**Avoid:**
- dense spreadsheets
- tiny controls
- enormous settings panels
- jargon
- feature clutter

The application should look capable without looking complicated.

---

## 47. The Sidebar Should Show Where You Are

The sidebar should make the mental model obvious.

Example:
```
WRITE
  Home, Inbox, Manuscript, Reader

DEVELOP
  Characters, Places, Themes, Arcs, Relationships

UNDERSTAND
  Analysis, Search, Timeline, Compare

OUTPUT
  Export, Project
```

This is much easier to understand than a flat list of fifteen unrelated tools.

---

## 48. V12 Should Not Become a Productivity App

Explicitly reject:
- writing streaks
- achievement badges
- leaderboards
- productivity scores
- excessive word-count statistics
- daily pressure
- motivational nonsense

The purpose is to help the writer create. Not to make them feel guilty about not creating.

---

## 49. V12 Should Not Become an Autonomous AI Author

Reject:
- automatic chapter rewriting
- automatic plot changes
- automatic character decisions
- automatic canon changes
- automatic deletion
- AI silently modifying manuscript text

The system can say:
- "I noticed this."
- "You might consider this."
- "This appears inconsistent."
- "Here are three possibilities."

But: the writer decides.

---

## 50. Phased Implementation

This is too large for a single undifferentiated build. V12 should be delivered in controlled phases.

### PHASE 1 — WRITING FOUNDATION

Create the genuine writing environment:
- project structure
- manuscript tree
- chapter management
- editor
- basic formatting
- autosave
- word count
- find/replace
- focus mode
- Reader ↔ Editor connection

**Definition of success:** The user can actually write a chapter comfortably.

### PHASE 2 — WRITING QUALITY

Add:
- spelling
- grammar
- sentence length
- repetition
- basic style checks
- contextual highlighting
- issue panel
- ignore/dismiss

**Definition of success:** The user can improve prose without leaving the editor.

### PHASE 3 — CHARACTERS

Add:
- character section
- profiles
- notes
- evidence
- character links
- relationships
- existing character analysis integration

**Definition of success:** A character profile shows both what the writer says about the character and where that character actually appears.

### PHASE 4 — PLACES / THEMES

Add:
- place profiles
- theme profiles
- evidence
- links to manuscript
- analysis integration

**Definition of success:** The writer can investigate an idea, place or theme and immediately reach the relevant writing.

### PHASE 5 — ARCS / STRUCTURE

Add:
- character arcs
- story arcs
- scenes
- beats
- timeline
- continuity
- existing emotional-arc tools

**Definition of success:** The writer can understand the shape of the story without constructing a complicated planning system.

### PHASE 6 — INTEGRATED ANALYSIS

Bring existing analysis tools into the editor and development areas.

Add:
- passage analysis
- chapter analysis
- character analysis
- thematic analysis
- structural analysis
- Things Worth Looking At
- evidence
- Dealt With / Dismissed

**Definition of success:** Analysis becomes part of the writing process rather than a separate destination.

### PHASE 7 — UNIFIED SEARCH / MEMORY

Expand V11 search across:
- manuscript, Inbox, characters, places, themes, arcs, relationships, notes, analysis

**Definition of success:** The writer can remember something vaguely and find it.

### PHASE 8 — DEEP INTEGRATION

Connect:
- passage ↔ character
- passage ↔ place
- passage ↔ theme
- passage ↔ arc
- passage ↔ analysis
- passage ↔ note
- brain dump ↔ development object
- analysis ↔ note
- development object ↔ manuscript

**Definition of success:** The application behaves like one coherent system rather than a collection of modules.

### PHASE 9 — UI / UX POLISH

Only after the functionality works:
- dark default
- icon
- typography
- spacing
- navigation
- empty states
- contextual panels
- keyboard shortcuts
- transitions
- focus mode
- responsive layouts

### PHASE 10 — SAFETY / RELEASE

- autosave testing
- recovery testing
- backup testing
- import/export testing
- project corruption testing
- performance testing
- large manuscript testing
- full regression suite
- Windows packaging
- installer
- final user journey testing

---

## 51. Testing Strategy

V12 has significantly more moving parts, so testing must change.

Every feature needs:
- **Unit test** — Does the underlying operation work?
- **Integration test** — Does it interact correctly with related systems?
- **UI/functional test** — Can the user actually perform the operation?
- **Regression test** — Did anything else break?

---

## 52. Critical V12 Test Journeys

**Journey 1 — Write:** Create project → create chapter → write → save → close → reopen → text remains.

**Journey 2 — Check:** Write poor sentence → checker identifies it → writer dismisses/changes → save.

**Journey 3 — Character:** Create character → write character into manuscript → character appears in evidence → open passage from profile.

**Journey 4 — Theme:** Create theme → associate passages → open theme → navigate to evidence.

**Journey 5 — Arc:** Create arc → connect scenes → compare intended arc with actual manuscript.

**Journey 6 — Brain dump:** Dump idea → automatic suggestions → manually correct → save → develop into character/theme/note → retain original dump.

**Journey 7 — Analysis:** Analyse passage → finding appears → open evidence → create note → revise → mark finding dealt with.

**Journey 8 — Search:** Search a remembered concept → results from manuscript/brain dumps/entities/analysis → open relevant passage.

**Journey 9 — Recovery:** Write → crash/close unexpectedly → reopen → recover latest version.

These journeys matter more than simply accumulating hundreds of isolated tests.

---

## 53. Performance Target

The app should feel immediate for normal writing. Basic operations should not require AI.

Opening: project, manuscript, chapter, character, place, theme — should be fast.

Heavy analysis can take time, but should run without freezing the application.

---

## 54. Data Ownership

Maintain a strict distinction.

**Writer-owned:**
- manuscript
- character information explicitly saved
- place information explicitly saved
- themes explicitly saved
- arcs
- notes
- manual tags

**Machine-derived:**
- automatic tags
- detected entities
- analysis
- suggestions
- possible continuity issues

The machine must not silently promote derived information into authoritative project truth.

---

## 55. What Happens to V11?

V11 is not thrown away. V11 becomes the foundation.

**Keep:**
- Inbox, intelligent tagging, editable tags, Reader, unified search, analysis, analysis history, relationship mapping, emotional arc comparison, exports, local-first architecture, dark theme, app identity.

**Evolve:**
- Reader → Reader + Editor
- Tags → navigation/context
- Analysis → integrated writing intelligence
- Characters → full development objects
- Places → development objects
- Themes → development objects
- Arcs → structured development objects
- Search → project-wide memory
- Home → Writer's Desk

---

## 56. What We Must Not Do

Even though V12 is ambitious, avoid building:
- full Scrivener clone
- full Microsoft Word clone
- professional publishing software
- desktop layout software
- collaborative Google Docs system
- cloud platform
- social network
- AI chatbot everywhere
- complicated project-management suite
- massive graph database
- vector/RAG infrastructure unless later proven necessary
- dozens of new AI analysis engines
- automatic rewriting engine
- automatic story generator

V12 is large because it connects many useful capabilities. It should not become large because every possible writing feature was added.

---

## 57. The V12 Architectural Test

Every proposed feature should answer three questions:

1. Does it help me write? If no, question it.
2. Does it help me understand or organise what I have written? If no, question it.
3. Does it connect naturally to something that already exists? If no, it needs a very good reason to exist.

---

## 58. The Ultimate V12 Experience

Imagine opening Scribbler.

The application says: "Welcome back. Your last chapter is open."

You write. A sentence is too long. Scribbler quietly highlights it.

You click it.
> Long sentence. This sentence contains several clauses and may be easier to follow if divided.
> [Ignore] [Review]

You continue. You mention Sarah. The contextual panel shows: Sarah — Her profile is one click away.

You click Sarah. You see: motivation, relationships, current arc, notes, relevant chapters, recent emotional beats.

You return to writing.

Later you wonder: "Where did I mention the hospital?"

Search: hospital

Scribbler finds:
- Chapter 2
- Chapter 8
- Brain dump from six months ago
- Sarah's character evidence
- Hospital place notes
- an old analysis observation

You open the old brain dump. It contains an idea you had forgotten. You promote the relevant material into development.

Then Scribbler shows:
> Possible connection: Sarah's current character motivation may relate to this earlier note.

You decide whether it does.

Later you run chapter analysis. Scribbler finds three things worth looking at. You fix two. You dismiss one. You continue writing.

**That is V12.**

---

## 59. V12 Definition of Done

V12 is successful when the writer can genuinely use it as their primary writing workspace without constantly having to leave the application for:

- basic writing
- manuscript organisation
- character development
- theme development
- place development
- arc development
- finding material
- checking prose
- analysing writing
- tracking issues
- understanding relationships
- remembering old ideas

And, critically:

> The writer should never feel that the application has become more complicated than the problem it is solving.

The application should feel like: **A writing desk + a filing cabinet + a corkboard + an editor + a second brain.**

Not: A database with a text box attached.

---

## 60. Final V12 Principle

V11's ambition was: **Make Scribbler remember for the writer.**

V12's ambition is: **Give the writer somewhere to actually write — and make the intelligence of Scribbler available everywhere that writing happens.**

The manuscript is the centre. Everything else exists to help the writer create, understand, organise and improve it.

**Write. Develop. Understand. Improve. Then write again.**
