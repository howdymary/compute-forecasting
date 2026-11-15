"""Bounded independent-process research, CPU populations and frozen policy comparison."""
import datetime as dt,hashlib,json,os,pathlib,random,subprocess,sys,time,traceback,uuid
from common import *
sys.path.insert(0,str(ROOT))
from providers import Providers,Ledger
from role import recalled
from model_policy import Policy,train
import dataset
def publish():
 subprocess.run([sys.executable,"-B",str(ROOT/"phase2/publish.py")],check=True)
def role(name,data,tag):
 inp=save("roles/"+tag+"_input.json",data);out=OUT/"roles"/(tag+"_output.json")
 env={k:v for k,v in os.environ.items() if k not in {"EXA_API_KEY","TINKER_API_KEY","MODAL_TOKEN_ID","MODAL_TOKEN_SECRET","GH_TOKEN","GITHUB_TOKEN"}}
 if name=="researcher":env["EXA_API_KEY"]=os.environ["EXA_API_KEY"]
 subprocess.run([sys.executable,"-B",str(ROOT/"phase2/role.py"),"--role",name,"--input",str(inp),"--output",str(out)],
  env=env,timeout=180,check=True)
 return json.loads(out.read_text())
def exact_neighborhoods(populations):
 from search import Incidence,pool_hash,digest_words
 from cp_sat import solve
 inc=Incidence(16);baseline=(ROOT/"artifacts/best_code.txt").read_text().splitlines();best=[int(w,2) for w in baseline];reports=[]
 diverse={}
 for r in populations:
  for code in r.get("archive",[]):diverse.setdefault(orbit([format(w,"016b") for w in code]),code)
 candidates=list(diverse.values())
 for i in range(6):
  if not before_cutoff():break
  if i<3 and len(candidates)>=3:
   parents=[candidates[(i*3+j)%len(candidates)] for j in range(3)]
   fixed=sorted(set(parents[0])&set(parents[1])&set(parents[2]));pool=sorted(set().union(*map(set,parents))-set(fixed))
   seedcode=[w for w in max(parents,key=len) if w not in fixed];target=max(len(best),226)-len(fixed)+1
   definition={"type":"three_parent_union","parents":[digest_words(p) for p in parents],"candidate_cap":None}
  else:
   rng=random.Random(45000+i);removed=set(rng.sample(best,[16,24,48][i%3]));fixed=[w for w in best if w not in removed]
   full=inc.compatible_pool(fixed);pool=full
   if len(full)>3000:
    other=[w for w in full if w not in removed];rng.shuffle(other);other.sort(key=lambda w:inc.sizes[w])
    pool=sorted(removed|set(other[:3000-len(removed)]))
   seedcode=list(removed);target=len(best)-len(fixed)+1
   definition={"type":"bounded_ruin_repair","removed":sorted(removed),"compatible_pool_before_cap":len(full),"cap":3000,
    "restriction":"Always include removed incumbents; seeded order biased by descendant size for the remaining bounded pool only"}
  trial,r=solve(inc,pool,target,seedcode,seconds=20,seed=45000+i,workers=1)
  r.update({"id":"exact-"+str(i),"definition":definition,"fixed_outside":fixed,"candidate_pool":pool,"fixed_outside_sha256":digest_words(fixed),
   "incumbent_witness_sha256":digest_words(best),"global_optimality_claim":False})
  if trial:
   code=fixed+trial;words=[format(w,"016b") for w in code];r["independent_verification"]=check_words(words,"worker_exact_"+str(i)+".txt")
   if len(code)>len(best):best=code
  reports.append(r);save("exact_repairs.json",reports)
 return reports
