"""Sparse tensor search over exact distinct-deletion incidence; only protected verifiers accept codes."""
import argparse,collections,hashlib,importlib.util,json,os,pathlib,random,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words
from supervisor import verify,check_integrity
def matrices(n,device):
 import torch
 inc=Incidence(n);rows=[];cols=[]
 for w,ds in enumerate(inc.desc):
  for d in ds:rows.append(d);cols.append(w)
 ij=torch.tensor([rows,cols],dtype=torch.int64);coo=torch.sparse_coo_tensor(ij,torch.ones(len(rows)),(inc.M,inc.N)).coalesce()
 A=coo.to_sparse_csr().to(device);AT=coo.transpose(0,1).coalesce().to_sparse_csr().to(device)
 sizes=torch.tensor(inc.sizes,dtype=torch.float32,device=device);return inc,A,AT,sizes
def synchronize(device):
 import torch
 if str(device).startswith("cuda"):torch.cuda.synchronize()
def evaluate(A,AT,sizes,h,weights=None):
 import torch
 q=torch.sparse.mm(A,h);energy=(q.square().sum(0)-(sizes[:,None]*h).sum(0))/2
 if weights is None:gradient=torch.sparse.mm(AT,q)-h*sizes[:,None]
 else:gradient=torch.sparse.mm(AT,q*weights)-h*torch.sparse.mm(AT,weights)
 return q,energy,gradient
