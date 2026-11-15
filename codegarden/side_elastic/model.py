"""Full-universe exact-target packing and explicitly invalid elastic diagnostics."""
import collections,hashlib,json,pathlib,time
def descendants(w,n):
 result=set()
 for i in range(n-1):
  a=(w&((1<<i)-1))|((w>>(i+1))<<i)
  for j in range(i+1,n):
   result.add((a&((1<<(j-1))-1))|((a>>j)<<(j-1)))
 return sorted(result)
def literal_desc(w,n):
 s=format(w,"0"+str(n)+"b")
 return {s[:i]+s[i+1:j]+s[j+1:] for i in range(n) for j in range(i+1,n)}
def literal_energy(words,n):
 counts=collections.Counter(d for w in words for d in literal_desc(w,n))
 return sum(max(0,v-1) for v in counts.values())
def incidence(n):
 rows=[[] for _ in range(1<<(n-2))]
 for w in range(1<<n):
  for d in descendants(w,n):rows[d].append(w)
 return rows
def make_model(n,rows,target,cap,hint):
 from ortools.sat.python import cp_model
 model=cp_model.CpModel();xs=[model.new_bool_var("w"+str(w)) for w in range(1<<n)]
 model.add(sum(xs)==target);slacks=[];hc=collections.Counter(d for w in hint for d in descendants(w,n))
 for d,words in enumerate(rows):
  vv=[xs[w] for w in words]
  if cap is None:model.add_at_most_one(vv)
  else:
   z=model.new_int_var(0,cap,"over"+str(d));slacks.append(z);model.add(sum(vv)<=1+z);model.add_hint(z,max(0,hc[d]-1))
 if cap is not None:model.add(sum(slacks)<=cap);model.minimize(sum(slacks))
 chosen=set(hint)
 for w,v in enumerate(xs):model.add_hint(v,int(w in chosen))
 return model,xs,slacks
def smoke():
 from ortools.sat.python import cp_model
 checked=0;results=[]
 for n in range(3,9):
  for w in range(1<<n):
   assert {format(d,"0"+str(n-2)+"b") for d in descendants(w,n)}==literal_desc(w,n)
   checked+=1
 for n in range(4,7):
  rows=incidence(n);m=cp_model.CpModel();xs=[m.new_bool_var("w"+str(w)) for w in range(1<<n)]
  for row in rows:m.add_at_most_one([xs[w] for w in row])
  m.maximize(sum(xs));s=cp_model.CpSolver();s.parameters.num_search_workers=1;s.parameters.max_time_in_seconds=15
  status=s.solve(m);assert status==cp_model.OPTIMAL
  code=[w for w,v in enumerate(xs) if s.value(v)];assert literal_energy(code,n)==0
  em,ev,_=make_model(n,rows,len(code),2,code);es=cp_model.CpSolver();es.parameters.num_search_workers=1;es.parameters.max_time_in_seconds=15
  est=es.solve(em);assert est in [cp_model.FEASIBLE,cp_model.OPTIMAL] and round(es.objective_value)==0
  candidate=[w for w,v in enumerate(ev) if es.value(v)];assert len(candidate)==len(code) and literal_energy(candidate,n)==0
  bad,bv,_=make_model(n,rows,len(code)+1,None,[]);bs=cp_model.CpSolver();bs.parameters.num_search_workers=1;bs.parameters.max_time_in_seconds=15
  bst=bs.solve(bad);assert bst==cp_model.INFEASIBLE
  results.append({"n":n,"exact_small_optimum":len(code),"elastic_zero_agrees":True,"larger_hard_target_infeasible":True})
 return {"literal_descendant_agreements":checked,"small_solver_cases":results,"scope":"Small-instance correctness checks, not a length16 bound."}
def run(spec,shadow,source,folder,checkpoint):
 from ortools.sat.python import cp_model
 from supervisor import verify
 folder=pathlib.Path(folder);folder.mkdir(parents=True,exist_ok=True);began=time.monotonic()
 rows=incidence(16);assert len(rows)==16384 and all(len(r)==137 for r in rows)
 assert len(shadow)==len(set(shadow))==227 and literal_energy(shadow,16)==2
 model,xs,slacks=make_model(16,rows,227,spec["cap"],shadow)
 mh=hashlib.sha256(str(model.proto).encode()).hexdigest()
 result={"source_sha":source,"spec":spec,"status":"running","universe":65536,"fixed_words":[],"target":227,"descendant_constraints":16384,"incidences":sum(map(len,rows)),"model_text_sha256":mh,"initial_diagnostic_energy":2,"positive_energy_is_invalid":True,"proof_artifact":None,"events":[]}
 (folder/"model.pbtxt").write_text(str(model.proto))
 log=folder/"solver.log";last=[time.monotonic()]
 def save():
  (folder/"checkpoint.json").write_text(json.dumps(result));checkpoint()
 save()
 solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=spec["seconds"];solver.parameters.num_search_workers=8;solver.parameters.random_seed=spec["seed"]
 solver.parameters.log_search_progress=True;solver.parameters.log_to_stdout=False
 def log_cb(line):
  with log.open("a") as stream:stream.write(line)
  if time.monotonic()-last[0]>=60:
   last[0]=time.monotonic();result["elapsed_seconds"]=last[0]-began;result["last_log_tail"]=line[-1000:];save()
 solver.log_callback=log_cb
 class Export(cp_model.CpSolverSolutionCallback):
  def on_solution_callback(self):
   words=[w for w,v in enumerate(xs) if self.value(v)];assert len(words)==len(set(words))==227
   actual=literal_energy(words,16)
   if spec["cap"] is None:assert actual==0
   else:assert actual==round(self.objective_value)
   row={"seconds":self.wall_time,"literal_energy":actual,"accepted_as_code":False}
   if actual==0:
    p=folder/"candidate.txt";p.write_text("".join(format(w,"016b")+"\n" for w in words))
    try:checked=verify(p)
    except Exception as e:row["verification_rejected"]=str(e)[:1500]
    else:
     row["accepted_as_code"]=True;row["verification"]=checked;result["words"]=[format(w,"016b") for w in words];result["verification"]=checked;self.stop_search()
   else:
    row["diagnostic_invalid_words"]=words
   result["events"].append(row);save()
 status=solver.solve(model,Export())
 result.update(status=solver.status_name(status),wall_seconds=solver.wall_time,total_seconds=time.monotonic()-began,branches=solver.num_branches,conflicts=solver.num_conflicts,proof_artifact=None,global_record_claim=False)
 if spec["cap"] is not None and status in [cp_model.FEASIBLE,cp_model.OPTIMAL]:
  result["objective_energy"]=solver.objective_value;result["objective_bound"]=solver.best_objective_bound
 if "words" not in result:result["conclusion"]="No independently verified227 witness returned within this bounded encoded search. A positive-energy diagnostic is invalid. No global absence proof is claimed."
 else:result["conclusion"]="Explicit227 witness passed both worker verifiers; separate isolated acceptance is required."
 result["solver_log_sha256"]=hashlib.sha256(log.read_bytes()).hexdigest() if log.exists() else None
 (folder/"result.json").write_text(json.dumps(result));save();return result
if __name__=="__main__":print(json.dumps(smoke(),indent=2))
