"""Audit old-prefix plus new disjoint suffix coverage without inferring missing results."""
import json,pathlib,os
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/fresh8_resume_001";plan=json.loads((OUT/"plan.json").read_text());rows=[]
for p in plan["cases"]:
 case=p["case"];n=p.get("pool_size",0);seen=set(range(p.get("old_completed_prefix",0)));duplicates=[];workers=[];positives=[]
 for shard in range(4):
  path=OUT/"workers"/str(4*case+shard)/"report.json"
  if not path.exists():workers.append({"shard":shard,"status":"MISSING_OPEN"});continue
  r=json.loads(path.read_text());assert r["source_sha"]==os.environ["GITHUB_SHA"] and r["parent"]==case and r["shard"]==shard
  if r["status"]!="SEARCHED":workers.append({"shard":shard,"status":r["status"],"reason":r["reason"]});continue
  assert r["starting_sha256"]==p["starting_sha256"] and r["ordered_pool_sha256"]==p["ordered_pool_sha256"]
  ids=[i for i in range(p["old_completed_prefix"],n) if i%4==shard][:r["new_completed_roots"]]
  duplicates.extend(i for i in ids if i in seen);seen.update(ids);workers.append({"shard":shard,"complete":r["native"]["complete"],"completed_roots":len(ids),"found":r["native"]["found"]})
  if r["positive"]:positives.append(r["positive"])
 complete=p.get("old_complete",False) or (p["eligible"] and len(seen)==n and not duplicates and all(w.get("complete",False) for w in workers) and not positives)
 rows.append({"parent":case,"source_incumbent_sha256":p["starting_sha256"],"pool_size":n,"old_completed_prefix":p.get("old_completed_prefix"),"total_unique_completed_roots":len(seen),"uncovered_roots":sorted(set(range(n))-seen),"duplicate_completed_roots":duplicates,"all_root_coverage_complete":complete,"goal_filter_enabled":p.get("goal_filter_enabled"),"workers":workers,"positive_verifications":positives,"formal_absence_certificate":False})
report={"source_sha":os.environ["GITHUB_SHA"],"parents":rows,"scope":"Coverage audit only. A completed unfiltered family is a conditional native strict-augmentation result at radius8 for this225seed. Filtered completion is limited to encoded connected goal bundles/saturated pools. No global result or independent formal absence proof. Missing workers and interrupted roots remain open."}
(OUT/"coverage.json").write_text(json.dumps(report,indent=2));print("FRESH8_COVERAGE",json.dumps([{"parent":r["parent"],"complete":r["all_root_coverage_complete"],"uncovered":len(r["uncovered_roots"]),"positives":len(r["positive_verifications"])} for r in rows]),flush=True)
