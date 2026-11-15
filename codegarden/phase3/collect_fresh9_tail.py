"""Add disjoint new prefixes to previous rank9coverage, retaining unresolved roots explicitly."""
import json,os,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/fresh9_tail_001";plan=json.loads((OUT/"plan.json").read_text());previous=json.loads((OUT/"previous_coverage.json").read_text());rows=[]
for p in plan["parents"]:
 parent=p["case"];old=previous["parents"][parent];N=p["pool_size"];left=set(old["uncovered_roots"]);seen=set(range(N))-left;duplicates=[];workers=[];positives=[]
 for shard in range(4):
  case=parent*4+shard;path=OUT/"workers"/str(case)/"report.json";expected=sorted(i for i in left if i%4==shard)
  if not path.exists():workers.append({"shard":shard,"status":"MISSING_OPEN"});continue
  r=json.loads(path.read_text());assert r["source_sha"]==os.environ["GITHUB_SHA"] and r["parent"]==parent and r["shard"]==shard
  if r["status"]=="NO_SEARCH":
   assert not expected;workers.append({"shard":shard,"complete":True,"status":"previously_closed"});continue
  assert r["starting_sha256"]==p["starting_sha256"] and r["ordered_pool_sha256"]==p["ordered_pool_sha256"] and r["native"]["k"]==9
  ids=expected[:r["new_completed_roots"]];duplicates.extend(i for i in ids if i in seen);seen.update(ids);workers.append({"shard":shard,"complete":r["native"]["complete"],"new_completed_roots":len(ids),"found":r["native"]["found"]})
  if r["positive"]:positives.append(r["positive"])
 complete=len(seen)==N and not duplicates and not positives and all(w.get("complete",False) for w in workers)
 rows.append({"parent":parent,"source_incumbent_sha256":p["starting_sha256"],"pool_size":N,"previous_unique_completed_roots":old["total_unique_completed_roots"],"total_unique_completed_roots":len(seen),"uncovered_roots":sorted(set(range(N))-seen),"duplicate_completed_roots":duplicates,"all_root_coverage_complete":complete,"goal_filter_enabled":p["goal_filter_enabled"],"workers":workers,"positive_verifications":positives,"formal_absence_certificate":False})
report={"source_sha":os.environ["GITHUB_SHA"],"exchange_rank":9,"previous_coverage_sha256":plan["previous_coverage_sha256"],"parents":rows,"scope":"Old global prefix plus first-pass modulo prefixes plus new disjoint modulo suffixes. Only reported completed roots are closed. Missing/interrupted roots stay open. Five unfiltered strict families and two narrower known-goal-filtered families; no global bound or formal independent absence certificate."}
(OUT/"coverage.json").write_text(json.dumps(report,indent=2));print("FRESH9_TAIL_COVERAGE",json.dumps([{"parent":r["parent"],"complete":r["all_root_coverage_complete"],"uncovered":len(r["uncovered_roots"]),"positives":len(r["positive_verifications"])} for r in rows]),flush=True)
