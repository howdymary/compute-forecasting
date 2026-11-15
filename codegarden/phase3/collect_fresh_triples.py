import json,os,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/fresh_triples_001";p=json.loads((OUT/"plan.json").read_text());rows=[];covered={};positives=[];best=225
for case in range(12):
 path=OUT/"workers"/str(case)/"report.json"
 if not path.exists():rows.append({"case":case,"status":"MISSING_OPEN"});continue
 r=json.loads(path.read_text());assert r["case"]==case and r["source_sha"]==os.environ["GITHUB_SHA"]
 for q in r["results"]:
  assert q["query"] not in covered and q["query"]%12==case;covered[q["query"]]=q
 if r["positive"]:positives.append({"case":case,"positive":r["positive"],"followups":r["strict_followups"]})
 best=max(best,r["best_method_independently_verified"]);rows.append({k:r[k] for k in ["case","assigned_queries","attempted_queries","best_method_independently_verified"]})
report={"source_sha":os.environ["GITHUB_SHA"],"workers":rows,"explicit_models":len(p["queries"]),"attempted":len(covered),"complete_no_new226":[i for i,q in covered.items() if q["complete"]],"open_timeouts":[i for i,q in covered.items() if q["limited"]],"not_attempted":sorted(set(range(len(p["queries"])))-set(covered)),"positive_verifications":positives,"best_method_independently_verified":best,"retained_global_best_verified":max(226,best),"scope":p["scope"],"formal_absence_certificate":False}
(OUT/"summary.json").write_text(json.dumps(report,indent=2));print("FRESH_TRIPLES_SUMMARY",json.dumps({"models":report["explicit_models"],"attempted":report["attempted"],"complete_no_new226":len(report["complete_no_new226"]),"open":len(report["open_timeouts"]),"best":best,"positive":len(positives)}),flush=True)
