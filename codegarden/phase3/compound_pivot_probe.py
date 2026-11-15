"""Force an outside pivot, remove its core blockers, solve its full compatible repair."""
import argparse,json,os,pathlib,sys,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.revisit_frontiers import orbit
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;check_integrity();out=ROOT/"artifacts/phase3/compound_pivot_001"/str(case);out.mkdir(parents=True,exist_ok=True)
 info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=sorted(set.intersection(*(set(C) for C in info["codes"])));C=sorted(info["codes"][0]);raw="226 "+" ".join(map(str,C))+"\n216 "+" ".join(map(str,core))+"\n"
 r=json.loads(subprocess.run([str(ROOT/".build/compound_pivot"),str(case),"600",str(1411001+case),str(out/"checkpoint.txt")],input=raw,text=True,capture_output=True,check=True,timeout=900).stdout)
 rows=r.pop("rows")
 for row in rows:
  row["pool_count"]=len(row["pool"]);row["pool_sha256"]=pool_hash(row.pop("pool"));row["fixed_code_sha256"]=digest_words(sorted(set(core)-set(row["removed_core"])|set(row["forced"])));row["proof_artifact"]=None
 (out/"queries.jsonl").write_text("".join(json.dumps(x,separators=(",",":"))+"\n" for x in rows))
 best=226;novel=[];steps=[];known={orbit(c) for c in info["codes"]}
 for i,C in enumerate(r["new226_candidates"]):
  p=out/("candidate_"+str(i)+".txt");p.write_text(canonical(C));v=verify(p)
  if len(C)>=227:best=len(C)
  if len(C)==226 and orbit(C) in known:continue
  novel.append({"path":p.name,"verification":v,"missing_core":len(set(core)-set(C))})
  if best>=227:break
  for k,seconds in [(6,5),(7,20),(8,60),(9,120),(10,180)]:
   z=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+100,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0")).stdout);z["pool_sha256"]=pool_hash(z.pop("candidate_pool"));z.pop("neighbors");z["starting_sha256"]=digest_words(C)
   if z["found"]:
    C=sorted(set(C)-set(z["removed"])|set(z["added"]));p=out/("augmented_"+str(i)+".txt");p.write_text(canonical(C));z["verification"]=verify(p);best=max(best,len(C))
   steps.append(z)
   if best>=227:break
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"best_verified":best,"new226":novel,"polish":steps,"native":{k:v for k,v in r.items() if k not in ["winner","new226_candidates"]},"scope":"Bounded randomized compound pivots. Cases0..3 force2 rankcap14,4..7 force3 rankcap20,8..11 force4 rankcap26;12..15 switch pivot count2..5 and rank cap16..32 every512 proposals. Each repair uses the full universe compatible with fixed core plus mutually compatible forced words. Cap1024 candidates/.035CPU/250000nodes per target. Exact negatives apply only to individual encoded repair; no exhaustive family or global claim."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("COMPOUND_PIVOT",json.dumps({"case":case,"best":best,"new226":len(novel),"native":report["native"]}),flush=True)
 if best>=227:print("CORE_VERIFIED_WINNER",flush=True)
if __name__=="__main__":main()
