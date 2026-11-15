"""Paired evaluation uses verified cardinality first; timeout never means infeasible."""
import json,os,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/fresh_cp_001";pairs=[]
for pair in range(4):
 paths=[OUT/str(2*pair+i)/"report.json" for i in range(2)]
 if not all(p.exists() for p in paths):pairs.append({"pair":pair,"status":"MISSING_OPEN"});continue
 a,b=[json.loads(p.read_text()) for p in paths];assert a["source_sha"]==b["source_sha"]==os.environ["GITHUB_SHA"] and a["fixed_sha256"]==b["fixed_sha256"] and a["pool_sha256"]==b["pool_sha256"] and a["hint_sha256"]==b["hint_sha256"] and a["seed"]==b["seed"]
 pairs.append({"pair":pair,"same_fixed_pool_hint_seed":True,"control":{k:a[k] for k in ["status","solver_best_verified","best_method_independently_verified","best_objective_bound_total","solver_process_cpu_seconds"]},"treatment":{k:b[k] for k in ["status","solver_best_verified","best_method_independently_verified","best_objective_bound_total","solver_process_cpu_seconds"]},"primary_treatment_gain":b["best_method_independently_verified"]-a["best_method_independently_verified"]})
(OUT/"comparison.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"pairs":pairs,"scope":"Verified cardinality primary. Goal-model bounds/status and runtime supporting only. Four correlated source families, no trained/Tinker claim or global upper bound."},indent=2));print("FRESH_CP_COMPARISON",json.dumps(pairs),flush=True)
