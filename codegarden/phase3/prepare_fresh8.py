"""Read each worker's own immutable archive; continue only valid completed root prefixes."""
import hashlib,io,json,os,pathlib,subprocess,sys,time,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity,verify
from search import pool_hash,digest_words
check_integrity();out=ROOT/"artifacts/phase3/fresh8_resume_001";out.mkdir(parents=True,exist_ok=True);repo=os.environ["GITHUB_REPOSITORY"];runid=43734021124;source="72871c8d78aacefbf79a3eea44e7e86387865fa1"
def api(path,raw=False):
 r=subprocess.run(["gh","api",path],capture_output=True,check=True);return r.stdout if raw else json.loads(r.stdout)
begin=time.monotonic()
while True:
 run=api("repos/"+repo+"/actions/runs/"+str(runid));assert run["head_sha"]==source
 if run["status"]=="completed":break
 if time.monotonic()-begin>600:raise RuntimeError("upstream still running; no completion inferred")
 time.sleep(15)
assert run["conclusion"]=="success"
artifacts={a["name"]:a for a in api("repos/"+repo+"/actions/runs/"+str(runid)+"/artifacts?per_page=100")["artifacts"]};rows=[];goal=False
for case in range(7):
 a=artifacts["codegarden-fresh225-"+str(case)];assert not a["expired"] and a["workflow_run"]["head_sha"]==source;raw=api("repos/"+repo+"/actions/artifacts/"+str(a["id"])+"/zip",True);archivehash=hashlib.sha256(raw).hexdigest();assert a["digest"]=="sha256:"+archivehash;z=zipfile.ZipFile(io.BytesIO(raw));prefix=str(case)+"/";target=out/"sources"/str(case);target.mkdir(parents=True,exist_ok=True)
 for p in z.namelist():assert not pathlib.PurePosixPath(p).is_absolute() and ".." not in pathlib.PurePosixPath(p).parts
 reportRaw=z.read(prefix+"report.json");r=json.loads(reportRaw);assert r["source_sha"]==source and r["case"]==case
 (target/"source_report.json").write_bytes(reportRaw)
 for name in ["starting.txt","known226.txt","ending.txt"]:(target/name).write_bytes(z.read(prefix+name))
 C=[int(w,2) for w in (target/"starting.txt").read_text().split()];v=verify(target/"starting.txt");assert v["cardinality"]==225 and digest_words(C)==r["starting_sha256"]
 ending=verify(target/"ending.txt");assert ending["cardinality"]==r["best_method_independently_verified"]
 row={"case":case,"archive_id":a["id"],"archive_sha256":archivehash,"source_report_sha256":hashlib.sha256(reportRaw).hexdigest(),"source_sha":source,"starting_sha256":digest_words(C),"source_verification":v,"eligible":False}
 if ending["cardinality"]>225:
  row["reason"]="upstream_positive_requires_followup";row["positive_verification"]=ending;goal|=ending["cardinality"]>=227
  print("VERIFIED_227_UPSTREAM" if ending["cardinality"]>=227 else "VERIFIED_NEW226_UPSTREAM",target/"ending.txt",flush=True)
 else:
  level=next(s for s in r["steps"] if s["k"]==8);assert level["incumbent_sha256"]==digest_words(C)
  (target/"source_level.json").write_text(json.dumps(level,indent=2));(target/"candidate_pool.txt").write_bytes(z.read(prefix+level["candidate_pool_file"]));P=list(map(int,(target/"candidate_pool.txt").read_text().split()));assert len(P)==len(set(P))==level["candidate_count"]
  ph=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in P)).hexdigest();assert ph==level["search_order_sha256"] and pool_hash(P)==level["candidate_pool_sha256"]
  assert level["root_shards"]==1 and level["root_shard"]==0 and level["last_finished_root"]==level["completed_roots"]-1
  assert level["complete"] or level["completed_roots"]>0 or level["active_root"]>=0,"Do not resume an incompletely built candidate pool"
  row.update(pool_size=len(P),pool_sha256=pool_hash(P),ordered_pool_sha256=ph,old_completed_prefix=level["completed_roots"],goal_filter_enabled=level["goal_filter_enabled"],old_complete=level["complete"],eligible=not level["complete"],reason="old_family_already_complete" if level["complete"] else "resume_open_suffix")
  if level["complete"]:assert level["completed_roots"]==len(P)
 rows.append(row)
plan={"colored_kernel_sha256":hashlib.sha256((ROOT/"phase3/bundle_colored.cpp").read_bytes()).hexdigest(),"source_sha":os.environ["GITHUB_SHA"],"upstream_source":source,"upstream_run":runid,"goal_candidate227":goal,"cases":rows,"shards_per_parent":4,"native_cpu_per_worker":150,"scope":"Old completed contiguous prefix plus four disjoint modulo4suffix shards. Same literal ordered pool and incumbent required at runtime. New greedy-color full-repair pruning was tested separately. Filtered roots only support their goal-model scope; no formal independent absence certificate."}
(out/"plan.json").write_text(json.dumps(plan,indent=2));print("FRESH8_PLAN",json.dumps([{k:r.get(k) for k in ["case","eligible","pool_size","old_completed_prefix","goal_filter_enabled","reason"]} for r in rows]),flush=True)
