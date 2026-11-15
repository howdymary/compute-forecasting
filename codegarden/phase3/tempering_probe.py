"""Matched CPU-budget genuine annealing and replica-exchange discovery pilots."""
import argparse,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--seed",type=int,required=True);a=ap.parse_args()
 out=ROOT/"artifacts/phase3/tempering_001"/str(a.seed);out.mkdir(parents=True,exist_ok=True);base=ROOT/"artifacts/phase3/tempering_001/preflight/baseline.txt";checked=verify(base);best=checked["cardinality"];rows=[]
 for mode in ["anneal","tempered"]:
  p=subprocess.run([str(ROOT/".build/infeasible"),"120",str(a.seed),mode,str(out/(mode+"_checkpoint.json"))],input=base.read_text(),text=True,capture_output=True,check=True,timeout=250);r=json.loads(p.stdout);r["source_sha"]=os.environ["GITHUB_SHA"]
  if r["proposed_zero_conflict"]:
   q=out/(mode+"_candidate.txt");q.write_text("\n".join(format(w,"016b") for w in sorted(r["closest_state"]))+"\n");r["independent_verification"]=verify(q);best=max(best,r["independent_verification"]["cardinality"])
  rows.append(r);(out/"report.json").write_text(json.dumps({"best_verified":best,"experiments":rows,"same_seed_and_baseline":True,"cpu_seconds_per_condition":120,"source_baseline":checked,"scope":"Finite heuristic runs; positive energies are invalid and non-discovery is not infeasibility."},indent=2))
  print("TEMPERING_PROGRESS",json.dumps({"seed":a.seed,"mode":mode,"best":best,"minimum_energy":r["minimum_pair_energy"],"iterations":r["iterations"],"near_archive":len(r["near_states"]),"swaps":r["swap_accepted"]}),flush=True)
  if best>=227:return
if __name__=="__main__":main()
