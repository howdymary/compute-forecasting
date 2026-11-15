"""Area-gradient proposals and bounded structural search. Certificates are separate."""
import ctypes,json,os,pathlib,time
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parent
class Kernel:
 def __init__(self,path=None):
  self.lib=ctypes.CDLL(str(path or ROOT/".build/area.so"));self.fn=self.lib.cg_area_grad
  self.fn.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_int)]
  self.fn.restype=ctypes.c_int
 def __call__(self,x):
  x=np.ascontiguousarray(x,dtype=np.float64);g=np.empty_like(x);a=ctypes.c_double();slabs=ctypes.c_int()
  rc=self.fn(len(x),x.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),ctypes.byref(a),g.ctypes.data_as(ctypes.POINTER(ctypes.c_double)),ctypes.byref(slabs))
  if rc:raise ValueError("Kernel status "+str(rc))
  return a.value,g,slabs.value
def witness(x):
 return {"offsets":[format(float(v-x[0]),".18f") for v in x]}
class BudgetStop(Exception):pass
def run(spec,baseline,source,folder,checkpoint):
 from scipy.optimize import minimize
 from verify import verify
 folder=pathlib.Path(folder);folder.mkdir(parents=True,exist_ok=True)
 kernel=Kernel();rng=np.random.default_rng(spec["seed"]);start=time.monotonic();deadline=start+spec["seconds"];last=[start]
 x=np.array([float(v) for v in baseline["offsets"]]);x-=x[0];baseline_area=kernel(x)[0];best=[baseline_area,x.copy()];evaluations=[0];events=[];trial=[0]
 def save():
  data={"source_sha":source,"spec":spec,"status":"running","best_native_area":best[0],"best_proposal":witness(best[1]),"evaluations":evaluations[0],"completed_trials":trial[0],"seconds":time.monotonic()-start,"floating_proposal_only":True}
  (folder/"checkpoint.json").write_text(json.dumps(data));checkpoint()
 def objective(z):
  if time.monotonic()>=deadline:raise BudgetStop()
  xx=np.concatenate(([0.],z));a,g,_=kernel(xx);evaluations[0]+=1
  if a<best[0]:best[0]=a;best[1]=xx.copy()
  if time.monotonic()-last[0]>15:last[0]=time.monotonic();save()
  return a,g[1:]
 current=x.copy();current_a=baseline_area;stale=0
 save()
 while time.monotonic()<deadline:
  before=best[0];proposal=current.copy();description={"trial":trial[0],"policy":spec["policy"]}
  if trial[0]:
   width=int(rng.choice(spec["widths"]));begin=int(rng.integers(0,129-width));amplitude=float(rng.choice(spec["amplitudes"]))*float(rng.normal())
   perturb=np.zeros(128);perturb[begin:begin+width]=amplitude;perturb-=perturb[0]
   if spec["policy"]=="coordinate":
    noise=rng.normal(size=127);noise*=np.linalg.norm(perturb[1:])/max(np.linalg.norm(noise),1e-300);perturb=np.concatenate(([0.],noise))
   elif spec["policy"]=="structural" and trial[0]%5==0:
    reflected=-proposal[begin:begin+width][::-1];reflected+=np.mean(proposal[begin:begin+width])-np.mean(reflected);proposal[begin:begin+width]=reflected
   proposal+=perturb;proposal-=proposal[0]
   description.update(begin=begin,width=width,amplitude=amplitude,perturbation_l2=float(np.linalg.norm(perturb)))
  try:
   result=minimize(objective,proposal[1:],jac=True,method="L-BFGS-B",bounds=[(-3.,3.)]*127,options={"maxiter":100,"maxfun":240,"maxls":20,"ftol":1e-14,"gtol":1e-8})
   candidate=np.concatenate(([0.],result.x));a=kernel(candidate)[0];description.update(local_area=a,optimizer_status=int(result.status),local_evaluations=int(result.nfev))
  except BudgetStop:break
  # Same bounded basin-hopping rule in paired policies; retain a separate best proposal.
  accepted=a<current_a or rng.random()<np.exp(min(0.,(current_a-a)/spec["temperature"]))
  if accepted:current=candidate;current_a=a
  stale=stale+1 if best[0]>=before-1e-12 else 0
  description.update(accepted=bool(accepted),best_native_area=best[0],seconds=time.monotonic()-start,stagnation_trials=stale);events.append(description);trial[0]+=1
  if stale>=8:
   current=best[1].copy();stale=0
  if time.monotonic()-last[0]>15:last[0]=time.monotonic();save()
 data=witness(best[1]);(folder/"best_proposal.json").write_text(json.dumps(data,indent=2))
 result={"source_sha":source,"spec":spec,"status":"completed","baseline_native_area":baseline_area,"best_native_area":best[0],"evaluations":evaluations[0],"completed_trials":trial[0],"wall_seconds":time.monotonic()-start,"moves":events,"proposal":data,"durable_folder":str(folder),"record_claim":False}
 if best[0]<baseline_area-1e-11:
  try:result["verification"]=verify(data)
  except Exception as e:result["verification_rejected"]=str(e)[:1500]
 result["native_improvement_only"]=best[0]<baseline_area
 result["certified_arena_improvement"]=bool(result.get("verification",{}).get("accepted") and result["verification"]["score"]<spec["arena_incumbent"]-1e-9)
 (folder/"result.json").write_text(json.dumps(result));checkpoint();return result
