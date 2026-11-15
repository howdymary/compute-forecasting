"""Recover each worker only from its own archive, avoiding stale copied siblings."""
import datetime,hashlib,io,json,os,pathlib,subprocess,sys,time,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical
check_integrity();kind=sys.argv[1]
specs={"random":{"run":43721175424,"source":"3ab7f42e2b94bb2cfbf808ba0cb8e44021548fb7","prefix":"codegarden-random-resume-","cases":[0,2,4,6],"out":"random_resume_recovered_001"},"minimum":{"run":43721599974,"source":"e8915ee0d29c36364e33d347f475072e2ec1620d","prefix":"codegarden-min-growth-","cases":list(range(16)),"out":"min_growth_recovered_001"}}
spec=specs[kind];OUT=ROOT/"artifacts/phase3"/spec["out"];OUT.mkdir(parents=True,exist_ok=True);repo=os.environ["GITHUB_REPOSITORY"]
def api(path,raw=False):
 p=subprocess.run(["gh","api",path],capture_output=True,check=True);return p.stdout if raw else json.loads(p.stdout)
start=time.monotonic()
while True:
 run=api("repos/"+repo+"/actions/runs/"+str(spec["run"]));assert run["head_sha"]==spec["source"]
 if run["status"]=="completed":break
 if time.monotonic()-start>1000:raise RuntimeError("Source run still active; no checkpoint/result inferred")
 time.sleep(15)
artifacts=api("repos/"+repo+"/actions/runs/"+str(spec["run"])+"/artifacts?per_page=100")["artifacts"];byname={a["name"]:a for a in artifacts};rows=[];plan_hash=None;original_plan=None
for case in spec["cases"]:
 a=byname[spec["prefix"]+str(case)];assert not a["expired"] and a["workflow_run"]["head_sha"]==spec["source"]
 raw=api("repos/"+repo+"/actions/artifacts/"+str(a["id"])+"/zip",True);sha=hashlib.sha256(raw).hexdigest();assert a.get("digest")=="sha256:"+sha
 z=zipfile.ZipFile(io.BytesIO(raw));prefix=str(case)+"/";selected=[]
 for name in z.namelist():
  path=pathlib.PurePosixPath(name);assert not path.is_absolute() and ".." not in path.parts
  if not name.startswith(prefix) or name.endswith("/"):continue
  target=OUT/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name));selected.append(name)
 assert prefix+"report.json" in selected and prefix+"checkpoint.json" in selected
 cp=OUT/str(case)/"checkpoint.json";rp=OUT/str(case)/"report.json";state=json.loads(cp.read_text());r=json.loads(rp.read_text())
 assert state["case"]==case and r["case"]==case and state["source_sha"]==spec["source"] and r["source_sha"]==spec["source"]
 assert len(state["history"])==r["trials"] and len(state["current_fixed"])==r["final_closed_fixed_count"]
 witness=OUT/str(case)/"recovered_incumbent.txt";witness.write_text(canonical(state["incumbent"]));v=verify(witness);assert v["cardinality"]==state["best_in_family_verified"] and set(state["current_fixed"])<=set(state["incumbent"])
 plan_name="resumption_plan.json" if kind=="random" else "plan.json";pr=z.read(plan_name);ps=hashlib.sha256(pr).hexdigest()
 if plan_hash is None:plan_hash=ps;original_plan=json.loads(pr);(OUT/plan_name).write_bytes(pr)
 assert ps==plan_hash
 if kind=="random":
  base=next(row for row in original_plan["cases"] if row["case"]==case);new_trials=r["trials"]-base["old_trials"];new_closed=r["completed225_families"]-base["old_completed_families"]
 else:
  base=original_plan["migrations"][case];new_trials=r["new_trials"];new_closed=r["new_completed225_families"];assert r["trials"]-base["carried_trials"]==new_trials
 rows.append({"case":case,"source_run":spec["run"],"source_sha":spec["source"],"artifact_name":a["name"],"artifact_id":a["id"],"archive_sha256":sha,"checkpoint_sha256":hashlib.sha256(cp.read_bytes()).hexdigest(),"report_sha256":hashlib.sha256(rp.read_bytes()).hexdigest(),"copied_files":len(selected),"starting_fixed_count":base.get("old_fixed_count",base.get("starting_fixed_count")),"final_fixed_count":len(state["current_fixed"]),"new_trials":new_trials,"new_closed_families":new_closed,"cumulative_trials":r["trials"],"cumulative_closed_families":r["completed225_families"],"best_in_family_verified":v["cardinality"],"retained_global_best_verified":max(226,v["cardinality"]),"verification":v,"condition":r["mode"],"wall_seconds":r["wall_seconds"],"self_cpu_seconds":r.get("self_cpu_seconds"),"children_cpu_seconds":r.get("children_cpu_seconds")})
receipt={"recovery_source_sha":os.environ["GITHUB_SHA"],"source":spec,"observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"original_run_conclusion":run["conclusion"],"artifact_rule":"Each numeric directory comes solely from its own named worker artifact; never merge stale sibling directories.","plan_sha256":plan_hash,"cases":rows,"best_independently_verified":max(r["retained_global_best_verified"] for r in rows),"scope":"Evidence recovery, no repeated search/provider spending. Original pins preserved. Each incumbent passes both protected verifiers. Local negatives are scoped, without a formal global proof."}
(OUT/"recovery_receipt.json").write_text(json.dumps(receipt,indent=2));print("HULL_RECOVERY",json.dumps({"kind":kind,"cases":len(rows),"new_trials":sum(r["new_trials"] for r in rows),"new_closed":sum(r["new_closed_families"] for r in rows),"best":receipt["best_independently_verified"]}),flush=True)
