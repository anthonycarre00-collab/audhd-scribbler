# The Audhd Scribbler

A writer's tool suite for an AUDHD brain. Built for a hybrid memoir + research book (60–80k words), but works for any long-form writing project.

**Low-shame. At-a-glance. No rigid methods. No console needed.**

---

## Quick Start (No Console Needed)

### Step 1: Download

1. Go to your private repo on GitHub
2. Click the green **"Code"** button → **"Download ZIP"**
3. Extract the ZIP file somewhere on your computer (Desktop, Documents, wherever you like)

### Step 2: Install (one time only)

Double-click the installer for your system:

- **Windows:** Double-click `INSTALL-Windows.bat`
- **Mac:** Double-click `INSTALL-Mac.command`
  - *First time on Mac:* Right-click → "Open" → "Open Anyway" (Mac security thing)

The installer takes 2-3 minutes. It installs Python dependencies and sets up the folders. When it says "INSTALLATION COMPLETE", you're done.

**Prerequisite:** You need Python 3.8+ installed.
- Windows: Download from [python.org](https://www.python.org/downloads/) — **check the box "Add Python to PATH"** during install
- Mac: `brew install python3` (or download from python.org)

### Step 3: Use It

Double-click to open the menu:

- **Windows:** Double-click `SCRIBBLER-Windows.bat`
- **Mac:** Double-click `SCRIBBLER-Mac.command`

A numbered menu appears. Pick a number. That's it.

```
  THE AUDHD SCRIBBLER
  Your memoir's calm companion

  What would you like to do?

    1.  Tag all my dumps  (organize raw text files)
    2.  Open the dashboard  (see everything at a glance)
    3.  What should I do next?  (3 suggested actions)
    4.  Analyze a chapter  (run the full analysis suite)
    5.  Analyze ALL chapters  (batch analysis)
    6.  Show project stats  (word count, file count)
    7.  Export a file  (to Word, markdown, or plain text)
    8.  Market research  (find comparable titles)
    9.  Find links between files  (what connects to what)
    10. Open the raw-dumps folder  (drop new files here)
    11. Quit
```

### Your Daily Workflow

1. Double-click `SCRIBBLER-Windows.bat` (or `.command` on Mac)
2. Pick **10** to open the `raw-dumps` folder
3. Drop your text files in there (`.txt` or `.md`)
4. Back in the menu, pick **1** to tag them
5. Pick **2** to see your dashboard
6. Pick **3** if you don't know what to do next

That's the whole thing. No console. No commands to remember.

---

## What it does

### Auto-Labeller (Menu option 1)

Reads messy text dumps and adds YAML frontmatter tags:
- **Characters** (via spaCy NER + family-role detection)
- **Places** (via NER + domestic-place lexicon)
- **Era** (childhood / adolescence / twenties / now)
- **Themes** (AUDHD-specific lexicon: diagnosis, masking, sensory, meltdown, burnout, etc.)
- **Voice** (narrator / character / research / lyric)
- **Sensory details** (sight, sound, smell, taste, touch, proprioception, interoception)
- **Emotional register** (tender, enraged, numb, funny, grief, anxious, defensive)
- **Beats** (scene-level units of change — LLM-assisted)
- **Summary** (3-line plain-English summary — LLM-assisted)

**Never alters your prose. Only adds metadata.**

### Analysis Suite (Menu options 4 & 5)

Six analyzers for final-draft chapters:

| Tool | What it does |
|------|-------------|
| **Craft** | Sentence rhythm, paragraph distribution, repetition, readability, sensory density, dialogue ratio, weak words, filter words, alliteration |
| **Voice & Tense** | Tense distribution per sentence, tense shifts, first-person pronoun density, narrator distance (experiencing self vs. narrating self), grammar patterns |
| **Characters** | Character presence timeline, agency arcs (agentive vs. passive), voice fingerprint (function words, punctuation, lexical diversity) |
| **Continuity** | Timeline reconstruction, flashback detection, setting consistency, anachronism watchlist (80s–2025), research-claim extraction |
| **Themes** | Theme density per chapter, emotional valence arc, Vonnegut's six shapes (descriptive, not prescriptive), motif detection |
| **Editor** | Strengths inventory FIRST, then memoir-specific patterns (distant narrator, defensive register, missing stakes, essay-vs-memoir drift) using the low-shame feedback grammar |

**Every observation follows the grammar:**
> I noticed [observation]. It had [effect on reader]. Would you like to [option A], [option B], or keep as-is?

Never says "fix this." Always offers 2–3 optional paths. One is always "this may be intentional."

### Dashboard (Menu option 2)

Generates an interactive HTML file (opens in your browser, no server needed):
- **Overview** — status badges, file counts, resting chapters
- **Chapter grid** — all chapters with status, era, themes, mood at a glance
- **Characters** — who appears where, how often
- **Themes** — frequency bars
- **Relationship Map** — force-directed graph of files ↔ characters ↔ themes
- **Activity** — recent actions log

### Market Research (Menu option 8)

Comp-title research against a curated neurodiversity-memoir seed list (Devon Price, Sarah Kurchak, Esmé Weijun Wang, Maggie Nelson, Leslie Jamison, etc.). Suggests 2–3 comps with match reasons. Flags comps that are too famous, too old, or too obscure. Recommends BISAC category and shelf positioning.

### Next Action (Menu option 3)

Addresses decision paralysis. Returns 3 concrete, low-friction things you could do right now.

### Export (Menu option 7)

Export any file to:
- Word document (.docx)
- Markdown (.md, with frontmatter)
- Plain text (.txt, stripped of metadata)

---

## Design Principles

1. **Zero decisions before writing** — opening the menu gives you 3 suggested next actions
2. **Always-visible state** — nothing hidden in folders; the dashboard shows everything
3. **One screen, one decision** — each view answers one question
4. **Describe, don't prescribe** — no "should," "must," "fix," "problem," "overdue"
5. **Pick-one-of-three** — decision paralysis replaced with concrete options
6. **Externalise working memory** — the tool remembers what you don't have to
7. **Growth-metaphor status** — seedling → growing → shaping → polishing → resting (not "Draft 1/2/3")
8. **Calm sensory defaults** — muted blue palette, no animations, no autoplay
9. **One tool, everything in-app** — no context-switching between apps
10. **3-line plain-English summaries** on every output

---

## Status Taxonomy

| Status | Meaning |
|--------|---------|
| **seedling** | Raw material, just dropped in |
| **growing** | Being developed, tags applied |
| **shaping** | Structural work happening |
| **polishing** | Near-final, ready for analysis |
| **resting** | Not touched in 7+ days (a valid status, not a nudge) |

---

## Folder Structure

```
audhd-scribbler/
├── INSTALL-Windows.bat    ← Double-click to install (Windows)
├── INSTALL-Mac.command    ← Double-click to install (Mac)
├── SCRIBBLER-Windows.bat  ← Double-click to use (Windows)
├── SCRIBBLER-Mac.command  ← Double-click to use (Mac)
├── raw-dumps/             ← Drop text files here
├── triage/                ← Tagged, awaiting confirmation
├── chapters/              ← Chapter drafts
├── characters/            ← Character files
├── places/                ← Place files
├── themes/                ← Theme files
├── research/              ← Research-braid sources
├── comps/                 ← Comp-title research
├── drafts/                ← Past first-draft
├── final/                 ← Polished chapters
├── archive/               ← Older material (never deleted)
├── data/                  ← Database + reports (private)
└── scribbler/             ← The tool itself (don't touch)
```

---

## LLM Integration (Optional)

The tagger uses Z.ai (GLM-4-Plus) for LLM-assisted tagging if available. Without it, the tagger still works fully — just less smart on beats and summaries.

To enable LLM-assisted tagging:
1. Install Node.js from [nodejs.org](https://nodejs.org/)
2. Open a terminal once and run: `npm install -g z-ai-web-dev-sdk`
3. Or set an environment variable: `SCRIBBLER_LLM_API_KEY=your-key`

This is optional. Everything works without it.

---

## Privacy

- Your text files stay on your machine
- The SQLite database is local only
- If you use the LLM, text snippets are sent to Z.ai for processing
- Without the LLM, nothing leaves your machine
- The `.gitignore` excludes all your writing from git

---

## Backing Up to GitHub

If you want to push your work back to GitHub (optional):

1. Open GitHub Desktop (download from [desktop.github.com](https://desktop.github.com/))
2. Add the `audhd-scribbler` folder as a repository
3. Click "Commit" and "Push"

Or, if you're comfortable with the console:
```bash
cd audhd-scribbler
git add .
git commit -m "new drafts"
git push
```

Your actual writing files are gitignored by default — they won't be pushed unless you edit `.gitignore`.

---

## Troubleshooting

**"Python is not installed"**
- Install Python 3.8+ from [python.org](https://www.python.org/downloads/)
- On Windows, check "Add Python to PATH" during install
- Re-run the installer

**Mac: "Cannot be opened because it is from an unidentified developer"**
- Right-click the `.command` file → "Open" → "Open Anyway"
- This is a one-time Mac security thing

**The installer failed halfway**
- Re-run `INSTALL-Windows.bat` or `INSTALL-Mac.command`
- It'll pick up where it left off

**"No text files found"**
- Make sure your files are `.txt` or `.md` (not `.docx` or `.rtf`)
- Make sure they're in the `raw-dumps` folder
- Use menu option 10 to open that folder

---

## For You

This tool was built for one specific AUDHD writer. It is not generic. Every design decision — the blue palette, the growth-metaphor statuses, the "resting" reframe of stale drafts, the strengths-first feedback, the pick-one-of-three next actions — exists because that's what your brain needs.

The tool is a calm companion, never a coach. It describes, never prescribes. It offers choices, never demands.

Happy scribbling.
