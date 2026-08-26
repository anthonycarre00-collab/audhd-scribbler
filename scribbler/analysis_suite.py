"""Deterministic, genre-neutral analysis tools. Evidence first, no grading."""
from __future__ import annotations
import re
from collections import Counter
from statistics import mean

STOP=set("the a an and or but if then than so because as of to in on at for from by with about into through during before after above below is are was were be been being have has had do does did this that these those it its i me my mine we us our you your he him his she her they their what which who when where why how not no very just only more most some any all each every both other same can could will would should may might must".split())

def words(t): return re.findall(r"\b[\w’'-]+\b", t, re.UNICODE)
def sentences(t): return [x.strip() for x in re.split(r"(?<=[.!?…])\s+",t.strip()) if x.strip()]
def paragraphs(t): return [x.strip() for x in re.split(r"\n\s*\n",t) if x.strip()]
def _content(t): return [x.lower().strip("’'-") for x in words(t) if x.lower() not in STOP and len(x)>3]
def _ngrams(t,n=2,limit=20):
    w=_content(t); c=Counter(" ".join(w[i:i+n]) for i in range(len(w)-n+1))
    return [{"phrase":p,"count":count} for p,count in c.most_common(limit) if count>=2]

def _evidence(text, terms, limit=5):
    hits=[]
    for s in sentences(text):
        if any(re.search(term,s,re.I) for term in terms):
            hits.append(s[:280])
            if len(hits)>=limit: break
    return hits

def repetition(t):
    w=_content(t); c=Counter(w)
    repeated=[{"term":x,"count":n} for x,n in c.most_common(30) if n>=3]
    phrases=_ngrams(t,2,20); echoes=_ngrams(t,3,15)
    candidates=[x for x in repeated if x["count"]>=max(3,round(len(w)/150))][:8]
    advice=[]
    if candidates: advice.append("Review the highest-frequency terms in context; keep deliberate refrain, but check whether any repetition is accidental.")
    else: advice.append("No unusually strong repeated-word signal was found; do not force variation where repetition is serving emphasis or voice.")
    return {"repeated_words":repeated,"repeated_phrases":phrases,"three_word_echoes":echoes,"review_candidates":candidates,"advice":advice,"note":"Repeated language is a review signal, not automatically a flaw."}

