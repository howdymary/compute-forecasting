"""Bounded numerical proposals; all outputs are untrusted until independently certified."""
import copy, json, math, time, hashlib
import numpy as np
from scipy.optimize import minimize, linprog
FORMS=((1,-1),(1,0),(0,1),(1,1),(1,2))
class TimedOut(Exception): pass
def maps(points):
    z=np.asarray(points,dtype=int)
    return [np.unique(z[:,0]*a+z[:,1]*b,return_inverse=True)[1] for a,b in FORMS]
def entropies(p,images):
    hs=[]; gs=[]
    for ids in images:
        q=np.bincount(ids,weights=p)
        safe=np.maximum(q,1e-300)
        hs.append(-np.sum(q*np.log(safe)))
        gs.append(-(np.log(safe[ids])+1))
    return np.asarray(hs),np.asarray(gs)
def floats(law):
    return np.array([a/b for a,b in law["weights"]])
def certificate(laws,ps,alpha):
    # Round an untrusted numerical proposal to EXACT rational laws.
    # Largest-remainder rounding on a 10^30 grid, retaining a positive tail.
    den=10**30
    rounded=[]
    for law,p in zip(laws,ps):
        p=np.maximum(p,1e-30); p/=p.sum()
        ws=[max(1,int(float(x)*den)) for x in p]
        i=int(np.argmax(p)); ws[i]+=den-sum(ws)
        if ws[i]<=0: raise ValueError("rounding invalid")
        rounded.append({"points":copy.deepcopy(law["points"]),"weights":[[v,den] for v in ws]})
    # For a positive linear-program mixture, rationalise its digit counts.
    counts=[max(1,round(float(a)*10**18)) for a in alpha]
    m=max(abs(a*x+b*y) for law in rounded for x,y in law["points"] for a,b in FORMS)
    return {"problem":"C3c four-slope arithmetic Kakeya","base":2*m+1,"counts":counts,"laws":rounded,"claimed_lower_bound":[0,1]}
def score(c):
    hs=np.array([entropies(floats(l),maps(l["points"]))[0] for l in c["laws"]])
    w=np.array(c["counts"],dtype=float); w/=w.sum()
    h=w@hs
    return float(h[0]/max(h[1:]))
def optimize(c,seconds=12,maxiter=180):
    laws=c["laws"]; sizes=[len(l["points"]) for l in laws]; K=len(laws)
    images=[maps(l["points"]) for l in laws]
    starts=np.cumsum([0]+sizes)
    alpha=np.array(c["counts"],dtype=float); alpha/=alpha.sum()
    ps=[floats(l) for l in laws]
    hs=np.array([entropies(p,m)[0] for p,m in zip(ps,images)])
    t=max(alpha@hs[:,1:])
    x0=np.r_[np.concatenate(ps),alpha,t]
    end=time.monotonic()+seconds; last=x0.copy(); calls=0
    def calc(x):
        h=[]; g=[]
        for k,m in enumerate(images):
            a,b=starts[k:k+2]; hv,gv=entropies(x[a:b],m); h.append(hv); g.append(gv)
        return np.array(h),g
    def obj(x):
        nonlocal calls,last
        calls+=1
        if time.monotonic()>end: raise TimedOut()
        last=x.copy()
        h,g=calc(x); w=x[-K-1:-1]; t=max(x[-1],1e-12)
        num=w@h[:,0]
        grad=np.zeros_like(x)
        for k in range(K): grad[starts[k]:starts[k+1]]=-w[k]*g[k][0]/t
        grad[-K-1:-1]=-h[:,0]/t; grad[-1]=num/t**2
        return -num/t,grad
    A=np.zeros((K+1,len(x0)))
    for k in range(K): A[k,starts[k]:starts[k+1]]=1
    A[K,-K-1:-1]=1
    def inequal(x):
        h,g=calc(x); w=x[-K-1:-1]
        return x[-1]-w@h[:,1:]
    def jac(x):
        h,g=calc(x); w=x[-K-1:-1]
        j=np.zeros((4,len(x)))
        for k in range(K): j[:,starts[k]:starts[k+1]]=-w[k]*g[k][1:]
        j[:,-K-1:-1]=-h[:,1:].T; j[:,-1]=1
        return j
    status="timeout"
    try:
        r=minimize(obj,x0,jac=True,method="SLSQP",
            bounds=[(1e-30,1)]*sum(sizes)+[(1e-8,1)]*K+[(1e-8,20)],
            constraints=[{"type":"eq","fun":lambda x:A@x-1,"jac":lambda x:A},
                         {"type":"ineq","fun":inequal,"jac":jac}],
            options={"maxiter":maxiter,"ftol":1e-13,"disp":False})
        x=r.x; status=str(r.message); nit=int(r.nit)
    except TimedOut: x=last; nit=None
    # Always recompute actual nonsmooth ratio; never trust solver objective/feasibility.
    result=certificate(laws,[x[starts[k]:starts[k+1]] for k in range(K)],x[-K-1:-1])
    return result,{"status":status,"iterations":nit,"function_calls":calls,"float_score":score(result)}
