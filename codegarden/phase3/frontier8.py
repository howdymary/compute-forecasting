"""Diverse size225 incumbents, larger exact connected exchanges, then polish new226 basins."""
import argparse,hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.revisit_frontiers import orbit
OUT=ROOT/"artifacts/phase3/frontier8_001"
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);path=ROOT/"artifacts/phase3/revisit_frontiers_001/plan.json";old=json.loads(path.read_text());candidates=[r for r in old["cases"] if len(r["words"])==225];info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));root=set(info["codes"][0])
 # Explicit greedy farthest-point selection using symmetric difference, not a permanent exclusion.
 chosen=[];left=list(candidates);distance=lambda A,B:225-max(len(A&set(O)) for O in [B,[65535^w for w in B],[int(format(w,"016b")[::-1],2) for w in B],[65535^int(format(w,"016b")[::-1],2) for w in B]])
 while left and len(chosen)<32:
  if not chosen:item=min(left,key=lambda r:(len(set(r["words"])&core),digest_words(r["words"])))
  else:item=max(left,key=lambda r:(min(distance(set(r["words"]),s["words"]) for s in chosen),-len(set(r["words"])&core),digest_words(r["words"])))
  chosen.append(item);left.remove(item)
 cases=[{**r,"witness_sha256":digest_words(r["words"]),"common216_overlap":len(set(r["words"])&core),"root_overlap":len(set(r["words"])&root)} for r in chosen]
 plan={"source_sha":os.environ["GITHUB_SHA"],"input_path":str(path.relative_to(ROOT)),"input_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"input_count":len(candidates),"cases":cases,"k8_cpu_seconds":120,"novel226_polish":[[7,20],[8,60],[9,120]],"selection":"32 greedy farthest-point size225 symmetry-distinct states; first minimizes overlap with common216. Others remain eligible for future batches.","hypothesis":"Radius6/7 closure of diverse225 local maxima does not imply radius8 closure. An eight-word augmentation may reach an unvisited226 basin."}
 (OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("FRONTIER8_PLAN",json.dumps({"selected":len(cases),"core_overlaps":[r["common216_overlap"] for r in cases]}),flush=True)
def run(case):
 out=OUT/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((OUT/"plan.json").read_text());item=plan["cases"][case];C=item["words"];p=out/"starting.txt";p.write_text(canonical(C));accepted=verify(p);steps=[];best=226
 info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known={orbit(c) for c in info["codes"]}
 todo=[(8,120)]
 while todo:
  k,seconds=todo.pop(0);r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+80,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0")).stdout)
  r["candidate_pool_sha256"]=pool_hash(r.pop("candidate_pool"));r.pop("neighbors");r["incumbent_sha256"]=digest_words(C);r["candidate_pool_definition"]="All outside words with at mostk incumbent blockers; no dominance/no-goods/truncation";r["seconds_limit"]=seconds
  if r["found"]:
   C=sorted(set(C)-set(r["removed"])|set(r["added"]));q=out/("candidate_"+str(len(steps))+".txt");q.write_text(canonical(C));r["verification"]=verify(q);best=max(best,len(C));r["known226_orbit"]=orbit(C) in known
   if len(C)==226 and orbit(C) not in known:todo=[tuple(x) for x in plan["novel226_polish"]]
  steps.append(r)
  if best>=227:break
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"selected_source":item,"starting_verification":accepted,"steps":steps,"ending_size":len(C),"best_verified":best,"scope":"Only logged bounded removal neighborhoods. Complete no-improvement is local; timeouts are not infeasibility. All positive witnesses pass both protected verifiers."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("FRONTIER8",json.dumps({"case":case,"ending":len(C),"best":best,"statuses":[{"k":s["k"],"complete":s["complete"],"found":s["found"]} for s in steps]}),flush=True)
if __name__=="__main__":
 check_integrity();ap=argparse.ArgumentParser();ap.add_argument("--prepare",action="store_true");ap.add_argument("--case",type=int);a=ap.parse_args()
 if a.prepare:prepare()
 else:run(a.case)
