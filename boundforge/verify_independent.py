"""Independent certificate checker, no imports from search or Arb verifier.
Logarithms use exact rational atanh series with an explicit rational remainder.
Endpoint calculations, probability aggregation and comparisons are exact fractions.
"""
import json, sys, math
from fractions import Fraction as Q
from functools import lru_cache
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_CEILING
def series(t,n):
    # 2 atanh(t); t >=0 and t <= 1/3
    z=t*t
    power=t
    s=Q()
    for i in range(n):
        s+=2*power/(2*i+1)
        power*=z
    return s,s+2*power/((2*n+1)*(1-z))
@lru_cache(maxsize=4096)
def logarithm(q,n=96):
    if q<=0: raise ValueError("log domain")
    if q==1: return Q(),Q()
    # q=2^k r, with 1 <= r < 2; integer comparisons only.
    k=q.numerator.bit_length()-q.denominator.bit_length()
    r=q/(Q(2)**k)
    while r<1: r*=2; k-=1
    while r>=2: r/=2; k+=1
    l,u=series((r-1)/(r+1),n)
    a,b=series(Q(1,3),n)
    lo,hi=(l+k*a,u+k*b) if k>=0 else (l+k*b,u+k*a)
    # Outward dyadic rounding prevents huge coprime denominators in entropy sums.
    scale=1<<384
    low=(lo.numerator*scale)//lo.denominator
    high=-((-hi.numerator*scale)//hi.denominator)
    return Q(low,scale),Q(high,scale)
def decimal(q,up=False):
    with localcontext() as c:
        c.prec=64
        c.rounding=ROUND_CEILING if up else ROUND_FLOOR
        return str(Decimal(q.numerator)/Decimal(q.denominator))
def check(c):
    B=c["base"]; ns=c["counts"]; laws=c["laws"]
    assert type(B) is int and B>=2
    assert len(ns)==len(laws)>0 and all(type(n) is int and n>0 for n in ns)
    lower=[Q() for _ in range(5)]; upper=lower.copy()
    n=sum(ns)
    for law,count in zip(laws,ns):
        pairs=law["points"]; fractions=law["weights"]
        assert len(pairs)==len(fractions)>0
        assert all(len(p)==2 and all(type(x) is int for x in p) for p in pairs)
        assert len(set(tuple(p) for p in pairs))==len(pairs)
        assert all(len(w)==2 and all(type(x) is int for x in w) and w[0]>0 and w[1]>0 for w in fractions)
        weights=[Q(w[0],w[1]) for w in fractions]
        assert sum(weights)==1
        images=[{} for _ in range(5)]
        for (x,y),w in zip(pairs,weights):
            vals=(x-y,x,y,x+y,x+2*y)
            assert all(-B<2*v<B for v in vals)
            for j,v in enumerate(vals): images[j][v]=images[j].get(v,Q())+w
        for j,d in enumerate(images):
            for p in d.values():
                l,u=logarithm(p)
                lower[j]-=Q(count,n)*p*u
                upper[j]-=Q(count,n)*p*l
    assert min(lower[1:])>0
    lo=lower[0]/max(upper[1:])
    hi=upper[0]/max(lower[1:])
    claim=c.get("claimed_lower_bound",[0,1])
    assert len(claim)==2 and all(type(x) is int for x in claim) and claim[1]>0
    assert lo>=Q(*claim),"claim exceeds rigorous lower endpoint"
    return lo,hi
if __name__=="__main__":
    lo,hi=check(json.load(open(sys.argv[1])))
    output={"valid":True,"method":"exact rational series and explicit tail bound","ratio_interval":[decimal(lo),decimal(hi,True)]}
    if len(sys.argv)>2:
        baseline_lo,baseline_hi=check(json.load(open(sys.argv[2])))
        output["strict_improvement"]=lo>baseline_hi
    print(json.dumps(output))
