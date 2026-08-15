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

def repetition(t):
    w=_content(t); c=Counter(w)
    return {"repeated_words":[{"term":x,"count":n} for x,n in c.most_common(30) if n>=3],"repeated_phrases":_ngrams(t,2,20),"three_word_echoes":_ngrams(t,3,15),"note":"Repeated language is a review signal, not automatically a flaw."}

def pacing(t):
    ss=sentences(t); lens=[len(words(s)) for s in ss]
    if not lens:return {"status":"No analysable sentences found"}
    third=max(1,len(lens)//3); chunks=[lens[:third],lens[third:2*third],lens[2*third:]]; av=[round(mean(x),1) for x in chunks if x]
    direction="accelerating" if len(av)>=2 and av[-1]<av[0] else "slowing" if len(av)>=2 and av[-1]>av[0] else "steady"
    return {"sentence_length_by_section":av,"short_sentence_pct":round(sum(x<=8 for x in lens)/len(lens)*100,1),"long_sentence_pct":round(sum(x>=30 for x in lens)/len(lens)*100,1),"paragraph_count":len(paragraphs(t)),"sentence_count":len(ss),"momentum_signal":direction,"sentence_length_range":[min(lens),max(lens)]}

def structure(t):
    ps=paragraphs(t); ss=sentences(t); sizes=[len(words(p)) for p in ps]
    return {"paragraphs":len(ps),"sentences":len(ss),"opening":" ".join(words(ss[0])[:40]) if ss else "","closing":" ".join(words(ss[-1])[-40:]) if ss else "","paragraph_size_range":[min(sizes,default=0),max(sizes,default=0)],"short_paragraph_pct":round(sum(x<=40 for x in sizes)/len(sizes)*100,1) if sizes else 0,"long_paragraph_pct":round(sum(x>=180 for x in sizes)/len(sizes)*100,1) if sizes else 0,"note":"Structural signals describe shape; they do not decide whether the structure is good."}

def memoir(t):
    w=words(t); low=t.lower(); first=sum(x.lower() in {"i","me","my","mine","we","us","our"} for x in w)
    reflection=sum(low.count(x) for x in ["i remember","looking back","now i","in retrospect","i realise","i realize","i think","i wonder","at the time","years later"])
    uncertainty=sum(low.count(x) for x in ["perhaps","maybe","as far as i remember","i don't remember","i can't remember","if i remember","i think"])
    event=sum(low.count(x) for x in ["then","later","after","before","when","that day","the next day"])
    return {"first_person_pct":round(first/max(1,len(w))*100,2),"reflection_signals":reflection,"memory_uncertainty_signals":uncertainty,"event_sequence_signals":event,"note":"Memoir lens is optional and does not judge memory certainty or prose quality."}

def reader(t):
    ss=sentences(t); total=max(1,len(words(t))); dialogue=sum(len(words(x)) for pair in re.findall(r'"([^"]+)"|“([^”]+)”',t) for x in pair if x)
    refs=len(re.findall(r"\b(this|that|these|those|he|she|they|it)\b",t,re.I))
    return {"opening_words":len(words(ss[0])) if ss else 0,"question_rate":round(t.count('?')/max(1,len(ss))*100,2),"exclamation_rate":round(t.count('!')/max(1,len(ss))*100,2),"dialogue_pct":round(dialogue/total*100,2),"possible_reference_ambiguity_signals":refs,"note":"These are reader-friction signals to inspect, not proof that a passage is confusing."}

def research(t):
    years=sorted(set(re.findall(r"\b(?:19|20)\d{2}\b",t))); claims=re.findall(r"\b(?:according to|research shows|studies show|statistics|data shows|in \d{4})\b",t,re.I); urls=re.findall(r"https?://\S+",t)
    return {"years_found":years,"research_claim_signals":len(claims),"explicit_urls":len(urls),"note":"Flags candidates for verification; never establishes factual truth."}

def run(name,t):
    tools={"repetition":repetition,"pacing":pacing,"structure":structure,"memoir":memoir,"reader":reader,"research":research}
    if name not in tools: raise ValueError(f"Analysis tool '{name}' is not implemented")
    result=tools[name](t); result["analysis"]={"tool":name,"word_count":len(words(t)),"evidence_first":True}; return result
