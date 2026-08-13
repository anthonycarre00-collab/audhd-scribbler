"""Single source of truth for the visible analysis suite."""
ANALYSIS_CATALOG={
"craft":{"title":"Craft & Rhythm","stage":"draft","group":"Prose","purpose":"Sentence rhythm, balance and craft signals."},
"voice":{"title":"Voice & Tense","stage":"draft","group":"Prose","purpose":"Narrator voice, tense and narrative stance."},
"characters":{"title":"Characters & Relationships","stage":"draft","group":"Story","purpose":"Presence, relationships and character movement."},
"continuity":{"title":"Continuity & Timeline","stage":"draft","group":"Story","purpose":"Chronology, recurring facts and inconsistencies."},
"themes":{"title":"Themes & Emotional Arc","stage":"draft","group":"Story","purpose":"Themes and emotional movement."},
"editor":{"title":"Editorial Patterns","stage":"near-final","group":"Editorial","purpose":"Clarity, redundancy and editorial signals."},
"repetition":{"title":"Repetition & Echoes","stage":"draft","group":"Prose","purpose":"Repeated words and phrases worth reviewing."},
"pacing":{"title":"Pacing & Momentum","stage":"draft","group":"Structure","purpose":"Acceleration, slowing and changes of gear."},
"structure":{"title":"Structure & Chapter Purpose","stage":"near-final","group":"Structure","purpose":"Openings, endings, paragraph shape and structural signals."},
"memoir":{"title":"Memoir Lens","stage":"near-final","group":"Optional","purpose":"Reflection, event balance and memory uncertainty; useful for memoir but not required."},
"reader":{"title":"Reader Experience","stage":"near-final","group":"Editorial","purpose":"Opening, dialogue and possible reader-friction signals."},
"research":{"title":"Research & Fact Flags","stage":"near-final","group":"Accuracy","purpose":"Dates and claims worth checking; never declares facts true or false."},
"cadence":{"title":"Cadence & Rhythm","stage":"draft","group":"Prose","purpose":"Sentence movement, pauses and contrast."},
"motifs":{"title":"Motifs & Echoes","stage":"draft","group":"Story","purpose":"Recurring words and phrases as candidate motifs."},
"anchors":{"title":"Structural Anchors","stage":"draft","group":"Structure","purpose":"Recurring openings, endings and textual anchors."},
"voice_dna":{"title":"Voice DNA","stage":"draft","group":"Writer","purpose":"Compare selected writing against approved personal writing samples."},
"reader_perception":{"title":"Reader Perception","stage":"draft","group":"Writer","purpose":"Evidence-first impression of narrator/author and named characters when AI is configured."},
}

def recommended(stage="draft"):
 order={"draft":0,"near-final":1,"final":2}; ceiling=order.get(stage,0)
 return [k for k,v in ANALYSIS_CATALOG.items() if order.get(v.get("stage","draft"),0)<=ceiling]

def run_all_warning(selected):
 selected=list(dict.fromkeys(selected)); risky=[]
 safe={"craft":{"voice","editor","cadence"},"voice":{"craft","characters","cadence","voice_dna"},"characters":{"voice","continuity","themes"},"continuity":{"characters","themes","research"},"themes":{"characters","continuity","motifs"},"editor":{"craft","voice","repetition","pacing"},"repetition":{"craft","editor","motifs"},"pacing":{"themes","structure","continuity"},"structure":{"pacing","themes","continuity","anchors"},"memoir":{"themes","structure","voice","reader"},"reader":{"pacing","structure","themes"},"research":{"continuity","memoir"},"cadence":{"craft","voice","voice_dna"},"motifs":{"themes","repetition","anchors"},"anchors":{"structure","motifs"},"voice_dna":{"voice","cadence"},"reader_perception":{"voice","characters","themes"}}
 for k in selected:
  bad=[x for x in selected if x!=k and x not in safe.get(k,set())]
  if bad:risky.append((k,bad))
 return "Some selected tools overlap or answer different questions. Review findings in context; Scribbler will not treat any diagnostic as an instruction." if risky else None
