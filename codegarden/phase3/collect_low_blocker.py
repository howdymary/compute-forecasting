import json,os,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/low_blocker_001";plan=json.loads((OUT/"plan.json").read_text());rows=[];best=226;positives=[];complete=[];opened=[]
for case in range(8):
 path=OUT/"workers"/str(case)/"report.json"
 if not path.exists():rows.append({"case":case,"status":"MISSING_OPEN"});continue
 r=json.loads(path.read_text());assert r["case"]==case and r["source_sha"]==os.environ["GITHUB_SHA"];rows.append({k:r[k] for k in ["case","starting_sha256","results","best_method_independently_verified","unattempted_queries"]});best=max(best,r["best_method_independently_verified"])
 for q in r["results"]:
  if q["complete"]:complete.append(q["query"])
  if q["limited"]:opened.append(q["query"])
 if r["positive"]:positives.append({"case":case,"positive":r["positive"],"followups":r["strict_followups"]})
report={"source_sha":os.environ["GITHUB_SHA"],"workers":rows,"complete_goal_model_negatives":complete,"open_timeouts":opened,"positive_verifications":positives,"best_independently_verified":best,"scope":plan["scope"],"formal_absence_certificate":False}
(OUT/"summary.json").write_text(json.dumps(report,indent=2));print("LOW_BLOCKER_SUMMARY",json.dumps({"complete_no_new226":complete,"open":opened,"positive":len(positives),"best":best}),flush=True)
