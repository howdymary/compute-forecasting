"""Credit-bounded CPU fallback after the account rejected GPU functions."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import Ledger,cli
from supervisor import verify,check_integrity
from phase3.research3 import read
OUT=ROOT/"artifacts/phase3/research_cpu_001";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2))
def publish():subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_research_cpu.py")],check=True)
def main():
 check_integrity();prior=read("codegarden/artifacts/phase3/research_gpu_003/status.json","codegarden-research-gpu-005")
 assert prior["status"]=="failed_or_partial" and "payment method" in prior["error"]
 history={"source_run":"cpu-fallback-"+prior["source_sha"],"conservative_totals":{k:v["reserved"]+v["provider_reported_or_estimated"] for k,v in prior["budget"].items()},"reason":"GPU account restriction; retain entire prior0.868USD reservation and all unknown historical costs."}
 for name in ["status.json","ledger_progress.json"]:
  try:
   own=read("codegarden/artifacts/phase3/research_cpu_001/"+name,"codegarden-research-cpu-003");data=own.get("budget",own)
   for k,v in data.items():
    if isinstance(v,dict) and "reserved" in v:history["conservative_totals"][k]=max(history["conservative_totals"].get(k,0),v["reserved"]+v["provider_reported_or_estimated"])
  except Exception:pass
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2))
 spec=json.loads((ROOT/"budget/shared-allocation.json").read_text());gross=float(json.loads(cli("modal","billing","summary","--json"))["metered_cost"]);floor=248.87-max(0,gross-1.64005948);assert floor>=245
 spec["providers"]["modal"]["codegarden_cap"]=150;(ROOT/"budget/shared-allocation.json").write_text(json.dumps(spec,indent=2));ledger=Ledger(OUT)
 status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"credit_floor":floor,"history":history,"hardware_fallback":"CPU only; no billing or payment settings changed"}
 try:
  assert dt.datetime.now(dt.timezone.utc)<dt.datetime(2026,11,15,11,37,tzinfo=dt.timezone.utc),"Leave time before allocation expiry"
  choice=read("codegarden/artifacts/phase3/research_gpu_003/strategy_decision.json","codegarden-research-gpu-005");memory=read("codegarden/artifacts/phase3/research_gpu_003/strategist_recall.json","codegarden-research-gpu-005");sources=read("codegarden/artifacts/phase3/research_gpu_003/upstream_exa_sources.json","codegarden-research-gpu-005")
  save("strategy_provenance.json",{"actual_Tinker_choice":choice,"actual_researcher_memory":memory,"actual_Exa_sources":sources,"adaptation":"Same selected kernel/quota on CPU because the account rejected GPU deployment; no claim of a measured GPU speedup."})
  import modal
  from phase3.tensor_search4 import common_core
  core=common_core();quota=int(choice["action"].removeprefix("quota"));starting=[]
  for path in [next((ROOT/"artifacts/baselines").glob("arena_"+str(n)+"_*.txt")) for n in [226,225,208]]+[ROOT/"artifacts/phase3/frontier_002/projected225/starting_0.txt"]:
   verify(path);starting.append(path.read_text().splitlines())
  rates=json.loads(cli("modal","billing","rates","--json"));base=(float(rates["cpu_hour_cost"])+2*float(rates["mem_gib_hour_cost"]))/3600;bound=base*3*1.75*(1260+60)+.02;assert bound<=.15
  plan={"reservation_usd":.15,"conservative_bound_usd":bound,"rates":rates,"sensitivity_multipliers":{"nonpreemptible":3,"region":1.75},"cpu_request_and_limit":1,"memory_request_and_limit_gib":2,"function_timeout":1200,"host_wait_limit":1260,"shutdown_guard":60,"max_containers":1,"retries":0,"search_seconds":900,"batch":32,"quota":quota,"seed":1261001,"image":"Cached Debian/Python base; install pinned CPU-only torch inside bounded function","prior_holds_released":0}
  save("plan.json",plan);ledger.reserve("modal","codegarden",.15);save("ledger_progress.json",ledger.summary());publish()
  image=modal.Image.debian_slim(python_version="3.11")
  for rel in ["search.py","supervisor.py","protected/verify_descendants.py","protected/verify_lcs.py","protected/manifest.json","phase3/tensor_search4.py"]:image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
  app=modal.App("codegarden-phase3-cpu-tensor-fallback",tags={"project":"codegarden","hypothesis":"memory-selected-core-quota-on-available-CPU"})
  volume=modal.Volume.from_name("codegarden-phase3-cpu-tensor-checkpoints",create_if_missing=True)
  @app.function(serialized=True,image=image,cpu=(1,1),memory=(2048,2048),timeout=1200,max_containers=1,retries=0,scaledown_window=2,volumes={"/codegarden/results":volume})
  def worker(core,quota,starting,source):
   import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,threading,time,uuid,modal
   path=pathlib.Path("/codegarden/results")/uuid.uuid4().hex;path.mkdir();root=pathlib.Path("/opt/codegarden");(root/".tmp").mkdir(exist_ok=True);os.environ.update(PIP_CACHE_DIR=str(root/".cache/pip"),TMPDIR=str(root/".tmp"),PYTHONDONTWRITEBYTECODE="1",GITHUB_SHA=source);began=time.monotonic()
   meta={"source_sha":source,"started_at":dt.datetime.now(dt.timezone.utc).isoformat(),"seed":1261001,"quota":quota,"function_call_id":modal.current_function_call_id(),"input_id":modal.current_input_id(),"durable_path":str(path)};(path/"metadata.json").write_text(json.dumps(meta));volume.commit()
   subprocess.run([sys.executable,"-m","pip","install","torch==2.8.0","--index-url","https://download.pytorch.org/whl/cpu","--target",str(root/".runtime")],check=True,capture_output=True,text=True,timeout=240)
   sys.path.insert(0,str(root/".runtime"));sys.path.insert(0,str(root));from phase3.tensor_search4 import search,selftest,quota_test
   tests=selftest();tests["quota_tests"]=quota_test();(path/"tests.json").write_text(json.dumps(tests));volume.commit();stop=threading.Event()
   def persist():
    while not stop.wait(15):
     try:volume.commit()
     except Exception:pass
   thread=threading.Thread(target=persist,daemon=True);thread.start()
   try:r=search("cpu",min(900,max(30,1120-(time.monotonic()-began))),1261001,path,starting,32,core=core,quota=quota)
   finally:stop.set();thread.join(timeout=5)
   r["metadata"]=meta;r["runtime_including_setup"]=time.monotonic()-began;(path/"result.json").write_text(json.dumps(r));volume.commit();return r
  calls=[]
  with app.run():
   call=worker.spawn(core,quota,starting,os.environ["GITHUB_SHA"]);calls.append(call)
   try:r=call.get(timeout=1260)
   except Exception:
    call.cancel();raise
  save("tensor_result.json",r);best=226
  if r.get("winner"):
   q=OUT/"winner.txt";q.write_text("\n".join(format(w,"016b") for w in sorted(r["winner"]["words"]))+"\n");v=verify(q);assert v["cardinality"]==227;best=227;save("winner_verification.json",v)
  publish()
  if best<227:
   from phase3.project_tensor3 import project
   projected=project(OUT/"tensor_result.json",OUT/"projections");best=max(best,projected["best_independently_verified"]);publish()
   if best<227:
    from phase3.polish_tensor import run
    best=max(best,run(OUT)["best_verified"])
  status.update(status="completed",best_verified=best,actual_duration=r["runtime_including_setup"],raw_energy_is_not_validity=True)
 except Exception as e:status.update(status="failed_or_partial",error=str(e)[:1200]);traceback.print_exc()
 finally:
  status.update(budget=ledger.summary(),finished_at=dt.datetime.now(dt.timezone.utc).isoformat());save("status.json",status);publish();print("RESEARCH_CPU_FINAL",json.dumps(status),flush=True)
if __name__=="__main__":main()
