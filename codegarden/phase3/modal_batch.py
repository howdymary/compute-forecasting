"""One bounded, serialized Modal batch: four families, joint-pair repair and exact polish."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import Ledger
from supervisor import verify
OUT=ROOT/"artifacts/phase3/modal_pair_001";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2));return p
def publish():
 subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_modal.py")],check=True)
def main():
 import modal
 history_path=ROOT/"budget/historical-usage.json";history=json.loads(history_path.read_text())
 previous=OUT/"status.json";progress=OUT/"ledger_progress.json";carried=None
 if previous.exists():carried=json.loads(previous.read_text()).get("budget")
 elif progress.exists():carried=json.loads(progress.read_text())
 if carried:
  for p,v in carried.items():history["conservative_totals"][p]=max(history["conservative_totals"].get(p,0),v["reserved"]+v["provider_reported_or_estimated"])
  history["source_run"]="carried-modal-batch-"+os.environ["GITHUB_SHA"];history_path.write_text(json.dumps(history,indent=2))
 ledger=Ledger(OUT);source=os.environ["GITHUB_SHA"];calls=[];status={"status":"running","source_sha":source,"started_at":dt.datetime.now(dt.timezone.utc).isoformat()}
 try:
  global_checked=verify(ROOT/"artifacts/best_code.txt");target=global_checked["cardinality"]+1
  sources=[]
  for i,size in enumerate([208,223,225,226]):
   path=next((ROOT/"artifacts/baselines").glob("arena_"+str(size)+"_*.txt"));checked=verify(path)
   sources.append({"family":path.stem,"words":path.read_text().splitlines(),"starting_sha256":checked["reports"][0]["witness_sha256"],"seed":970000+i,"mode":"pairbreak","native_cpu_seconds":600})
  save("plan.json",{"cases":sources,"target":target,"resources_per_worker":{"cpu_request":1,"memory_mb":1536,"hard_timeout_seconds":1300},
   "max_concurrency":4,"reservation_per_worker_usd":2.6,"interpretation":"Different source families, same global target; discovery experiment, not a causal model comparison."})
  ledger.reserve("modal","codegarden",1)
  image=modal.Image.debian_slim(python_version="3.11").apt_install("g++").pip_install("ortools==9.14.6206")
  for rel in ["kernel.cpp","phase2/kernel_v2.cpp","phase3/infeasible.cpp"]:
   image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel,copy=True)
  image=image.run_commands("g++ -O3 -std=c++17 /opt/codegarden/phase3/infeasible.cpp -o /opt/codegarden/infeasible",
    "g++ -O3 -std=c++17 /opt/codegarden/phase2/kernel_v2.cpp -o /opt/codegarden/kernel_v2")
  for rel in ["phase3/refine.py","search.py","cp_sat.py","supervisor.py","protected/verify_descendants.py","protected/verify_lcs.py","protected/manifest.json"]:
   image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
  app=modal.App("codegarden-phase3-pair-repair",tags={"project":"codegarden","hypothesis":"infeasible-pair-repair"})
  volume=modal.Volume.from_name("codegarden-phase3-pair-checkpoints",create_if_missing=True)
  @app.function(serialized=True,image=image,cpu=1,memory=1536,timeout=1300,max_containers=4,volumes={"/codegarden/results":volume})
  def worker(spec,target,source):
   import importlib.util,threading,uuid
   import pathlib,sys,json,time,hashlib,subprocess
   sys.path.insert(0,"/opt/codegarden")
   from supervisor import verify
   from phase3.refine import refine
   path=pathlib.Path("/codegarden/results")/uuid.uuid4().hex;path.mkdir()
   baseline=path/"baseline.txt";baseline.write_text("\n".join(sorted(spec["words"]))+"\n");accepted=verify(baseline)
   metadata={**spec,"source_sha":source,"target":target,"starting_verification":accepted,
     "native_source_sha256":hashlib.sha256(pathlib.Path("/opt/codegarden/phase3/infeasible.cpp").read_bytes()).hexdigest(),
     "resources":{"cpu":1,"memory_mb":1536,"hard_timeout_seconds":1300}}
   (path/"metadata.json").write_text(json.dumps(metadata));volume.commit()
   stop=threading.Event()
   def persist():
    while not stop.wait(20):
     try:volume.commit()
     except Exception:pass
   thread=threading.Thread(target=persist,daemon=True);thread.start();start=time.perf_counter()
   try:
    result=subprocess.run(["/opt/codegarden/infeasible",str(spec["native_cpu_seconds"]),str(spec["seed"]),spec["mode"],str(path/"checkpoint.json"),str(target)],
      input=baseline.read_text(),text=True,capture_output=True,timeout=spec["native_cpu_seconds"]*1.8+25,check=True)
    native=json.loads(result.stdout);(path/"native.json").write_text(json.dumps(native))
    best_words=spec["words"];best=accepted
    if native["proposed_zero_conflict"]:
     q=path/"worker_native_winner.txt";q.write_text("\n".join(sorted(format(w,"016b") for w in native["closest_state"]))+"\n")
     best=verify(q);best_words=q.read_text().splitlines();refinement={"skipped":"Native zero-conflict proposal passed both verifiers"}
    else:
     refinement=refine(native,spec["words"],target,spec["seed"],path/"refinement")
     for item in refinement["valid_projections"]+refinement["polished"]:
      if item["verification"]["cardinality"]>best["cardinality"]:
       best=item["verification"];best_words=[format(w,"016b") for w in item["words"]]
     if refinement.get("winner"):
      q=path/"worker_exact_winner.txt";q.write_text("\n".join(sorted(format(w,"016b") for w in refinement["winner"]))+"\n")
      best=verify(q);best_words=q.read_text().splitlines()
    q=path/"worker_best.txt";q.write_text("\n".join(sorted(best_words))+"\n");verify(q)
    r={"metadata":metadata,"native":native,"refinement":refinement,"best_verification":best,"best_words":best_words,
      "runtime_seconds":time.perf_counter()-start,"durable_path":str(path)}
    (path/"result.json").write_text(json.dumps(r))
   finally:
    stop.set();thread.join(timeout=30);volume.commit()
   return r
  ledger.reserve("modal","codegarden",4*1300*.002);save("ledger_progress.json",ledger.summary());publish()
  rows=[]
  with app.run():
   calls=[worker.spawn(s,target,source) for s in sources]
   save("submitted.json",{"submitted_at":dt.datetime.now(dt.timezone.utc).isoformat(),"workers":len(calls)})
   for i,call in enumerate(calls):
    r=call.get(timeout=1500);q=OUT/("worker_best_"+str(i)+".txt");q.write_text("\n".join(sorted(r["best_words"]))+"\n")
    r["host_independent_verification"]=verify(q);save("workers/"+str(i)+".json",r);rows.append(r)
    save("progress.json",{"complete":len(rows),"best":max([global_checked["cardinality"]]+[r["host_independent_verification"]["cardinality"] for r in rows])});publish()
    if r["host_independent_verification"]["cardinality"]>=target:
     for other in calls[i+1:]:
      try:other.cancel()
      except Exception:pass
     status["verified_improvement"]={"witness":str(q.relative_to(ROOT.parent)),"verification":r["host_independent_verification"]};break
  status.update({"status":"completed","workers_collected":len(rows),"target":target,
   "best_verified":max([global_checked["cardinality"]]+[r["host_independent_verification"]["cardinality"] for r in rows]),
   "minimum_pair_energies":[r["native"]["minimum_pair_energy"] for r in rows],
   "near_state_counts":[r["native"].get("distinct_near_states") for r in rows],
   "publication_scope":"Only explicit accepted witnesses determine score; positive-energy target states are invalid diagnostics."})
 except Exception as e:
  status.update({"status":"failed_or_partial","error":str(e)[:800]});traceback.print_exc()
  for call in calls:
   try:call.cancel()
   except Exception:pass
 finally:
  status["budget"]=ledger.summary();status["finished_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
  save("status.json",status);publish();print("MODAL_PAIR_FINAL "+json.dumps(status),flush=True)
if __name__=="__main__":main()