def pacing(t):
    ss=sentences(t); lens=[len(words(s)) for s in ss]
    if not lens:return {"status":"No analysable sentences found","advice":[]}
    third=max(1,len(lens)//3); chunks=[lens[:third],lens[third:2*third],lens[2*third:]]; av=[round(mean(x),1) for x in chunks if x]
    direction="accelerating" if len(av)>=2 and av[-1]<av[0]*.82 else "slowing" if len(av)>=2 and av[-1]>av[0]*1.18 else "steady/mixed"
    short=round(sum(x<=8 for x in lens)/len(lens)*100,1); long=round(sum(x>=30 for x in lens)/len(lens)*100,1)
    advice=[]
    if direction=="accelerating": advice.append("The later sections use shorter sentences on average. Check whether that creates useful urgency or whether important material is being rushed.")
    elif direction=="slowing": advice.append("The later sections use longer sentences on average. Check whether the expansion feels reflective and deliberate or whether momentum is being lost.")
    else: advice.append("Sentence length does not show a strong overall acceleration or slowdown. Look for local changes at scene turns rather than forcing global variation.")
    if short>35: advice.append("A high proportion of short sentences can create punch and tension; inspect clusters for a deliberately clipped rhythm versus monotony.")
    if long>20: advice.append("Long sentences are common enough to inspect their clause structure; keep them where accumulation or thought-flow is doing useful work.")
    return {"sentence_length_by_section":av,"short_sentence_pct":short,"long_sentence_pct":long,"paragraph_count":len(paragraphs(t)),"sentence_count":len(ss),"momentum_signal":direction,"sentence_length_range":[min(lens),max(lens)],"advice":advice}

def structure(t):
    ps=paragraphs(t); ss=sentences(t); sizes=[len(words(p)) for p in ps]
    opening=" ".join(words(ss[0])[:40]) if ss else ""; closing=" ".join(words(ss[-1])[-40:]) if ss else ""
    advice=[]
    if ss and len(words(ss[0]))>45: advice.append("The opening sentence is long. Consider whether the extended entry creates the intended pull, or whether a sharper first beat would improve orientation.")
    if ss and len(words(ss[-1]))>45: advice.append("The closing sentence is long. Check whether the ending lands cleanly or buries its final beat in extra syntax.")
    if not advice: advice.append("No obvious structural shape problem was detected by these simple signals. Use the opening and closing extracts as prompts for a human read-through.")
    return {"paragraphs":len(ps),"sentences":len(ss),"opening":opening,"closing":closing,"paragraph_size_range":[min(sizes,default=0),max(sizes,default=0)],"short_paragraph_pct":round(sum(x<=40 for x in sizes)/len(sizes)*100,1) if sizes else 0,"long_paragraph_pct":round(sum(x>=180 for x in sizes)/len(sizes)*100,1) if sizes else 0,"advice":advice,"note":"Structural signals describe shape; they do not decide whether the structure is good."}

def memoir(t):
    w=words(t); low=t.lower(); first=sum(x.lower() in {"i","me","my","mine","we","us","our"} for x in w)
    reflection=sum(low.count(x) for x in ["i remember","looking back","now i","in retrospect","i realise","i realize","i think","i wonder","at the time","years later"])
    uncertainty=sum(low.count(x) for x in ["perhaps","maybe","as far as i remember","i don't remember","i can't remember","if i remember","i think"])
    event=sum(low.count(x) for x in ["then","later","after","before","when","that day","the next day"])
    balance=round(reflection/max(1,event),2)
    advice=["Use this as a memoir-specific lens, not a quality score. Reflection can be powerful even when sparse; concrete scenes can carry meaning without explicit reflection."]
    if balance<.15 and first/max(1,len(w))>.02: advice.append("There are relatively few explicit reflection signals compared with event-sequencing signals. If the chapter is intended to interpret the past, consider where a small amount of present-day perspective could deepen meaning.")
    if uncertainty: advice.append("Memory-uncertainty language is present. Keep it where it honestly represents memory; do not 'correct' uncertainty merely to sound authoritative.")
    return {"first_person_pct":round(first/max(1,len(w))*100,2),"reflection_signals":reflection,"memory_uncertainty_signals":uncertainty,"event_sequence_signals":event,"reflection_to_event_ratio":balance,"advice":advice,"note":"Memoir lens is optional and does not judge memory certainty or prose quality."}

def reader(t):
    ss=sentences(t); total=max(1,len(words(t))); dialogue=sum(len(words(x)) for pair in re.findall(r'"([^"]+)"|“([^”]+)”',t) for x in pair if x)
    refs=len(re.findall(r"\b(this|that|these|those|he|she|they|it)\b",t,re.I))
    question=round(t.count('?')/max(1,len(ss))*100,2); exclaim=round(t.count('!')/max(1,len(ss))*100,2)
    advice=[]
    if refs/max(1,len(ss))>1.2: advice.append("Pronoun/deictic references are frequent. Sample a few passages and check that 'he', 'it', 'this', etc. always have an obvious antecedent.")
    if exclaim>8: advice.append("Exclamation marks are frequent enough to review. Keep them where the voice genuinely needs overt emphasis; let strong sentences carry themselves elsewhere.")
    if question>10: advice.append("Questions are frequent enough to inspect for deliberate interrogation versus repeated rhetorical framing.")
    if not advice: advice.append("No strong generic reader-friction signal was detected. A clean result is not proof that every reader will find the passage clear.")
    return {"opening_words":len(words(ss[0])) if ss else 0,"question_rate":question,"exclamation_rate":exclaim,"dialogue_pct":round(dialogue/total*100,2),"possible_reference_ambiguity_signals":refs,"advice":advice,"note":"These are reader-friction signals to inspect, not proof that a passage is confusing."}

def research(t):
    years=sorted(set(re.findall(r"\b(?:19|20)\d{2}\b",t))); claims=re.findall(r"\b(?:according to|research shows|studies show|statistics|data shows|in \d{4})\b",t,re.I); urls=re.findall(r"https?://\S+",t)
    advice=[]
    if years: advice.append("Check each explicit year against your source material or timeline, especially where the year anchors a sequence of events.")
    if claims: advice.append("Research-claim language is present. Verify the underlying source and consider recording the citation rather than relying on a remembered attribution.")
    if urls: advice.append("URLs are present; confirm that each source is still the intended reference before final publication.")
    if not advice: advice.append("No explicit research-claim or URL signal was detected. This does not establish that the passage is factually verified.")
    return {"years_found":years,"research_claim_signals":len(claims),"explicit_urls":len(urls),"advice":advice,"note":"Flags candidates for verification; never establishes factual truth."}

def run(name,t):
    tools={"repetition":repetition,"pacing":pacing,"structure":structure,"memoir":memoir,"reader":reader,"research":research}
    if name not in tools: raise ValueError(f"Analysis tool '{name}' is not implemented")
    result=tools[name](t); result["analysis"]={"tool":name,"word_count":len(words(t)),"evidence_first":True}
    # Add summary and observations fields for consistency with other analyzers
    if "summary" not in result:
        wc=len(words(t))
        title=name.replace("_"," ").title()
        advice_list=result.get("advice",[])
        result["summary"]=f"What this is: {title} analysis of {wc} words\nWhat it found: {len(advice_list)} advice point(s)\nWhat you could do next: Review the advice below — each describes a pattern to notice"
    if "observations" not in result:
        advice_list=result.get("advice",[])
        result["observations"]=[
            {
                "category": name,
                "location": "whole chapter",
                "observation": a,
                "effect": "this is a pattern to notice, not a problem to fix",
                "options": ["review in context", "keep as-is if intentional"],
                "formatted": f"I noticed the following: {a} It had the effect that this is a pattern to notice. Would you like to (a) review it in context, (b) keep as-is if intentional, or (c) come back to this later?"
            } for a in advice_list
        ]
    return result
