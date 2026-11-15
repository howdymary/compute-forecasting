"""Decision-clique comparison with literal protected-string exhaustive search."""
import itertools,importlib.util,json,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity
check_integrity();spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);rng=random.Random(1250001);rows=[]
for case in range(16):
 n=5 if case<4 else 6;pool=rng.sample(range(1<<n),12+case%8);ds={w:set(D.descendants(format(w,"0%db"%n))) for w in pool}
 for target in [2,3,4,5]:
  expected=any(all(not ds[a]&ds[b] for a,b in itertools.combinations(C,2)) for C in itertools.combinations(pool,target))
  r=json.loads(subprocess.run([str(ROOT/".build/core5_repair"),"--repair",str(n),str(target),"5"],input=" ".join(map(str,pool)),text=True,capture_output=True,check=True).stdout)
  assert r["found"]==expected and (r["found"] or r["complete"])
  D.verify([format(w,"0%db"%n) for w in r["best"]],n)
  if r["found"]:assert len(r["best"])>=target
  rows.append({"case":case,"n":n,"pool":pool,"target":target,"feasible":expected,"nodes":r["nodes"]})
out=ROOT/"artifacts/phase3/core5_repair_001";out.mkdir(parents=True,exist_ok=True);(out/"tests.json").write_text(json.dumps(rows,indent=2));print("CORE_REPAIR_TESTS",len(rows),flush=True)
