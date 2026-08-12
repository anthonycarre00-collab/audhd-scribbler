"""Writer-intelligence features that stay useful across genres.

These are deliberately evidence-first. They describe patterns in the writer's
own corpus instead of grading prose against a universal ideal.
"""
from __future__ import annotations
import json, math, re
from collections import Counter
from pathlib import Path
from statistics import mean, pstdev
from .config import PROJECT_ROOT
from . import llm

PROFILE_PATH = PROJECT_ROOT / "data" / "voice_profile.json"
STOP = set("the a an and or but if then than so because as of to in on at for from by with about into through during before after above below is are was were be been being have has had do does did this that these those it its I me my mine we us our you your he him his she her they them their what which who when where why how not no yes very just only more most some any all each every both other same can could will would should may might must".lower().split())
POS = set("joy love loved happy happiness laugh laughter funny good great relief relieved safe calm hopeful hope proud excited wonder wonderful beautiful kind warm win won success succeed free freedom alive".lower().split())
NEG = set("anger angry hate hated fear afraid frightened sad sadness grief griefed pain painful loss lost lonely loneliness shame ashamed guilt guilty regret regretful worry worried anxious anxiety bleak dark death die dying hurt horror rage furious failure failed broken terrible awful".lower().split())


def words(text):
    return re.findall(r"\b[\w’'-]+\b", text, re.UNICODE)


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+", text.strip()) if s.strip()]


def metrics(text: str) -> dict:
    ws = words(text); ss = sentences(text)
    if not ws: return {"word_count": 0}
    lower = [w.lower().strip("’'-") for w in ws]
    lens = [len(words(s)) for s in ss] or [len(ws)]
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    p_lens = [len(words(p)) for p in paras] or [len(ws)]
    punctuation = Counter(ch for ch in text if ch in ",;:!?—–()\"'…")
    content = [w for w in lower if w not in STOP and len(w) > 2]
    freq = Counter(content)
    lexical = len(set(content)) / len(content) if content else 0
    m = mean(lens); sd = pstdev(lens) if len(lens) > 1 else 0
    return {
        "word_count": len(ws), "sentence_count": len(ss), "mean_sentence_length": round(m, 3),
        "sentence_length_sd": round(sd, 3), "cadence_cv": round(sd/m, 4) if m else 0,
        "median_sentence_length": sorted(lens)[len(lens)//2], "mean_paragraph_length": round(mean(p_lens), 3),
        "paragraph_length_sd": round(pstdev(p_lens), 3) if len(p_lens)>1 else 0,
        "lexical_diversity": round(lexical, 4), "first_person_pct": round(sum(1 for w in lower if w in {"i","me","my","mine","we","us","our"})/len(ws)*100,2),
        "dialogue_pct": round(sum(len(words(x)) for x in re.findall(r'“([^”]+)”|"([^"]+)"', text) for x in (x if isinstance(x, tuple) else (x,)) if x)/len(ws)*100,2),
        "question_rate": round(punctuation["?"]/len(ss)*100,2) if ss else 0,
        "exclamation_rate": round(punctuation["!"]/len(ss)*100,2) if ss else 0,
        "dash_rate": round((punctuation["—"]+punctuation["–"])/len(ss)*100,2) if ss else 0,
        "semicolon_rate": round(punctuation[";"]/len(ss)*100,2) if ss else 0,
        "ellipsis_rate": round(text.count("…")/len(ss)*100,2) if ss else 0,
        "positive_signal": round(sum(1 for w in lower if w in POS)/len(ws)*100,2),
        "negative_signal": round(sum(1 for w in lower if w in NEG)/len(ws)*100,2),
        "top_signature_words": freq.most_common(15),
    }


def _top_ngrams(text, n=3, limit=15):
    ws=[w.lower() for w in words(text) if w.lower() not in STOP]
    grams=Counter(" ".join(ws[i:i+n]) for i in range(len(ws)-n+1))
    return [{"phrase":p,"count":c} for p,c in grams.most_common(limit) if c>=2]


def motif_scan(text: str) -> dict:
    ws=[w.lower() for w in words(text)]
    content=[w for w in ws if w not in STOP and len(w)>3]
    freq=Counter(content)
    repeated=[{"motif":w,"count":c} for w,c in freq.most_common(25) if c>=3]
    return {"recurring_word_motifs":repeated[:15],"recurring_phrases":_top_ngrams(text,2,12),"note":"These are recurrence signals, not proof of thematic meaning. Confirm deliberate motifs yourself."}


def cadence_rhythm(text: str) -> dict:
    ss=sentences(text); lens=[len(words(s)) for s in ss]
    if not lens:return {}
    pauses=sum(text.count(x) for x in [",",";",":","—","–","…"])
    short=sum(1 for n in lens if n<=8); long=sum(1 for n in lens if n>=30)
    turns=sum(1 for a,b in zip(lens,lens[1:]) if (a<9 and b>=20) or (a>=20 and b<9))
    return {"mean_sentence_words":round(mean(lens),2),"sentence_variation":round(pstdev(lens),2) if len(lens)>1 else 0,"short_sentence_pct":round(short/len(lens)*100,1),"long_sentence_pct":round(long/len(lens)*100,1),"pause_density_per_sentence":round(pauses/len(lens),2),"contrast_turns":turns,"reading_rhythm":"high contrast" if turns/max(1,len(lens))*100>12 else "steady/mixed" if pstdev(lens)/max(1,mean(lens))>.45 else "even"}


def structural_anchors(text: str) -> dict:
    paras=[p.strip() for p in re.split(r"\n\s*\n",text) if p.strip()]
    ss=sentences(text)
    openings=[re.sub(r"\W+"," "," ".join(words(s)[:4]).lower()).strip() for s in ss]
    endings=[re.sub(r"\W+"," "," ".join(words(s)[-4:]).lower()).strip() for s in ss]
    def common(xs): return [{"anchor":x,"count":c} for x,c in Counter(xs).most_common(12) if c>1]
    return {"repeated_openings":common(openings),"repeated_endings":common(endings),"paragraph_count":len(paras),"chapter_open":" ".join(words(ss[0])[:30]) if ss else "","chapter_close":" ".join(words(ss[-1])[-30:]) if ss else "","note":"Anchors are recurring textual shapes or phrases; repetition may be intentional."}


def tone_vector(text: str) -> dict:
    m=metrics(text)
    total=m.get("positive_signal",0)+m.get("negative_signal",0)+0.001
    return {"positive":m.get("positive_signal",0),"negative":m.get("negative_signal",0),"net":round((m.get("positive_signal",0)-m.get("negative_signal",0))/total,3),"question_rate":m.get("question_rate",0),"exclamation_rate":m.get("exclamation_rate",0)}


def compare(a: dict,b: dict) -> dict:
    keys=["mean_sentence_length","cadence_cv","lexical_diversity","first_person_pct","dialogue_pct","positive_signal","negative_signal","question_rate","exclamation_rate","dash_rate"]
    out={}
    for k in keys:
        if k in a and k in b:
            base=float(a[k]); cur=float(b[k]); out[k]={"baseline":base,"current":cur,"delta":round(cur-base,3)}
    return out


def load_profile():
    if PROFILE_PATH.exists():
        try:return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        except Exception:pass
    return {"version":1,"samples":[],"baseline":None,"notes":"Only explicitly added writing samples shape this profile."}


def save_profile(profile):
    PROFILE_PATH.parent.mkdir(parents=True,exist_ok=True)
    PROFILE_PATH.write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding="utf-8")


