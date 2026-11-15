import json,pathlib,os
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/corridor_cp_001";rows=[];positives=[];best=226
for case in range(16):
 path=OUT/"workers"/str(case)/"report.json"
 if not path.exists():rows.append({"case":case,"status":"MISSING_OPEN"});continue
 r=json.loads(path.read_text());assert r["case"]==case and r["source_sha"]==os.environ["GITHUB_SHA"];rows.append({k:r[k] for k in ["case","pair","condition","source_parent","blocker_threshold","status","fixed_sha256","pool_sha256","solver_seed","solver_wall_seconds","solver_process_cpu_seconds","best_method_independently_verified"]});best=max(best,r["best_method_independently_verified"])
 if r["solutions"]:positives.append({"case":case,"solutions":r["solutions"],"followups":r["strict_followups"]})
pairs=[]
for pair in range(8):
 A=next((r for r in rows if r["case"]==pair*2),None);B=next((r for r in rows if r["case"]==pair*2+1),None)
 if A.get("pair")==B.get("pair")==pair:assert A["fixed_sha256"]==B["fixed_sha256"] and A["pool_sha256"]==B["pool_sha256"] and A["solver_seed"]==B["solver_seed"];pairs.append({"pair":pair,"control_status":A["status"],"treatment_status":B["status"],"control_best":A["best_method_independently_verified"],"treatment_best":B["best_method_independently_verified"]})
report={"source_sha":os.environ["GITHUB_SHA"],"rows":rows,"pairs":pairs,"positive_verifications":positives,"best_independently_verified":best,"formal_absence_certificate":False,"scope":"Feasibility CP-SAT at size>=226, exact known226exclusions, no artificial227ceiling. All missing/UNKNOWN models open. Treatment cuts depend on source-scoped native low2closure; control does not. Matched150solver-wall/two-worker caps, actual processCPU reported. No trained-policy or global bound claim."}
(OUT/"summary.json").write_text(json.dumps(report,indent=2));print("CORRIDOR_CP_SUMMARY",json.dumps({"pairs":pairs,"positive":len(positives),"best":best}),flush=True)
