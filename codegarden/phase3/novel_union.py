"""Search beyond closed orbit components in explicitly bounded construction word pools."""
import argparse,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words,pool_hash
from supervisor import verify
from ortools.sat.python import cp_model
def orbit(C):
 C=set(C);rev=lambda w:int(format(w,"016b")[::-1],2)
 return [C,{65535^w for w in C},{rev(w) for w in C},{65535^rev(w) for w in C}]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);a=ap.parse_args();case=a.case
 out=ROOT/"artifacts/phase3/novel_union_001"/str(case);out.mkdir(parents=True,exist_ok=True)
 parents=[];provenance=[]
 for size in [208,223,224,225,226]:
  p=next((ROOT/"artifacts/baselines").glob("arena_"+str(size)+"_*.txt"));v=verify(p);C={int(w,2) for w in p.read_text().split()};parents.append(C);provenance.append({"file":str(p.relative_to(ROOT)),"verification":v})
 pool=set().union(*parents)
 if case>=1:
  for wid in [2,3]:
   data=json.loads((ROOT/"artifacts/phase3/modal_pair_001/workers"/(str(wid)+".json")).read_text())
   for item in data["native"]["near_archive"]:pool.update(item["words"])
 if case>=2:
  pool=set().union(*(T for C in parents for T in orbit(C)))|pool
 if case==3:
  r=json.loads((ROOT/"artifacts/phase3/persistent_bundle_001/workers/0.json").read_text())
  for row in r["experiments"]:pool.update(row["incumbent_words"])
 pool=sorted(pool);inc=Incidence(16);model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for w in pool};at={}
 for w,x in xs.items():
  for d in inc.desc[w]:at.setdefault(d,[]).append(x)
 for group in at.values():
  if len(group)>1:model.add_at_most_one(group)
 comp=ROOT/"artifacts/phase3/bundle_004/component5";r=json.loads((comp/"report.json").read_text());assert r["complete_component"] and r["processed"]==38
 cut_sources=[];cuts=set()
 for row in r["rows"]:
  C={int(w,2) for w in (comp/row["incumbent_file"]).read_text().split()}
  assert row["complete"] and not row["found"] and len(C)==226
  for O in orbit(C):cuts.add(tuple(sorted(O)))
  cut_sources.append({"witness_sha256":row["incumbent_witness_sha256"],"source_file":row["incumbent_file"],"radius":5,"native_complete":True})
 for C in cuts:model.add(sum(xs[w] for w in C if w in xs)<=220)
 target=227 if case==3 else 226;model.add(sum(xs.values())>=target);model.maximize(sum(xs.values()))
 for w in parents[3]:
  if w in xs:model.add_hint(xs[w],1)
 report={"case":case,"source_sha":os.environ["GITHUB_SHA"],"candidate_pool":pool,"candidate_pool_sha256":pool_hash(pool),"target":target,
  "known_orbit_distance_cuts":len(cuts),"cut_sources":cut_sources,"parents":provenance,"solutions":[],
  "scope":"Restricted candidate universe with distance cuts from native local enumeration; no global upper-bound claim. A 226-word solution is only a new archive basin.",
  "cut_lemma":"Any new 226-word code within five replacements of a closed radius-five orbit component would already belong to it. Any 227-word code sharing at least 221 of its words would contradict that root's completed strict radius-five search.",
  "proof_limit":"No external formal proof certificate for native exhaustion. Even an INFEASIBLE model here is reported only for this explicit encoded pool and cuts."}
 (out/"plan.json").write_text(json.dumps(report,indent=2))
 class Export(cp_model.CpSolverSolutionCallback):
  def on_solution_callback(self):
   C=sorted(w for w,x in xs.items() if self.value(x));q=out/("candidate_"+str(len(report["solutions"]))+".txt");q.write_text(canonical(C));checked=verify(q)
   report["solutions"].append({"witness":q.name,"verification":checked,"objective":len(C),"solver_seconds":self.wall_time})
   (out/"progress.json").write_text(json.dumps(report,indent=2))
   if len(C)>=227:self.stop_search()
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=180;solver.parameters.num_search_workers=2;solver.parameters.random_seed=1050001+case
 t=time.monotonic();status=solver.solve(model,Export());report.update(status=solver.status_name(status),seconds_limit=180,workers=2,
  wall_seconds=time.monotonic()-t,best_objective_bound=solver.best_objective_bound,model_sha256=hashlib.sha256(str(model.proto).encode()).hexdigest())
 best=max([226]+[x["verification"]["cardinality"] for x in report["solutions"]]);report["native_followups"]=[]
 if report["solutions"] and best<227:
  first=report["solutions"][0];p=out/first["witness"]
  for k in [6,7]:
   native=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),"30","100000000000","0"],input=p.read_text(),text=True,capture_output=True,check=True,timeout=100).stdout)
   pool2=native.pop("candidate_pool");native["pool_sha256"]=pool_hash(pool2);native["starting_sha256"]=first["verification"]["reports"][0]["witness_sha256"]
   if native["found"]:
    C={int(w,2) for w in p.read_text().split()};C=C-set(native["removed"])|set(native["added"]);q=out/("native_"+str(k)+".txt");q.write_text(canonical(C));native["independent_verification"]=verify(q);best=max(best,len(C))
   report["native_followups"].append(native)
   if best>=227:break
 report["best_independently_verified"]=best;(out/"report.json").write_text(json.dumps(report,indent=2))
 print("NOVEL_UNION_FINAL",json.dumps({"case":case,"pool":len(pool),"status":report["status"],"sizes":[x["verification"]["cardinality"] for x in report["solutions"]],"best":best,"bound":report["best_objective_bound"]}),flush=True)
if __name__=="__main__":main()
