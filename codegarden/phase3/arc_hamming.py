"""Arc-consistency filtering of the collective mutation CSP, with independent proof replay."""
import argparse,collections,hashlib,json,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash
from supervisor import verify,check_integrity
from phase3.hamming_csp_env import balls,prepare
from phase3.verify_arc import check as replay
from ortools.sat.python import cp_model
def supports(groups,ds):
 at={}
 for i,g in enumerate(groups):
  for b,w in enumerate(g):
   for d in ds[w]:
    bucket=at.setdefault(d,{});bucket[i]=bucket.get(i,0)|(1<<b)
 table={};ALL=(1<<len(groups[0]))-1
 for g in groups:
  for w in g:
   row=[ALL]*len(groups)
   for d in ds[w]:
    for i,mask in at[d].items():row[i]&=~mask
   table[w]=row
 return table
def prune(C,n,v,ds,table,budget=5):
 groups=balls(C,n);domains=[sum(1<<b for b,w in enumerate(g) if not set(ds[w])&set(ds[v])) for g in groups]
 queue=collections.deque(range(len(groups)));queued=set(queue);trace=[];started=time.monotonic();capped=False
 while queue and all(domains):
  if time.monotonic()-started>=budget:capped=True;break
  j=queue.popleft();queued.remove(j)
  for i,g in enumerate(groups):
   if i==j:continue
   old=domains[i];remaining=old
   while remaining:
    bit=remaining&-remaining;remaining^=bit;w=g[bit.bit_length()-1]
    if not table[w][j]&domains[j]:domains[i]&=~bit;trace.append([i,w,j])
   if not domains[i]:break
   if domains[i]!=old and i not in queued:queue.append(i);queued.add(i)
 final=[[w for b,w in enumerate(g) if domains[i]&(1<<b)] for i,g in enumerate(groups)]
 return {"n":n,"parents":[format(w,"0%db"%n) for w in sorted(C)],"extra":format(v,"0%db"%n),"trace":trace,"final_domains":[sorted(g) for g in final],
  "status":"INFEASIBLE_EMPTY_DOMAIN" if not all(domains) else "TIMEOUT_VALID_PRUNING" if capped else "ARC_CONSISTENT_NOT_SOLVED","wall_seconds":time.monotonic()-started}
def test():
 rng=random.Random(1220001);rows=[]
 for n,C in [(5,[0]),(5,[0,31]),(6,[0,7]),(6,[0,7,56]),(6,[0,7,56,63])]:
  inc=Incidence(n);groups=balls(C,n);table=supports(groups,inc.desc);union={w for g in groups for w in g};pivots=[v for v in range(1<<n) if v not in union];rng.shuffle(pivots)
  for v in pivots[:8]:
   c=prune(C,n,v,inc.desc,table);checked=replay(c)
   def feasible(domains):
    def rec(i,used):
     if i==len(domains):return True
     return any(not set(inc.desc[w])&used and rec(i+1,used|set(inc.desc[w])) for w in domains[i])
    return rec(0,set(inc.desc[v]))
   initial=[[w for w in g if not set(inc.desc[w])&set(inc.desc[v])] for g in groups];before=feasible(initial);after=feasible(c["final_domains"])
   assert before==after and (not checked["infeasible_in_encoded_family"] or not before)
   rows.append({"n":n,"C":C,"extra":v,"original_feasible":before,"pruned_feasible":after,"replay":checked})
 out=ROOT/"artifacts/phase3/arc_hamming_001";out.mkdir(parents=True,exist_ok=True);(out/"tests.json").write_text(json.dumps(rows,indent=2));print("ARC_HAMMING_TESTS",len(rows),flush=True)
def run(case):
 out=ROOT/"artifacts/phase3/arc_hamming_001"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((out.parent/"plan.json").read_text());base=out.parent/"preflight/baseline.txt";accepted=verify(base);C={int(w,2) for w in base.read_text().split()};inc=Incidence(16)
 t=time.monotonic();table=supports(balls(C,16),inc.desc);build_seconds=time.monotonic()-t;rows=[];best=226
 for i,pivot in enumerate(plan["selected"][case::8]):
  v=pivot["word"];c=prune(C,16,v,inc.desc,table,5);p=out/("certificate_"+str(i)+".json");p.write_text(json.dumps(c))
  r={"extra":v,"pruning_status":c["status"],"certificate":p.name,"certificate_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"independent_string_replay":replay(c),
   "pruning_seconds":c["wall_seconds"],"removed_values":len(c["trace"]),"remaining_values":sum(map(len,c["final_domains"]))}
  if any(not g for g in c["final_domains"]):r["status"]="INFEASIBLE_BY_REPLAYED_DOMAIN_CERTIFICATE"
  else:
   model=cp_model.CpModel();xs={w:model.new_bool_var("w"+str(w)) for g in c["final_domains"] for w in g};at={}
   for g in c["final_domains"]:model.add_exactly_one(xs[w] for w in g)
   for w,x in xs.items():
    for d in inc.desc[w]:at.setdefault(d,[]).append(x)
   for group in at.values():
    if len(group)>1:model.add_at_most_one(group)
   for w,x in xs.items():model.add_hint(x,int(w in C))
   assert not model.validate();solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=20;solver.parameters.num_search_workers=1;solver.parameters.random_seed=1221001+case*100+i
   started=time.monotonic();status=solver.solve(model);r.update(status=solver.status_name(status),solver_wall_seconds=time.monotonic()-started,model_sha256=hashlib.sha256(str(model.proto).encode()).hexdigest())
   if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
    A=sorted([v]+[w for w,x in xs.items() if solver.value(x)]);q=out/"improvement.txt";q.write_text(canonical(A));r["verification"]=verify(q);assert r["verification"]["cardinality"]==227;best=227
  rows.append(r);(out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"case":case,"rows":rows,"best_verified":best,"starting_verification":accepted,"support_build_seconds":build_seconds,
   "scope":plan["scope"],"method":"Standard binary-CSP arc-consistency support pruning, then bounded exact CP-SAT; no timeout is promoted to infeasibility."},indent=2))
  print("ARC_HAMMING",json.dumps({"case":case,"attempt":i,"extra":v,"status":r["status"],"best":best,"removed_values":r["removed_values"]}),flush=True)
  if best>=227:break
def main():
 check_integrity();ap=argparse.ArgumentParser();ap.add_argument("--test",action="store_true");ap.add_argument("--prepare",action="store_true");ap.add_argument("--case",type=int);a=ap.parse_args()
 if a.test:test()
 elif a.prepare:prepare()
 else:run(a.case)
if __name__=="__main__":main()
