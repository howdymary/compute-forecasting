"""Dominance-safe reduction and full reduced-universe elastic packing at target 227."""
import collections,datetime as dt,hashlib,importlib.util,json,os,pathlib,random,subprocess,sys,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash,digest_words
from supervisor import verify
spec=importlib.util.spec_from_file_location("soft_protected_strings",ROOT/"protected/verify_descendants.py")
D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
def reduce(inc):
 dominated={};order=sorted(range(inc.N),key=lambda w:(inc.sizes[w],w))
 for u in order:
  if u in dominated:continue
  rare=min(inc.desc[u],key=lambda d:len(inc.children[d]))
  for v in inc.children[rare]:
   if v==u or v in dominated:continue
   if inc.sizes[v]<inc.sizes[u] or (inc.sizes[v]==inc.sizes[u] and v<u):continue
   if inc.masks[v]&inc.masks[u]==inc.masks[u]:dominated[v]=u
 return dominated,[w for w in range(inc.N) if w not in dominated]
def model_for(inc,pool,target,hint,cap,soft=True):
 from ortools.sat.python import cp_model
 model=cp_model.CpModel();variables={w:model.new_bool_var("w"+str(w)) for w in pool}
 bydesc=collections.defaultdict(list)
 for w,v in variables.items():
  for d in inc.desc[w]:bydesc[d].append(v)
 model.add(sum(variables.values())==target);slacks={}
 counts=collections.Counter(d for w in hint for d in inc.desc[w])
 for d,vv in bydesc.items():
  if len(vv)>1:
   if soft:
    z=model.new_int_var(0,cap,"over"+str(d));slacks[d]=z;model.add(sum(vv)<=1+z);model.add_hint(z,max(0,counts[d]-1))
   else:model.add_at_most_one(vv)
 if soft:model.add(sum(slacks.values())<=cap);model.minimize(sum(slacks.values()))
 for w,v in variables.items():model.add_hint(v,int(w in hint))
 return model,variables,slacks
