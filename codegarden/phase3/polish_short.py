"""Exploit genuinely different low-conflict states from completed short probes."""
import json,os,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from phase3.refine import refine
from supervisor import verify
def main():
 out=ROOT/"artifacts/phase3/short_polish_001";out.mkdir(parents=True,exist_ok=True);rows=[];best=226
 for seed in [950003,950002]:
  report=json.loads((ROOT/"artifacts/phase3/infeasible_probe_003"/("probe_"+str(seed))/"report.json").read_text())
  native=next(r for r in report["experiments"] if r["mode"]=="pairbreak")
  reference=[format(w,"016b") for w in native["baseline_valid_words"]]
  result=refine(native,reference,native["target_cardinality"],seed,out/str(seed))
  for kind in ["valid_projections","polished"]:
   for r in result[kind]:best=max(best,r["verification"]["cardinality"])
  if result.get("winner"):
   p=out/("worker_winner_"+str(seed)+".txt");p.write_text("\n".join(sorted(format(w,"016b") for w in result["winner"]))+"\n");best=max(best,verify(p)["cardinality"])
  rows.append({"seed":seed,"source_sha":os.environ["GITHUB_SHA"],"result":result})
  (out/"report.json").write_text(json.dumps({"experiments":rows,"best_independently_verified":best,"scope":"Projection, native augmentation and explicitly bounded exact repairs of archived near-feasible states"},indent=2))
  print("SHORT_POLISH "+json.dumps({"seed":seed,"best":best,"projection_sizes":[r["verification"]["cardinality"] for r in result["valid_projections"]],
   "polished_sizes":[r["verification"]["cardinality"] for r in result["polished"]],"exact_statuses":[r["status"] for r in result["exact"]]}),flush=True)
  if best>226:break
if __name__=="__main__":main()
