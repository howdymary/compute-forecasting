"""One credit-reserved CPU/GPU profile comparison, then a gated bounded tensor experiment."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import cli
from supervisor import verify
def run(ledger,out,source,quota,publish):
 import modal
 from phase3.tensor_search4 import common_core
 core=common_core();assert len(core)==216
 paths=[next((ROOT/"artifacts/baselines").glob("arena_"+str(n)+"_*.txt")) for n in [226,225,208]]
 paths.append(ROOT/"artifacts/phase3/frontier_002/projected225/starting_0.txt")
 starting=[]
 for path in paths:verify(path);starting.append(path.read_text().splitlines())
 rates=json.loads(cli("modal","billing","rates","--json"));cpu=float(rates["cpu_hour_cost"])/3600;mem=float(rates["mem_gib_hour_cost"])/3600;gpu=float(rates["gpu_hour_cost_t4"])/3600
 assert (cpu+4*mem)*1.75<=.0001 and (cpu+4*mem+gpu)*1.75<=.0004,"Observed rates outside reserved envelope"
 plan={"source_sha":source,"quota":quota,"core":core,"starting_hashes":[hashlib.sha256(("\n".join(sorted(C))+"\n").encode()).hexdigest() for C in starting],
  "device":"T4","profile_batch":32,"profile_steps":10,"minimum_gpu_speedup":1.5,"experiment_seconds":900,"max_gpu_concurrency":1,
  "resources":{"cpu_request_and_limit":1,"memory_request_and_limit_mb":4096,"retries":0,"scaledown_window":2},
  "reservation_usd":.868,"reservation_components":{"image":.25,"cpu_profile":.018,"gpu_profile":.096,"gpu_experiment":.504},"rates_observed":rates,
  "cost_scope":"Full conditional maximum held; no release from estimated account-wide metering. Host wait limits include retries and queueing. Profiles and experiment run serially."}
 (out/"gpu_plan.json").write_text(json.dumps(plan,indent=2));ledger.reserve("modal","codegarden",.868);(out/"ledger_progress.json").write_text(json.dumps(ledger.summary(),indent=2));publish()
 image=modal.Image.debian_slim(python_version="3.11").run_commands("python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128")
 for rel in ["search.py","supervisor.py","protected/verify_descendants.py","protected/verify_lcs.py","protected/manifest.json","phase3/tensor_search4.py"]:
  image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
 app=modal.App("codegarden-phase3-profiled-tensor",tags={"project":"codegarden","hypothesis":"escape-known-core-with-all-word-updates"})
 volume=modal.Volume.from_name("codegarden-phase3-tensor-checkpoints",create_if_missing=True)
 @app.function(serialized=True,image=image,cpu=(1,1),memory=(4096,4096),timeout=120,max_containers=1,retries=0,scaledown_window=2)
 def cpu_profile(core,quota):
  import sys;sys.path.insert(0,"/opt/codegarden");from phase3.tensor_search4 import profile
  return profile("cpu",32,10,core,quota)
 @app.function(serialized=True,image=image,cpu=(1,1),memory=(4096,4096),gpu="T4",timeout=180,max_containers=1,retries=0,scaledown_window=2)
 def gpu_profile(core,quota):
  import sys;sys.path.insert(0,"/opt/codegarden");from phase3.tensor_search4 import profile
  return profile("cuda",32,10,core,quota)
 @app.function(serialized=True,image=image,cpu=(1,1),memory=(4096,4096),gpu="T4",timeout=1200,max_containers=1,retries=0,scaledown_window=2,volumes={"/codegarden/results":volume})
 def experiment(core,quota,starting,source):
  import datetime as dt,hashlib,json,os,pathlib,sys,threading,time,uuid,modal
  sys.path.insert(0,"/opt/codegarden");from phase3.tensor_search4 import search
  from supervisor import verify,check_integrity
  check_integrity();os.environ["GITHUB_SHA"]=source;path=pathlib.Path("/codegarden/results")/uuid.uuid4().hex;path.mkdir()
  metadata={"source_sha":source,"quota":quota,"seed":1261001,"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"function_call_id":modal.current_function_call_id(),"input_id":modal.current_input_id(),
   "durable_path":str(path),"kernel_sha256":hashlib.sha256(pathlib.Path("/opt/codegarden/phase3/tensor_search4.py").read_bytes()).hexdigest()}
  (path/"metadata.json").write_text(json.dumps(metadata));volume.commit();stop=threading.Event()
  def persist():
   while not stop.wait(20):
    try:volume.commit()
    except Exception:pass
  thread=threading.Thread(target=persist,daemon=True);thread.start()
  try:r=search("cuda",900,1261001,path,starting,32,core=core,quota=quota)
  finally:stop.set();thread.join(timeout=5)
  r["metadata"]=metadata;(path/"result.json").write_text(json.dumps(r));volume.commit();return r
 def get(fn,args,timeout):
  call=fn.spawn(*args)
  try:return call.get(timeout=timeout)
  except Exception:
   try:call.cancel()
   except Exception:pass
   raise
 result={"status":"running","plan":plan}
 with app.run():
  cp=get(cpu_profile,(core,quota),120);(out/"cpu_profile.json").write_text(json.dumps(cp,indent=2));publish()
  gp=get(gpu_profile,(core,quota),180);(out/"gpu_profile.json").write_text(json.dumps(gp,indent=2));speedup=cp["seconds_per_step"]/gp["seconds_per_step"];result.update(cpu_profile=cp,gpu_profile=gp,kernel_speedup=speedup)
  if speedup<1.5:result["status"]="skipped_no_measured_gpu_advantage"
  elif dt.datetime.now(dt.timezone.utc)>=dt.datetime(2026,11,15,11,38,tzinfo=dt.timezone.utc):result["status"]="skipped_absolute_start_cutoff"
  else:
   r=get(experiment,(core,quota,starting,source),1200);(out/"tensor_result.json").write_text(json.dumps(r,indent=2));result.update(status="experiment_completed",minimum_raw_energy=r["minimum_raw_energy"],raw_states_are_invalid_unless_zero=True)
   if r.get("winner"):
    p=out/"winner.txt";p.write_text("\n".join(format(w,"016b") for w in sorted(r["winner"]["words"]))+"\n");result["host_independent_verification"]=verify(p);assert result["host_independent_verification"]["cardinality"]==227
 (out/"gpu_status.json").write_text(json.dumps(result,indent=2));publish();return result
