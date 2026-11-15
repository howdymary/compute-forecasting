"""Persistent precomputed search and batched durable checkpoints; only protected exports score."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import Ledger
from supervisor import verify
OUT=ROOT/"artifacts/phase3/persistent_bundle_001";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2));return p
def publish():subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_persistent.py")],check=True)
def main():
 import modal
 previous=json.loads((ROOT/"artifacts/phase3/modal_bundle_001/status.json").read_text());assert previous["status"]=="completed"
 history={"source_run":"modal-bundle-complete-"+previous["source_sha"],"conservative_totals":{p:v["reserved"]+v["provider_reported_or_estimated"] for p,v in previous["budget"].items()},"reason":"All older holds retained, including failed-launch reservation."}
 if (OUT/"status.json").exists():
  old=json.loads((OUT/"status.json").read_text()).get("budget",{})
  for p,v in old.items():history["conservative_totals"][p]=max(history["conservative_totals"].get(p,0),v["reserved"]+v["provider_reported_or_estimated"])
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2));ledger=Ledger(OUT);calls=[];status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"started_at":dt.datetime.now(dt.timezone.utc).isoformat()}
 try:
  plan=json.loads((ROOT/"artifacts/phase3/modal_bundle_001/plan.json").read_text());starts=plan["starting_projections"];assert len(starts)>=8
  save("plan.json",{"hypothesis":"Precomputed randomized neutral walks can explore distant valid basins at materially higher throughput.",
   "previous_measured_bottleneck":{"processed":[96,96],"native_cpu_seconds":[1.9,2.88],"wall_seconds":[207.78,529.07]},
   "conditions":["fixed3","adaptive34"],"same_starting_codes":starts[:8],"search_cpu_cap":400,"worker_wall_cap":650,"max_states":6000,
   "verification":"Both protected verifiers before promotion of any new best and on final exports; intermediate neutral states are proposals checked by native invariants.",
   "actual_tinker_prior_action":plan["actual_tinker_proposal"],"new_training":False,"resources":{"cpu":1,"memory_mb":1536,"timeout":900},"max_concurrency":2})
  ledger.reserve("modal","codegarden",1)
  image=modal.Image.debian_slim(python_version="3.11").apt_install("g++").add_local_file(str(ROOT/"phase3/bundle_server.cpp"),"/opt/codegarden/bundle.cpp",copy=True)
  image=image.run_commands("g++ -O3 -std=c++17 /opt/codegarden/bundle.cpp -o /opt/codegarden/bundle")
  for rel in ["supervisor.py","protected/verify_descendants.py","protected/verify_lcs.py","protected/manifest.json"]:image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
  app=modal.App("codegarden-phase3-persistent-neutral",tags={"project":"codegarden","hypothesis":"persistent-distant-basins"});volume=modal.Volume.from_name("codegarden-phase3-persistent-checkpoints",create_if_missing=True)
  @app.function(serialized=True,image=image,cpu=1,memory=1536,timeout=900,max_containers=2,volumes={"/codegarden/results":volume})
  def worker(starts,condition,seed,source):
   import functools,hashlib,json,pathlib,random,select,subprocess,sys,time,uuid
   sys.path.insert(0,"/opt/codegarden");from supervisor import verify
   path=pathlib.Path("/codegarden/results")/uuid.uuid4().hex;path.mkdir();rng=random.Random(seed);rows=[];seen=set();queue=[tuple(sorted(C)) for C in starts]
   reversals=[int(format(w,"016b")[::-1],2) for w in range(65536)]
   def canonical(C):return "".join(format(w,"016b")+"\n" for w in sorted(C))
   @functools.lru_cache(maxsize=12000)
   def orbit(C):
    r=tuple(sorted(reversals[w] for w in C))
    return min(C,tuple(65535-w for w in reversed(C)),r,tuple(65535-w for w in reversed(r)))
   best=queue[0];p=path/"best.txt";p.write_text(canonical(best));accepted=verify(p)
   server=subprocess.Popen(["/opt/codegarden/bundle","--server"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(path/"native_stderr.log").open("w"),text=True)
   cpu=0;total_process_cpu=0;started=time.monotonic();last_commit=started;last_gain=started;duplicate_pops=0;switches=[];last_k=None;skipped_verifier_calls=0
   try:
    while queue and cpu<400 and time.monotonic()-started<650 and len(rows)<6000:
     pos=rng.randrange(len(queue));C=queue.pop(pos);key=orbit(C)
     if key in seen:duplicate_pops+=1;continue
     seen.add(key);i=len(rows);stale=time.monotonic()-last_gain
     k=5 if len(C)>=226 else (4 if condition=="adaptive34" and stale>90 and i%8==0 else 3)
     if k!=last_k:switches.append({"step":i,"k":k,"reason":"new 226-word basin" if len(C)>=226 else "stagnation-budgeted larger repair" if k==4 else "breadth through radius-three neutral moves","claim_of_exhaustion":False});last_k=k
     seconds=min(20 if k>=4 else 2,400-cpu);sample_seed=seed*100000+i+1
     server.stdin.write("16 "+str(k)+" "+str(seconds)+" 100000000000 96 "+str(sample_seed)+" "+str(len(C))+"\n"+canonical(C));server.stdin.flush()
     ready,_,_=select.select([server.stdout],[],[],seconds+90)
     if not ready:raise TimeoutError("Native server request exceeded bounded wall allowance")
     line=server.stdout.readline()
     if not line:raise RuntimeError("Native server exited; inspect durable stderr")
     r=json.loads(line);cpu+=r["cpu_seconds"];total_process_cpu=r["process_cpu_total"];pool=r.pop("candidate_pool");neighbors=r.pop("neighbors")
     r.update(incumbent_words=list(C),incumbent_sha256=hashlib.sha256(canonical(C).encode()).hexdigest(),
      candidate_pool_sha256=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in sorted(pool))).hexdigest(),
      pool_definition="All outside words with at most k distinct incumbent blockers; order shuffled with logged seed",seconds_limit=seconds,
      intermediate_state_independently_verified=False)
     if r["found"]:
      candidate=tuple(sorted(set(C)-set(r["removed"])|set(r["added"])));q=path/("improvement_"+str(i)+".txt");q.write_text(canonical(candidate))
      r["independent_verification"]=verify(q)
      if len(candidate)>len(best):best=candidate;accepted=r["independent_verification"];last_gain=time.monotonic()
      queue.append(candidate)
     fresh=0
     for A in neighbors:
      A=tuple(A)
      if orbit(A) not in seen:queue.append(A);fresh+=1
     if len(queue)>600:rng.shuffle(queue);queue=queue[:600]
     r["fresh_proposed_neighbors"]=fresh;r["frontier_after_cap"]=len(queue);rows.append(r)
     if time.monotonic()-last_commit>15 or len(best)>=227:
      (path/"checkpoint.json").write_text(json.dumps({"source_sha":source,"seed":seed,"condition":condition,"best":best,"frontier":queue,
       "processed":len(rows),"seen_count":len(seen),"cpu_seconds":cpu,"process_cpu_total":total_process_cpu,"switches":switches}))
      (path/"experiments.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows));volume.commit();last_commit=time.monotonic()
     if len(best)>=227:break
   finally:
    try:server.stdin.close();server.wait(timeout=15)
    except Exception:server.kill();server.wait(timeout=15)
   p=path/"best.txt";p.write_text(canonical(best));result={"metadata":{"condition":condition,"seed":seed,"source_sha":source,"same_starts":starts},
    "best_words":[format(w,"016b") for w in best],"independent_verification":verify(p),"search_cpu_seconds":cpu,"process_cpu_seconds":total_process_cpu,
    "runtime_seconds":time.monotonic()-started,"processed":len(rows),"frontier":len(queue),"duplicate_pops":duplicate_pops,"switches":switches,
    "experiments":rows,"durable_path":str(path),"negative_scope":"Only logged complete native neighborhoods; partial/capped components remain unresolved.",
    "native_source_sha256":hashlib.sha256(pathlib.Path("/opt/codegarden/bundle.cpp").read_bytes()).hexdigest()}
   (path/"result.json").write_text(json.dumps(result));(path/"experiments.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows));volume.commit();return result
  ledger.reserve("modal","codegarden",2*900*.002);save("ledger_progress.json",ledger.summary());publish();rows=[]
  with app.run():
   calls=[worker.spawn(starts[:8],condition,1011001+i,os.environ["GITHUB_SHA"]) for i,condition in enumerate(["fixed3","adaptive34"])]
   for i,call in enumerate(calls):
    r=call.get(timeout=1200);p=OUT/("worker_best_"+str(i)+".txt");p.write_text("\n".join(sorted(r["best_words"]))+"\n");r["host_independent_verification"]=verify(p);save("workers/"+str(i)+".json",r);rows.append(r);publish()
    if len(r["best_words"])>=227:
     for other in calls[i+1:]:
      try:other.cancel()
      except Exception:pass
     break
  status.update(status="completed",workers_collected=len(rows),best_verified=max([226]+[len(r["best_words"]) for r in rows]))
 except Exception as e:
  status.update(status="failed_or_partial",error=str(e)[:1000]);traceback.print_exc()
  for call in calls:
   try:call.cancel()
   except Exception:pass
 finally:
  status.update(budget=ledger.summary(),finished_at=dt.datetime.now(dt.timezone.utc).isoformat());save("status.json",status);publish();print("PERSISTENT_FINAL",json.dumps(status),flush=True)
if __name__=="__main__":main()
