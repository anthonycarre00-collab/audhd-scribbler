"""Deterministic, genre-neutral analysis tools. Evidence first, no grading."""
from __future__ import annotations
import re
from collections import Counter
from statistics import mean, pstdev

STOP=set("the a an and or but if then than so because as of to in on at for from by with about into through during before after above below is are was were be been being have has had do does did this that these those it its i me my mine we us our you your he him his she her they them their what which who when where why how not no very just only more most some any all each every both other same can could will would should may might must".split())

def words(t): return re.findall(r"\b[\w’'-]+\b", t, re.UNICODE)
def sentences(t): return [x.strip() for x in re.split(r"(?<=[.!?…])\s+",t.strip()) if x.strip()]
def paragraphs(t): return [x.strip() for x in re.split(r"\n\s*\n",t) if x.strip()]

def repetition(t):
    w=[x.lower().strip("’'-") for x in words(t) if x.lower() not in STOP and len(x)>3]
    c=Counter(w); return {"repeated_words":[{"term":x,"count":n} for x,n in c.most_common(30) if n>=3],"repeated_phrases":[{"phrase":" ".join(w[i:i+2]),"count":n} for i in range(max(0,len(w)-1)) for n in [0] if False]}

def pacing(t):
    ss=sentences(t); lens=[len(words(s)) for s in ss]
    if not lens:return {}
    third=max(1,len(lens)//3); chunks=[lens[:third],lens[third:2*third],lens[2*third:]]
    return {"sentence_length_by_section":[round(mean(x),1) for x in chunks if x],"short_sentence_pct":round(sum(x<=8 for x in lens)/len(lens)*100,1),"long_sentence_pct":round(sum(x>=30 for x in lens)/len(lens)*100,1),"paragraph_count":len(paragraphs(t)),"momentum_signal":"accelerating" if len(chunks)>=2 and mean(chunks[-1])<mean(chunks[0]) else "slowing" if len(chunks)>=2 and mean(chunks[-1])>mean(chunks[0]) else "steady"}

def structure(t):
    ps=paragraphs(t); ss=sentences(t)
    return {"paragraphs":len(ps),"sentences":len(ss),"opening":" ".join(words(ss[0])[:40]) if ss else "","closing":" ".join(words(ss[-1])[-40:]) if ss else "","paragraph_size_range":[min([len(words(p)) for p in ps],default=0),max([len(words(p)) for p in ps],default=0)]}

def memoir(t):
    w=words(t); low=t.lower(); first=sum(x.lower() in {"i","me","my","mine","we","us","our"} for x in w)
    reflection=sum(low.count(x) for x in ["i remember","looking back","now i","in retrospect","i realise","i realize","i think","i wonder","at the time","years later"])
    uncertainty=sum(low.count(x) for x in ["i think","perhaps","maybe","as far as i remember","i don't remember","i can't remember","if i remember"])
    return {"first_person_pct":round(first/max(1,len(w))*100,2),"reflection_signals":reflection,"memory_uncertainty_signals":uncertainty,"note":"Memoir lens is optional and should not be used as a quality score."}

def reader(t):
    ss=sentences(t); return {"opening_words":len(words(ss[0])) if ss else 0,"question_rate":round(t.count('?')/max(1,len(ss))*100,2),"exclamation_rate":round(t.count('!')/max(1,len(ss))*100,2),"dialogue_signal":round(sum(len(words(x)) for x in re.findall(r'"([^"]+)"|“([^”]+)”',t) for x in x if x)/max(1,len(words(t)))*100,2),"possible_confusion_signals":len(re.findall(r"\b(this|that|he|she|they|it)\b",t,re.I))}

def research(t):
    years=sorted(set(re.findall(r"\b(?:19|20)\d{2}\b",t))); claims=re.findall(r"\b(?:according to|research shows|studies show|statistics|data shows|in \d{4})\b",t,re.I)
    return {"years_found":years,"research_claim_signals":len(claims),"note":"Flags candidates for verification; never establishes factual truth."}

def run(name,t):
    return {"repetition":repetition,"pacing":pacing,"structure":structure,"memoir":memoir,"reader":reader,"research":research}[name](t)
