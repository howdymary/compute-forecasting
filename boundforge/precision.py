"""High precision refinement of attributed incumbent constructions.
The stationary free-energy/Newton system is described in Jaswal's source README.
Our search uses it as a proposal mechanism; Arb and a separate rational checker certify outputs.
"""
import copy, time
from fractions import Fraction
import mpmath as mp
FORMS=((1,-1),(1,0),(0,1),(1,1),(1,2))
def laws_mp(c):
    return [[mp.mpf(a)/b for a,b in l["weights"]] for l in c["laws"]]
def images(pts,p):
    ds=[{} for _ in FORMS]
    for (x,y),w in zip(pts,p):
        for d,(a,b) in zip(ds,FORMS):d[a*x+b*y]=d.get(a*x+b*y,mp.mpf(0))+w
    return ds
def hv(pts,p):
    return [sum(-q*mp.log(q) for q in d.values()) for d in images(pts,p)]
def rationalise(laws,ps,alpha,digits=100):
    den=10**digits
    out=[]
    for law,p in zip(laws,ps):
        z=sum(p); ws=[max(1,int(mp.floor(v/z*den))) for v in p]
        ws[max(range(len(p)),key=lambda j:p[j])]+=den-sum(ws)
        out.append({"points":copy.deepcopy(law["points"]),"weights":[[v,den] for v in ws]})
    counts=[max(1,int(mp.floor(w*den))) for w in alpha]
    m=max(abs(a*x+b*y) for l in out for x,y in l["points"] for a,b in FORMS)
    return {"problem":"C3c","base":2*m+1,"counts":counts,"laws":out,"claimed_lower_bound":[0,1]}
def refine_composition(c,dps=110):
    mp.mp.dps=dps
    if len(c["laws"])!=2:raise ValueError("two-law refinement only")
    ps=laws_mp(c)
    hs=[hv(l["points"],p) for l,p in zip(c["laws"],ps)]
    candidates=[mp.mpf(0),mp.mpf(1),mp.mpf(c["counts"][0])/sum(c["counts"])]
    for j in range(1,5):
        for k in range(j+1,5):
            den=(hs[0][j]-hs[1][j])-(hs[0][k]-hs[1][k])
            if abs(den)>mp.mpf("1e-100"):
                a=(hs[1][k]-hs[1][j])/den
                if 0<a<1:candidates.append(a)
    def ratio(a):
        h=[a*hs[0][j]+(1-a)*hs[1][j] for j in range(5)]
        return h[0]/max(h[1:])
    a=max(candidates,key=ratio)
    if a<=0 or a>=1:raise ValueError("best composition is boundary; handle separately")
    result=copy.deepcopy(c)
    den=10**100; n=int(mp.floor(a*den))
    result["counts"]=[n,den-n];result["claimed_lower_bound"]=[0,1]
    return result,{"method":"all pairwise denominator intersections and endpoints; 110-digit arithmetic","alpha":mp.nstr(a,100),"ratio_estimate":mp.nstr(ratio(a),100),"candidate_alphas":len(candidates)}
def dual(c):
    ps=laws_mp(c)
    rows=[];rhs=[]
    for law,p in zip(c["laws"],ps):
        ds=images(law["points"],p)[1:]
        for (x,y),w in zip(law["points"],p):
            if w>mp.mpf("1e-14"):
                rows.append([mp.log(d[a*x+b*y]) for d,(a,b) in zip(ds,FORMS[1:])])
                rhs.append(mp.log(w))
    return list(mp.lu_solve(mp.matrix(rows).T*mp.matrix(rows),mp.matrix(rows).T*mp.matrix(rhs)))
def proposals(c,limit=8,radius=22):
    mp.mp.dps=110
    nu=dual(c);options=[]
    for k,(law,p) in enumerate(zip(c["laws"],laws_mp(c))):
        pts=law["points"];ds=images(pts,p)[1:];used=set(map(tuple,pts));targets=set(x-y for x,y in pts)
        for x in range(-radius,radius+1):
            for y in range(-radius,radius+1):
                if (x,y) in used or x-y in targets:continue
                exponent=mp.mpf(1);b=mp.mpf(0);missing=[]
                for j,(a,d) in enumerate(FORMS[1:]):
                    mass=ds[j].get(a*x+d*y)
                    if mass is None:exponent-=nu[j];missing.append(j)
                    else:b+=nu[j]*mp.log(mass)
                if exponent<=0:continue
                logp=b/exponent
                if logp>=-1 or logp<-210:continue
                options.append({"law":k,"point":[x,y],"logp":str(logp),"missing":missing,"heuristic_log_gain":str(logp+mp.log(exponent))})
    options.sort(key=lambda x:mp.mpf(x["heuristic_log_gain"]),reverse=True)
    return options[:limit],[mp.nstr(x,35) for x in nu]
