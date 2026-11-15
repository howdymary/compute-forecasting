"""Direct blocker-union search; bounded neutral components are not global proofs."""
import argparse,collections,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
def canonical(code):return "".join(format(w,"016b")+"\n" for w in sorted(code))
def digest(code):return hashlib.sha256(canonical(code).encode()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",required=True);a=ap.parse_args();mode=a.mode
 out=ROOT/"artifacts/phase3/bundle_anchor_001"/mode;out.mkdir(parents=True,exist_ok=True)
 baseline=ROOT/"artifacts/phase3/bundle_anchor_001/preflight/baseline.txt";root=sorted(int(w,2) for w in baseline.read_text().split())
 basecheck=verify(baseline);assert basecheck["cardinality"]>=226
 K=int(mode[-1]);neutral=0 if mode.startswith("strict") else 256
 queue=collections.deque([root]);seen={digest(root)};rows=[];best=len(root);started=time.monotonic();total_cpu=0;processed=0;complete_component=True
 def checkpoint():
  (out/"report.json").write_text(json.dumps({"mode":mode,"source_sha":os.environ["GITHUB_SHA"],"best_verified":best,
   "baseline":basecheck,"processed":processed,"discovered":len(seen),"frontier":len(queue),"rows":rows,
   "complete_component":not queue and complete_component,"scope":"Restricted blocker-union neighborhoods, at most k removed; caps make enumeration incomplete. No global optimality.",
   "kernel_cpu_seconds":total_cpu,"wall_seconds":time.monotonic()-started,"provider_calls":0},indent=2))
 while queue and processed<(1 if mode.startswith("strict") else 64) and time.monotonic()-started<650:
  code=queue.popleft();h=digest(code);p=out/("state_"+str(processed)+".txt");p.write_text(canonical(code));checked=verify(p)
  seconds=450 if mode.startswith("strict") else 30
  r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(K),str(seconds),"100000000000",str(neutral)],
   input=canonical(code),text=True,capture_output=True,check=True,timeout=seconds+60).stdout)
  pool=r.pop("candidate_pool");r["candidate_pool_sha256"]=hashlib.sha256(b"".join(int(w).to_bytes(4,"big") for w in pool)).hexdigest()
  r["candidate_pool_definition"]="Every outside 16-bit word with at most k distinct incumbent blockers; reconstruct from state witness."
  neighbors=r.pop("neighbors");r["neutral_neighbors_returned"]=len(neighbors);total_cpu+=r["cpu_seconds"];complete_component&=r["complete"]
  r.update(incumbent_witness_sha256=h,incumbent_file=p.name,parameters={"seconds":seconds,"nodes":100000000000,"neutral_cap":neutral},verification=checked)
  if r["found"]:
   candidate=sorted(set(code)-set(r["removed"])|set(r["added"]));winner=out/"improvement.txt";winner.write_text(canonical(candidate))
   accepted=verify(winner);assert accepted["cardinality"]>len(code);best=max(best,accepted["cardinality"]);r["independent_verification"]=accepted
  for nextcode in neighbors:
   nh=digest(nextcode)
   if nh not in seen:seen.add(nh);queue.append(nextcode)
  rows.append(r);processed+=1;checkpoint()
  print("BUNDLE_PROGRESS",json.dumps({"mode":mode,"best":best,"processed":processed,"frontier":len(queue),"pool":len(pool),"nodes":r["nodes"],"complete_neighborhood":r["complete"]}),flush=True)
  if best>len(root):break
 checkpoint()
if __name__=="__main__":main()