def mutate(c,kind,rng,trial):
    d=copy.deepcopy(c)
    if kind=="weights":
        for l in d["laws"]:
            p=floats(l)*np.exp(rng.normal(0,0.12,len(l["points"])))
            p/=p.sum()
            l["weights"]=[[max(1,int(v*10**30)),10**30] for v in p]
            i=int(np.argmax(p)); l["weights"][i][0]+=10**30-sum(a for a,b in l["weights"])
    elif kind in ("augment","exchange","new-law"):
        k=trial%len(d["laws"]); law=d["laws"][k]
        if kind=="new-law":
            law=copy.deepcopy(law); d["laws"].append(law); d["counts"].append(max(1,sum(d["counts"])//4))
            k=len(d["laws"])-1
        pts=law["points"]; used=set(map(tuple,pts))
        # Prefer intersections of existing projection fibres, plus a random exploration quota.
        xs=[x for x,y in pts]; ys=[y for x,y in pts]
        possibilities={(x,y) for x in set(xs) for y in set(ys)}-used
        existing=[set(a*x+b*y for x,y in pts) for a,b in FORMS[1:]]
        target=set(x-y for x,y in pts)
        def novelty(p):
            x,y=p
            return 4*int(x-y not in target)+sum(int(a*x+b*y in ss) for (a,b),ss in zip(FORMS[1:],existing))
        candidates=sorted(possibilities,key=lambda p:(-novelty(p),p))
        if not candidates: return d
        top=candidates[:max(12,len(candidates)//8)]
        chosen=[top[i] for i in rng.choice(len(top),size=min(4,len(top)),replace=False)]
        p=floats(law)
        if kind=="exchange" and len(pts)>8:
            # A bounded ruin-and-recreate neighborhood; no claim of global exhaustion.
            removable=np.argsort(p)[:max(2,len(p)//3)]
            gone=set(int(i) for i in rng.choice(removable,size=min(3,len(removable)),replace=False))
            law["points"]=[pt for i,pt in enumerate(pts) if i not in gone]
            p=np.array([v for i,v in enumerate(p) if i not in gone]); p/=p.sum()
        law["points"]+= [list(pt) for pt in chosen]
        q=np.r_[p*(1-1e-5),np.full(len(chosen),1e-5/len(chosen))]
        tmp=certificate([law],[q],[1])["laws"][0]
        d["laws"][k]=tmp
    return d
def compose(pool):
    """Optimise independent digit-law composition on the entropy cone."""
    hs=np.array([entropies(floats(l),maps(l["points"]))[0] for l in pool])
    r=linprog(-hs[:,0],A_ub=hs[:,1:].T,b_ub=np.ones(4),bounds=(0,None),method="highs")
    if not r.success: return None
    ids=np.flatnonzero(r.x>1e-9)
    if not len(ids): return None
    w=r.x[ids]; w/=w.sum()
    return certificate([pool[int(i)] for i in ids],[floats(pool[int(i)]) for i in ids],w)
