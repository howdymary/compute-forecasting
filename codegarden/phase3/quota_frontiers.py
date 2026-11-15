"""Reproject every final near-code, including stars with more than one conflict edge."""
import argparse,collections,hashlib,importlib.util,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.project_quota import project
from phase3.revisit_frontiers import orbit
OUT=ROOT/"artifacts/phase3/quota_frontiers_001"
def prepare():
 check_integrity();OUT.mkdir(parents=True,exist_ok=True);spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);archive=[];sources=[]
 for case in range(8):
  p=ROOT/"artifacts/phase3/corequota_001"/str(case)/"native.json";r=json.loads(p.read_text());C=r["best"];owner={};edges=set();counts=collections.Counter()
  for i,w in enumerate(C):
   for d in D.descendants(format(w,"016b")):
    for j in owner.get(d,[]):edges.add((j,i))
    owner.setdefault(d,[]).append(i);counts[d]+=1
  assert len(edges)==r["minimum_pair_conflicts"]
  archive.append({"words":C,"raw_energy":sum(n*(n-1)//2 for n in counts.values()),"case":case});sources.append({"case":case,"native_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"pair_conflicts":len(edges),"size":len(C)})
 path=OUT/"archive.json";path.write_text(json.dumps({"archive":archive},indent=2));projection=project(path,OUT/"projections")
 old=json.loads((ROOT/"artifacts/phase3/revisit_frontiers_001/plan.json").read_text());oldorbits={orbit(r["words"]) for r in old["cases"]};known=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known226={orbit(C) for C in known["codes"]};candidates={}
 for p in (OUT/"projections").glob("projection_*.txt"):
  C=[int(w,2) for w in p.read_text().split()];O=orbit(C)
  if len(C)==226 and O not in known226:candidates[O]={"words":C,"path":str(p.relative_to(ROOT)),"priority":0}
  elif len(C)==225 and O not in oldorbits:candidates[O]={"words":C,"path":str(p.relative_to(ROOT)),"priority":1}
 chosen=sorted(candidates.values(),key=lambda r:(r["priority"],digest_words(r["words"])))[:8];info={"source_sha":os.environ["GITHUB_SHA"],"upstream_run":43715961417,"source_receipts":sources,"projection_report":str((OUT/"projections/report.json").relative_to(ROOT)),"projections_verified":projection["unique_projections_verified"],"candidate_count_before_cap":len(candidates),"selected":chosen,"selection_cap":8,"hypothesis":"A227-state with several conflict edges may still yield226 when those edges share one endpoint. One-edge-only event capture is insufficient. Also retain fresh225 minimum-cover projections for bounded full-universe augmentation.","scope":"Finite final archived states only, not all visited states. Extra candidates remain exported rather than permanently excluded."}
 (OUT/"plan.json").write_text(json.dumps(info,indent=2));print("QUOTA_FRONTIER_PLAN",json.dumps({"projections":info["projections_verified"],"fresh":len(candidates),"selected":len(chosen),"sizes":[len(r["words"]) for r in chosen]}),flush=True)
def run(case):
 check_integrity();plan=json.loads((OUT/"plan.json").read_text());out=OUT/str(case);out.mkdir(parents=True,exist_ok=True)
 if case>=len(plan["selected"]):(out/"report.json").write_text(json.dumps({"case":case,"status":"no_selected_frontier","best_verified":226}));return
 item=plan["selected"][case];C=item["words"];start=out/"starting.txt";start.write_text(canonical(C));accepted=verify(start);best=226;steps=[];known={orbit(c) for c in json.loads((ROOT/"phase3/learned_certificates_input.json").read_text())["codes"]};todo=[(6,15),(7,45),(8,120),(9,180)]
 while todo:
  k,seconds=todo.pop(0);r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+100,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0")).stdout);r["pool_sha256"]=pool_hash(r.pop("candidate_pool"));r.pop("neighbors");r["incumbent_sha256"]=digest_words(C)
  if r["found"]:
   C=sorted(set(C)-set(r["removed"])|set(r["added"]));p=out/("candidate_"+str(len(steps))+".txt");p.write_text(canonical(C));r["verification"]=verify(p);best=max(best,len(C));r["known226_orbit"]=orbit(C) in known
   if len(C)==226 and orbit(C) not in known:todo=[(6,5),(7,20),(8,60),(9,120),(10,180)]
   elif len(C)==226:todo=[]
  steps.append(r)
  if best>=227:break
 final=out/"ending.txt";final.write_text(canonical(C));ending=verify(final);report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"starting_verification":accepted,"steps":steps,"ending_verification":ending,"best_verified":best,"scope":"Only the selected explicit projected code and bounded exact exchange neighborhoods. Timeout is unknown. Retained global226 is separate from this method's ending cardinality."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("QUOTA_FRONTIER",json.dumps({"case":case,"ending":len(C),"best":best,"statuses":[{"k":r["k"],"found":r["found"],"complete":r["complete"]} for r in steps]}),flush=True)
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--prepare",action="store_true");ap.add_argument("--case",type=int);a=ap.parse_args();prepare() if a.prepare else run(a.case)
