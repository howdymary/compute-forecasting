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
def quota_topk(scores,k,core,outside,quota):
 import torch
 vc,ic=torch.topk(scores.index_select(0,core),min(quota,len(core),k),dim=0);vo,io=torch.topk(scores.index_select(0,outside),k,dim=0)
 ids=torch.cat([core[ic],outside[io]],dim=0);values=torch.cat([vc,vo],dim=0);take=torch.topk(values,k,dim=0).indices
 return ids.gather(0,take)
def mixed_topk(scores,k,core,outside,quota):
 import torch
 half=scores.shape[1]//2
 return torch.cat([torch.topk(scores[:,:half],k,dim=0).indices,quota_topk(scores[:,half:],k,core,outside,quota)],dim=1)
def common_core():
 info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());return sorted(set.intersection(*(set(C) for C in info["codes"])))
def quota_test():
 import torch,itertools
 torch.manual_seed(1240201);scores=torch.randn((32,3));core=torch.arange(8);outside=torch.arange(8,32);rows=[]
 for limit in [0,1,2,3]:
  ids=quota_topk(scores,3,core,outside,limit)
  for b in range(3):
   chosen=ids[:,b].tolist();assert len(set(chosen))==3 and sum(w<8 for w in chosen)<=limit
   expected=max(sum(float(scores[w,b]) for w in C) for C in itertools.combinations(range(32),3) if sum(w<8 for w in C)<=limit)
   assert abs(sum(float(scores[w,b]) for w in chosen)-expected)<1e-5;rows.append({"limit":limit,"column":b,"exact_selection_agrees":True})
 return rows
def profile(device="cpu",batch=32,steps=10,core=None,quota=206):
 import torch
 torch.set_num_threads(1);torch.manual_seed(1240101);t=time.monotonic();inc,A,AT,sizes=matrices(16,device);build=time.monotonic()-t
 scores=torch.randn((65536,batch),device=device);h=torch.zeros_like(scores);core=core if core is not None else common_core();ci=torch.tensor(core,dtype=torch.int64,device=device);oi=torch.tensor([w for w in range(65536) if w not in set(core)],dtype=torch.int64,device=device)
 def step():
  ids=mixed_topk(scores,227,ci,oi,quota);h.zero_();h.scatter_(0,ids,1);q,E,g=evaluate(A,AT,sizes,h);scores.add_(g,alpha=-.001)
 for _ in range(2):step()
 synchronize(device);t=time.monotonic()
 for _ in range(steps):step()
 synchronize(device);elapsed=time.monotonic()-t
 return {"device":device,"batch":batch,"steps":steps,"seconds":elapsed,"seconds_per_step":elapsed/steps,"build_seconds":build,"nnz":A._nnz(),"torch":torch.__version__,
  "device_name":torch.cuda.get_device_name() if str(device).startswith("cuda") else "CPU","quota":quota,"core_sha256":hashlib.sha256(json.dumps(core).encode()).hexdigest(),"includes":"unrestricted/quota-limited top227 selection, sparse occupancy, raw conflict energy, sparse all-word derivative, score update; synchronized timer"}
