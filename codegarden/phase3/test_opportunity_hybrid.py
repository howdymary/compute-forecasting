"""Literal descendant-pair and sparse edge-weight checks independent of the search generator."""
import hashlib,importlib.util,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity
check_integrity();spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
r=json.loads(subprocess.run([str(ROOT/".build/opportunity_hybrid"),"--weighted-test"],text=True,capture_output=True,check=True).stdout);cache={}
def desc(w):
 if w not in cache:cache[w]=set(D.descendants(format(w,"016b")))
 return cache[w]
def conflict(a,b):return a!=b and bool(desc(a)&desc(b))
queries=0
for obs in r["observations"]:
 C=obs["selected"];weights={tuple(sorted((a,b))):v for a,b,v in obs["penalties"]};e=we=0
 for i,a in enumerate(C):
  for b in C[i+1:]:
   if conflict(a,b):e+=1;we+=1+weights.get(tuple(sorted((a,b))),0)
 assert e==obs["pair_energy"] and we==obs["weighted_energy"]
 for w,v in obs["field_samples"]:
  expected=sum(1+weights.get(tuple(sorted((w,a))),0) for a in C if conflict(w,a));assert expected==v;queries+=1
out=ROOT/"artifacts/phase3/opportunity_hybrid_001";out.mkdir(parents=True,exist_ok=True);(out/"literal_weight_tests.json").write_text(json.dumps({"passed":True,"snapshots":len(r["observations"]),"literal_field_queries":queries,"kernel_sha256":hashlib.sha256((ROOT/"phase3/opportunity_hybrid.cpp").read_bytes()).hexdigest(),"scope":"Invalid intermediate states used only to test exact pair and weighted fields; no code construction claimed."},indent=2));print("WEIGHTED_LITERAL_TESTS",queries,flush=True)
