"""Restricted-mask invariant and protected positive-export checks."""
import json,os,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical
exe=ROOT/".build/pool_kernel";base=next((ROOT/"artifacts/baselines").glob("arena_208_*.txt"));C={int(w,2) for w in base.read_text().split()};rows=[]
for case in range(4):
 rng=random.Random(1181900+case);pool=C|set(rng.sample(range(65536),100+case*50));p=ROOT/".build/test_pool.txt";p.write_text("\n".join(map(str,sorted(pool)))+"\n")
 r=json.loads(subprocess.run([str(exe),"1",str(1181900+case),"adaptive","","227"],input=canonical(C),text=True,capture_output=True,check=True,env=dict(os.environ,CODEGARDEN_POOL=str(p))).stdout)
 assert set(r["best"])<=pool and all(set(A)<=pool for A in r["archive"])
 q=ROOT/".build/test_pool_best.txt";q.write_text(canonical(r["best"]));v=verify(q);assert v["cardinality"]>=len(C);rows.append({"case":case,"iterations":r["iterations"],"verified_size":v["cardinality"]})
out=ROOT/"artifacts/phase3/pool_bridge_001";out.mkdir(parents=True,exist_ok=True);(out/"mask_tests.json").write_text(json.dumps(rows,indent=2));print("POOL_MASK_TESTS",len(rows))
