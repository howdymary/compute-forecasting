"""Deterministically partition a radius-nine search with independently checked reductions."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import Ledger,cli
from supervisor import verify
OUT=ROOT/"artifacts/phase3/sharded9_001";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2));return p
def publish():subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_sharded9.py")],check=True)
def main():
 import modal
 from phase3.renew_budget3 import main as renew
 renew();renewal=json.loads((ROOT/"artifacts/phase3/budget_renewal_003/receipt.json").read_text())
 assert renewal["status"]=="renewed","No Modal launch without sufficient authenticated floor and carried history"
 ledger=Ledger(OUT);source=os.environ["GITHUB_SHA"];calls=[];status={"status":"running","source_sha":source,"started_at":dt.datetime.now(dt.timezone.utc).isoformat()}
 try:
  base=ROOT/"artifacts/phase3/sharded9_001/preflight/baseline.txt";checked=verify(base);words=base.read_text().splitlines()
  info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());assert checked["reports"][0]["witness_sha256"]==info["root_hash"]
  import importlib.util
  spec=importlib.util.spec_from_file_location("protected_dom",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
  certs=json.loads((ROOT/"artifacts/phase3/soft_global_001/dominance.json").read_text())["certificates"]
  for c in certs:assert set(D.descendants(format(c["replacement"],"016b")))<=set(D.descendants(format(c["removed"],"016b")))
  mask=ROOT/".build/dominated.txt";mask.write_text("\n".join(str(c["removed"]) for c in certs)+"\n")
  C={int(w,2) for w in words};proofs={r["incumbent_witness_sha256"]:r for r in info["report"]["rows"]};clauses=[]
  occupied={d:w for w in C for d in D.descendants(format(w,"016b"))}
  for other in info["codes"]:
   U=set(other)-C;R=C-set(other);h=hashlib.sha256(("\n".join(format(w,"016b") for w in sorted(other))+"\n").encode()).hexdigest();r=proofs[h]
   assert r["complete"] and not r["found"] and r["k"]==7
   if not U or 9-len(U)>7:continue
   assert len(U)==len(R) and {occupied[d] for w in U for d in D.descendants(format(w,"016b")) if d in occupied}==R
   clauses.append(sorted(U))
  clausepath=ROOT/".build/learned.txt";clausepath.write_text("".join(str(len(g))+" "+" ".join(map(str,g))+"\n" for g in clauses))
  cases=[{"starting_words":words,"starting_sha256":info["root_hash"],"starting_verification":checked,"case_index":i,"root_shard":i,"root_shards":16} for i in range(16)]
  kernel=ROOT/"phase3/bundle_sharded.cpp"
  save("plan.json",{"cases":cases,"target":227,"radius":9,"cpu_seconds_per_case":600,"hard_timeout":900,"max_concurrency":8,"resources":{"cpu":1,"memory_mb":2048},
   "learned_groups":clauses,"proof_source":info["proof_source"],"kernel_sha256":hashlib.sha256(kernel.read_bytes()).hexdigest(),"reservation_total_usd":29.8,
   "partition":"Canonical minimum-index roots r mod 16. All compatible suffix candidates remain available. No random seed; deterministic exact search. All 16 complete statuses required for a full radius-nine no-improvement conclusion."})
  ledger.reserve("modal","codegarden",1)
  image=modal.Image.debian_slim(python_version="3.11").apt_install("g++").add_local_file(str(kernel),"/opt/codegarden/bundle.cpp",copy=True)
  image=image.add_local_file(str(mask),"/opt/codegarden/dominated.txt",copy=True).add_local_file(str(clausepath),"/opt/codegarden/learned.txt",copy=True)
  image=image.run_commands("g++ -O3 -std=c++17 /opt/codegarden/bundle.cpp -o /opt/codegarden/bundle")
  for rel in ["supervisor.py","protected/verify_descendants.py","protected/verify_lcs.py","protected/manifest.json"]:image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
  app=modal.App("codegarden-phase3-sharded-nine",tags={"project":"codegarden","hypothesis":"canonical-root-partitions"});volume=modal.Volume.from_name("codegarden-phase3-sharded9-checkpoints",create_if_missing=True)
  @app.function(serialized=True,image=image,cpu=1,memory=2048,timeout=900,max_containers=8,volumes={"/codegarden/results":volume})
  def worker(case,source):
   import hashlib,json,os,pathlib,subprocess,sys,time,uuid
   sys.path.insert(0,"/opt/codegarden");from supervisor import verify
   path=pathlib.Path("/codegarden/results")/uuid.uuid4().hex;path.mkdir();start=path/"starting.txt";start.write_text("\n".join(sorted(case["starting_words"]))+"\n");accepted=verify(start)
   metadata={**case,"source_sha":source,"radius":9,"cpu_seconds":600,"node_cap":100000000000,"neutral_cap":0,"resources":{"cpu":1,"memory_mb":2048,"timeout":900},"reservation_upper_usd":1.8,"actual_worker_cost":"not independently attributed; conservative hold retained",
    "kernel_sha256":hashlib.sha256(pathlib.Path("/opt/codegarden/bundle.cpp").read_bytes()).hexdigest()}
   (path/"metadata.json").write_text(json.dumps(metadata));volume.commit();t=time.monotonic()
   try:
    proc=subprocess.run(["/opt/codegarden/bundle","16","9","600","100000000000","0"],input=start.read_text(),text=True,capture_output=True,timeout=850,check=True,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="/opt/codegarden/dominated.txt",CODEGARDEN_LEARNED_NOGOODS="/opt/codegarden/learned.txt",CODEGARDEN_ROOT_SHARDS=str(case["root_shards"]),CODEGARDEN_ROOT_SHARD=str(case["root_shard"])));r=json.loads(proc.stdout)
    pool=r.pop("candidate_pool");r["candidate_pool_sha256"]=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest()
    r["candidate_pool_definition"]="All outside binary 16-bit words with at most nine distinct incumbent blockers, certified dominance filtered, canonical root partition";best=case["starting_words"]
    if r["found"]:
     C={int(w,2) for w in case["starting_words"]};C=C-set(r["removed"])|set(r["added"]);best=[format(w,"016b") for w in sorted(C)]
    q=path/"best.txt";q.write_text("\n".join(sorted(best))+"\n");result={"metadata":metadata,"native":r,"best_words":best,"independent_verification":verify(q),"runtime_seconds":time.monotonic()-t,"durable_path":str(path)}
   except Exception as e:
    result={"metadata":metadata,"status":"failed_or_timeout","error":str(e)[:1000],"best_words":case["starting_words"],"independent_verification":accepted,
     "runtime_seconds":time.monotonic()-t,"durable_path":str(path),"conclusion":"No neighborhood infeasibility conclusion"}
   (path/"result.json").write_text(json.dumps(result));volume.commit();return result
  ledger.reserve("modal","codegarden",16*900*.002);save("ledger_progress.json",ledger.summary());publish();rows=[]
  with app.run():
   calls=[worker.spawn(case,source) for case in cases]
   for i,call in enumerate(calls):
    r=call.get(timeout=2400);p=OUT/("worker_best_"+str(i)+".txt");p.write_text("\n".join(sorted(r["best_words"]))+"\n");r["host_independent_verification"]=verify(p);save("workers/"+str(i)+".json",r);rows.append(r)
    save("progress.json",{"collected":len(rows),"total":16,"best_verified":max(len(x["best_words"]) for x in rows),
     "complete_no_improvement":sum(x.get("native",{}).get("complete",False) and not x.get("native",{}).get("found",False) for x in rows)});publish()
    if len(r["best_words"])>=227:
     status["verified_improvement"]={"case":i,"witness":str(p.relative_to(ROOT.parent)),"verification":r["host_independent_verification"]}
     for other in calls[i+1:]:
      try:other.cancel()
      except Exception:pass
     break
  status.update(status="completed",cases_collected=len(rows),best_verified=max([226]+[len(r["best_words"]) for r in rows]),
   complete_no_improvement=sum(r.get("native",{}).get("complete",False) and not r.get("native",{}).get("found",False) for r in rows))
 except Exception as e:
  status.update(status="failed_or_partial",error=str(e)[:1000]);traceback.print_exc()
  for call in calls:
   try:call.cancel()
   except Exception:pass
 finally:
  try:status["account_summary_at_finish"]=json.loads(cli("modal","billing","summary","--json"))
  except Exception as e:status["account_summary_error"]=str(e)[:300]
  status.update(budget=ledger.summary(),finished_at=dt.datetime.now(dt.timezone.utc).isoformat());save("status.json",status);publish();print("SHARDED9_FINAL",json.dumps(status),flush=True)
if __name__=="__main__":main()
