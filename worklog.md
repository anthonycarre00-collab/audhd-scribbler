# The Audhd Scribbler — Worklog

---
Task ID: build-1
Agent: Super Z (main)
Task: Build the complete Audhd Scribbler tool suite based on the planning document and user answers to open questions.

Work Log:
- Read LLM skill to understand Z.ai API integration (z-ai CLI available, OpenAI-compatible endpoint)
- Created project structure at /home/z/my-project/audhd-scribbler/ with 11 writing folders + scribbler/ package
- Initialized git repository
- Wrote scribbler/config.py — all configuration: folders, eras (80s-2025), statuses (seedling→resting), sensory lexicon (with interoception/proprioception), AUDHD theme lexicon (12 themes), weak words, filter words, era anachronism watchlist (80s-2025), comp-title seed list (12 books), low-shame word swaps, calm blue palette
- Wrote scribbler/llm.py — LLM interface with 3-tier fallback: z-ai CLI → openai package → rule-based
- Wrote scribbler/db.py — SQLite database with files, analysis_results, characters, places, activity_log tables; fixed nested-connection lock issue by inlining activity logging
- Wrote scribbler/feedback.py — low-shame feedback engine: make_observation(), strengths_first(), plain_summary(), format_flag()
- Wrote scribbler/tagger.py — auto-labeller with: character detection (spaCy NER + family roles), place detection, era detection, theme detection (AUDHD lexicon), voice detection, sensory detection, emotional register, anachronism detection, LLM-assisted beats/themes/summary, YAML frontmatter writer, 4-stage pipeline (triage→link→cluster→orphan)
- Wrote scribbler/analyzers/craft.py — line-level craft: sentence rhythm (CV, monotony runs), paragraph distribution, repetition (Dunning-style + 3-strike rule), readability (Flesch/FKGL/Gunning Fog as band), sensory density, dialogue ratio, weak words, filter words, alliteration
- Wrote scribbler/analyzers/voice_tense.py — voice & tense tracker (user answer #8): tense distribution per sentence, tense shifts, first-person pronoun density, narrator distance (experiencing self vs narrating self per Gornick), grammar patterns (declarative/interrogative/imperative/conditional/fragment)
- Wrote scribbler/analyzers/characters.py — character presence timeline, agency arcs (agentive vs passive verbs), voice fingerprint (function words, punctuation, MATTR lexical diversity)
- Wrote scribbler/analyzers/continuity.py — temporal expression extraction, timeline building, flashback detection, setting extraction, anachronism flags (80s-2025), research claim extraction with citation checking
- Wrote scribbler/analyzers/themes.py — theme density (AUDHD lexicon), emotional valence arc per sentence, Vonnegut's six shapes classification (descriptive not prescriptive), motif detection
- Wrote scribbler/analyzers/editor.py — strengths inventory FIRST, then memoir-specific patterns (distant narrator, defensive register, missing stakes, essay-vs-memoir drift, summary-where-scene)
- Wrote scribbler/analyzers/market.py — comp-title finder against 12-book seed list, semantic match scoring, positioning advice (BISAC, shelf), market gap detection (AUDHD-specific scarcity)
- Wrote scribbler/dashboard/generator.py — interactive HTML dashboard with: overview (status badges, resting chapters), chapter grid, characters, themes (bar chart), relationship map (force-directed SVG graph), activity log; calm blue palette, no animations
- Wrote scribbler/export.py — export to markdown, plain text, DOCX (python-docx), and analysis report (markdown)
- Wrote scribbler/cli.py — full CLI with: init, label, label-all, analyze, analyze-all, dashboard, market, next, links, stats, export
- Wrote install.sh — one-command installer (creates venv, installs deps, downloads spaCy model, inits project)
- Wrote requirements.txt, pyproject.toml, .gitignore, README.md
- Fixed DB lock issue (nested connections in upsert_file/save_analysis)
- Fixed market analyzer name collision with CLI command
- Fixed dashboard --no-open flag
- Fixed next command name
- Tested end-to-end: init → label sample dump → analyze → dashboard → stats → next → market → export

Stage Summary:
- Complete working tool suite at /home/z/my-project/audhd-scribbler/
- Entry point: ./scribbler.sh (or python -m scribbler.cli)
- 11 commands working: init, label, label-all, analyze, analyze-all, dashboard, market, next, links, stats, export
- 6 analyzers: craft, voice_tense, characters, continuity, themes, editor
- Sample dump successfully tagged (detected: Mom, kitchen, masking, identity, tender_remembrance)
- Sample analysis produced low-shame observations with 2-3 optional paths each
- Dashboard generates interactive HTML with relationship map
- Export to DOCX works
- LLM integration via z-ai CLI works (with rule-based fallback)
- Calm blue palette per user preference (not green)
- Era watchlist covers 80s-2025 per user answer
- Voice & tense analyzer per user answer #8 (first-person memoir, tense/grammar tracking)
- Low-shame feedback grammar throughout: "I noticed X. It had effect Y. Would you like A, B, or keep as-is?"
- Growth-metaphor status: seedling → growing → shaping → polishing → resting
- Ready for git push to private GitHub repo
