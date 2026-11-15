"""Bounded integer expression grammar and deterministic entropy/free-energy optimizer.
Graph support (d+y(d),y(d)) guarantees injective target X-Y=d.
This restricted grammar is an adaptation, not unrestricted AlphaEvolve.
"""
import hashlib,json,time,math
import numpy as np
from scipy.optimize import minimize,linprog
FORMS=((1,-1),(1,0),(0,1),(1,1),(1,2))
OPS={"add":2,"sub":2,"mul":2,"div":2,"mod":2,"abs":1,"neg":1}
def validate(expr,depth=0,counter=None):
    if counter is None:counter=[0]
    counter[0]+=1
    if depth>9 or counter[0]>64:raise ValueError("expression exceeds structural budget")
    if type(expr) is int:
        if abs(expr)>32:raise ValueError("integer literal too large")
        return
    if isinstance(expr,str) and expr in ("d","r"):return
    if not isinstance(expr,list) or not expr or not isinstance(expr[0],str) or expr[0] not in OPS or len(expr)!=OPS[expr[0]]+1:raise ValueError("invalid expression")
    for x in expr[1:]:validate(x,depth+1,counter)
def evaluate(expr,d,r):
    if type(expr) is int:return expr
    if isinstance(expr,str) and expr=="d":return d
    if isinstance(expr,str) and expr=="r":return r
    op=expr[0];a=evaluate(expr[1],d,r);b=evaluate(expr[2],d,r) if len(expr)==3 else None
    if op=="add":v=a+b
    elif op=="sub":v=a-b
    elif op=="mul":v=a*b
    elif op=="div":
        if b==0:raise ValueError("division by zero")
        v=a//b
    elif op=="mod":
        if b==0:raise ValueError("modulo zero")
        v=a%b
    elif op=="abs":v=abs(a)
    elif op=="neg":v=-a
    else:raise ValueError("unknown operator")
    if abs(v)>100000:raise ValueError("intermediate integer bound")
    return v
def support(expr,r=24):
    validate(expr)
    pts=[]
    for d in range(-r,r+1):
        y=evaluate(expr,d,r)
        if abs(y)>4*r:raise ValueError("coordinate bound")
        pts.append([d+y,y])
    return pts
def maps(pts):
    a=np.array(pts,dtype=int)
    return [np.unique(x*a[:,0]+y*a[:,1],return_inverse=True)[1] for x,y in FORMS]
def hs(p,ids):
    H=[];G=[]
    for j in ids:
        q=np.bincount(j,weights=p);z=np.maximum(q,1e-300)
        H.append(-np.sum(q*np.log(z)));G.append(-(np.log(z[j])+1))
    return np.array(H),np.array(G)
def rational_law(pts,p,den=10**50):
    p=np.maximum(p,1e-50);p/=p.sum()
    w=[max(1,int(float(v)*den)) for v in p]
    w[int(np.argmax(p))]+=den-sum(w)
    return {"points":pts,"weights":[[v,den] for v in w]}
def optimize(pts,nu,seed,seconds=25,initial=None,maxiter=160):
    rng=np.random.default_rng(seed);nu=np.array(nu);ids=maps(pts)
    start=time.monotonic();deadline=start+seconds;best=None;calls=0;statuses=[]
    d=np.array([x-y for x,y in pts],dtype=float)
    for restart in range(3):
        p0=np.exp(-0.5*(d/(3+restart*3))**2+rng.normal(0,0.2,len(d)))
        if initial is not None and restart==0:p0=np.array(initial)
        p0=np.maximum(p0,1e-30);p0/=p0.sum()
        z=np.log(p0)
        last=z.copy()
        def obj(z):
            nonlocal calls,last,best
            if time.monotonic()>deadline:raise TimeoutError("bounded local optimizer")
            calls+=1;last=z.copy()
            e=np.exp(z-np.max(z));p=e/e.sum();h,g=hs(p,ids)
            F=h[0]-nu@h[1:]
            gp=g[0]-nu@g[1:]
            grad=p*(gp-p@gp)
            if best is None or F>best[0]:best=(float(F),p.copy(),h.copy())
            return -F,-grad
        try:
            res=minimize(obj,z,jac=True,method="L-BFGS-B",bounds=[(-80,10)]*len(z),options={"maxiter":maxiter,"ftol":1e-14,"gtol":1e-9,"maxls":30})
            statuses.append(str(res.message))
        except TimeoutError:statuses.append("timeout");break
    if best is None:raise ValueError("no evaluation")
    F,p,h=best
    return {"law":rational_law(pts,p),"free_energy":F,"entropies":h.tolist(),"ratio":float(h[0]/max(h[1:])) if max(h[1:])>1e-15 else None,"nondegenerate":bool(h[0]>0.2 and max(p)<0.99),"calls":calls,"seconds":time.monotonic()-start,"statuses":statuses,"support_sha256":hashlib.sha256(json.dumps(pts).encode()).hexdigest(),"seed":seed}
def structured():
    # Fixed before model evaluation; distinct periodic/rounding geometry.
    base=["div",["neg","d"],3]
    return [
      {"name":"slope-half","expr":["div",["neg","d"],2]},
      {"name":"slope-third","expr":base},
      {"name":"odd-x-third","expr":["add",base,["mod",["sub",["sub",1,"d"],base],2]]},
      {"name":"odd-x-half","expr":["add",["div",["neg","d"],2],["mod",["sub",["sub",1,"d"],["div",["neg","d"],2]],2]]},
      {"name":"periodic-third","expr":["add",base,["mod","d",3]]},
      {"name":"staircase-fifths","expr":["div",["mul",-2,"d"],5]}
    ]
def random_programs(seed=404,n=6):
    rng=np.random.default_rng(seed);out=[]
    for i in range(n):
        slope=int(rng.integers(1,5));den=int(rng.integers(2,8));period=int(rng.integers(2,6));offset=int(rng.integers(-2,3))
        expr=["add",["div",["mul",-slope,"d"],den],["sub",["mod",["add","d",offset],period],period//2]]
        out.append({"name":"random-"+str(i),"expr":expr})
    return out
def compose(laws):
    hh=[]
    for law in laws:
        p=np.array([a/b for a,b in law["weights"]])
        hh.append(hs(p,maps(law["points"]))[0])
    hh=np.array(hh)
    r=linprog(-hh[:,0],A_ub=hh[:,1:].T,b_ub=np.ones(4),bounds=(0,None),method="highs")
    if not r.success:raise ValueError("finite bank LP failed")
    ids=np.flatnonzero(r.x>1e-9);w=r.x[ids];w/=w.sum()
    selected=[laws[int(i)] for i in ids]
    counts=[max(1,int(round(float(v)*10**30))) for v in w]
    m=max(abs(a*x+b*y) for l in selected for x,y in l["points"] for a,b in FORMS)
    cert={"base":2*m+1,"counts":counts,"laws":selected,"claimed_lower_bound":[0,1]}
    return cert,{"law_indices":ids.tolist(),"weights":w.tolist(),"float_objective":float(-r.fun),"dual_weights":(-r.ineqlin.marginals).tolist(),"warning":"finite-bank numerical LP, not a universal entropy upper bound"}
