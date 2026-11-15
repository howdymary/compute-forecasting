"""Matched feasibility versus valid-partial-packing optimization in collective mutation domains."""
import argparse,hashlib,importlib.util,itertools,json,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash,digest_words
from supervisor import verify,check_integrity
from phase3.hamming_csp_env import balls,prepare
from ortools.sat.python import cp_model
def model_for(C,n,v,ds,soft):
 groups=[[w for w in g if not set(ds[w])&set(ds[v])] for g in balls(C,n)];assert len(set(w for g in groups for w in g))==sum(map(len,groups))
 model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for g in groups for w in g};skips=[];at={}
 for i,g in enumerate(groups):
  if soft:
   skip=model.new_bool_var("skip"+str(i));skips.append(skip);model.add_exactly_one([xs[w] for w in g]+[skip])
   original=sorted(C)[i];model.add_hint(skip,int(original not in g))
  else:model.add_exactly_one(xs[w] for w in g)
 for w,x in xs.items():
  for d in ds[w]:at.setdefault(d,[]).append(x)
 for group in at.values():
  if len(group)>1:model.add_at_most_one(group)
 for w,x in xs.items():model.add_hint(x,int(w in C))
 if soft:model.minimize(sum(skips))
 assert not model.validate();return model,xs,skips,groups
def test():
 spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 rng=random.Random(1210001);rows=[]
 for n,C in [(5,[0]),(5,[0,31]),(6,[0,7]),(6,[0,7,56]),(6,[0,7,56,63])]:
  ds={w:set(D.descendants(format(w,"0%db"%n))) for w in range(1<<n)};union={w for g in balls(C,n) for w in g};pivots=[v for v in ds if v not in union];rng.shuffle(pivots)
  for v in pivots[:8]:
   groups=[[w for w in g if not ds[w]&ds[v]] for g in balls(C,n)];best=[1]
   def rec(i,used,count):
    if i==len(groups):best[0]=max(best[0],count);return
    rec(i+1,used,count)
    for w in groups[i]:
     if not ds[w]&used:rec(i+1,used|ds[w],count+1)
   rec(0,set(ds[v]),1);model,xs,skips,_=model_for(set(C),n,v,ds,True);solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=5;solver.parameters.num_search_workers=1;solver.parameters.cp_model_presolve=False;status=solver.solve(model)
   assert status==cp_model.OPTIMAL;A=[v]+[w for w,x in xs.items() if solver.value(x)];assert len(A)==best[0] and len(A)==1+len(C)-sum(solver.value(x) for x in skips)
   D.verify([format(w,"0%db"%n) for w in A],n);rows.append({"n":n,"C":C,"extra":v,"oracle_optimum":best[0],"solver_optimum":len(A)})
 out=ROOT/"artifacts/phase3/hamming_diag_001";out.mkdir(parents=True,exist_ok=True);(out/"tests.json").write_text(json.dumps(rows,indent=2));print("HAMMING_DIAG_TESTS",len(rows),flush=True)
def run(case):
 out=ROOT/"artifacts/phase3/hamming_diag_001"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((out.parent/"plan.json").read_text());pivot=plan["selected"][0];v=pivot["word"];soft=case>=2;presolve=(case%2==0)
 base=out.parent/"preflight/baseline.txt";accepted=verify(base);C={int(w,2) for w in base.read_text().split()};inc=Incidence(16);model,xs,skips,groups=model_for(C,16,v,inc.desc,soft)
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"pair":0,"presolve_enabled":presolve,"mode":"soft_packing" if soft else "hard_feasibility","seed":1231001,"extra":v,"pivot_features":pivot,
  "starting_verification":accepted,"groups":groups,"pool_sha256":pool_hash(sorted(xs)),"model_sha256":hashlib.sha256(str(model.proto).encode()).hexdigest(),"seconds_limit":60,"workers":1,"solutions":[],"best_exported":0,"best_verified":226,
  "scope":"Four configurations on the same runner and fixed pivot, same seed,60-second cap. Toggle presolve in hard/soft modes; actual preprocessing/search logs retained. Soft mode allows omitted parent balls; zero omissions and hard feasibility encode the same227 target. Actual consumption and all lower-cardinality exports are recorded; returning226 is not a global improvement."}
 class Export(cp_model.CpSolverSolutionCallback):
  def on_solution_callback(self):
   A=sorted([v]+[w for w,x in xs.items() if self.value(x)]);p=out/("candidate_"+str(len(report["solutions"]))+".txt");p.write_text(canonical(A));checked=verify(p);assert len(A)==len(set(A))
   if soft:assert len(A)==227-sum(self.value(x) for x in skips)
   else:assert len(A)==227
   report["solutions"].append({"witness":p.name,"verification":checked,"solver_seconds":self.wall_time});report["best_exported"]=max(report["best_exported"],len(A));report["best_verified"]=max(226,len(A))
   (out/"progress.json").write_text(json.dumps(report,indent=2))
   if len(A)>=227:self.stop_search()
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=60;solver.parameters.num_search_workers=1;solver.parameters.random_seed=report["seed"];solver.parameters.cp_model_presolve=presolve;solver.parameters.log_search_progress=True;solver.parameters.log_to_stdout=False;logs=[];solver.log_callback=logs.append
 t=time.monotonic();status=solver.solve(model,Export());report.update(status=solver.status_name(status),wall_seconds=time.monotonic()-t,best_objective_bound=solver.best_objective_bound,branches=solver.num_branches,conflicts=solver.num_conflicts,followups=[])
 (out/"solver_log.txt").write_text("\n".join(logs))
 info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());rev=lambda w:int(format(w,"016b")[::-1],2)
 known={digest_words(O) for P in info["codes"] for O in [P,[65535^w for w in P],[rev(w) for w in P],[65535^rev(w) for w in P]]}
 for row in report["solutions"]:
  if row["verification"]["cardinality"]!=226:continue
  h=row["verification"]["reports"][0]["witness_sha256"]
  if h in known:continue
  p=out/row["witness"];A={int(w,2) for w in p.read_text().split()};row["novel_to_known_component"]=True
  for k in [3,5,7,9]:
   r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),"20","1000000000000","0"],input=p.read_text(),text=True,capture_output=True,check=True,timeout=80,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1")).stdout)
   r["pool_sha256"]=pool_hash(r.pop("candidate_pool"));r.pop("neighbors")
   if r["found"]:
    B=A-set(r["removed"])|set(r["added"]);q=out/"improvement.txt";q.write_text(canonical(B));r["verification"]=verify(q);report["best_verified"]=r["verification"]["cardinality"]
   report["followups"].append(r)
   if report["best_verified"]>=227:break
  if report["best_verified"]>=227:break
 (out/"report.json").write_text(json.dumps(report,indent=2));print("HAMMING_SOFT",json.dumps({k:report[k] for k in ["case","pair","mode","extra","status","best_exported","best_verified","wall_seconds","branches","conflicts"]}),flush=True)
def main():
 check_integrity();ap=argparse.ArgumentParser();ap.add_argument("--test",action="store_true");ap.add_argument("--prepare",action="store_true");ap.add_argument("--case",type=int);a=ap.parse_args()
 if a.test:test()
 elif a.prepare:prepare()
 else:run(a.case)
if __name__=="__main__":main()
