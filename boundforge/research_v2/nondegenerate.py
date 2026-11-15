"""Exploratory entropy-constrained free-energy optimization; no mathematical acceptance changes."""
import time,numpy as np
from scipy.optimize import minimize
from constructions import maps,hs,rational_law
def optimize(pts,nu,seed,initial=None,seconds=25):
    nu=np.array(nu);ids=maps(pts);rng=np.random.default_rng(seed)
    start=time.monotonic();cpu=time.process_time();deadline=start+seconds
    d=np.array([x-y for x,y in pts],dtype=float);best=None;calls=0;status=[]
    def objective(p):
        nonlocal best,calls
        if time.monotonic()>deadline:raise TimeoutError("bounded constrained optimizer")
        calls+=1
        h,g=hs(p,ids);F=h[0]-nu@h[1:];gp=g[0]-nu@g[1:]
        q=np.maximum(p,1e-16);q/=q.sum();hh,_=hs(q,ids)
        ff=hh[0]-nu@hh[1:]
        if hh[0]>=1-1e-7 and (best is None or ff>best[0]):best=(float(ff),q.copy(),hh.copy())
        return -F,-gp
    for restart in range(3):
        p=np.exp(-0.5*(d/(3+restart*3))**2+rng.normal(0,0.2,len(d)))
        if initial is not None and restart==0:p=np.array(initial)
        p=np.maximum(p,1e-16);p/=p.sum()
        constraints=[{"type":"eq","fun":lambda p:p.sum()-1,"jac":lambda p:np.ones_like(p)},
                     {"type":"ineq","fun":lambda p:hs(p,ids)[0][0]-1,"jac":lambda p:hs(p,ids)[1][0]}]
        try:
            r=minimize(objective,p,jac=True,method="SLSQP",bounds=[(1e-16,1)]*len(p),constraints=constraints,
              options={"maxiter":160,"ftol":1e-12,"disp":False})
            status.append(str(r.message))
        except TimeoutError:status.append("timeout");break
    if best is None:raise ValueError("no entropy-feasible numerical iterate")
    F,p,h=best
    return {"law":rational_law(pts,p),"free_energy":F,"entropies":h.tolist(),
      "nondegenerate":bool(h[0]>0.2 and p.max()<.99),"entropy_floor":1.0,"numerical_entropy_feasible":bool(h[0]>=1-1e-7),
      "ratio":float(h[0]/max(h[1:])),"calls":calls,"seconds":time.monotonic()-start,"cpu_seconds":time.process_time()-cpu,"statuses":status}