def main():
 import modal
 events=[]
 def log(kind,value):
  events.append({"kind":kind,"value":value,"time":time.time()});save("provider_trace.json",events)
  print("PHASE2_EVENT "+json.dumps({"kind":kind,"keys":list(value)}),flush=True)
 providers=Providers(OUT,log);ledger=providers.ledger
 status={"status":"running","source_sha":os.getenv("GITHUB_SHA"),"campaign_start":load_start(),"search_cutoff":"2026-11-15T05:33:09Z"}
 active=[]
 try:
  assert json.loads((OUT/"preflight.json").read_text())["problem"]["matches_pinned_verifier"]
  roots=json.loads((OUT/"root_sweeps.json").read_text())
  cp=json.loads((ROOT/"artifacts/cp_global.json").read_text())["experiments"][0]
  facts={"root_exchanges":[{k:r[k] for k in ["k","status","complete","found","incumbent_sha256","candidate_universe_sha256","restrictions","context_key"]} for r in roots],
   "global_cp":{"status":cp["status"],"target":cp["target"],"pool_sha256":cp["candidate_pool_sha256"],"complete":False},
   "conclusion":"Exact root k=1,2 neighborhoods are exhausted only if their complete flags are true. Full-universe UNKNOWN is not impossibility."}
  a=role("analyst",{"kind":"phase2_scoped_root_facts","content":facts,"experiment_id":"phase2-root"},"analyst_root")
  research=role("researcher",{"required_source":a["source_id"],"query":"Recall the analyst's phase-two exact root exchange exhaustion and the larger repair bottleneck."},"researcher_method")
  plan=role("strategist",{"required_source":research["source_id"],"query":"Recall the researcher's larger repair hypothesis after the root radius-two scan."},"strategist_plan")
  ledger.reserve("modal","codegarden",1) # image build uncertainty
  image=modal.Image.debian_slim(python_version="3.11").apt_install("g++")
  for rel in ["kernel.cpp","phase2/kernel_v2.cpp"]:
   image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel,copy=True)
  image=image.run_commands("g++ -O3 -std=c++17 /opt/codegarden/phase2/kernel_v2.cpp -o /opt/codegarden/kernel_v2")
  for rel in ["protected/verify_descendants.py","protected/verify_lcs.py"]:
   image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
  app=modal.App("codegarden-phase2-cpu",tags={"project":"codegarden","campaign":"phase2"})
  volume=modal.Volume.from_name("codegarden-phase2-checkpoints",create_if_missing=True)
  @app.function(serialized=True,image=image,cpu=1,memory=768,timeout=650,max_containers=4,volumes={"/codegarden/results":volume})
  def worker(words,seed,seconds,policy,arm,target,tag):
   import importlib.util,threading
   runid=uuid.uuid4().hex;path=pathlib.Path("/codegarden/results")/runid;path.mkdir();cpfile=path/"checkpoint.txt"
   stop=threading.Event();commits=[]
   def persist():
    while not stop.wait(20):
     try:volume.commit();commits.append(time.time())
     except Exception:pass
   thread=threading.Thread(target=persist,daemon=True);thread.start();started=time.perf_counter()
   try:
    p=subprocess.run(["/opt/codegarden/kernel_v2",str(seconds),str(seed),policy,str(cpfile),str(target),str(arm)],
      input="\n".join(words)+"\n",text=True,capture_output=True,timeout=seconds*1.6+30,check=True)
    r=json.loads(p.stdout)
   finally:stop.set();thread.join(timeout=3)
   def module(name,rel):
    spec=importlib.util.spec_from_file_location(name,"/opt/codegarden/"+rel);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
   D=module("phase2_worker_desc","protected/verify_descendants.py");L=module("phase2_worker_lcs","protected/verify_lcs.py")
   final=[format(w,"016b") for w in r["best"]];r["words"]=final;r["current_words"]=[format(w,"016b") for w in r["current"]]
   r["verification"]={"descendant":D.verify(final),"lcs":L.verify(final)}
   assert all(v["valid"] for v in r["verification"].values())
   r.update({"runtime_seconds":time.perf_counter()-started,"starting_witness_sha256":D.verify(words)["witness_sha256"],
    "resources":{"cpu":1,"memory_mb":768},"tag":tag,"run_id":runid,"durable_commits":len(commits),
    "source_sha256":hashlib.sha256(pathlib.Path("/opt/codegarden/phase2/kernel_v2.cpp").read_bytes()).hexdigest()})
   for code in r["archive"]:D.verify([format(w,"016b") for w in code])
   (path/"result.json").write_text(json.dumps(r));(path/"witness.txt").write_text("\n".join(sorted(final))+"\n");volume.commit()
   r["durable_result"]=str(path/"result.json");r["archive"]=r["archive"][:12];return r
  target=json.loads((OUT/"preflight.json").read_text())["target"]
  parents=[p.read_text().splitlines() for p in sorted((ROOT/"artifacts/baselines").glob("arena_*.txt"))[-4:]]
  # Parent choice and all seeds frozen before evaluating any policy.
  longspec=[{"words":parents[i//2],"seed":61000+i,"policy":"fixed" if i%2==0 else "adaptive","arm":0} for i in range(8)]
  save("long_manifest.json",{"specifications":longspec,"cpu_seconds_per_period":240,"periods":2,"max_concurrency":4})
  with app.run():
   ledger.reserve("modal","codegarden",8*240*.002)
   calls=[worker.spawn(s["words"],s["seed"],240,s["policy"],s["arm"],target,"long1-"+str(i)) for i,s in enumerate(longspec)];active.extend(calls)
   # CPU workers run while the independent GitHub host builds and verifies training cases.
   manifest,examples,gate=dataset.build();save("dataset_gate.json",gate);publish()
   trained_path=None;training=None
   if gate["meaningful"] and before_cutoff():
    trained_path,training=train(examples,ledger);save("training.json",training)
   else:save("training.json",{"status":"not_trained","reason":"Verifier-grounded action differences did not pass the preregistered gate, or cutoff reached","gate":gate})
   phase1=[c.get(timeout=1000) for c in calls]
   for i,r in enumerate(phase1):r["host_verification"]=check_words(r["words"],"worker_long1_"+str(i)+".txt")
   save("long_period1.json",phase1);publish()
   repairs=exact_neighborhoods(phase1)
   # Exchange entire archived populations between islands at the period boundary.
   seeds2=[]
   for i,s in enumerate(longspec):
    other=phase1[(i+3)%len(phase1)];options=other.get("archive",[])
    selected=options[(i+1)%len(options)] if options else other["best"]
    seeds2.append([format(w,"016b") for w in selected])
   ledger.reserve("modal","codegarden",8*240*.002)
   calls2=[worker.spawn(words,62000+i,240,longspec[i]["policy"],0,target,"long2-"+str(i)) for i,words in enumerate(seeds2)];active.extend(calls2)
   save("population_exchange.json",{"from_period":1,"to_period":2,"starts":[{"seed":62000+i,"starting_sha256":sha(w),"words":w,"donor_worker":(i+3)%8} for i,w in enumerate(seeds2)]})
   if gate["meaningful"]:
    baseline_policy=Policy(ledger);learned=Policy(ledger,trained_path) if trained_path else None
   else:baseline_policy=None;learned=None
   conditions=["fixed","adaptive_no_external","adaptive_with_research"]+(["trained"] if learned else [])
   held=[c for c in manifest["cases"] if c["split"]=="heldout"]
   trials={(c["case_id"],condition):{"case_id":c["case_id"],"condition":condition,"words":c["starting_words"],
      "best_words":c["starting_words"],"initial_size":len(c["starting_words"]),"chunks":[],"recent":[],"overhead_seconds":0,"created_at":time.time(),"time_to_first_improvement_cpu":None}
      for c in held for condition in conditions}
   for round_id in range(4):
    if not before_cutoff():break
    recalled_method=role("recall",{"identity":"strategist","required_source":research["source_id"],
      "query":"Recall the source-backed larger repair method after phase-two root local exhaustion."},"eval_recall_"+str(round_id))
    # Compact actual recalled content: preserve structure and source ID, no ceremony-only read.
    memory_context=recalled_method["evidence"]
    ledger.reserve("modal","codegarden",len(trials)*30*.002)
    jobs=[]
    for case in held:
     for condition in conditions:
      trial=trials[(case["case_id"],condition)]
      if time.time()-trial["created_at"]>=2400:raise TimeoutError("Preregistered case wall-time cap reached")
      context=state(trial["words"],trial["recent"],
       trial["chunks"][-1]["stagnation_cpu_seconds"] if trial["chunks"] else case["state"]["stagnation_cpu_seconds"],(4-round_id)*30)
      decision=None;arm=0;t=time.perf_counter()
      if condition!="fixed":
       if condition in ["adaptive_with_research","trained"]:context["external_research"]=memory_context
       policy=learned if condition=="trained" else baseline_policy
       if policy:
        decision=policy.choose(context);arm=ACTIONS.index(decision["action"]) if decision["valid_action"] else 0
       else:
        # Explicit non-LLM fallback, never labeled as a trained policy.
        arm=round_id%6;decision={"action":ACTIONS[arm],"valid_action":True,"fallback":"Empirical operator sweep; training-data gate failed"}
      trial["overhead_seconds"]+=time.perf_counter()-t
      save("contexts/"+case["case_id"]+"_"+condition+"_"+str(round_id)+".json",{"state":context,"decision":decision,
        "actual_memory_source":research["source_id"] if condition in ["adaptive_with_research","trained"] else None})
      seed=case["seed"]*10+round_id
      call=worker.spawn(trial["words"],seed,30,"fixed",arm,target,"eval-"+case["case_id"]+"-"+condition+"-"+str(round_id))
      active.append(call);jobs.append((trial,call,arm,decision))
    for trial,call,arm,decision in jobs:
     r=call.get(timeout=1000);r["host_verification"]=check_words(r["words"],"worker_eval_"+trial["case_id"]+"_"+trial["condition"]+"_"+str(round_id)+".txt")
     previous_best=len(trial["best_words"])
     if len(r["words"])>trial["initial_size"] and trial["time_to_first_improvement_cpu"] is None:
      trial["time_to_first_improvement_cpu"]=sum(c["cpu_seconds"] for c in trial["chunks"])+next((p[0] for p in r["progress"] if p[1]>trial["initial_size"]),r["cpu_seconds"])
     if len(r["words"])>previous_best:trial["best_words"]=r["words"]
     trial["words"]=r["current_words"];trial["recent"].append({"action":ACTIONS[arm],"best_verified_gain":max(0,len(r["words"])-previous_best),"cpu_seconds":r["cpu_seconds"]})
     r.pop("archive",None)
     for key in ["words","current_words","best","current"]:r.pop(key,None)
     r["witness_path"]="codegarden/artifacts/phase2/worker_eval_"+trial["case_id"]+"_"+trial["condition"]+"_"+str(round_id)+".txt"
     r["decision"]=decision;trial["chunks"].append(r)
    save("evaluation_progress.json",{"trials":list(trials.values()),"completed_rounds":round_id+1,"conditions":conditions});publish()
   phase2=[c.get(timeout=1000) for c in calls2]
   for i,r in enumerate(phase2):r["host_verification"]=check_words(r["words"],"worker_long2_"+str(i)+".txt")
   save("long_period2.json",phase2)
   result={"conditions":conditions,"trials":list(trials.values()),"gate":gate,"incomplete_conditions":["trained"] if not learned else [],
    "protocol":{"heldout_cases":8,"chunks":4,"search_cpu_seconds_per_chunk":30,"maximum_case_wall_seconds":2400,
      "per_condition_caps":{"modal_usd":2.5,"tinker_usd":2,"past_credits":400},"same_seed_per_case_chunk_across_conditions":True,
      "training_cost_accounted_separately":True,"timing_note":"Controller and retrieval overhead reported separately; stopping action can overshoot CPU cap slightly, recorded per chunk."}}
   result["summary"]={condition:{"cases":8,"completed_chunks":sum(len(t["chunks"]) for t in trials.values() if t["condition"]==condition),
    "sum_best_sizes":sum(len(t["best_words"]) for t in trials.values() if t["condition"]==condition),
    "improved_cases":sum(len(t["best_words"])>t["initial_size"] for t in trials.values() if t["condition"]==condition),
    "search_cpu_seconds":sum(r["cpu_seconds"] for t in trials.values() if t["condition"]==condition for r in t["chunks"]),
    "controller_seconds":sum(t["overhead_seconds"] for t in trials.values() if t["condition"]==condition)} for condition in conditions}
   save("evaluation.json",result)
   # Independent process reads the analyst's verified outcomes before updating the next hypothesis.
   result_source=role("analyst",{"kind":"phase2_verified_outcomes","content":{"summary":result["summary"],"artifact":"codegarden/artifacts/phase2/evaluation.json"},
      "experiment_id":"phase2-evaluation","parents":[plan["source_id"]]},"analyst_results")
   role("recall",{"identity":"researcher","required_source":result_source["source_id"],"query":"Recall the analyst's verified phase-two evaluation results to guide the next hypothesis."},"researcher_results")
   if baseline_policy and before_cutoff():
    from memory_benchmark import run
    run(baseline_policy,providers,a["source_id"],facts,manifest)
   status.update({"status":"completed","evaluation_summary":result["summary"],"training_status":training["status"] if training else "not_trained",
    "role_execution":"Independent OS processes and separate input/output contexts; policy sampling contexts are stateless per decision.",
    "research_memory_changed":"Actual recalled context supplied to research/trained conditions; benefit judged only from ablations."})
 except Exception as e:
  status.update({"status":"failed_or_partial","error_type":type(e).__name__,"error":str(e)[:800]});traceback.print_exc()
 finally:
  # app.run is scoped; bounded workers checkpoint their own Volume and have hard timeouts.
  if status.get("status")!="completed":
   cancelled=0
   for call in active:
    try:call.cancel();cancelled+=1
    except Exception:pass
   status["own_calls_cancel_requested"]=cancelled
  status["budget"]=ledger.summary();status["finished_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
  save("campaign_status.json",status);publish();print("PHASE2_FINAL "+json.dumps(status),flush=True)
def load_start():return json.loads((ROOT/"budget/shared-allocation.json").read_text())["campaign_start"]
if __name__=="__main__":main()
