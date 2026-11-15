"""Enumerate all560relative-orientation triples across seven fresh source families."""
import hashlib,itertools,json,os,pathlib,random,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash,Incidence
from supervisor import verify,check_integrity
check_integrity();OUT=ROOT/"artifacts/phase3/fresh_triples_001";OUT.mkdir(parents=True,exist_ok=True)
data=json.loads((ROOT/"phase3/fresh225_plan.json").read_text());sources=data["cases"];assert len(sources)==7
rev=lambda w:int(format(w,"016b")[::-1],2)
def images(C):return [sorted(C),sorted(65535^w for w in C),sorted(rev(w) for w in C),sorted(65535^rev(w) for w in C)]
parents=[];receipts=[];inc=Incidence(16)
for row in sources:
 C=row["words"];assert digest_words(C)==row["sha256"];p=OUT/("seed_"+str(row["case"])+".txt");p.write_text(canonical(C));v=verify(p);assert v["cardinality"]==225
 parents.append(images(C));receipts.append({"case":row["case"],"source_case":row["source_case"],"path":p.name,"verification":v})
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known=sorted({tuple(K) for B in info["codes"] for K in images(B)})
kp=OUT/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,K))+"\n" for K in known))
proposals=[];seen=set()
for a,b,c in itertools.combinations(range(7),3):
 for ob,oc in itertools.product(range(4),repeat=2):
  A,B,C=map(set,[parents[a][0],parents[b][ob],parents[c][oc]]);F=sorted(A&B&C);P=sorted((A|B|C)-set(F));key=(tuple(F),tuple(P))
  occupied=inc.occupied(F);assert len(P)<=675 and all(not occupied&inc.masks[w] for w in P)
  if key in seen:continue
  seen.add(key);qid=len(proposals);random.Random(1523101+qid).shuffle(P)
  proposals.append({"query":qid,"parent_families":[a,b,c],"orientations":[0,ob,oc],"parent_sha256":[digest_words(A),digest_words(B),digest_words(C)],"fixed":F,"pool":P,"fixed_sha256":digest_words(F),"pool_sha256":pool_hash(P),"ordered_pool_sha256":hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in P)).hexdigest(),"target_total":226,"target_added":226-len(F),"native_cpu_limit_seconds":2})
plan={"source_sha":os.environ["GITHUB_SHA"],"parents":receipts,"proposed_relative_triples":560,"unique_explicit_fixed_pool_models":len(proposals),"known226_count":len(known),"known226_sha256":hashlib.sha256(kp.read_bytes()).hexdigest(),"queries":proposals,"shards":12,"hypothesis":"Pair unions incident to these new parents were closed without a new226; three-parent unions can contain compatible combinations unavailable to any pair. Explore all relative triples of seven new source-family representatives, targeting a new226before strict227polish.","scope":"Explicit three-parent unions with common fixed code only. All distinct fixed/pool models are retained; not full-universe search or all225parents. A2CPU-second timeout remains open. Exact known226arrays excluded, eligible larger supersets remain. Primary target227unchanged."}
(OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("FRESH_TRIPLES_PLAN",json.dumps({k:plan[k] for k in ["proposed_relative_triples","unique_explicit_fixed_pool_models","known226_count","hypothesis"]}),flush=True)
