"""Four fixed-budget infeasible-space hypotheses per seed; never count invalid words."""
import argparse,datetime as dt,hashlib,importlib.util,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--seed",type=int,required=True);parser.add_argument("--seconds",type=float,default=180);a=parser.parse_args()
 out=ROOT/"artifacts/phase3"/os.environ.get("CODEGARDEN_BATCH","infeasible_probe_001")/("probe_"+str(a.seed));out.mkdir(parents=True,exist_ok=True)
 baseline=ROOT/"artifacts/phase3"/os.environ.get("CODEGARDEN_BATCH","infeasible_probe_001")/"preflight/baseline.txt";accepted=verify(baseline);target=accepted["cardinality"]+1
 modes=["persist","novel"];shift=a.seed%2;modes=modes[shift:]+modes[:shift]
 rows=[];best=accepted["cardinality"]
 metadata={"source_sha":os.environ["GITHUB_SHA"],"starting_witness_sha256":accepted["reports"][0]["witness_sha256"],"seed":a.seed,
  "seconds_per_mode":a.seconds,"modes":modes,"target":target,"funding":"Free standard public GitHub CPU runner; no sponsor provider calls"}
 (out/"metadata.json").write_text(json.dumps(metadata,indent=2))
 for mode in modes:
  started=time.perf_counter();p=subprocess.run([str(ROOT/".build/infeasible"),str(a.seconds),str(a.seed),mode,str(out/("checkpoint_"+mode+".json"))],
   input=baseline.read_text(),text=True,capture_output=True,timeout=a.seconds*2+40,check=True);r=json.loads(p.stdout)
  words=[format(w,"016b") for w in r["closest_state"]];candidate={"words":words}
  diagnostic=subprocess.run([sys.executable,"-B",str(ROOT/"protected/verify_descendants.py"),"-"],input=json.dumps(candidate),text=True,capture_output=True,check=False)
  report=json.loads(diagnostic.stdout);r["protected_descendant_diagnostic"]=report
  if r["proposed_zero_conflict"]:
   path=out/("worker_valid_"+mode+"_"+str(a.seed)+".txt");path.write_text("\n".join(sorted(words))+"\n")
   r["independent_verification"]=verify(path);assert r["independent_verification"]["cardinality"]==target
   best=max(best,target)
  else:assert not report["valid"],"Native nonzero energy disagrees with independent verifier"
  r["closest_state_kind"]="proposal_passed_both_verifiers" if r["proposed_zero_conflict"] else "invalid_diagnostic_not_a_code"
  r["total_runtime_seconds"]=time.perf_counter()-started;r["source_sha"]=metadata["source_sha"];rows.append(r)
  (out/"report.json").write_text(json.dumps({"metadata":metadata,"experiments":rows,"best_verified_cardinality":best},indent=2))
  print("INFEASIBLE_PROBE "+json.dumps({k:v for k,v in r.items() if k not in ["closest_state","baseline_valid_words","protected_descendant_diagnostic"]}),flush=True)
  if best>=target:break
 print("PROBE_DONE "+json.dumps({"seed":a.seed,"best_verified_cardinality":best,"minimum_pair_energy":min(r["minimum_pair_energy"] for r in rows)}),flush=True)
if __name__=="__main__":main()
