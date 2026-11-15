"""Full-universe symmetry-orbit packing probes, outside the preregistered policy study."""
import hashlib,json,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash
from supervisor import verify
def main():
 from ortools.sat.python import cp_model
 out=ROOT/"artifacts/phase2/orbit_search";out.mkdir(parents=True,exist_ok=True)
 inc=Incidence(16);rev16=[int(format(w,"016b")[::-1],2) for w in range(65536)]
 rev14=[int(format(w,"014b")[::-1],2) for w in range(16384)]
 for w in range(65536):
  assert set(inc.desc[w^65535])=={d^16383 for d in inc.desc[w]}
  assert set(inc.desc[rev16[w]])=={rev14[d] for d in inc.desc[w]}
 rows=[]
 for experiment,group in enumerate(["complement","complement_and_reversal"]):
  start=time.perf_counter();orbits=[];desc_masks=[];seen=set();rejected=0
  for w in range(65536):
   if w in seen:continue
   orb=sorted({w,w^65535} if group=="complement" else {w,w^65535,rev16[w],rev16[w]^65535})
   seen.update(orb);used=0;ok=True
   for v in orb:
    if inc.masks[v]&used:ok=False;break
    used|=inc.masks[v]
   if not ok:rejected+=1;continue
   orbits.append(orb);desc_masks.append(used)
  greedy=[];best=[]
  for seed in range(32):
   rng=random.Random(713000+experiment*100+seed);order=list(range(len(orbits)));rng.shuffle(order)
   order.sort(key=lambda i:desc_masks[i].bit_count()/len(orbits[i])+rng.random()*[1,4,12,40][seed%4])
   used=0;selected=[]
   for i in order:
    if not used&desc_masks[i]:selected.append(i);used|=desc_masks[i]
   words=[w for i in selected for w in orbits[i]]
   if len(words)>len(best):best=words;greedy=selected
  path=out/("worker_"+group+"_greedy.txt");path.write_text(canonical(best));greedy_checked=verify(path)
  model=cp_model.CpModel();variables=[model.new_bool_var("o"+str(i)) for i in range(len(orbits))]
  by_desc={}
  for i,orb in enumerate(orbits):
   for w in orb:
    for d in inc.desc[w]:by_desc.setdefault(d,[]).append(variables[i])
  for vv in by_desc.values():
   if len(vv)>1:model.add_at_most_one(vv)
  objective=sum(len(orb)*v for orb,v in zip(orbits,variables))
  model.maximize(objective)
  for i,v in enumerate(variables):model.add_hint(v,int(i in greedy))
  solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=60;solver.parameters.num_search_workers=1
  solver.parameters.random_seed=713000+experiment;solver.parameters.log_search_progress=False
  status=solver.solve(model);name=solver.status_name(status);checked=None
  if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
   result=[w for orb,v in zip(orbits,variables) if solver.value(v) for w in orb]
   p=out/("worker_"+group+"_cp.txt");p.write_text(canonical(result));checked=verify(p)
   if len(result)>len(best):best=result
  row={"group":group,"symmetries_checked_all_words":65536,"candidate_universe_sha256":pool_hash(range(65536)),
   "source_sha":os.environ["GITHUB_SHA"],"valid_orbits":len(orbits),"rejected_internal_collision_orbits":rejected,
   "candidate_definition":"All group orbits in the full 16-bit universe, excluding only orbits with an internal descendant collision",
   "orbit_pool_sha256":hashlib.sha256(json.dumps(orbits,separators=(",",":")).encode()).hexdigest(),
   "encoded_model_sha256":hashlib.sha256(model.proto.SerializeToString()).hexdigest(),
   "fixed_outside":[],"solver_status":name,"solver_seconds":solver.wall_time,"solver_time_cap_seconds":60,"solver_workers":1,
   "solver_best_bound":solver.best_objective_bound,"greedy_verification":greedy_checked,"solver_verification":checked,
   "best_size":len(best),"wall_seconds":time.perf_counter()-start,
   "conclusion":"Optimal within the stated symmetry-invariant family" if status==cp_model.OPTIMAL else
    "Feasible symmetry-invariant code; no optimality conclusion" if checked else "No CP-SAT conclusion; greedy code verified",
   "global_optimality_claim":False}
  rows.append(row);(out/"report.json").write_text(json.dumps({"experiments":rows,"scope":"Exploratory mathematical probes; not part of controlled adaptive-policy evaluation"},indent=2))
  print("ORBIT_SEARCH "+json.dumps({k:v for k,v in row.items() if "verification" not in k}),flush=True)
 repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-radius34";head=os.environ["SOURCE_SHA"]
 def api(path,payload=None,method=None):
  args=["gh","api",path]
  if payload is not None:args+=["--method",method or "POST","--input","-"]
  p=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(p.stdout)
 assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
 parent=api("repos/"+repo+"/git/commits/"+head)
 entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in list(out.glob("*.json"))+list(out.glob("*.txt"))]
 t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries})
 c=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":t["sha"],"message":"Record independently verified symmetry-orbit packing probes and exact scope"})
 api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":c["sha"],"force":False},"PATCH")
if __name__=="__main__":main()