def independent_energy(inc,words):
 count=collections.Counter(d for w in words for d in inc.desc[w]);return sum(v*(v-1)//2 for v in count.values())
def selftest():
 import torch
 torch.set_num_threads(1);inc,A,AT,sizes=matrices(6,"cpu")
 spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 ds={w:{int(s,2) for s in D.descendants(format(w,"06b"))} for w in range(64)}
 assert all(set(inc.desc[w])==ds[w] for w in ds);rng=random.Random(1240001);cases=[]
 for k in range(3,9):
  B=8;h=torch.zeros((64,B));words=[rng.sample(range(64),k) for _ in range(B)]
  for b,C in enumerate(words):h[C,b]=1
  weights=torch.tensor([[rng.randrange(1,4) for _ in range(B)] for _ in range(16)],dtype=torch.float32)
  q,E,g=evaluate(A,AT,sizes,h,weights)
  for b,C in enumerate(words):
   counts=collections.Counter(d for w in C for d in ds[w]);expected=sum(c*(c-1)//2 for c in counts.values());assert E[b].item()==expected
   for w in range(64):
    expected_g=sum(int(weights[d,b])*(counts[d]-int(w in C)) for d in ds[w]);assert g[w,b].item()==expected_g
   cases.append({"k":k,"energy":expected,"literal_string_energy_agrees":True,"all64_weighted_derivatives_agree":True})
 valid=[0,7,56,63];h=torch.zeros((64,1));h[valid,0]=1;assert evaluate(A,AT,sizes,h)[1].item()==0;D.verify([format(w,"06b") for w in valid],6)
 return {"passed":True,"cases":cases,"distinct_descendants_checked_for_all64_words":True,"positive_small_baseline":4}
def profile(device="cpu",batch=32,steps=10):
 import torch
 torch.set_num_threads(1);torch.manual_seed(1240101);t=time.monotonic();inc,A,AT,sizes=matrices(16,device);build=time.monotonic()-t
 scores=torch.randn((65536,batch),device=device);h=torch.zeros_like(scores)
 def step():
  ids=torch.topk(scores,227,dim=0).indices;h.zero_();h.scatter_(0,ids,1);q,E,g=evaluate(A,AT,sizes,h);scores.add_(g,alpha=-.001)
 for _ in range(2):step()
 synchronize(device);t=time.monotonic()
 for _ in range(steps):step()
 synchronize(device);elapsed=time.monotonic()-t
 return {"device":device,"batch":batch,"steps":steps,"seconds":elapsed,"seconds_per_step":elapsed/steps,"build_seconds":build,"nnz":A._nnz(),"torch":torch.__version__,
  "device_name":torch.cuda.get_device_name() if str(device).startswith("cuda") else "CPU","includes":"top227 selection, sparse occupancy, raw conflict energy, sparse all-word derivative, score update; synchronized timer"}
def search(device,seconds,seed,out,starting,batch=32,action="penalty_topk"):
 import torch
 torch.set_num_threads(1);torch.manual_seed(seed);inc,A,AT,sizes=matrices(16,device);N=65536;M=16384;target=227
 scores=torch.randn((N,batch),device=device)*.1
 for b in range(batch):scores[[int(w,2) for w in starting[b%len(starting)]],b]+=3
 h=torch.zeros_like(scores);momentum=torch.zeros_like(scores);weights=torch.ones((M,batch),device=device);wsize=sizes[:,None].expand(N,batch).clone()
 bestE=[10**9]*batch;last=[0]*batch;bestWords=[None]*batch;archive={};progress=[];start=time.monotonic();lastsave=0;steps=0;winner=None
 while time.monotonic()-start<seconds:
  noise=torch.tensor([.05 if b<batch//2 else min(2.5,.05+(steps-last[b])*.0005) for b in range(batch)],device=device)
  ids=torch.topk(scores+torch.randn_like(scores)*noise,227,dim=0).indices;h.zero_();h.scatter_(0,ids,1)
  q=torch.sparse.mm(A,h);E=(q.square().sum(0)-(sizes[:,None]*h).sum(0))/2
  gradient=torch.sparse.mm(AT,q*weights)-h*wsize
  momentum.mul_(.8).add_(gradient,alpha=.2);scale=1+gradient.mean(0);scores.add_(-.07*momentum/scale);scores.sub_(scores.mean(0));scores.clamp_(-12,12)
  if steps%40==0:
   energies=[int(round(x)) for x in E.cpu().tolist()];chosen=ids.cpu().tolist()
   for b,e in enumerate(energies):
    if e<bestE[b]:bestE[b]=e;last[b]=steps;bestWords[b]=sorted(chosen[i][b] for i in range(227))
    if e<=8:
     C=sorted(chosen[i][b] for i in range(227));assert len(set(C))==227;actual=independent_energy(inc,C);assert actual==e,"Tensor/integer energy disagreement"
     key=digest_words(C)
     if key not in archive:archive[key]={"words":C,"raw_energy":e,"step":steps,"replica":b,"condition":"fixed_noise" if b<batch//2 else action}
     if e==0:
      p=out/"candidate.txt";p.write_text(canonical(C));winner={"words":C,"verification":verify(p)};assert winner["verification"]["cardinality"]==227;break
   if winner:break
   if action=="penalty_topk":
    weights[:,batch//2:]+=.04*(q[:,batch//2:]>1);weights.clamp_(1,6)
    if steps%400==0:weights[:,batch//2:]=1+(weights[:,batch//2:]-1)*.9
    wsize=torch.sparse.mm(AT,weights)
   for b in range(batch//2,batch):
    if steps-last[b]>1600 and bestWords[b]:
     scores[:,b].normal_(0,.15);keep=bestWords[b][:]
     # Deterministic RNG from the recorded seed/step; destroy a substantial fraction.
     rng=random.Random(seed+steps*1009+b);rng.shuffle(keep);scores[keep[:180],b]+=3;last[b]=steps
  steps+=1;elapsed=time.monotonic()-start
  if elapsed-lastsave>=20:
   archive=dict(sorted(archive.items(),key=lambda kv:(kv[1]["raw_energy"],kv[1]["step"]))[:64])
   progress.append({"seconds":elapsed,"step":steps,"minimum_raw_energy":min(bestE),"mathematical_best_retained":226})
   (out/"tensor_checkpoint.json").write_text(json.dumps({"source_sha":os.environ.get("GITHUB_SHA"),"seed":seed,"steps":steps,"minimum_raw_energy":min(bestE),"archive":list(archive.values()),"progress":progress,"scope":"Positive energy states are invalid diagnostic target-size states, never accepted codes."}));lastsave=elapsed
 synchronize(device)
 return {"device":device,"seed":seed,"batch":batch,"action":action,"steps":steps,"wall_seconds":time.monotonic()-start,"minimum_raw_energy":min(bestE),
  "per_replica_minimum_energy":bestE,"archive":list(sorted(archive.values(),key=lambda r:(r["raw_energy"],r["step"]))[:64]),"winner":winner,
  "scope":"Full binary universe; target227 distinct words. Fixed-noise and adaptive replicas share batch compute; no claim of policy superiority from energies. Only independent accepted witness cardinality is a mathematical result."}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--action",choices=["test","profile","search"],required=True);ap.add_argument("--device",default="cpu");ap.add_argument("--seconds",type=float,default=30);a=ap.parse_args()
 out=ROOT/"artifacts/phase3/tensor_cpu_001";out.mkdir(parents=True,exist_ok=True);check_integrity()
 if a.action=="test":r=selftest()
 elif a.action=="profile":r=profile(a.device)
 else:
  baseline=next((ROOT/"artifacts/baselines").glob("arena_226_*.txt"));v=verify(baseline);r=search(a.device,a.seconds,1241001,out,[baseline.read_text().splitlines()],16);r["baseline_verification"]=v
 (out/(a.action+".json")).write_text(json.dumps(r,indent=2));print("TENSOR",json.dumps({k:v for k,v in r.items() if k not in ["archive","winner","cases","baseline_verification"]}),flush=True)
if __name__=="__main__":main()
