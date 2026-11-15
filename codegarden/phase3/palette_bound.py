"""Independently enumerate the25-variable known-component palette, not the whole universe."""
import hashlib,importlib.util,json,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words
from supervisor import verify,check_integrity
check_integrity();out=ROOT/"artifacts/phase3/fusion3_001/palette";out.mkdir(parents=True,exist_ok=True);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());codes=info["codes"];core=set.intersection(*(set(C) for C in codes));palette=set.union(*(set(C) for C in codes));pool=sorted(palette-core)
spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
ds={w:set(D.descendants(format(w,"016b"))) for w in palette}
assert len(core)==216 and len(palette)==241 and len(pool)==25
assert all(not ds[a]&ds[b] for a in core for b in palette if b!=a),"Common vertices must be compatible with the whole palette"
adj=[sum(1<<j for j,v in enumerate(pool) if w!=v and not ds[w]&ds[v]) for w in pool]
best=[pool.index(w) for w in set(codes[0])-core];assert len(best)==10;nodes=0;start=time.monotonic();complete=True;found=False
class Limited(Exception):pass
class Target(Exception):pass
def dfs(chosen,available):
 global nodes,best
 nodes+=1
 if nodes%4096==0 and time.monotonic()-start>30:raise Limited()
 if len(chosen)>len(best):best=chosen[:]
 if len(best)>=11:raise Target()
 while available:
  if len(chosen)+available.bit_count()<=len(best):return
  bit=available&-available;available-=bit;v=bit.bit_length()-1;dfs(chosen+[v],available&adj[v])
try:dfs([], (1<<25)-1)
except Limited:complete=False
except Target:complete=False;found=True
C=sorted(core|{pool[i] for i in best});path=out/"best.txt";path.write_text(canonical(C));accepted=verify(path)
report={"source_codes_sha256":hashlib.sha256(json.dumps(codes,sort_keys=True).encode()).hexdigest(),"palette":sorted(palette),"fixed_common_core":sorted(core),"variable_pool":pool,"common_vertices_are_universally_compatible_with_palette":True,"enumeration_nodes":nodes,"seconds":time.monotonic()-start,"complete":complete,"feasible227":found,"best_verified":accepted,"palette_optimum":len(C) if complete else None,"scope":"Only codes whose words lie in this explicit241-word palette. Common216 are universally compatible, so every palette optimum can include them. Exhaustive independent literal-string clique enumeration on remaining25 words; no global bound."}
(out/"report.json").write_text(json.dumps(report,indent=2));print("PALETTE_BOUND",json.dumps({"complete":complete,"palette_optimum":report["palette_optimum"],"best_verified":accepted["cardinality"],"nodes":nodes}),flush=True)
if accepted["cardinality"]>=227:print("PALETTE_WINNER_WORDS",json.dumps(path.read_text().splitlines()),flush=True)
