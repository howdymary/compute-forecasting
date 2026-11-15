"""C2 bounded polish with explicit GPU-access handling and exact host acceptance."""
import concurrent.futures,hashlib,importlib.util,json,os,pathlib,subprocess,sys,time,traceback
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1];K=ROOT/"c2";sys.path.insert(0,str(ROOT))
sp=importlib.util.spec_from_file_location("c2_service_helpers",ROOT/"side_services/cycle.py");C=importlib.util.module_from_spec(sp);sp.loader.exec_module(C)
C.BRANCH="codegarden-c2-continuation-001";C.OUT=ROOT/"artifacts/c2/continuation_001";C.OUT.mkdir(parents=True,exist_ok=True);C.ledger.rows=[];C.ledger.caps["modal"]=20
W=ROOT/"artifacts/c2_witnesses"/os.environ["GITHUB_RUN_ID"];W.mkdir(parents=True,exist_ok=True)
def frozen():
 for rel,h in json.loads((K/"manifest.json").read_text())["files"].items():
  assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,"Protected C2 source changed"
def official(values):
 sp=importlib.util.spec_from_file_location("c2_frozen_float",K/"official.py");m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m.evaluate({"values":values})
def choose():
 import tinker
 C.ledger.reserve("tinker","codegarden",.1)
 service=tinker.ServiceClient(display_name="CodeGarden C2 endpoint continuation");sampler=service.create_sampling_client(base_model="Qwen/Qwen3.5-4B")
 if hasattr(sampler,"result"):sampler=sampler.result()
 tok=sampler.get_tokenizer();state={"task":"Test retaining the smoothed optimizer endpoint when its true nonsmooth score temporarily drops. Prior greedy propagation made different schedules converge to an identical witness, best_npy_sha256 1dce5b2b6817d04bac8003bd330804486f5c78e488a3439c2cb1e9d0acefb151; both exact0.9636616088232245, below Arena increment. Equal900sec arms differ only in propagation.","fixed_control_betas":"Both arms use your chosen schedule","allowed_actions":{"coarse_to_fine":[1e3,1e5,1e7,1e9,1e11],"extra_fine":[1e5,1e7,1e9,1e11]},"source":"justinkang221/second-autocorrelation-inequality; Dinkelbach and smoothing cascade adapted with fixed mass and fixed inner temperature.","budget":"Same seed and900seconds. True integer certificates, not the smooth objective, accept candidates."}
 ids=tok.apply_chat_template([{"role":"system","content":"Return only coarse_to_fine or extra_fine. Select an implemented schedule, never fabricate an outcome."},{"role":"user","content":json.dumps(state)}],tokenize=True,add_generation_prompt=True,enable_thinking=False,return_dict=False)
 r=sampler.sample(prompt=tinker.ModelInput.from_ints(ids),sampling_params=tinker.types.SamplingParams(max_tokens=24,temperature=0),num_samples=1).result();reply=tok.decode(r.sequences[0].tokens,skip_special_tokens=True).strip()
 choices=state["allowed_actions"];action=reply if reply in choices else "coarse_to_fine";result={"action":action,"betas":choices[action],"valid_reply":reply in choices,"model":"Qwen/Qwen3.5-4B","trained":False,"prompt_tokens":len(ids),"output_tokens":len(r.sequences[0].tokens)}
 C.save("tinker.json",result);C.publish();return result
