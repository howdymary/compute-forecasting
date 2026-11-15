"""Bounded FP64 autoconvolution proposals. Only host exact certificates accept records."""
import hashlib,json,pathlib,time
import numpy as np
class SearchDeadline(Exception):pass
def run(spec,source,folder,checkpoint):
 import torch
 torch.set_num_threads(spec.get("threads",4));torch.manual_seed(spec["seed"]);rng=np.random.default_rng(spec["seed"])
 device="cuda" if torch.cuda.is_available() else "cpu";folder=pathlib.Path(folder);folder.mkdir(parents=True,exist_ok=True)
 original=np.load("/opt/codegarden/c2/baseline.npy",allow_pickle=False);assert original.ndim==1 and np.isfinite(original).all() and np.min(original)>=0
 n=len(original);m=2*n-1;L=1
 while L<m:L<<=1
 began=time.monotonic();deadline=began+spec["seconds"];last=[began]
 base=torch.tensor(original,dtype=torch.float64,device=device);mass=float(base.sum());events=[];evaluations=[0]
 def conv(f):
  F=torch.fft.rfft(f,n=L);return torch.fft.irfft(F*F,n=L)[:m]
 def score(f):
  g=conv(f);return (2*torch.sum(g*g)+torch.sum(g[:-1]*g[1:]))/(3*torch.sum(g)*torch.max(g))
 with torch.no_grad():baseline=float(score(base));best=[baseline,base.clone()]
 def save():
  np.save(folder/"best.npy",best[1].detach().cpu().numpy(),allow_pickle=False)
  data={"source_sha":source,"spec":spec,"device":device,"status":"running","baseline_gpu":baseline,"best_gpu":best[0],"evaluations":evaluations[0],"events":events,"seconds":time.monotonic()-began,"floating_proposal_only":True}
  (folder/"checkpoint.json").write_text(json.dumps(data));checkpoint()
 # Record the actual FFT backend, not a promised GPU speedup.
 started=time.monotonic()
 with torch.no_grad():
  for _ in range(3):score(base)
 if device=="cuda":torch.cuda.synchronize()
 device_forward=(time.monotonic()-started)/3
 cpu_started=time.monotonic()
 with torch.no_grad():score(torch.tensor(original,dtype=torch.float64,device="cpu"))
 cpu_forward=time.monotonic()-cpu_started
 profile={"cpu_forward_seconds":cpu_forward,"device":device,"gpu_name":torch.cuda.get_device_name() if device=="cuda" else None,"score_seconds":device_forward,"torch":str(torch.__version__)}
 save();cycle=0;current=best[1].detach().clone();terminal_status="completed";partial_error=None
 try:
  while time.monotonic()<deadline:
   if spec["propagation"]=="greedy_best" or cycle==0:current=best[1].detach().clone()
   if cycle:
    noise=torch.tensor(rng.uniform(0,spec["noise"],n),dtype=torch.float64,device=device);current=current+noise
   for beta in spec["betas"]:
    for outer in range(spec.get("outer",2)):
     if time.monotonic()>=deadline:raise SearchDeadline()
     with torch.no_grad():
      gg=conv(current);peak=float(gg.max());lam=float(score(current));reference=float(gg.sum()*gg.max())
     tau=max(peak/beta,1e-30);w=torch.sqrt(torch.clamp(current,min=0)).detach().requires_grad_(True)
     optimizer=torch.optim.LBFGS([w],lr=1,max_iter=spec.get("max_iter",80),max_eval=spec.get("max_eval",120),history_size=30,line_search_fn="strong_wolfe",tolerance_grad=1e-14,tolerance_change=1e-15)
     inner_best=[lam,current.detach().clone()]
     def closure():
      if time.monotonic()>=deadline:raise SearchDeadline()
      optimizer.zero_grad();raw=w*w;f=raw*(mass/torch.clamp(raw.sum(),min=1e-300));g=conv(f)
      numerator=(2*torch.sum(g*g)+torch.sum(g[:-1]*g[1:]))/3;total=torch.sum(g);peak_now=g.max()
      exact_float=float((numerator/(total*peak_now)).detach())
      if not np.isfinite(exact_float) or not 0<exact_float<1.00000001:raise RuntimeError("Invalid numerical state")
      evaluations[0]+=1
      if exact_float>inner_best[0]:inner_best[0]=exact_float;inner_best[1]=f.detach().clone()
      if exact_float>best[0]:best[0]=exact_float;best[1]=f.detach().clone()
      # Fixed temperature within each inner solve, and fixed mass, remove scale drift.
      proxy=tau*torch.logsumexp(g/tau,dim=0);loss=-(numerator-lam*total*proxy)/reference
      if not torch.isfinite(loss):raise RuntimeError("Nonfinite loss")
      loss.backward()
      if time.monotonic()-last[0]>30:last[0]=time.monotonic();save()
      return loss
     optimizer.step(closure)
     if spec["propagation"]=="endpoint":
      with torch.no_grad():
       raw=w*w;current=(raw*(mass/torch.clamp(raw.sum(),min=1e-300))).detach().clone()
       if not torch.isfinite(current).all():raise RuntimeError("Nonfinite endpoint")
     else:current=inner_best[1]
     with torch.no_grad():endpoint_score=float(score(current))
     events.append({"cycle":cycle,"beta":beta,"outer":outer,"inner_best":inner_best[0],"endpoint_score":endpoint_score,"propagation":spec["propagation"],"best_gpu":best[0],"evaluations":evaluations[0],"seconds":time.monotonic()-began})
     if spec["propagation"]=="greedy_best" and inner_best[0]<=lam+1e-13:break
   cycle+=1
 except SearchDeadline:pass
 except Exception as e:
  terminal_status="partial_error";partial_error=str(e)[:1000]
 save()
 path=folder/"best.npy";result={"source_sha":source,"spec":spec,"status":terminal_status,"partial_error":partial_error,"profile":profile,"baseline_gpu":baseline,"best_gpu":best[0],"evaluations":evaluations[0],"cycles":cycle,"wall_seconds":time.monotonic()-began,"events":events,"best_rel":str(path.relative_to("/codegarden/results")),"best_npy_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"record_claim":False}
 (folder/"result.json").write_text(json.dumps(result));checkpoint();return result