def main():
 from ortools.sat.python import cp_model
 out=ROOT/"artifacts/phase3/soft_global_001";out.mkdir(parents=True,exist_ok=True)
 small=[]
 for n in range(3,7):
  inc=Incidence(n);dom,pool=reduce(inc);values=[]
  for candidate in [list(range(inc.N)),pool]:
   model=cp_model.CpModel();vv={w:model.new_bool_var("w"+str(w)) for w in candidate};children=collections.defaultdict(list)
   for w,v in vv.items():
    for d in inc.desc[w]:children[d].append(v)
   for arr in children.values():model.add_at_most_one(arr)
   model.maximize(sum(vv.values()));solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=20;solver.parameters.num_search_workers=1
   status=solver.solve(model);assert status==cp_model.OPTIMAL,"Small dominance regression must be exact"
   words=[format(w,"0%db"%n) for w,v in vv.items() if solver.value(v)]
   D.verify(words,n=n);values.append(len(words))
  assert values[0]==values[1];small.append({"n":n,"full_optimum":values[0],"reduced_optimum":values[1],"removed":len(dom),"complete":True})
 (out/"small_tests.json").write_text(json.dumps(small,indent=2))
 inc=Incidence(16);start=time.perf_counter();dom,pool=reduce(inc);cert=[]
 cache={}
 def ds(w):
  if w not in cache:cache[w]=set(D.descendants(format(w,"016b")))
  return cache[w]
 for v,u in dom.items():
  assert u not in dom and ds(u)<=ds(v)
  cert.append({"removed":v,"replacement":u,"replacement_descendants":len(ds(u)),"removed_descendants":len(ds(v))})
 reduction={"source_sha":os.environ["GITHUB_SHA"],"candidate_universe":65536,"remaining":len(pool),"removed":len(dom),"candidate_pool":pool,
  "candidate_pool_sha256":pool_hash(pool),"certificates":cert,"independent_string_subset_checks":len(cert),"seconds":time.perf_counter()-start,
  "proof":"Every removed candidate v has a retained u with nonempty D2(u) subset D2(v). In any valid code containing v, u cannot already be another codeword; replacing v by u preserves cardinality and cannot introduce a collision. Processing all such replacements yields a code entirely in the retained pool.",
  "record_claim":False}
 (out/"dominance.json").write_text(json.dumps(reduction,indent=2));del cache
 baseline=(ROOT/"artifacts/best_code.txt").read_text().splitlines();accepted=verify(ROOT/"artifacts/best_code.txt")
 mapped=sorted(dom.get(int(w,2),int(w,2)) for w in baseline);assert len(set(mapped))==len(mapped);inc.occupied(mapped)
 # Safe replacements may release descendants. Attempt free greedy additions first.
 occupied=inc.occupied(mapped)
 for w in sorted(pool,key=lambda w:(inc.sizes[w],w)):
  if not inc.masks[w]&occupied:mapped.append(w);occupied|=inc.masks[w]
 path=out/"worker_dominance_greedy.txt";path.write_text(canonical(mapped));mapped_checked=verify(path)
 target=accepted["cardinality"]+1
 if len(mapped)>=target:
  (out/"report.json").write_text(json.dumps({"verified_improvement":mapped_checked,"witness":str(path.relative_to(ROOT.parent)),"global_record_audit_pending":True},indent=2));return
 hint=set(mapped);scores=collections.Counter(d for w in hint for d in inc.desc[w])
 extra=min((w for w in pool if w not in hint),key=lambda w:(sum(scores[d] for d in inc.desc[w]),w));hint.add(extra)
 assert len(hint)==target;counts=collections.Counter(d for w in hint for d in inc.desc[w]);cap=sum(max(0,c-1) for c in counts.values());assert cap>0
 model,vv,slacks=model_for(inc,pool,target,hint,cap);proto_hash=hashlib.sha256(model.proto.SerializeToString()).hexdigest();rows=[]
 for presolve in [True,False]:
  solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=90;solver.parameters.num_search_workers=2;solver.parameters.random_seed=951611
  solver.parameters.cp_model_presolve=presolve;t=time.perf_counter();cput=time.process_time();status=solver.solve(model)
  assert status!=cp_model.INFEASIBLE,"Encoded elastic model contradicts its explicit feasible target-size hint"
  row={"status":solver.status_name(status),"presolve":presolve,"time_cap_seconds":90,"workers":2,"wall_seconds":time.perf_counter()-t,"cpu_seconds":time.process_time()-cput,
   "target":target,"initial_slack_cap":cap,"candidate_pool_sha256":pool_hash(pool),"encoded_model_sha256":proto_hash,
   "objective":"Sum of descendant over-occupancy, not pair energy. Zero is valid; a positive value is invalid.","proof_artifact":None}
  if status in [cp_model.FEASIBLE,cp_model.OPTIMAL]:
   words=[w for w,v in vv.items() if solver.value(v)];cc=collections.Counter(d for w in words for d in inc.desc[w])
   cost=sum(max(0,c-1) for c in cc.values());row["actual_slack_energy"]=cost;row["solver_objective"]=solver.objective_value;row["solver_bound"]=solver.best_objective_bound
   assert cost==round(solver.objective_value);row["diagnostic_target_state"]=words
   if cost==0:
    path=out/("worker_soft_global_"+str(int(presolve))+".txt");path.write_text(canonical(words));row["independent_verification"]=verify(path)
   else:row["accepted_as_code"]=False
  rows.append(row);(out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"small_tests":small,"mapped_baseline":mapped_checked,
    "reduced_candidates":len(pool),"experiments":rows,"global_optimality_claim":False},indent=2))
  print("GLOBAL_SOFT "+json.dumps({k:v for k,v in row.items() if k!="diagnostic_target_state"}),flush=True)
  if row.get("actual_slack_energy")==0:break
if __name__=="__main__":main()
