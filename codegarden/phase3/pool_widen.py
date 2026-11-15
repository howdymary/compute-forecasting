"""Avoid the known neutral backbone while searching a small construction union."""
import argparse,hashlib,json,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
def orbit(C):
 rev=lambda w:int(format(w,"016b")[::-1],2)
 return [set(C),{65535^w for w in C},{rev(w) for w in C},{65535^rev(w) for w in C}]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case
 out=ROOT/"artifacts/phase3/pool_widen_001"/str(case);out.mkdir(parents=True,exist_ok=True);check_integrity()
 data=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known=[O for C in data["codes"] for O in orbit(C)]
 core=set.intersection(*(set(C) for C in data["codes"]));startpath=next((ROOT/"artifacts/baselines").glob("arena_225_*.txt"));start={int(w,2) for w in startpath.read_text().split()};accepted=verify(startpath)
 union=json.loads((ROOT/"artifacts/phase3/cp_lns_001/0/plan.json").read_text())["candidate_pool"];assert len(union)>=3000 and start<=set(union)
 families=[set.intersection(*(orbit(C)[i] for C in data["codes"])) for i in range(4)];rng=random.Random(1180001+case//3);banned=set()
 for family in families:
  candidates=sorted((family&set(union))-start-{0,65535});assert candidates
  banned.add(rng.choice(candidates))
 assert all(C&banned for C in known),"Every known component symmetry must be excluded"
 mode=case%3;candidate=set(union)
 if mode==1:candidate|=set(random.Random(1189001+case//3).sample(range(65536),8192))
 if mode==2:candidate=set(range(65536))
 pool=sorted(candidate-banned);assert start<=set(pool)
 mask=out/"pool.txt";mask.write_text("\n".join(map(str,pool))+"\n");p=out/"starting.txt";p.write_text(canonical(start))
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"pool_condition":["construction_union","union_plus_8192","full_universe"][mode],"seed":1183001+case//3,"forbidden_words":sorted(banned),"pool_sha256":pool_hash(pool),"pool_count":len(pool),
  "starting_verification":accepted,"scope":"Heuristic on the recorded candidate pool after forbidding one shared backbone word per known symmetry family. Same starting code, forbidden set, seed and 180-second inner budget within each three-condition block. No infeasibility or global optimum claim.",
  "hypothesis":"Test whether candidate support, rather than only local descent, blocks escape: compare a construction union, an 8192-word extension and the entire binary universe under identical backbone exclusions.",
  "best_verified":226,"best_exported":225}
 r=json.loads(subprocess.run([str(ROOT/".build/pool_kernel"),"180",str(report["seed"]),"adaptive",str(out/"checkpoint.txt"),"226"],input=p.read_text(),text=True,capture_output=True,check=True,timeout=260,env=dict(os.environ,CODEGARDEN_POOL=str(mask))).stdout)
 A=r["best"];assert set(A)<=set(pool);q=out/"pool_best.txt";q.write_text(canonical(A));v=verify(q);report.update(native=r,exported_verification=v,best_exported=v["cardinality"]);report["followups"]=[]
 if v["cardinality"]>=226:
  assert set(A) not in known
  for k in [3,5,7,9]:
   z=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),"30","1000000000000","0"],input=q.read_text(),text=True,capture_output=True,check=True,timeout=80,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1")).stdout)
   z["pool_sha256"]=pool_hash(z.pop("candidate_pool"));z.pop("neighbors")
   if z["found"]:
    B=set(A)-set(z["removed"])|set(z["added"]);p=out/"improvement.txt";p.write_text(canonical(B));z["verification"]=verify(p);report["best_verified"]=z["verification"]["cardinality"]
   report["followups"].append(z)
   if report["best_verified"]>=227:break
 (out/"report.json").write_text(json.dumps(report,indent=2));print("POOL_WIDEN",json.dumps({"case":case,"exported":report["best_exported"],"best":report["best_verified"],"iterations":r["iterations"]}),flush=True)
if __name__=="__main__":main()