def search(device,seconds,seed,out,starting,batch=32,action="penalty_topk",core=None,quota=206,max_steps=None):
 import torch
 torch.set_num_threads(1);torch.manual_seed(seed);inc,A,AT,sizes=matrices(16,device);N=65536;M=16384;target=227
 assert batch%4==0;group=batch//4;scores=(torch.randn((N,group),device=device)*.1).repeat(1,4)
 for b in range(batch):scores[[int(w,2) for w in starting[(b%group)%len(starting)]],b]+=3
 core=core if core is not None else common_core();ci=torch.tensor(core,dtype=torch.int64,device=device);oi=torch.tensor([w for w in range(N) if w not in set(core)],dtype=torch.int64,device=device)
 labels=["unrestricted_fixed","unrestricted_adaptive","quota_fixed","quota_adaptive"];adaptive=[b for b in range(batch) if (b//group)%2==1]
 h=torch.zeros_like(scores);momentum=torch.zeros_like(scores);weights=torch.ones((M,batch),device=device);wsize=sizes[:,None].expand(N,batch).clone()
 bestE=[10**9]*batch;last=[0]*batch;bestWords=[None]*batch;archive={};progress=[];start=time.monotonic();lastsave=0;steps=0;winner=None
 while time.monotonic()-start<seconds and (max_steps is None or steps<max_steps):
  noise=torch.tensor([min(2.5,.05+(steps-last[b])*.0005) if b in adaptive else .05 for b in range(batch)],device=device)
  ids=mixed_topk(scores+torch.randn((N,group),device=device).repeat(1,4)*noise,227,ci,oi,quota);h.zero_();h.scatter_(0,ids,1)
  q=torch.sparse.mm(A,h);E=(q.square().sum(0)-(sizes[:,None]*h).sum(0))/2
  gradient=torch.sparse.mm(AT,q*weights)-h*wsize
  momentum.mul_(.8).add_(gradient,alpha=.2);scale=1+gradient.mean(0);scores.add_(-.07*momentum/scale);scores.sub_(scores.mean(0));scores.clamp_(-12,12)
  if steps%40==0:
   energies=[int(round(x)) for x in E.cpu().tolist()];chosen=ids.cpu().tolist()
   for b,e in enumerate(energies):
    if e<bestE[b]:bestE[b]=e;last[b]=steps;bestWords[b]=sorted(chosen[i][b] for i in range(227))
    if e<=32:
     C=sorted(chosen[i][b] for i in range(227));assert len(set(C))==227;actual=independent_energy(inc,C);assert actual==e,"Tensor/integer energy disagreement"
     key=digest_words(C)
     if key not in archive:archive[key]={"words":C,"raw_energy":e,"step":steps,"replica":b,"condition":labels[b//group],"core_overlap":sum(w in set(core) for w in C)}
     if e==0:
      p=out/"candidate.txt";p.write_text(canonical(C));winner={"words":C,"verification":verify(p)};assert winner["verification"]["cardinality"]==227;break
   if winner:break
   if action=="penalty_topk":
    weights[:,adaptive]+=.04*(q[:,adaptive]>1);weights.clamp_(1,6)
    if steps%400==0:weights[:,adaptive]=1+(weights[:,adaptive]-1)*.9
    wsize=torch.sparse.mm(AT,weights)
   for b in adaptive:
    if steps-last[b]>1600 and bestWords[b]:
     scores[:,b].normal_(0,.15);keep=bestWords[b][:]
     # Deterministic RNG from the recorded seed/step; destroy a substantial fraction.
     rng=random.Random(seed+steps*1009+b);rng.shuffle(keep);scores[keep[:180],b]+=3;last[b]=steps
  steps+=1;elapsed=time.monotonic()-start
  if elapsed-lastsave>=20:
   ordered=sorted(archive.items(),key=lambda kv:(kv[1]["raw_energy"],kv[1]["step"]));kept={};counts=collections.Counter()
   for key,item in ordered:
    if counts[item["condition"]]<16:kept[key]=item;counts[item["condition"]]+=1
   archive=kept
   progress.append({"seconds":elapsed,"step":steps,"minimum_raw_energy":min(bestE),"mathematical_best_retained":226})
   (out/"tensor_checkpoint.json").write_text(json.dumps({"source_sha":os.environ.get("GITHUB_SHA"),"seed":seed,"steps":steps,"minimum_raw_energy":min(bestE),"archive":list(archive.values()),"progress":progress,"scope":"Positive energy states are invalid diagnostic target-size states, never accepted codes."}));lastsave=elapsed
 for b,C in enumerate(bestWords):
  if C is not None:
   actual=independent_energy(inc,C);assert actual==bestE[b]
   archive.setdefault(digest_words(C),{"words":C,"raw_energy":actual,"step":last[b],"replica":b,"condition":labels[b//group],"core_overlap":sum(w in set(core) for w in C),"per_replica_best":True})
 ordered=sorted(archive.items(),key=lambda kv:(kv[1]["raw_energy"],kv[1]["step"]));kept={};counts=collections.Counter()
 for key,item in ordered:
  if counts[item["condition"]]<16:kept[key]=item;counts[item["condition"]]+=1
 # Always retain every replica best even if an equal-energy beam filled its condition.
 for b,C in enumerate(bestWords):
  if C is not None:kept[digest_words(C)]=archive[digest_words(C)]
 archive=kept
 synchronize(device)
 return {"device":device,"seed":seed,"batch":batch,"action":action,"steps":steps,"wall_seconds":time.monotonic()-start,"minimum_raw_energy":min(bestE),
  "per_replica_minimum_energy":bestE,"condition_minimum_energy":{labels[i]:min(bestE[i*group:(i+1)*group]) for i in range(4)},"quota":quota,"core_count":len(core),"best_independently_verified":227 if winner else 226,"archive":list(sorted(archive.values(),key=lambda r:(r["raw_energy"],r["step"]))),"winner":winner,
  "scope":"Full binary universe; target227 distinct words. Fixed-noise and adaptive replicas share batch compute; no claim of policy superiority from energies. Only independent accepted witness cardinality is a mathematical result."}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--action",choices=["test","profile","search"],required=True);ap.add_argument("--device",default="cpu");ap.add_argument("--seconds",type=float,default=60);ap.add_argument("--quota",type=int,default=206);ap.add_argument("--steps",type=int,default=None);a=ap.parse_args()
 out=ROOT/"artifacts/phase3/tensor_cpu_004";out.mkdir(parents=True,exist_ok=True);check_integrity()
 if a.action=="test":r=selftest();r["quota_tests"]=quota_test()
 elif a.action=="profile":r=profile(a.device,quota=a.quota)
 else:
  baseline=next((ROOT/"artifacts/baselines").glob("arena_226_*.txt"));v=verify(baseline);r=search(a.device,a.seconds,1241001,out,[baseline.read_text().splitlines()],16,core=common_core(),quota=a.quota);r["baseline_verification"]=v
 (out/(a.action+".json")).write_text(json.dumps(r,indent=2));print("TENSOR",json.dumps({k:v for k,v in r.items() if k not in ["archive","winner","cases","baseline_verification"]}),flush=True)
if __name__=="__main__":main()
