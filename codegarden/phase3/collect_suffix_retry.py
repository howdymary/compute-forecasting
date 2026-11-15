import json,os,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/suffix_retry_001";plan=json.loads((OUT/"plan.json").read_text());families=[]
for p in plan["families"]:
 N=p["pool_size"];oldleft=set(p["previous_uncovered_roots"]);seen=set(range(N))-oldleft;duplicates=[];workers=[];positives=[]
 for q in plan["tasks"]:
  if q["family"]!=p["family"]:continue
  path=OUT/"workers"/str(q["case"])/"report.json"
  if not path.exists():workers.append({"case":q["case"],"status":"MISSING_OPEN"});continue
  r=json.loads(path.read_text());assert r["case"]==q["case"] and r["source_sha"]==os.environ["GITHUB_SHA"] and r["family"]==p["family"] and r["starting_sha256"]==p["starting_sha256"] and r["ordered_pool_sha256"]==p["ordered_pool_sha256"]
  E=sorted(i for i in oldleft if i%p["shards"]==q["shard"]);ids=E[:r["new_completed_roots"]];duplicates.extend(i for i in ids if i in seen);seen.update(ids);workers.append({"case":q["case"],"shard":q["shard"],"complete":r["native"]["complete"],"completed":len(ids),"found":r["native"]["found"]})
  if r["positive"]:positives.append({"case":q["case"],"positive":r["positive"],"followups":r["strict_followups"]})
 families.append({"family":p["family"],"name":p["name"],"rank":p["rank"],"starting_sha256":p["starting_sha256"],"pool_size":N,"previous_completed":p["previous_completed"],"new_unique_completed_roots":len(seen)-(N-len(oldleft)),"total_unique_completed_roots":len(seen),"uncovered_roots":sorted(set(range(N))-seen),"duplicate_completed_roots":duplicates,"all_root_coverage_complete":len(seen)==N and not duplicates and not positives and all(w.get("complete",False) for w in workers),"workers":workers,"positive_verifications":positives})
report={"source_sha":os.environ["GITHUB_SHA"],"families":families,"formal_absence_certificate":False,"scope":plan["scope"]}
(OUT/"coverage.json").write_text(json.dumps(report,indent=2));print("SUFFIX_RETRY_COVERAGE",json.dumps([{"name":f["name"],"complete":f["all_root_coverage_complete"],"open":len(f["uncovered_roots"]),"positives":len(f["positive_verifications"])} for f in families]),flush=True)
