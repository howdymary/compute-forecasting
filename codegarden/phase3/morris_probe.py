"""Matched fixed-time comparison: event-driven Morris adaptation versus fixed penalties."""
import argparse,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from phase3.refine import refine
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--seed",type=int,required=True);a=ap.parse_args()
 out=ROOT/"artifacts/phase3/morris_001"/str(a.seed);out.mkdir(parents=True,exist_ok=True)
 base=ROOT/"artifacts/phase3/morris_001/preflight/baseline.txt";accepted=verify(base);rows=[];best=accepted["cardinality"]
 for mode in ["pairbreak","morris"]:
  command=[str(ROOT/".build/infeasible"),"180",str(a.seed),mode,str(out/(mode+"_checkpoint.json")),str(best+1)]
  p=subprocess.run(command,input=base.read_text(),text=True,capture_output=True,check=True,timeout=360);r=json.loads(p.stdout)
  r["proposer_source_sha"]=os.environ["GITHUB_SHA"];r["source_baseline"]=accepted
  if r["proposed_zero_conflict"]:
   candidate=out/(mode+"_candidate.txt");candidate.write_text("\n".join(format(w,"016b") for w in sorted(r["closest_state"]))+"\n")
   r["independent_verification"]=verify(candidate);best=max(best,r["independent_verification"]["cardinality"])
  rows.append(r);(out/"report.json").write_text(json.dumps({"best_verified":best,"experiments":rows,
   "scope":"Restricted conflicted-word pair moves; event-driven weighting is an adaptation, not an exact implementation of every Morris neighborhood. Positive energies are invalid.",
   "provider_calls":0},indent=2))
  print("MORRIS_PROGRESS",json.dumps({"seed":a.seed,"mode":mode,"best":best,"energy":r["minimum_pair_energy"],"distinct_near_states":r["distinct_near_states"],"iterations":r["iterations"],"penalties":r["penalty_updates"]}),flush=True)
  if best>226:return
if __name__=="__main__":main()
