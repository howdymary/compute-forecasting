"""Independent exhaustive bipartite checks, including matching/cover dual witnesses."""
import itertools,json,pathlib,random,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];rng=random.Random(1320001);rows=[]
for case in range(100):
 l=1+rng.randrange(6);r=1+rng.randrange(6);edges={(i,j) for i in range(l) for j in range(r) if rng.random()<.4};raw=f"{l} {r} {len(edges)}\n"+"\n".join(f"{i} {j}" for i,j in sorted(edges));a=json.loads(subprocess.run([str(ROOT/".build/recombine"),"--graph"],input=raw,text=True,capture_output=True,check=True).stdout)
 L=set(a["independent_left"]);R=set(a["independent_right"]);assert not any(i in L and j in R for i,j in edges)
 optimum=max(mask.bit_count() for mask in range(1<<(l+r)) if not any(mask&(1<<i) and mask&(1<<(l+j)) for i,j in edges))
 assert len(L)+len(R)==optimum==l+r-a["matching"];rows.append({"case":case,"left":l,"right":r,"edges":len(edges),"optimum":optimum})
out=ROOT/"artifacts/phase3/recombine_long_001";out.mkdir(parents=True,exist_ok=True);(out/"tests.json").write_text(json.dumps(rows,indent=2));print("RECOMBINE_TESTS",len(rows),flush=True)
