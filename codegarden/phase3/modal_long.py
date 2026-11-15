"""Bounded full-universe diversification with hard resource limits and matched native CPU allowances."""
import concurrent.futures,datetime as dt,hashlib,json,os,pathlib,random,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import Ledger,cli
from supervisor import verify
OUT=ROOT/"artifacts/phase3/long_diversification_001";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2))
def publish():subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_long.py")],check=True)
def main():
 import modal
 from phase3.research3 import read
 previous=read("codegarden/artifacts/phase3/sharded10_001/status.json","codegarden-modal-008")
 assert previous["status"] in ["completed","failed_or_partial"]
 history={"source_run":"sharded10-complete-"+previous["source_sha"],"conservative_totals":{p:v["reserved"]+v["provider_reported_or_estimated"] for p,v in previous["budget"].items()},
  "reason":"All unknown historical and completed hard-time holds retained. New lower unit ceiling applies only to new explicitly CPU/memory-limited workers."}
 assert history["conservative_totals"]["modal"]>=141.76
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2))
 from phase3.renew_budget5 import main as renew
 renew();receipt=json.loads((ROOT/"artifacts/phase3/budget_renewal_005/receipt.json").read_text());assert receipt["status"]=="renewed"
 ledger=Ledger(OUT);source=os.environ["GITHUB_SHA"];calls=[];rows=[];status={"status":"running","source_sha":source,"started_at":dt.datetime.now(dt.timezone.utc).isoformat()}
 try:
  roots=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text())["codes"];core=set.intersection(*(set(C) for C in roots))
  rev=lambda w:int(format(w,"016b")[::-1],2)
  families=[core,{65535^w for w in core},{rev(w) for w in core},{65535^rev(w) for w in core}]
  paths=[next((ROOT/"artifacts/baselines").glob("arena_225_*.txt")),ROOT/"artifacts/phase3/frontier_002/projected225/starting_0.txt"]
  cases=[]
  for family,path in enumerate(paths):
   v=verify(path);assert v["cardinality"]==225;words=path.read_text().splitlines();C={int(w,2) for w in words}
   for repeat in range(2):
    pair=family*2+repeat;rng=random.Random(1190001+pair);banned=sorted({rng.choice(sorted(F-C-{0,65535})) for F in families})
    for policy in ["fixed","adaptive"]:
     cases.append({"case_index":len(cases),"pair":pair,"family":family,"starting_words":words,"starting_verification":v,"seed":1191001+pair,"policy":policy,"forbidden":banned})
  save("plan.json",{"cases":cases,"target":227,"native_cpu_allowance_per_case":6000,"wall_limit_per_worker":7200,"hard_timeout":7800,"max_concurrency":8,
   "resources":{"cpu_request_and_limit":1,"memory_request_and_limit_mb":1024,"gpu":None,"scaledown_window":2,"retries":0},
   "reservation_usd":7.22,"unit_upper_usd_per_second":.0001,"resource_seconds_reserved":8*(7800+600),"image_reserve_usd":.5,
   "pricing_source":"https://modal.com/pricing","pricing_observed":"2026-11-15","base_cpu_core_second":.0000131,"base_gib_second":.00000222,
   "cost_scope":"Ceiling is over six times CPU1+GiB1 base Function pricing, with startup/idle overhead and image reserve. This is a new conservative reservation, not an actual charge; prior unknown holds remain.",
   "comparison":"Four matched pairs, same family/seed/forbidden set and 6000 native child-CPU-second allowance. Exact polishing/controller CPU and wall are separate; early win or hard-time interruption censors comparison. No new training.",
   "pool_definition":"All 65536 binary words except the four recorded backbone exclusions. Exclusions apply only to these experiments, never to mathematical validity or the whole project."})
  ledger.reserve("modal","codegarden",.5)
  image=modal.Image.debian_slim(python_version="3.11").apt_install("g++")
  for sourcefile,target in [("phase3/pool_kernel_cpu.cpp","pool.cpp"),("phase3/bundle_connected_v2.cpp","bundle.cpp")]:
   image=image.add_local_file(str(ROOT/sourcefile),"/opt/codegarden/"+target,copy=True)
  image=image.run_commands("g++ -O3 -std=c++17 /opt/codegarden/pool.cpp -o /opt/codegarden/pool","g++ -O3 -std=c++17 /opt/codegarden/bundle.cpp -o /opt/codegarden/bundle")
  for rel in ["supervisor.py","protected/verify_descendants.py","protected/verify_lcs.py","protected/manifest.json"]:image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
  app=modal.App("codegarden-phase3-long-diversification",tags={"project":"codegarden","hypothesis":"full-universe-backbone-avoidance"})
  volume=modal.Volume.from_name("codegarden-phase3-long-checkpoints",create_if_missing=True)
  @app.function(serialized=True,image=image,cpu=(1,1),memory=(1024,1024),scaledown_window=2,retries=0,timeout=7800,max_containers=8,volumes={"/codegarden/results":volume})
  def worker(case,source):
   import hashlib,json,os,pathlib,resource,subprocess,sys,threading,time,uuid
   sys.path.insert(0,"/opt/codegarden");from supervisor import verify
   path=pathlib.Path("/codegarden/results")/uuid.uuid4().hex;path.mkdir();best=case["starting_words"];base=path/"best.txt";base.write_text("\n".join(sorted(best))+"\n");accepted=verify(base)
   mask=path/"pool.txt";allowed=[w for w in range(65536) if w not in case["forbidden"]];mask.write_text("\n".join(map(str,allowed))+"\n")
   meta={**case,"source_sha":source,"pool_sha256":hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in allowed)).hexdigest(),"kernel_sha256":hashlib.sha256(pathlib.Path("/opt/codegarden/pool.cpp").read_bytes()).hexdigest(),
    "resources":{"cpu_request_and_limit":1,"memory_request_and_limit_mb":1024,"timeout":7800},"durable_path":str(path)}
   (path/"metadata.json").write_text(json.dumps(meta));volume.commit();began=time.monotonic();used=0.;polishCPU=0.;segments=[];polished=set();stop=threading.Event()
   def persist():
    while not stop.wait(30):
     try:volume.commit()
     except Exception:pass
   thread=threading.Thread(target=persist,daemon=True);thread.start();error=None
   def childcpu():
    r=resource.getrusage(resource.RUSAGE_CHILDREN);return r.ru_utime+r.ru_stime
   try:
    while used<5999 and time.monotonic()-began<7000:
     i=len(segments);budget=min(600,6000-used);target=226 if len(best)<226 else 227;before=childcpu()
     result=subprocess.run(["/opt/codegarden/pool",str(budget),str(case["seed"]+i*100003),case["policy"],str(path/"unverified_live_checkpoint.txt"),str(target)],
      input="\n".join(best)+"\n",text=True,capture_output=True,check=True,timeout=min(900,max(30,7100-(time.monotonic()-began))),env=dict(os.environ,CODEGARDEN_POOL=str(mask)))
     consumed=childcpu()-before;used+=consumed;r=json.loads(result.stdout);A=r["best"];assert not set(A)&set(case["forbidden"])
     q=path/("segment_"+str(i)+".txt");q.write_text("\n".join(format(w,"016b") for w in sorted(A))+"\n");v=verify(q);assert v["cardinality"]>=len(best)
     best=q.read_text().splitlines();base.write_text(q.read_text());row={"index":i,"native":r,"native_child_cpu_seconds":consumed,"verification":v,"polish":[]}
     if len(best)>=227:segments.append(row);break
     h=v["reports"][0]["witness_sha256"]
     if len(best)==226 and h not in polished:
      polished.add(h)
      for k in [3,5,7,9]:
       if time.monotonic()-began>=7000:break
       before=childcpu();z=json.loads(subprocess.run(["/opt/codegarden/bundle","16",str(k),"20","1000000000000","0"],input=q.read_text(),text=True,capture_output=True,check=True,timeout=70,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1")).stdout);polishCPU+=childcpu()-before
       pool=z.pop("candidate_pool");z.pop("neighbors");z["pool_sha256"]=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest()
       if z["found"]:
        B=set(A)-set(z["removed"])|set(z["added"]);base.write_text("\n".join(format(w,"016b") for w in sorted(B))+"\n");z["verification"]=verify(base);best=base.read_text().splitlines()
       row["polish"].append(z)
       if len(best)>=227:break
     segments.append(row);(path/"progress.json").write_text(json.dumps({"segments":segments,"native_cpu_seconds":used,"polish_cpu_seconds":polishCPU,"best_verified":len(best)}));volume.commit()
     if len(best)>=227:break
   except Exception as e:error=str(e)[:1200]
   finally:
    stop.set();thread.join(timeout=5)
   live=path/"unverified_live_checkpoint.txt"
   if live.exists():
    try:
     recovered=verify(live)
     if recovered["cardinality"]>len(best):base.write_text(live.read_text());best=live.read_text().splitlines()
    except Exception:pass
   verified=verify(base);report={"metadata":meta,"segments":segments,"best_words":best,"verification":verified,"native_cpu_seconds":used,"polish_cpu_seconds":polishCPU,
    "wall_seconds":time.monotonic()-began,"status":"completed" if error is None else "failed_or_partial","error":error,"allowance_reached":used>=5999}
   (path/"result.json").write_text(json.dumps(report));volume.commit();return report
  ledger.reserve("modal","codegarden",8*(7800+600)*.0001);save("ledger_progress.json",ledger.summary());publish()
  with app.run():
   calls=[worker.spawn(c,source) for c in cases];executor=concurrent.futures.ThreadPoolExecutor(max_workers=8)
   pending={executor.submit(call.get,timeout=8500):i for i,call in enumerate(calls)}
   try:
    for future in concurrent.futures.as_completed(pending):
     i=pending[future];r=future.result();p=OUT/("best_"+str(i)+".txt");p.write_text("\n".join(sorted(r["best_words"]))+"\n");r["host_independent_verification"]=verify(p)
     assert r["host_independent_verification"]["cardinality"]==len(r["best_words"]);save("workers/"+str(i)+".json",r);rows.append(r)
     save("progress.json",{"collected":len(rows),"total":8,"best_verified":max([226]+[len(v["best_words"]) for v in rows])});publish()
     if len(r["best_words"])>=227:
      status["verified_improvement"]={"case":i,"verification":r["host_independent_verification"]}
      for j,call in enumerate(calls):
       if j!=i:
        try:call.cancel()
        except Exception:pass
      break
   finally:executor.shutdown(wait=False,cancel_futures=True)
  status.update(status="completed",collected=len(rows),best_verified=max([226]+[len(r["best_words"]) for r in rows]))
 except Exception as e:
  status.update(status="failed_or_partial",error=str(e)[:1200]);traceback.print_exc()
  for call in calls:
   try:call.cancel()
   except Exception:pass
 finally:
  status.update(budget=ledger.summary(),finished_at=dt.datetime.now(dt.timezone.utc).isoformat());save("status.json",status);publish();print("LONG_FINAL",json.dumps(status),flush=True)
if __name__=="__main__":main()
