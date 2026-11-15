"""Bound memory by explicit diverse induced word pools after full ReduMIS bad_alloc."""
import hashlib,importlib.util,json,os,pathlib,subprocess,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import check_integrity,verify
check_integrity();OUT=ROOT/"artifacts/phase3/induced_kamis_001";OUT.mkdir(parents=True,exist_ok=True);url="https://raw.githubusercontent.com/"+os.environ["GITHUB_REPOSITORY"]+"/244cb4f9d894fd8aca8c8e1131019cfe6aa03d0b/codegarden/artifacts/phase3/low_blocker_001/plan.json"
with urllib.request.urlopen(url,timeout=60) as response:raw=response.read()
assert hashlib.sha256(raw).hexdigest()=="2ff78e247e7dfdd7959aece345c8d8edf789a34253c4792a98e1f2dc9f6871e2";old=json.loads(raw);assert old["source_sha"]=="3160937c2b7f9252477d31991fbf7030fd39ccf4";(OUT/"source_low_plan.json").write_bytes(raw);rev=lambda w:int(format(w,"016b")[::-1],2)
pools=[]
for b,expected_n,expected_h in [(3,8672,"2890dc5475acae8c524168b1a1994ec01f112b9c795f0906e42b0a5dc22862bd"),(4,22338,"74bb03f6a1bdc19d9c0e1ec473ac4218c24292c2adcd9fb078c19c0ba709f9f2")]:
 S=set()
 for row in old["cases"]:
  S.update(row["starting_words"]);S.update(next(q for q in row["models"] if q["blocker_threshold"]==b)["outside_pool"])
 P=sorted({v for w in S for v in [w,w^65535,rev(w),rev(w)^65535]});assert len(P)==expected_n and pool_hash(P)==expected_h;(OUT/("pool_"+str(b)+".txt")).write_text("\n".join(map(str,P))+"\n");pools.append({"blocker_union":b,"pool_count":len(P),"pool_sha256":pool_hash(P),"path":"pool_"+str(b)+".txt"})
for i,row in enumerate(old["cases"]):
 p=OUT/("seed_"+str(i)+".txt");p.write_text(canonical(row["starting_words"]));v=verify(p);assert v["reports"][0]["witness_sha256"]==row["starting_sha256"]
info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known=sorted({tuple(sorted(O)) for C in info["codes"] for O in [C,[w^65535 for w in C],[rev(w) for w in C],[rev(w)^65535 for w in C]]});(OUT/"known226.txt").write_text("".join("226 "+" ".join(map(str,C))+"\n" for C in known))
# Verify every edge of a small arbitrary induced graph with frozen literal descendants.
P=[w for w in range(64) if w%5!=0];sp=OUT/"small_pool.txt";sp.write_text("\n".join(map(str,P))+"\n");gp=ROOT/".build/small_induced.graph";r=subprocess.run([str(ROOT/".build/induced_graph"),"6",str(sp),str(gp)],text=True,capture_output=True,check=True);lines=gp.read_text().splitlines();assert int(lines[0].split()[0])==len(P)
spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D);ds=[set(D.descendants(format(w,"06b"))) for w in P]
for i,line in enumerate(lines[1:]):assert {int(v)-1 for v in line.split()}=={j for j in range(len(P)) if j!=i and ds[i]&ds[j]}
cases=[]
for case in range(8):
 b=3 if case<4 else 4;mode="evolutionary_cold" if case%2==0 else "ils_warm";parent=[1,3,5,7][case//2];cases.append({"case":case,"blocker_union":b,"mode":mode,"warm_parent":parent if case%2 else None,"seed":1550001+case,"rounds":2,"seconds_per_round":300})
plan={"source_sha":os.environ["GITHUB_SHA"],"upstream_repository":"https://github.com/KarlsruheMIS/KaMIS","upstream_revision":"2e4b3861b8063f05e8520434b97ce59e21ca49e7","source_low_plan_sha256":hashlib.sha256(raw).hexdigest(),"pools":pools,"cases":cases,"small_graph_all_edges_independently_checked":True,"hypothesis":"Earlier full65536vertex ReduMIS aborted with bad_alloc. Unioning low-blocker neighborhoods from eight diverse incumbent families gives larger shared universes than any single corridor, while reducing graph memory. Profile actual sparse edges, gate32times CSR below5GB, and try evolutionary search plus warm ILS. No graph is persisted in Git.","scope":"Two explicit induced word pools, not the entire universe. Heuristic runs have no impossibility or optimality claim. Initialization differs between cold evolutionary and warm ILS, so no causal algorithm superiority is inferred. Only protected witness checks assign scores. Failed memory gates/processes are failures, not negative mathematical results."}
(OUT/"plan.json").write_text(json.dumps(plan,indent=2));print("INDUCED_KAMIS_PLAN",json.dumps({"pools":pools,"small_graph_passed":True,"cases":cases}),flush=True)
