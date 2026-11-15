"""Independent literal-string replay of a finite domain-removal certificate."""
import functools,importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity
def check(certificate):
 check_integrity();n=certificate["n"];C=certificate["parents"];extra=certificate["extra"];assert len(C)==len(set(C)) and all(len(w)==n and not set(w)-set("01") for w in C+[extra])
 spec=importlib.util.spec_from_file_location("protected_d2",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);D.verify(C,n)
 @functools.lru_cache(None)
 def ds(w):return set(D.descendants(format(w,"0%db"%n)))
 groups=[{int(w,2)}|{int(w,2)^(1<<i) for i in range(n)} for w in C];assert sum(map(len,groups))==len(set.union(*groups))
 v=int(extra,2);assert v not in set.union(*groups);domains=[{w for w in g if not ds(w)&ds(v)} for g in groups]
 for i,w,j in certificate["trace"]:
  assert i!=j and w in domains[i]
  assert all(ds(w)&ds(u) for u in domains[j]),"Removed a supported value"
  domains[i].remove(w)
 assert [sorted(g) for g in domains]==certificate["final_domains"]
 impossible=any(not g for g in domains)
 return {"valid_pruning_certificate":True,"infeasible_in_encoded_family":impossible,"removals":len(certificate["trace"]),"n":n,"parent_count":len(C),
  "scope":"Exactly one representative from each specified radius-one parent ball plus the fixed extra word. No statement about all binary codes."}
if __name__=="__main__":print(json.dumps(check(json.loads(pathlib.Path(sys.argv[1]).read_text())),sort_keys=True))
