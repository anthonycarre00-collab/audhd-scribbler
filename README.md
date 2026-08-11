# The Audhd Scribbler

A writer's tool suite for an AUDHD brain. Built for a hybrid memoir + research book (60–80k words), but works for any long-form writing project.

**Low-shame. At-a-glance. No rigid methods.**

---

## Quick Start

```bash
# 1. Install (one command)
./install.sh

# 2. Drop text files into raw-dumps/
#    (brain dumps, voice memos, freewrites — any .txt or .md file)

# 3. Tag them
./scribbler label-all

# 4. See your project at a glance
./scribbler dashboard

# 5. Get 3 things you could do next
./scribbler next
```

That's it. The tool is private — your text stays on your machine.

---

## What it does

### 1. Auto-Labeller (`label`, `label-all`)

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

### 2. Analysis Suite (`analyze`, `analyze-all`)

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

### 3. Dashboard (`dashboard`)

Generates an interactive HTML file (opens in your browser, no server needed):
- **Overview** — status badges, file counts, resting chapters
- **Chapter grid** — all chapters with status, era, themes, mood at a glance
- **Characters** — who appears where, how often
- **Themes** — frequency bars
- **Relationship Map** — force-directed graph of files ↔ characters ↔ themes
- **Activity** — recent actions log

### 4. Market Research (`market`)

Comp-title research against a curated neurodiversity-memoir seed list (Devon Price, Sarah Kurchak, Esmé Weijun Wang, Maggie Nelson, Leslie Jamison, etc.). Suggests 2–3 comps with match reasons. Flags comps that are too famous, too old, or too obscure. Recommends BISAC category and shelf positioning.

### 5. Next Action (`next`)

Addresses decision paralysis. Returns 3 concrete, low-friction things you could do right now.

### 6. Export (`export`)

Export any file to:
- Markdown (with frontmatter)
- Plain text (stripped of metadata)
- DOCX (Word document)

---

## Design Principles

1. **Zero decisions before writing** — opening the tool gives you 3 suggested next actions
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
├── raw-dumps/     ← Drop text here
├── triage/        ← Tagged, awaiting confirmation
├── chapters/      ← Chapter drafts
├── characters/    ← Character files
├── places/        ← Place files
├── themes/        ← Theme files
├── research/      ← Research-braid sources
├── comps/         ← Comp-title research
├── drafts/        ← Past first-draft
├── final/         ← Polished chapters
├── archive/       ← Older material (never deleted)
├── data/          ← SQLite DB + reports (gitignored)
└── scribbler/     ← The tool itself
```

---

## LLM Integration

The tagger uses Z.ai (GLM-4-Plus) for LLM-assisted tagging if available:
1. **`z-ai` CLI** (if installed) — works out of the box
2. **`openai` Python package** with `SCRIBBLER_LLM_API_KEY` env var — for local install
3. **Rule-based fallback** — if no LLM available, still fully functional (just less smart)

To enable LLM-assisted tagging locally:
```bash
# Option A: Install z-ai CLI
npm install -g z-ai-web-dev-sdk

# Option B: Set API key
export SCRIBBLER_LLM_API_KEY="your-z-ai-api-key"
```

---

## Privacy

- Your text files stay on your machine
- The SQLite database is local only
- If you use the LLM, text snippets are sent to Z.ai for processing
- Without the LLM, nothing leaves your machine
- The `.gitignore` excludes all your writing from git

---

## Push to GitHub

```bash
cd audhd-scribbler
git add .
git commit -m "Initial setup"
git remote add origin git@github.com:yourusername/audhd-scribbler.git
git push -u origin main
```

The `.gitignore` ensures your actual writing (in `raw-dumps/`, `chapters/`, etc.) is NOT pushed — only the tool code and folder structure.

---

## Commands Reference

| Command | What it does |
|---------|-------------|
| `scribbler init` | Create folder structure |
| `scribbler label <file>` | Tag a single file |
| `scribbler label-all [folder]` | Tag all files in a folder |
| `scribbler analyze <file>` | Run full analysis suite |
| `scribbler analyze-all` | Analyze all chapters |
| `scribbler dashboard` | Generate and open dashboard |
| `scribbler market [-d "desc"]` | Comp-title research |
| `scribbler next` | Get 3 suggested next actions |
| `scribbler links <file>` | Show connected files |
| `scribbler stats` | Project statistics |
| `scribbler export <file> [-f md\|txt\|docx]` | Export a file |

---

## Tech Stack

- **Python 3.8+** (CLI)
- **spaCy** (NLP — NER, parsing)
- **SQLite** (local index)
- **Z.ai GLM-4-Plus** (LLM for assisted tagging — optional)
- **Vanilla HTML/CSS/JS** (dashboard — no build step, no server)

---

## For You

This tool was built for one specific AUDHD writer. It is not generic. Every design decision — the blue palette, the growth-metaphor statuses, the "resting" reframe of stale drafts, the strengths-first feedback, the pick-one-of-three next actions — exists because that's what your brain needs.

The tool is a calm companion, never a coach. It describes, never prescribes. It offers choices, never demands.

Happy scribbling.
