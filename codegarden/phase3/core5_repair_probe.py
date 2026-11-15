"""Full-universe exact rank-five repair; every query is scoped."""
import argparse,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.revisit_frontiers import orbit
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;check_integrity();out=ROOT/"artifacts/phase3/core5_repair_001"/str(case);out.mkdir(parents=True,exist_ok=True);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=sorted(set.intersection(*(set(C) for C in info["codes"])));known={orbit(C) for C in info["codes"]};from phase3.core5_input import load_input;raw=load_input(out.parent,case)
 r=json.loads(subprocess.run([str(ROOT/".build/core5_repair"),str(case),"600",str(1391001+case),str(out/"checkpoint.txt")],input=raw,text=True,capture_output=True,check=True,timeout=800).stdout)
 early_winner=out/"best.txt";early_winner.write_text(canonical(r["winner"]));early_verification=verify(early_winner);(out/"early_verification.json").write_text(json.dumps(early_verification,indent=2))
 primary_codes=r.pop("primary_status_codes");secondary_codes=r.pop("secondary_status_codes")
 for label,codes in [("primary",primary_codes),("secondary",secondary_codes)]:
  for offset in range(0,len(codes),100000):(out/(label+"_statuses_"+str(offset//100000)+".txt")).write_text(codes[offset:offset+100000])
 rows=r.pop("rows");core_set=set(core)
 for item in rows:
  fixed=sorted(core_set-set(item["removed_core"]));item["fixed_code_sha256"]=digest_words(fixed);item["primary_pool_count"]=len(item["primary_pool"]);item["secondary_pool_count"]=len(item["secondary_pool"]);item["primary_pool_sha256"]=pool_hash(item.pop("primary_pool"));item["secondary_pool_sha256"]=pool_hash(item.pop("secondary_pool"));item["primary_target_added"]=227-len(fixed);item["secondary_target_added"]=226-len(fixed);item["primary_pool_definition"]="All outside16-bit words compatible with fixed common core minus these removed words";item["secondary_pool_definition"]="The full primary pool excluding the explicitly removed core words";item["proof_artifact"]=None
 for index in range(0,len(rows),500):(out/("queries_"+str(index//500)+".jsonl")).write_text("".join(json.dumps(x,separators=(",",":"))+"\n" for x in rows[index:index+500]))
 winner=out/"best.txt";winner.write_text(canonical(r["winner"]));best=verify(winner);winning_words=r["winner"];novel=[];steps=[]
 for i,C in enumerate(r["new226_candidates"]):
  p=out/("candidate_"+str(i)+".txt");p.write_text(canonical(C));v=verify(p)
  if orbit(C) in known:continue
  novel.append({"witness":p.name,"verification":v})
  if len(novel)>8 or best["cardinality"]>=227:continue
  for k,seconds in [(6,5),(7,10),(8,30),(9,60)]:
   z=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+80,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="")).stdout);z["candidate_pool_sha256"]=pool_hash(z.pop("candidate_pool"));z.pop("neighbors");z["starting_hash"]=digest_words(C)
   if z["found"]:
    C=sorted(set(C)-set(z["removed"])|set(z["added"]));q=out/("augmented_"+str(i)+".txt");q.write_text(canonical(C));z["verification"]=verify(q)
    if len(C)>best["cardinality"]:best=z["verification"];winning_words=C[:]
   steps.append(z)
   if best["cardinality"]>=227:break
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"native":{k:v for k,v in r.items() if k not in ["winner","new226_candidates"]},"new226":novel,"polish":steps,"best_verified":best["cardinality"],"winner_verification":best,"scope":"Explicit supported five-core removal sets from support_plan.json, partitioned by index modulo16. All unsupported sets are eliminated only by the documented lemma and completed lower-depth prerequisites; status files I=infeasible in exact encoded query, T=timeout,C=pool cap,F=feasible,N=notrun. Sampled rows have literal pool hashes; full candidate pools are reconstructible from fixed code and universe. Only explicit fixed-core repair families. Primary227 query allows the FULL compatible universe. Secondary226 query explicitly excludes all removed core words; its infeasibility does not by itself exclude every226 code. Timeouts/caps are not proofs."}
 winner.write_text(canonical(winning_words));assert verify(winner)["cardinality"]==best["cardinality"]
 (out/"report.json").write_text(json.dumps(report,indent=2));print("CORE_REPAIR",json.dumps({"case":case,"best":best["cardinality"],"novel226":len(novel),"native":report["native"]}),flush=True)
 if best["cardinality"]>=227:print("CORE_VERIFIED_WINNER",json.dumps(winning_words),flush=True)
if __name__=="__main__":main()
