import json,os,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/induced_kamis_001";rows=[];best=226;new226=0
for case in range(8):
 p=OUT/"workers"/str(case)/"report.json"
 if not p.exists():rows.append({"case":case,"status":"MISSING_UNRESOLVED"});continue
 r=json.loads(p.read_text());assert r["case"]==case and r["source_sha"]==os.environ["GITHUB_SHA"];rows.append(r);best=max(best,r["retained_global_best_verified"]);new226+=int(r["novel226"])
report={"source_sha":os.environ["GITHUB_SHA"],"workers":rows,"best_independently_verified":best,"workers_with_new226":new226,"global_record_claim":False,"scope":"Bounded induced-pool heuristic trials. No timeout, memory gate, or lack of improvement is a proof. Initializations differ, and no trained-policy advantage is claimed."}
(OUT/"summary.json").write_text(json.dumps(report,indent=2));print("INDUCED_KAMIS_SUMMARY",json.dumps({"best":best,"new226workers":new226}),flush=True)
