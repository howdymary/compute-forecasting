"""Literal-string conflict graph and complete minimum-cover projection of a tensor archive."""
import argparse,collections,functools,hashlib,importlib.util,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words
from supervisor import verify,check_integrity
def project(path,out):
 check_integrity();out.mkdir(parents=True,exist_ok=True);data=json.loads(path.read_text());info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());rev=lambda w:int(format(w,"016b")[::-1],2)
 known={digest_words(O) for C in info["codes"] for O in [C,[65535^w for w in C],[rev(w) for w in C],[65535^rev(w) for w in C]]}
 spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 @functools.lru_cache(None)
 def ds(w):return set(D.descendants(format(w,"016b")))
 rows=[];checked={};novel=[];best=226
 for index,item in enumerate(data["archive"]):
  C=item["words"];assert len(C)==227 and len(set(C))==227;owner={};edges=set();counts=collections.Counter()
  for i,w in enumerate(C):
   for d in ds(w):
    for j in owner.get(d,[]):edges.add((j,i))
    owner.setdefault(d,[]).append(i);counts[d]+=1
  energy=sum(v*(v-1)//2 for v in counts.values());assert energy==item["raw_energy"]
  minimum=[999];covers=set();nodes=[0]
  def rec(left,chosen):
   nodes[0]+=1
   if nodes[0]>1000000:raise RuntimeError("Projection enumeration cap; no optimum claim")
   if len(chosen)>minimum[0]:return
   if not left:
    if len(chosen)<minimum[0]:minimum[0]=len(chosen);covers.clear()
    covers.add(tuple(sorted(chosen)));return
   u,v=next(iter(left))
   for x in [u,v]:rec({e for e in left if x not in e},chosen|{x})
  rec(edges,set());results=[]
  for cover in sorted(covers):
   A=sorted(w for i,w in enumerate(C) if i not in cover);h=digest_words(A)
   if h not in checked:
    p=out/("projection_"+h[:16]+".txt");p.write_text(canonical(A));checked[h]={"verification":verify(p),"witness":p.name}
   results.append({**checked[h],"removed_words":[C[i] for i in cover],"known226_orbit":h in known})
   best=max(best,len(A))
   if len(A)>=226 and h not in known:novel.append(checked[h])
  rows.append({"archive_index":index,"raw_energy":energy,"edges":[[C[i],C[j]] for i,j in sorted(edges)],"minimum_cover_size":minimum[0],"cover_enumeration_complete":True,"enumeration_nodes":nodes[0],"projections":results})
 report={"source_file":str(path.relative_to(ROOT)),"source_file_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"rows":rows,"unique_projections_verified":len(checked),"novel226_orbits":novel,"best_independently_verified":best,
  "scope":"Only this finite archived state list. Positive-energy states are invalid; projected explicit codes are accepted only by both protected verifiers. Recovery of known226 is not a new result."}
 (out/"report.json").write_text(json.dumps(report,indent=2));return report
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--batch",default="tensor_cpu_002");a=ap.parse_args();r=project(ROOT/"artifacts/phase3"/a.batch/"search.json",ROOT/"artifacts/phase3"/a.batch/"projections");print("TENSOR_PROJECTIONS",json.dumps({k:r[k] for k in ["unique_projections_verified","novel226_orbits","best_independently_verified"]}),flush=True)
