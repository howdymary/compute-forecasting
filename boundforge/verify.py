"""Protected verifier: exact projected masses + Arb interval entropies."""
import argparse, hashlib, json
from fractions import Fraction
from flint import arb, fmpq, ctx
FORMS=((1,-1),(1,0),(0,1),(1,1),(1,2))
NAMES=("x-y","x","y","x+y","x+2y")
def integer(x):
    return type(x) is int
def validate(c):
    if not integer(c["base"]) or c["base"]<2: raise ValueError("invalid base")
    if not c["laws"] or len(c["laws"])!=len(c["counts"]): raise ValueError("count mismatch")
    if not all(integer(x) and x>0 for x in c["counts"]): raise ValueError("invalid counts")
    for law in c["laws"]:
        pts,ws=law["points"],law["weights"]
        if not pts or len(pts)!=len(ws): raise ValueError("invalid law length")
        if any(len(p)!=2 or not all(integer(t) for t in p) for p in pts): raise ValueError("coordinates must be integers")
        if len(set(map(tuple,pts)))!=len(pts): raise ValueError("duplicate points")
        if any(len(w)!=2 or not all(integer(t) for t in w) or min(w)<=0 for w in ws): raise ValueError("invalid rational weight")
        ps=[Fraction(*w) for w in ws]
        if sum(ps)!=1: raise ValueError("probabilities must sum exactly to one")
        if any(2*abs(a*x+b*y)>=c["base"] for x,y in pts for a,b in FORMS): raise ValueError("digit encoding not certified injective")
    return c
def measure(c,bits=384):
    validate(c)
    ctx.prec=bits
    totals=[arb(0) for _ in FORMS]
    n=sum(c["counts"])
    for law,count in zip(c["laws"],c["counts"]):
        ps=[Fraction(*w) for w in law["weights"]]
        for j,(a,b) in enumerate(FORMS):
            masses={}
            for (x,y),p in zip(law["points"],ps):
                v=a*x+b*y
                masses[v]=masses.get(v,Fraction())+p
            h=arb(0)
            for p in masses.values():
                t=arb(fmpq(p.numerator,p.denominator))
                h-=t*t.log()
            totals[j]+=arb(fmpq(count,n))*h
    if any(not bool(d>0) for d in totals[1:]): raise ValueError("denominator not strictly positive")
    rs=[totals[0]/d for d in totals[1:]]
    lo=min((r.lower() for r in rs),key=lambda v:float(v))
    hi=min((r.upper() for r in rs),key=lambda v:float(v))
    # float is used only to choose an initial candidate; exact comparisons select extrema.
    for r in rs:
        if bool(r.lower()<lo): lo=r.lower()
        if bool(r.upper()<hi): hi=r.upper()
    return lo,hi,totals
def report(c):
    lo,hi,hs=measure(c)
    claim=c.get("claimed_lower_bound",[0,1])
    if len(claim)!=2 or not all(integer(x) for x in claim) or claim[1]<=0: raise ValueError("invalid claim")
    proven=bool(lo>=arb(fmpq(*claim)))
    return {"valid":True,"claim_certified":proven,"ratio_interval_arb":[lo.str(65),hi.str(65)],"entropies":dict(zip(NAMES,[h.str(55) for h in hs]))}
def improves(candidate,baseline):
    a,_,_=measure(candidate)
    _,b,_=measure(baseline)
    return bool(a>b)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("certificate")
    p.add_argument("--baseline")
    a=p.parse_args()
    raw=open(a.certificate,"rb").read()
    c=json.loads(raw)
    out=report(c)
    out["sha256"]=hashlib.sha256(raw).hexdigest()
    if a.baseline: out["strict_improvement"]=improves(c,json.load(open(a.baseline)))
    print(json.dumps(out,indent=2))
    if not out["claim_certified"]: raise SystemExit(1)
