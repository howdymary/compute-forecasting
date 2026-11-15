"""Reach a new226 basin with symmetry-family hitting exclusions, then attempt227."""
import argparse,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.revisit_frontiers import orbit
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;out=ROOT/"artifacts/phase3/basin_escape_001"/str(case);out.mkdir(parents=True,exist_ok=True);check_integrity()
 plan=json.loads((ROOT/"artifacts/phase3/revisit_frontiers_001/plan.json").read_text());candidates=[r["words"] for r in plan["cases"] if len(r["words"])==225];C=candidates[(case//2*73)%len(candidates)];start=out/"starting.txt";start.write_text(canonical(C));accepted=verify(start)
 info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(c) for c in info["codes"]));rev=lambda w:int(format(w,"016b")[::-1],2);cores=[core,{65535^w for w in core},{rev(w) for w in core},{65535^rev(w) for w in core}];forbidden=set()
 for S in cores:
  if not S&forbidden:forbidden.add(min(S-set(C)-{0,65535},key=lambda w:(w.bit_count(),w)))
 assert not forbidden&set(C) and all(S&forbidden for S in cores)
 bp=out/"forbidden.txt";bp.write_text("\n".join(map(str,sorted(forbidden))));known=out/"known226.txt";orbits=[sorted(O) for c in info["codes"] for O in [c,[65535^w for w in c],[rev(w) for w in c],[65535^rev(w) for w in c]]];known.write_text("".join("226 "+" ".join(map(str,c))+"\n" for c in orbits));knownsets={tuple(c) for c in orbits}
 mode="fixed" if case%2==0 else "adaptive";seed=1311001+case//2
 def invoke(C,target,seconds,label):
  r=json.loads(subprocess.run([str(ROOT/".build/basin_escape"),str(seconds),str(seed),mode,str(out/(label+"_checkpoint.txt")),str(known),str(target),str(bp)],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+100).stdout);(out/(label+".json")).write_text(json.dumps(r,indent=2));return r
 r=invoke(C,226,300,"new226_search");steps=[];best=226;new=None
 if r["minimum_pair_conflicts"]==0:
  C=r["best"];assert len(C)==226 and not set(C)&forbidden and tuple(sorted(C)) not in knownsets
  q=out/"new226.txt";q.write_text(canonical(C));new=verify(q);assert new["cardinality"]==226
  for k,seconds in [(6,5),(7,20),(8,60),(9,120)]:
   a=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+100,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0")).stdout);a["pool_sha256"]=pool_hash(a.pop("candidate_pool"));a.pop("neighbors");a["incumbent_sha256"]=digest_words(C)
   if a["found"]:
    C=sorted(set(C)-set(a["removed"])|set(a["added"]));q=out/"candidate227.txt";q.write_text(canonical(C));a["verification"]=verify(q);best=max(best,len(C))
   steps.append(a)
   if best>=227:break
  if best<227:
   # Exact repair may use excluded words; the original new226 still obeys the search bans.
   C=r["best"];s=invoke(C,227,300,"target227_search")
   if s["minimum_pair_conflicts"]==0:
    q=out/"candidate227_soft.txt";q.write_text(canonical(s["best"]));checked=verify(q);best=max(best,checked["cardinality"]);steps.append({"soft_target227_verification":checked})
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"mode":mode,"seed":seed,"starting_verification":accepted,"starting_sha256":digest_words(candidates[(case//2*73)%len(candidates)]),"forbidden":sorted(forbidden),"hitting_scope":"At leastone absent225 word from the shared216 core of each of the four validated symmetry families; excludes all known38x4 codes, not all226 codes.","new226":new,"new226_search_cpu_seconds":r["cpu_seconds"],"new226_minimum_pair_conflicts":r["minimum_pair_conflicts"],"steps":steps,"best_verified":best,"scope":"Bounded heuristic restricted by the explicit hitting set. No infeasibility or global-record claim from a negative result; positives accepted only by two protected verifiers."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("BASIN_ESCAPE",json.dumps({"case":case,"new226":new is not None,"best":best,"minimum_pair_conflicts":r["minimum_pair_conflicts"]}),flush=True)
if __name__=="__main__":main()