def update_profile(samples: list[dict], label="approved sample"):
    profile=load_profile()
    for sample in samples:
        if not sample.get("text"): continue
        profile["samples"].append({"label":sample.get("label",label),"path":sample.get("path",""),"metrics":metrics(sample["text"])})
    profile["samples"]=profile["samples"][-20:]
    numeric=[s["metrics"] for s in profile["samples"]]
    if numeric:
        keys=[k for k in numeric[0] if isinstance(numeric[0].get(k),(int,float))]
        profile["baseline"]={k:round(mean([float(x.get(k,0)) for x in numeric]),4) for k in keys}
    save_profile(profile); return profile


def voice_report(text: str, profile=None) -> dict:
    profile=profile or load_profile(); current=metrics(text); baseline=profile.get("baseline")
    if not baseline:return {"current":current,"profile_ready":False,"message":"Add two or more approved samples to establish a personal voice baseline."}
    diffs=compare(baseline,current)
    distance=[]
    for k,v in diffs.items():
        scale=max(abs(v["baseline"]),1.0); distance.append(abs(v["delta"])/scale)
    score=max(0,min(100,round(100-mean(distance)*35,1))) if distance else 100
    return {"current":current,"baseline":baseline,"voice_alignment":score,"profile_ready":True,"differences":diffs,"message":"Alignment is similarity to your selected baseline, not a quality score. Genuine author growth can be tracked by keeping dated samples rather than forcing new work back to an old baseline."}


def chapter_comparison(chapters: list[dict]) -> dict:
    rows=[]
    for c in chapters:
        m=metrics(c["text"]); rows.append({"label":c.get("label") or Path(c.get("path","")).stem,"path":c.get("path",""),"metrics":m,"tone":tone_vector(c["text"]),"motifs":motif_scan(c["text"]),"cadence":cadence_rhythm(c["text"])})
    if not rows:return {"chapters":[]}
    baseline=rows[0]["metrics"]
    for r in rows:r["from_first_chapter"]=compare(baseline,r["metrics"])
    return {"chapters":rows,"interpretation":"Differences can indicate intentional author growth, scene/genre changes or voice drift. Scribbler flags change; it does not label change as a defect."}


def ai_perceptions(text: str, labels: list[str]=None) -> dict|None:
    if not llm.llm_available():return None
    labels=labels or []
    prompt=f"""Read this writing as an editorial observer. Return JSON with keys: author_perception (5 concise observations about the implied narrator/author persona, clearly labelled as reader perception), character_perceptions (array of {{name, impression, evidence_phrase}} for named people if identifiable), tone, motifs, structural_anchors, cautions. Do not invent biography. Separate textual evidence from inference. Named hints: {labels}. Text:\n\n{text[:30000]}"""
    return llm.llm_json(prompt,system="You are an evidence-first literary analyst. Never diagnose the author or state an inference as fact.")
