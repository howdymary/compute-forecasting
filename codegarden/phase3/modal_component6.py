"""Exact radius-six improvements across the complete verified radius-five component."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import Ledger
from supervisor import verify
OUT=ROOT/"artifacts/phase3/component6_001";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2));return p
def publish():subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_component6.py")],check=True)
def main():
 import modal
 ledger=Ledger(OUT);source=os.environ["GITHUB_SHA"];calls=[];status={"status":"running","source_sha":source,"started_at":dt.datetime.now(dt.timezone.utc).isoformat()}
 try:
  component=ROOT/"artifacts/phase3/bundle_004/component5";report=json.loads((component/"report.json").read_text())
  assert report["complete_component"] and report["processed"]==38
  closed={}
  for rel in ["artifacts/phase3/bundle_003/strict6/report.json","artifacts/phase3/bundle_004/newroot6/report.json"]:
   r=json.loads((ROOT/rel).read_text())
   for row in r["rows"]:
    if row["complete"] and not row["found"]:closed[row["incumbent_witness_sha256"]]=rel
  cases=[]
  for row in report["rows"]:
   path=component/row["incumbent_file"];checked=verify(path);h=checked["reports"][0]["witness_sha256"]
   if h in closed:continue
   cases.append({"starting_words":path.read_text().splitlines(),"starting_sha256":h,"starting_verification":checked,"case_index":len(cases)})
  assert len(cases)==36
  # Select from measured implementations. Anchor receipt may not yet be published; safe fallback is the completed fast kernel.
  choice="fast";selection={"fast_root_cpu_seconds":251.957,"cache_root_cpu_seconds":267.655}
  receipt=ROOT/"artifacts/phase3/bundle_anchor_001/strict6/report.json"
  if receipt.exists():
   result=json.loads(receipt.read_text())["rows"][0];selection["anchor_root_cpu_seconds"]=result["cpu_seconds"]
   if result["complete"] and not result["found"] and result["cpu_seconds"]<251.957:choice="anchor"
  kernel=ROOT/("phase3/bundle_anchor.cpp" if choice=="anchor" else "phase3/bundle_fast.cpp")
  save("plan.json",{"cases":cases,"skipped_exact_radius6":closed,"selected_kernel":choice,"selection_evidence":selection,
   "kernel_sha256":hashlib.sha256(kernel.read_bytes()).hexdigest(),"target":227,"radius":6,"cpu_seconds_per_case":300,
   "hard_timeout":650,"resources":{"cpu":1,"memory_mb":1536},"max_concurrency":8,
   "reservation_total_usd":47.8,"interpretation":"All 36 unexamined roots in the 38-code component. Timeouts remain open neighborhoods."})
  ledger.reserve("modal","codegarden",1)
  image=modal.Image.debian_slim(python_version="3.11").apt_install("g++").add_local_file(str(kernel),"/opt/codegarden/bundle.cpp",copy=True)
  image=image.run_commands("g++ -O3 -std=c++17 /opt/codegarden/bundle.cpp -o /opt/codegarden/bundle")
  for rel in ["supervisor.py","protected/verify_descendants.py","protected/verify_lcs.py","protected/manifest.json"]:image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
  app=modal.App("codegarden-phase3-component-six",tags={"project":"codegarden","hypothesis":"beyond-radius-five-component"});volume=modal.Volume.from_name("codegarden-phase3-component6-checkpoints",create_if_missing=True)
  @app.function(serialized=True,image=image,cpu=1,memory=1536,timeout=650,max_containers=8,volumes={"/codegarden/results":volume})
  def worker(case,source):
   import hashlib,json,pathlib,subprocess,sys,time,uuid
   sys.path.insert(0,"/opt/codegarden");from supervisor import verify
   path=pathlib.Path("/codegarden/results")/uuid.uuid4().hex;path.mkdir();start=path/"starting.txt";start.write_text("\n".join(sorted(case["starting_words"]))+"\n");accepted=verify(start)
   metadata={**case,"source_sha":source,"radius":6,"cpu_seconds":300,"node_cap":100000000000,"neutral_cap":0,"resources":{"cpu":1,"memory_mb":1536,"timeout":650},
    "kernel_sha256":hashlib.sha256(pathlib.Path("/opt/codegarden/bundle.cpp").read_bytes()).hexdigest()}
   (path/"metadata.json").write_text(json.dumps(metadata));volume.commit();t=time.monotonic()
   try:
    proc=subprocess.run(["/opt/codegarden/bundle","16","6","300","100000000000","0"],input=start.read_text(),text=True,capture_output=True,timeout=600,check=True);r=json.loads(proc.stdout)
    pool=r.pop("candidate_pool");r["candidate_pool_sha256"]=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest()
    r["candidate_pool_definition"]="All outside binary 16-bit words with at most six distinct incumbent blockers";best=case["starting_words"]
    if r["found"]:
     C={int(w,2) for w in case["starting_words"]};C=C-set(r["removed"])|set(r["added"]);best=[format(w,"016b") for w in sorted(C)]
    q=path/"best.txt";q.write_text("\n".join(sorted(best))+"\n");result={"metadata":metadata,"native":r,"best_words":best,"independent_verification":verify(q),"runtime_seconds":time.monotonic()-t,"durable_path":str(path)}
   except Exception as e:
    result={"metadata":metadata,"status":"failed_or_timeout","error":str(e)[:1000],"best_words":case["starting_words"],"independent_verification":accepted,
     "runtime_seconds":time.monotonic()-t,"durable_path":str(path),"conclusion":"No neighborhood infeasibility conclusion"}
   (path/"result.json").write_text(json.dumps(result));volume.commit();return result
  ledger.reserve("modal","codegarden",36*650*.002);save("ledger_progress.json",ledger.summary());publish();rows=[]
  with app.run():
   calls=[worker.spawn(case,source) for case in cases]
   for i,call in enumerate(calls):
    r=call.get(timeout=2400);p=OUT/("worker_best_"+str(i)+".txt");p.write_text("\n".join(sorted(r["best_words"]))+"\n");r["host_independent_verification"]=verify(p);save("workers/"+str(i)+".json",r);rows.append(r)
    save("progress.json",{"collected":len(rows),"total":36,"best_verified":max(len(x["best_words"]) for x in rows),
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
  status.update(budget=ledger.summary(),finished_at=dt.datetime.now(dt.timezone.utc).isoformat());save("status.json",status);publish();print("COMPONENT6_FINAL",json.dumps(status),flush=True)
if __name__=="__main__":main()
