"""Coverage of bounded connected neutral9families, not an impossibility claim."""
import json,os,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/neutral9_goal_001";p=json.loads((OUT/"plan.json").read_text());N=p["pool_size"];seen=set();duplicates=[];workers=[];positives=[];best=226
for case in range(8):
 path=OUT/"workers"/str(case)/"report.json"
 if not path.exists():workers.append({"case":case,"status":"MISSING_OPEN"});continue
 r=json.loads(path.read_text());assert r["case"]==case and r["source_sha"]==os.environ["GITHUB_SHA"] and r["starting_sha256"]==p["starting_sha256"] and r["ordered_pool_sha256"]==p["ordered_pool_sha256"]
 E=[i for i in range(N) if i%8==case];ids=E[:r["new_completed_roots"]];duplicates.extend(i for i in ids if i in seen);seen.update(ids);workers.append({"case":case,"complete":r["native"]["complete"],"completed_roots":len(ids),"found":r["native"]["found"],"best":r["best_independently_verified"]});best=max(best,r["best_independently_verified"])
 if r["positive"]:positives.append({"case":case,"positive":r["positive"],"strict_followups":r["strict_followups"]})
report={"source_sha":os.environ["GITHUB_SHA"],"starting_sha256":p["starting_sha256"],"exchange_rank":9,"neutral_or_improving":True,"pool_size":N,"pool_sha256":p["pool_sha256"],"ordered_pool_sha256":p["ordered_pool_sha256"],"workers":workers,"total_unique_completed_roots":len(seen),"uncovered_roots":sorted(set(range(N))-seen),"duplicate_completed_roots":duplicates,"all_root_coverage_complete":len(seen)==N and not duplicates and all(w.get("complete",False) for w in workers),"positives":positives,"best_independently_verified":best,"formal_absence_certificate":False,"scope":p["scope"]}
(OUT/"coverage.json").write_text(json.dumps(report,indent=2));print("NEUTRAL9_COVERAGE",json.dumps({"complete":report["all_root_coverage_complete"],"uncovered":len(report["uncovered_roots"]),"positives":len(positives),"best":best}),flush=True)
