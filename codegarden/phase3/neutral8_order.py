"""Try neutral-eight bridges from dispersed known roots, then strict repair of any new verified code."""
import argparse,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,digest_words,pool_hash
def orbit(C):
 rev=lambda w:int(format(w,"016b")[::-1],2)
 return [set(C),{65535^w for w in C},{rev(w) for w in C},{65535^rev(w) for w in C}]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case
 out=ROOT/"artifacts/phase3/neutral8_order_001"/str(case);out.mkdir(parents=True,exist_ok=True);check_integrity()
 info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());codes=info["codes"];known={digest_words(O) for C in codes for O in orbit(C)}
 chosen=[codes[0]];unused=codes[1:]
 while len(chosen)<4:
  Q=max(unused,key=lambda C:min(len(set(C)^set(P)) for P in chosen));chosen.append(Q);unused.remove(Q)
 C=chosen[case//2];order="2" if case%2 else "1";p=out/"starting.txt";p.write_text(canonical(C));accepted=verify(p)
 result=subprocess.run([str(ROOT/".build/bundle"),"16","8","300","1000000000000","4096"],input=p.read_text(),text=True,capture_output=True,check=True,timeout=420,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER=order))
 r=json.loads(result.stdout);pool=r.pop("candidate_pool");neighbors=r.pop("neighbors")
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"candidate_order":"ascending blockers" if order=="2" else "descending blockers","starting_verification":accepted,
  "native":r,"pool_sha256":pool_hash(pool),"neighbor_count":len(neighbors),"novel_verified":[],"known_component_hashes":sorted(known),"strict_followups":[],"best_verified":226,
  "scope":"Any capped neutral enumeration is incomplete. Completeness applies only to this one root, not a component. Only two protected verifiers assign cardinality."}
 if r["found"]:
  Q=set(C)-set(r["removed"])|set(r["added"]);q=out/"direct_improvement.txt";q.write_text(canonical(Q));v=verify(q);report["direct_improvement"]=v;report["best_verified"]=v["cardinality"]
 for A in neighbors:
  h=digest_words(A)
  if h in known:continue
  known.add(h);q=out/("novel_"+str(len(report["novel_verified"]))+".txt");q.write_text(canonical(A));v=verify(q);report["novel_verified"].append({"witness":q.name,"verification":v})
  for k in [3,5,7]:
   z=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),"20","1000000000000","0"],input=q.read_text(),text=True,capture_output=True,check=True,timeout=70,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1")).stdout)
   z["pool_sha256"]=pool_hash(z.pop("candidate_pool"));z.pop("neighbors");z["starting_sha256"]=h
   if z["found"]:
    T=set(A)-set(z["removed"])|set(z["added"]);w=out/"strict_improvement.txt";w.write_text(canonical(T));z["verification"]=verify(w);report["best_verified"]=z["verification"]["cardinality"]
   report["strict_followups"].append(z)
   if report["best_verified"]>=227:break
  if report["best_verified"]>=227 or len(report["novel_verified"])>=8:break
 (out/"report.json").write_text(json.dumps(report,indent=2));print("NEUTRAL8_ORDER",json.dumps({"case":case,"best":report["best_verified"],"neighbors":len(neighbors),"novel":len(report["novel_verified"]),"native_complete":r["complete"],"cpu":r["cpu_seconds"]}),flush=True)
if __name__=="__main__":main()