def main():
 import modal
 frozen()
 row=json.loads((ROOT/"artifacts/c2/preflight_001/baseline_api_response.json").read_text())[0]
 f=np.maximum(np.asarray(row["data"]["values"],dtype=np.float64),0);f/=f.max();assert 1<=len(f)<=2000000 and np.isfinite(f).all()
 baseline=official(f.tolist());assert abs(baseline-row["score"])<1e-10
 data=K/".data";data.mkdir(exist_ok=True)
 old_volume=modal.Volume.from_name("codegarden-c2-results-43763414376",create_if_missing=False)
 warm_path=data/"baseline.npy"
 with warm_path.open("wb") as stream:
  for chunk in old_volume.read_file("d0f0147dd2c746e88d8c5d8233571913/best.npy"):stream.write(chunk)
 warm_hash=hashlib.sha256(warm_path.read_bytes()).hexdigest();assert warm_hash=="1dce5b2b6817d04bac8003bd330804486f5c78e488a3439c2cb1e9d0acefb151"
 f=np.load(warm_path,allow_pickle=False);assert f.ndim==1 and 1<=len(f)<=2000000 and np.isfinite(f).all() and np.min(f)>=0 and f.max()>0
 warm_score=official(f.tolist());assert abs(warm_score-0.9636616094034781)<1e-10
 warm_ints=np.rint(f/f.max()*(1<<32)).astype(np.uint64).tolist();warm_text=str(len(warm_ints))+"\n"+" ".join(map(str,warm_ints))+"\n"
 warm_run=subprocess.run([str(K/".build/exact")],input=warm_text,text=True,capture_output=True,check=True,timeout=180);warm_cert=json.loads(warm_run.stdout)
 assert warm_cert["numerator"]=="2764182317012209325424310583885229346642720637" and warm_cert["denominator"]=="2868415937403266316664617946072713880495748028"
 C.save("warm_exact_certificate.json",warm_cert);del warm_ints,warm_text
 C.save("warm_start.json",{"volume":"codegarden-c2-results-43763414376","path":"d0f0147dd2c746e88d8c5d8233571913/best.npy","npy_sha256":warm_hash,"float_score":warm_score,"previous_exact_quantized_score":0.9636616088232245,"live_arena_target":baseline,"arena_required_increment":1e-5});C.publish()
 C.save("status.json",{"status":"running","problem":"second-autocorrelation-inequality","baseline":baseline,"leader_id":row["id"],"source_sha":C.SOURCE});C.publish()
 try:
  C.ledger.reserve("exa","codegarden",.1);query="second autocorrelation inequality nonmonotone smoothing continuation optimize nonsmooth maximum autoconvolution Dinkelbach"
  r=C.http("https://api.exa.ai/search",os.environ["EXA_API_KEY"],{"query":query,"type":"auto","numResults":3},header="x-api-key")
  C.log("exa_c2_methods",{"query":query,"request_id":r.get("requestId"),"sources":[{"title":x.get("title"),"url":x["url"]} for x in r.get("results",[])],"adaptation":"Endpoint continuation tested against greedy best propagation with equal fixed900sec budgets. Source retrieval informs this explicit hypothesis, not a claim of success."});C.publish()
 except Exception as e:C.save("exa_unavailable.json",{"error":str(e)[:500]})
 proposal=choose()
 plans=[{"label":mode,"propagation":mode,"betas":proposal["betas"],"seed":630201,"noise":1e-10,"seconds":900,"threads":4,"outer":2,"max_iter":80,"max_eval":120} for mode in ["greedy_best","endpoint"]]
 C.save("plan.json",{"workers":plans,"source_sha":C.SOURCE,"initial_n":len(f),"baseline":baseline,"baseline_npy_sha256":hashlib.sha256((data/"baseline.npy").read_bytes()).hexdigest(),"device_request":"cpu","gpu_attempted":False,"hypothesis":"Endpoint continuation crosses a temporary drop in the true objective that greedy best propagation rejects.","record_claim":False});C.publish();C.ledger.reserve("modal","codegarden",15)
 image=modal.Image.debian_slim(python_version="3.12").pip_install("torch==2.9.1","numpy==2.4.6")
 image=image.add_local_file(str(K/"continuation_search.py"),"/opt/codegarden/c2/continuation_search.py").add_local_file(str(data/"baseline.npy"),"/opt/codegarden/c2/baseline.npy")
 volume=modal.Volume.from_name("codegarden-c2-results-"+os.environ["GITHUB_RUN_ID"],create_if_missing=True);results=[];calls=[];best=baseline
 def batch(gpu):
  nonlocal calls,best
  app=modal.App("codegarden-c2-"+("gpu-" if gpu else "cpu-")+os.environ["GITHUB_RUN_ID"])
  options={"serialized":True,"image":image,"cpu":4 if gpu else 8,"memory":8192 if gpu else 16384,"timeout":1200,"max_containers":2,"retries":0,"scaledown_window":2,"volumes":{"/codegarden/results":volume}}
  if gpu:options["gpu"]="A100-40GB"
  @app.function(**options)
  def worker(spec,source):
   import pathlib,sys,uuid
   sys.path.insert(0,"/opt/codegarden/c2")
   from continuation_search import run
   return run(spec,source,str(pathlib.Path("/codegarden/results")/uuid.uuid4().hex),volume.commit)
  with app.run():
   for p in plans:
    call=worker.spawn(p,C.SOURCE);calls.append(call)
    C.save("live_calls.json",{"app_id":getattr(app,"app_id",None),"requested_device":"gpu" if gpu else "cpu","calls":[{"spec":q,"function_call_id":getattr(c,"object_id",None)} for q,c in zip(plans,calls)]});C.publish()
   with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    pending={executor.submit(call.get):i for i,call in enumerate(calls)}
    for future in concurrent.futures.as_completed(pending):
     i=pending[future]
     try:
      result=future.result();assert abs(result["baseline_gpu"]-warm_score)<1e-9
      rel=result["best_rel"];assert not rel.startswith("/") and ".." not in pathlib.PurePosixPath(rel).parts
      path=W/("worker_"+str(i)+".npy")
      with path.open("wb") as stream:
       for chunk in volume.read_file(rel):stream.write(chunk)
      assert hashlib.sha256(path.read_bytes()).hexdigest()==result["best_npy_sha256"]
      values=np.load(path,allow_pickle=False);assert values.shape==f.shape and np.isfinite(values).all() and np.min(values)>=0 and values.max()>0
      ints=np.rint(values/values.max()*(1<<32)).astype(np.uint64).tolist()
      text=str(len(ints))+"\n"+" ".join(map(str,ints))+"\n";txt=W/("worker_"+str(i)+".txt");txt.write_text(text)
      cert_run=subprocess.run([str(K/".build/exact")],input=text,text=True,capture_output=True,timeout=180)
      assert cert_run.returncode==0,cert_run.stderr
      cert=json.loads(cert_run.stdout);true_score=official(ints);assert abs(true_score-cert["score"])<1e-10
      result["verification"]={"official_score":true_score,"exact_certificate":cert,"integer_witness_sha256":hashlib.sha256(txt.read_bytes()).hexdigest()}
      if cert["score"]>best:
       best=cert["score"]
       if best>baseline+1e-5:
        (W/"candidate.txt").write_text(text);(W/"candidate.json").write_text(json.dumps({"values":ints},separators=(",",":")));(W/"candidate_target.json").write_text(json.dumps({"baseline":baseline,"leader_id":row["id"],"source_sha":C.SOURCE}));C.save("candidate_verification.json",result["verification"])
      C.save("workers/"+str(i)+".json",result);results.append(result);C.publish()
     except Exception as e:C.save("workers/"+str(i)+"_error.json",{"error":str(e)[:1500],"scope":"Infrastructure or proposal failure; no mathematical negative."});C.publish()
 batch(False)
 summary={"status":"completed_batch","source_sha":C.SOURCE,"problem":"second-autocorrelation-inequality","baseline":baseline,"best_exact_verified":max([r["verification"]["exact_certificate"]["score"] for r in results],default=None),"best_reproduced_or_verified":best,"workers":[{"label":r["spec"]["label"],"profile":r["profile"],"best_gpu_proposal":r["best_gpu"],"exact_score":r["verification"]["exact_certificate"]["score"],"evaluations":r["evaluations"],"wall_seconds":r["wall_seconds"]} for r in results],"new_verified_candidate":best>baseline+1e-5,"arena_min_improvement_met":best>baseline+1e-5,"global_record_claim":False,"warm_start_float":warm_score,"comparison":"equal wall-clock budgets; same schedule and seed; only propagation differs"}
 C.save("summary.json",summary);C.save("status.json",summary);C.ledger.persist();C.publish()
 if summary["new_verified_candidate"]:
  with open(os.environ["GITHUB_OUTPUT"],"a") as stream:stream.write("has_candidate=true\n")
 print("C2_POLISH_FINAL",json.dumps(summary),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  traceback.print_exc();C.save("fatal.json",{"error":str(e)[:1500]})
  try:C.publish()
  except Exception:traceback.print_exc()
  raise
