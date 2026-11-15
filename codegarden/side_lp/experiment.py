"""LP packing bounds and LP-guided exact repair; code cardinality remains the objective."""
import datetime as dt,hashlib,importlib.util,json,math,os,pathlib,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/"side_lp"))
from supervisor import verify
from dual_verify import check as check_dual
spec=importlib.util.spec_from_file_location("cg_lp_services",ROOT/"side_services/cycle.py")
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
C.BRANCH="codegarden-side-lp-001";C.OUT=ROOT/"artifacts/side_research/lp_001";C.OUT.mkdir(parents=True,exist_ok=True);C.ledger.rows=[]
OUT=C.OUT
def d2(x):
 ds=set()
 for i in range(16):
  y=(x&((1<<i)-1))|((x>>(i+1))<<i)
  for j in range(i,15):ds.add((y&((1<<j)-1))|((y>>(j+1))<<j))
 return sorted(ds)
def digest(pool):return hashlib.sha256(("".join(format(w,"016b")+"\n" for w in pool)).encode()).hexdigest()
def sampler(state):
 import tinker
 C.ledger.reserve("tinker","codegarden",.1)
 service=tinker.ServiceClient(display_name="CodeGarden LP repair selector")
 client=service.create_sampling_client(base_model="Qwen/Qwen3.5-4B")
 if hasattr(client,"result"):client=client.result()
 tok=client.get_tokenizer();allowed=["fractional_hint","reduced_cost_hint"]
 messages=[{"role":"system","content":"Choose exactly one implemented LP-guided repair hint: fractional_hint or reduced_cost_hint. Return only that identifier. Never invent a construction or score."},{"role":"user","content":json.dumps(state,sort_keys=True)}]
 ids=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False,return_dict=False)
 if len(ids)>8192:raise RuntimeError("Context too long")
 r=client.sample(prompt=tinker.ModelInput.from_ints(ids),sampling_params=tinker.types.SamplingParams(max_tokens=24,temperature=0),num_samples=1).result()
 text=tok.decode(r.sequences[0].tokens,skip_special_tokens=True).strip()
 action=text if text in allowed else None
 out={"action":action,"valid_action":action is not None,"model":"Qwen/Qwen3.5-4B","prompt_tokens":len(ids),"output_tokens":len(r.sequences[0].tokens),"reply_sha256":hashlib.sha256(text.encode()).hexdigest(),"trained":False}
 C.save("tinker.json",out);C.publish();return action or "fractional_hint"
