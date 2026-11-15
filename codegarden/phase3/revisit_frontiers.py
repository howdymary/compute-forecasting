"""Revisit older capped suboptimal-code frontiers with the newer connected search."""
import argparse,glob,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
def orbit(C):
 rev=lambda w:int(format(w,"016b")[::-1],2)
 return min(tuple(sorted(O)) for O in [C,[65535^w for w in C],[rev(w) for w in C],[65535^rev(w) for w in C]])
def prepare():
 out=ROOT/"artifacts/phase3/revisit_frontiers_001";states={};sources=[]
 for lineage in ["arena225","projected225","arena224","arena223"]:
  directory=ROOT/"artifacts/phase3/frontier_002"/lineage
  for path in sorted((directory/"shards").glob("*.json")):
   rows=json.loads(path.read_text());sources.append({"file":str(path.relative_to(ROOT)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"rows":len(rows)})
   for row in rows:
    C=sorted(row["incumbent"]);key=orbit(C)
    if key not in states:states[key]={"words":C,"lineages":[lineage],"prior_radius":row["k"],"prior_status_complete":row["complete"],"prior_source":row.get("source_sha")}
    elif lineage not in states[key]["lineages"]:states[key]["lineages"].append(lineage)
 cases=sorted(states.values(),key=lambda r:(-len(r["words"]),digest_words(r["words"])))
 plan={"source_sha":os.environ["GITHUB_SHA"],"cases":cases,"source_artifacts":sources,"case_count":len(cases),
  "hypothesis":"Prior frontier_002 timeouts used bundle_server, predating the much faster blocker-connected kernel. Revisit at radii6 and7 with exact pool definitions, then polish a genuinely new226 basin.",
  "duplicate_policy":"Deduplicate only by previously validated complement/reversal symmetries. A timeout at radius8 does not exhaust radius6 under an incomplete search order.",
  "budget":{"k6_cpu_seconds":5,"k7_cpu_seconds":10,"max_worker_wall_seconds":1100},"kernel_sha256":hashlib.sha256((ROOT/"phase3/bundle_guard.cpp").read_bytes()).hexdigest()}
 assert len(cases)>=350;(out/"plan.json").write_text(json.dumps(plan,indent=2));print("REVISIT_PLAN",json.dumps({"orbits":len(cases),"sizes":{s:sum(len(r["words"])==s for r in cases) for s in [223,224,225]}}),flush=True)
def run(case):
 out=ROOT/"artifacts/phase3/revisit_frontiers_001"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((out.parent/"plan.json").read_text())
 info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known={orbit(C) for C in info["codes"]};root_orbit=orbit(info["codes"][0]);rows=[];best=226;began=time.monotonic();covered=0
 def invoke(C,k,seconds,label):
  nonlocal best
  p=out/(label+"_start.txt");p.write_text(canonical(C));v=verify(p)
  r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=p.read_text(),text=True,capture_output=True,check=True,timeout=seconds+80,
   env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0")).stdout)
  pool=r.pop("candidate_pool");r.pop("neighbors");r.update(starting_verification=v,candidate_pool_sha256=pool_hash(pool),candidate_pool_definition="All outside16-bit words with at mostk distinct incumbent blockers; no dominance, no truncation, no learned no-goods",seconds_limit=seconds)
  if r["found"]:
   Q=set(C)-set(r["removed"])|set(r["added"]);q=out/(label+"_candidate.txt");q.write_text(canonical(Q));r["verification"]=verify(q);best=max(best,len(Q));return sorted(Q),r
  return C,r
 for index,item in enumerate(plan["cases"][case::8]):
  if time.monotonic()-began>1050:break
  C=item["words"];steps=[]
  for round in range(3):
   advanced=False
   for k,seconds in [(6,5),(7,10)]:
    if len(C)>=226:
     if orbit(C)==root_orbit:steps.append({"skipped":"Known root symmetry already has completed strict radius9"});break
     if orbit(C) in known and k<=7:steps.append({"skipped":"Known component symmetry already has completed strict radius7"});continue
    Q,r=invoke(C,k,seconds,str(index)+"_"+str(round)+"_"+str(k));steps.append(r)
    if len(Q)>len(C):C=Q;advanced=True;break
   if best>=227 or not advanced:break
  if len(C)==226 and orbit(C) not in known:
   for k,seconds in [(8,20),(9,30)]:
    Q,r=invoke(C,k,seconds,str(index)+"_novel_"+str(k));steps.append(r)
    if len(Q)>226:C=Q;break
  rows.append({"source_case_sha256":digest_words(item["words"]),"lineages":item["lineages"],"starting_size":len(item["words"]),"ending_size":len(C),"steps":steps});covered+=1
  (out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"case":case,"processed":covered,"planned":len(plan["cases"][case::8]),"rows":rows,"best_verified":best,"wall_seconds":time.monotonic()-began,
   "scope":"Separate bounded neighborhoods at each logged incumbent and radius. Every positive export passes both protected verifiers. A completed case is not global optimality."},indent=2))
  print("REVISIT",json.dumps({"case":case,"processed":covered,"starting":len(item["words"]),"ending":len(C),"global_best_verified":best}),flush=True)
  if best>=227:break
def main():
 check_integrity();ap=argparse.ArgumentParser();ap.add_argument("--prepare",action="store_true");ap.add_argument("--case",type=int);a=ap.parse_args()
 if a.prepare:prepare()
 else:run(a.case)
if __name__=="__main__":main()