def newton(c,addition=None,seconds=90):
    mp.mp.dps=110
    laws=copy.deepcopy(c["laws"]);ps=laws_mp(c);nu=dual(c)
    if addition is not None:
        k=addition["law"];pt=addition["point"]
        if pt in laws[k]["points"]:raise ValueError("duplicate proposed point")
        eps=mp.exp(mp.mpf(addition.get("logp","-35")))
        eps=min(eps,mp.mpf("0.001"))
        ps[k]=[p*(1-eps) for p in ps[k]]+[eps]
        laws[k]["points"].append(pt)
    if len(laws)!=2:raise ValueError("Newton system expects two laws")
    if any(len({x-y for x,y in l["points"]})!=len(l["points"]) for l in laws):raise ValueError("stationarity formula requires injective target")
    sizes=list(map(len,ps));N=sum(sizes)
    offsets=[0,sizes[0]]
    initial=[mp.log(p) for group in ps for p in group]+nu+[mp.mpf(c["counts"][0])/sum(c["counts"])]
    grouping=[]
    for l in laws:
        ids=[]
        for a,b in FORMS[1:]:
            keys={}
            for i,(x,y) in enumerate(l["points"]):keys.setdefault(a*x+b*y,[]).append(i)
            ids.append(keys)
        grouping.append(ids)
    deadline=time.monotonic()+seconds
    def evaluate(z,jac=False):
        if time.monotonic()>deadline:raise TimeoutError("bounded high precision Newton deadline")
        probabilities=[[mp.exp(z[offsets[k]+i]) for i in range(sizes[k])] for k in range(2)]
        v=z[N:N+4];alpha=z[N+4]
        eq=mp.matrix(N+5,1);J=mp.matrix(N+5,N+5) if jac else None
        hs=[];gradients=[]
        for k,(law,p) in enumerate(zip(laws,probabilities)):
            ds=images(law["points"],p)[1:]
            h=[sum(-q*mp.log(q) for q in d.values()) for d in ds]
            hs.append(h);dg=[]
            for j,(a,b) in enumerate(FORMS[1:]):
                dg.append([-(mp.log(ds[j][a*x+b*y])+1)*pi for (x,y),pi in zip(law["points"],p)])
            gradients.append(dg)
            for i,(x,y) in enumerate(law["points"]):
                row=offsets[k]+i
                eq[row]=z[row]-sum(v[j]*mp.log(ds[j][a*x+b*y]) for j,(a,b) in enumerate(FORMS[1:]))
                if jac:
                    J[row,row]=1
                    for j,(a,b) in enumerate(FORMS[1:]):
                        q=ds[j][a*x+b*y]
                        J[row,N+j]=-mp.log(q)
                        for l in grouping[k][j][a*x+b*y]:J[row,offsets[k]+l]-=v[j]*p[l]/q
            eq[N+k]=sum(p)-1
            if jac:
                for i,pi in enumerate(p):J[N+k,offsets[k]+i]=pi
        for j in range(1,4):
            row=N+1+j
            eq[row]=alpha*(hs[0][j]-hs[0][0])+(1-alpha)*(hs[1][j]-hs[1][0])
            if jac:
                for k,w in enumerate((alpha,1-alpha)):
                    for i in range(sizes[k]):J[row,offsets[k]+i]=w*(gradients[k][j][i]-gradients[k][0][i])
                J[row,N+4]=(hs[0][j]-hs[0][0])-(hs[1][j]-hs[1][0])
        return (eq,J) if jac else eq
    z=mp.matrix(initial);iterations=0;residual=None
    for iteration in range(16):
        eq,J=evaluate(z,True);residual=mp.norm(eq,p=mp.inf)
        iterations=iteration
        if residual<mp.mpf("1e-85"):break
        step=mp.lu_solve(J,-eq)
        scale=mp.mpf(1);accepted=False
        for _ in range(12):
            candidate=z+scale*step
            if 0<candidate[N+4]<1 and min(candidate[N:N+4])>0:
                rr=mp.norm(evaluate(candidate),p=mp.inf)
                if rr<residual:z=candidate;accepted=True;break
            scale/=2
        if not accepted:raise ValueError("Newton line search stalled")
    residual=mp.norm(evaluate(z),p=mp.inf)
    if residual>mp.mpf("1e-65"):raise ValueError("Newton residual too large: "+str(residual))
    pp=[[mp.exp(z[offsets[k]+i]) for i in range(sizes[k])] for k in range(2)]
    alpha=z[N+4]
    cert=rationalise(laws,pp,[alpha,1-alpha])
    return cert,{"method":"analytic stationary free-energy Newton system, attributed to incumbent README","iterations":iterations,"residual":str(residual),"alpha":mp.nstr(alpha,100),"nu":[mp.nstr(t,60) for t in z[N:N+4]],"addition":addition}
