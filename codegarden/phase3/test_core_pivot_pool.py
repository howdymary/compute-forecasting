"""Independent literal deletion replay of full65536-word forced-pivot pools."""
import importlib.util,itertools,json,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity
from search import digest_words,pool_hash
check_integrity();info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=sorted(set.intersection(*(set(C) for C in info["codes"])));raw="226 "+" ".join(map(str,info["codes"][0]))+"\n216 "+" ".join(map(str,core))+"\n"
spec=importlib.util.spec_from_file_location("literal",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);ds={w:set(D.descendants(format(w,"016b"))) for w in core};pairs=list(itertools.combinations(range(16),2));rng=random.Random(1400001);rows=[]
for i in range(4):
 while True:
  w=rng.randrange(65536);d=set(D.descendants(format(w,"016b")));B=sorted(v for v in core if ds[v]&d)
  if 6<=len(B)<=18:break
 native=json.loads(subprocess.run([str(ROOT/".build/core_pivot"),"--forced-pool",str(w)],input=raw,text=True,capture_output=True,check=True).stdout);fixed=sorted(set(core)-set(B)|{w});assert native["blockers"]==B and sorted(native["fixed"])==fixed
 occupied=set().union(*(set(D.descendants(format(v,"016b"))) for v in fixed));pool=[];fixedset=set(fixed)
 for v in range(65536):
  if v in fixedset:continue
  s=format(v,"016b")
  if all(s[:a]+s[a+1:b]+s[b+1:] not in occupied for a,b in pairs):pool.append(v)
 assert native["pool"]==pool
 rows.append({"pivot":w,"blockers":B,"fixed_sha256":digest_words(fixed),"pool_count":len(pool),"pool_sha256":pool_hash(pool),"independent_replay_passed":True})
out=ROOT/"artifacts/phase3/core_pivot_001";out.mkdir(parents=True,exist_ok=True);(out/"independent_pool_tests.json").write_text(json.dumps(rows,indent=2));print("CORE_PIVOT_POOL_TESTS",len(rows),flush=True)