def main():
 import numpy as np,scipy,modal
 from scipy.optimize import linprog
 from scipy.sparse import coo_matrix
 seed=ROOT/"artifacts/best_code.txt";verify(seed);base=[int(s,2) for s in seed.read_text().splitlines()]
 assert hashlib.sha256(seed.read_bytes()).hexdigest()=="417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa"
 q=json.loads((ROOT/"side_services/models.json").read_text())[2];removed=set(q["removed_indices"]);fixed=[w for i,w in enumerate(base) if i not in removed]
 D=[d2(w) for w in range(65536)];cases=[];reports=[];certs=[]
 C.save("status.json",{"status":"running","source_sha":C.SOURCE,"best_verified":226});C.publish()
 try:C.recall("strategist","CodeGarden side services_001 measured_results3151 unresolved stronger bounds codegarden-side-43748900357-analyst-100d6d05","codegarden-side-43748900357-analyst-100d6d05")
 except Exception as e:C.log("memory_read_pending_or_unavailable",{"error":str(e)[:400]})
 try:
  C.ledger.reserve("exa","codegarden",.1)
  query="Primary references on set packing linear programming dual covers and reduced cost variable fixing for integer solutions; exact sparse LP marginals and validity of dual objective cuts in large neighborhood repair"
  r=C.http("https://api.exa.ai/search",os.environ["EXA_API_KEY"],{"query":query,"type":"auto","numResults":4,"contents":{"highlights":True}},header="x-api-key")
  C.log("exa_lp_research",{"query":query,"request_id":r.get("requestId"),"sources":[{"title":x.get("title"),"url":x["url"],"excerpt":" ".join(" ".join(x.get("highlights",[])).split()[:10])} for x in r.get("results",[])],"experiment":"LP dual-cover / reduced-cost repair"});C.publish()
 except Exception as e:C.log("exa_failure",{"error":str(e)[:300]})
 for forced in [True,False]:
  name="forced3151" if forced else "unforced3176"
  fixed_now=fixed+([int(q["forced"],2)] if forced else [])
  occupied=set().union(*(set(D[w]) for w in fixed_now))
  pool=[w for w in range(65536) if not occupied.intersection(D[w])]
  expected=q["pool_sha256"] if forced else "6fb37782459eeccb5100dab6fde2b1aa88958e96fb69573622d12306c046e7fb"
  assert digest(pool)==expected
  rr=[];cc=[]
  for j,w in enumerate(pool):
   rr.extend(D[w]);cc.extend([j]*len(D[w]))
  A=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(16384,len(pool))).tocsc()
  begun=time.monotonic();res=linprog(-np.ones(len(pool)),A_ub=A,b_ub=np.ones(16384),bounds=(0,None),method="highs-ds",options={"time_limit":30})
  report={"name":name,"status":int(res.status),"message":res.message,"success":bool(res.success),"seconds":time.monotonic()-begun,"scipy":scipy.__version__,"pool":len(pool),"pool_sha256":digest(pool),"fixed":len(fixed_now),"required_repair":227-len(fixed_now),"nnz":len(rr),"literal_removed_indices":q["removed_indices"],"fixed_words":[format(w,"016b") for w in sorted(fixed_now)],"dual_certificate":None}
  cert=None;x=[];cost=[]
  if res.success and res.ineqlin.marginals is not None:
   assert np.isfinite(res.ineqlin.marginals).all()
   scale=1000000;y=[int(math.ceil(max(0.,-float(v))*scale)) for v in res.ineqlin.marginals]
   for w in pool:
    deficit=scale-sum(y[d] for d in D[w])
    if deficit>0:y[D[w][0]]+=deficit
   cert={"n":16,"required_total":227,"fixed_words":report["fixed_words"],"pool_words":[format(w,"016b") for w in pool],"scale":scale,"weights":{format(d,"014b"):v for d,v in enumerate(y) if v},"source_sha":C.SOURCE,"neighborhood_name":name}
   checked=check_dual(cert);C.save("certificates/"+name+".json",cert);C.save("dual_checks/"+name+".json",checked);certs.append(name)
   report.update(numerical_lp_objective=-float(res.fun),dual_certificate=checked)
   x=[float(v) for v in res.x];cost=[sum(y[d] for d in D[w]) for w in pool]
   C.save("lp_vectors/"+name+".json",{"pool_words":pool,"fractional_values":x,"integer_cover_costs":cost,"scale":scale})
  C.save("lp_reports/"+name+".json",report);reports.append(report)
  if cert is None or not report["dual_certificate"]["excludes_227_in_this_fixed_neighborhood"]:
   cases.append({"name":name,"fixed_words":fixed_now,"pool_words":pool,"pool_sha256":digest(pool),"required_repair":227-len(fixed_now),"fractional":x,"cost":cost,"scale":cert["scale"] if cert else None,"dual_total":sum(cert["weights"].values()) if cert else None,"seed_words":base})
  C.publish()
 state={"verified_best":226,"target":227,"lp_reports":[{k:r.get(k) for k in ["name","pool","fixed","required_repair","numerical_lp_objective","dual_certificate"]} for r in reports],"hint_actions":{"fractional_hint":"Sort by decreasing LP value, then cover cost","reduced_cost_hint":"Sort by increasing integer cover cost, then decreasing LP value"}}
 action=sampler(state) if cases else "fractional_hint"
 image=modal.Image.debian_slim(python_version="3.12").pip_install("ortools==9.14.6206")
 for rel in ["supervisor.py","protected/manifest.json","protected/verify_descendants.py","protected/verify_lcs.py"]:
  image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
 app=modal.App("codegarden-side-lp-repair-001");volume=modal.Volume.from_name("codegarden-side-lp-20261115",create_if_missing=True)
 @app.function(serialized=True,image=image,cpu=2,memory=2048,timeout=120,max_containers=4,retries=0,scaledown_window=2,volumes={"/codegarden/checkpoints":volume})
 def exact(case,treatment,hint_action,source):
  import hashlib,json,pathlib,subprocess,sys,time,uuid
  from ortools.sat.python import cp_model
  sys.path.insert(0,"/opt/codegarden")
  from supervisor import verify
  def desc(x):
   out=set()
   for i in range(16):
    yy=(x&((1<<i)-1))|((x>>(i+1))<<i)
    for j in range(i,15):out.add((yy&((1<<j)-1))|((yy>>(j+1))<<j))
   return out
  pool=case["pool_words"];D=[desc(w) for w in pool];inc={}
  for j,ds in enumerate(D):
   for d in ds:inc.setdefault(d,[]).append(j)
  model=cp_model.CpModel();v=[model.NewBoolVar("x_"+str(w)) for w in pool]
  for indices in inc.values():model.Add(sum(v[i] for i in indices)<=1)
  required=case["required_repair"];model.Add(sum(v)>=required)
  fixed_zero=[];slack=None
  if treatment and case["cost"]:
   delta=[c-case["scale"] for c in case["cost"]];assert min(delta)>=0
   slack=case["dual_total"]-required*case["scale"]
   if slack<0:model.Add(False)
   else:
    model.Add(sum(d*z for d,z in zip(delta,v))<=slack)
    for i,d in enumerate(delta):
     if d>slack:model.Add(v[i]==0);fixed_zero.append(i)
  seed=set(case["seed_words"]);seed_hint=[i for i,w in enumerate(pool) if w in seed and i not in fixed_zero]
  preferred=list(range(len(pool)))
  if treatment and case["fractional"]:
   preferred.sort(key=(lambda i:(-case["fractional"][i],case["cost"][i],pool[i])) if hint_action=="fractional_hint" else (lambda i:(case["cost"][i],-case["fractional"][i],pool[i])))
  seen=set();greedy=[]
  for i in preferred:
   if i not in fixed_zero and not seen.intersection(D[i]):seen.update(D[i]);greedy.append(i)
  hint=greedy if len(greedy)>len(seed_hint) else seed_hint
  for i in hint:model.AddHint(v[i],1)
  if model.Validate():raise RuntimeError(model.Validate())
  solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=60;solver.parameters.num_search_workers=2;solver.parameters.random_seed=2271133;solver.parameters.repair_hint=True;solver.parameters.hint_conflict_limit=1000
  begin=time.monotonic();status=solver.Solve(model)
  selected=[pool[i] for i,z in enumerate(v) if solver.Value(z)] if status in [cp_model.FEASIBLE,cp_model.OPTIMAL] else []
  code=sorted(case["fixed_words"]+selected) if selected else sorted(case["seed_words"])
  folder=pathlib.Path("/codegarden/checkpoints")/uuid.uuid4().hex;folder.mkdir();p=folder/"witness.txt";p.write_text("".join(format(w,"016b")+"\n" for w in code))
  checked=verify(p)
  result={"name":case["name"],"treatment":treatment,"hint_action":hint_action,"source_sha":source,"solver_status":solver.StatusName(status),"wall_seconds":time.monotonic()-begin,"branches":solver.NumBranches(),"conflicts":solver.NumConflicts(),"pool_sha256":case["pool_sha256"],"required_repair":required,"hint_indices":hint,"hint_origin":"lp_or_word_order_greedy" if len(greedy)>len(seed_hint) else "incumbent_seed","proposed_greedy_hint_indices":greedy,"incumbent_hint_indices":seed_hint,"proposal_changed_actual_hint":hint!=seed_hint,"fixed_zero_indices":fixed_zero,"dual_cut_rhs":slack,"verification":checked,"words":[format(w,"016b") for w in code],"durable_path":str(folder),"scope":"Only the explicit fixed-code-compatible universe. UNKNOWN is unresolved; feasibility satisfies227 only after protected verification."}
  (folder/"result.json").write_text(json.dumps(result));volume.commit();return result
 outputs=[];calls=[]
 if cases:
  C.ledger.reserve("modal","codegarden",1)
  try:
   with app.run():
    calls=[exact.spawn(case,treatment,action,C.SOURCE) for case in cases for treatment in [False,True]]
    for i,call in enumerate(calls):
     r=call.get(timeout=180);p=OUT/("worker_"+str(i)+".txt");p.write_text("\n".join(r["words"])+"\n");r["host_verification"]=verify(p);C.save("workers/"+str(i)+".json",r);outputs.append(r);C.publish()
     if len(r["words"])>=227:
      (OUT/"candidate.txt").write_text(p.read_text())
      with open(os.environ["GITHUB_OUTPUT"],"a") as stream:stream.write("has_candidate=true\n")
      for other in calls[i+1:]:
       try:other.cancel()
       except Exception:pass
      break
  finally:
   for call in calls[len(outputs):]:
    try:call.cancel()
    except Exception:pass
 summary={"status":"completed","source_sha":C.SOURCE,"best_verified":max([226]+[len(r["words"]) for r in outputs]),"lp_reports":reports,"exact_models":[{k:r[k] for k in ["name","treatment","solver_status","wall_seconds","branches","conflicts"]} for r in outputs],"certificate_names":certs,"global_record_claim":False,"new_training_claim":False}
 C.save("summary.json",summary);C.save("status.json",summary)
 sid="codegarden-lp-"+os.environ["GITHUB_RUN_ID"]+"-analyst"
 item={"id":sid,"identity":"codegarden-side-analyst","audience":"codegarden-side-services-v1","timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),"label":"CodeGarden LP findings","content":json.dumps({"project":"codegarden","experiment":"lp_001","summary":summary,"interpretation":"All bounds concern only explicitly fixed neighborhoods; cardinality remains the primary objective."})}
 try:
  C.ledger.reserve("past","codegarden",30);pending={"source_id":sid,"state":"prepared","idempotency_key":sid};C.save("memory_handle.json",pending);C.publish()
  ingestion=C.http("https://api.past.dev/api/v1/ingest",os.environ["PAST_API_KEY"],{**item,"idempotencyKey":sid});pending.update(ingestion_id=ingestion["ingestionId"],state="accepted");C.save("memory_handle.json",pending)
 except Exception as e:C.save("memory_error.json",{"error":str(e)[:400]})
 C.ledger.persist();C.publish();print("CODEGARDEN_LP_FINAL",json.dumps({"best_verified":summary["best_verified"],"lp":[(r["name"],r.get("numerical_lp_objective"),r.get("dual_certificate",{})) for r in reports],"exact":summary["exact_models"]}),flush=True)
if __name__=="__main__":
 try:main()
 except Exception as e:
  traceback.print_exc();C.save("fatal.json",{"error":str(e)[:1200]})
  try:C.publish()
  except Exception:traceback.print_exc()
  raise
