"""Full-universe fixed216-core bound and all maxima by independent string arithmetic."""
import hashlib,importlib.util,itertools,json,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words
from supervisor import verify,check_integrity
check_integrity();out=ROOT/"artifacts/phase3/audits_001/core_all";out.mkdir(parents=True,exist_ok=True);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());codes=info["codes"];core=set.intersection(*(set(C) for C in codes));assert len(core)==216
spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
occupied=set().union(*(set(D.descendants(format(w,"016b"))) for w in core));pairs=list(itertools.combinations(range(16),2));pool=[];ds={};start=time.monotonic()
for w in range(65536):
 if w in core:continue
 s=format(w,"016b");desc=set();okay=True
 for i,j in pairs:
  d=s[:i]+s[i+1:j]+s[j+1:]
  if d in occupied:okay=False;break
  desc.add(d)
 if okay:pool.append(w);ds[w]=desc
assert len(pool)==57
adj=[sum(1<<j for j,v in enumerate(pool) if w!=v and not ds[w]&ds[v]) for w in pool]
best=[pool.index(w) for w in set(codes[0])-core];nodes=0;complete=True;found=False
class Limited(Exception):pass
class Target(Exception):pass
def dfs(chosen,available):
 global nodes,best
 nodes+=1
 if nodes%4096==0 and time.monotonic()-start>60:raise Limited()
 if len(chosen)>len(best):best=chosen[:]
 if len(best)>=11:raise Target()
 while available:
  if len(chosen)+available.bit_count()<=len(best):return
  bit=available&-available;available-=bit;v=bit.bit_length()-1;dfs(chosen+[v],available&adj[v])
try:dfs([], (1<<len(pool))-1)
except Limited:complete=False
except Target:complete=False;found=True
C=sorted(core|{pool[i] for i in best});path=out/"best.txt";path.write_text(canonical(C));accepted=verify(path)
maxima=[];all_nodes=0
def enumerate_maxima(chosen,available):
 global all_nodes
 all_nodes+=1
 if len(chosen)==10:maxima.append(sorted(core|{pool[i] for i in chosen}));return
 while available:
  if len(chosen)+available.bit_count()<10:return
  bit=available&-available;available-=bit;v=bit.bit_length()-1;enumerate_maxima(chosen+[v],available&adj[v])
if complete and len(best)==10:
 enumerate_maxima([], (1<<len(pool))-1);assert {tuple(C) for C in maxima}=={tuple(sorted(C)) for C in codes}
 for i,C in enumerate(maxima):
  p=out/("maximum_"+str(i)+".txt");p.write_text(canonical(C));assert verify(p)["cardinality"]==226
report={"fixed_core":sorted(core),"fixed_core_sha256":digest_words(core),"compatible_full_universe_variable_pool":pool,"enumeration_nodes":nodes,"all_maxima_nodes":all_nodes,"complete":complete,"feasible227":found,"best_verified":accepted,"fixed_core_optimum":len(C) if complete else None,"maximum_codes":maxima,"maximum_code_hashes":[digest_words(C) for C in maxima],"count":len(maxima),"seconds":time.monotonic()-start,"scope":"All65536 words considered for compatibility with this fixed216-core. Independent literal-string clique bound on57 variables. Exactly38 maxima verified if complete. Every227 or different226 must omit some core word; no global bound."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("CORE_ALL_OPTIMA",json.dumps({"complete":complete,"count":len(maxima),"best":accepted["cardinality"],"nodes":nodes,"all_nodes":all_nodes}),flush=True)
if accepted["cardinality"]>=227:print("CORE_ALL_WINNER",json.dumps(path.read_text().splitlines()),flush=True)
