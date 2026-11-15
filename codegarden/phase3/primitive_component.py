"""Walk primitive neutral exchanges, verifying selected roots and every claimed improvement."""
import argparse,collections,hashlib,json,os,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical,pool_hash,digest_words
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",required=True);a=ap.parse_args();k=int(a.mode[-1]);out=ROOT/"artifacts/phase3/primitive_001"/a.mode;out.mkdir(parents=True,exist_ok=True)
 base=ROOT/"artifacts/phase3/primitive_001/preflight/baseline.txt";root=sorted(int(w,2) for w in base.read_text().split());best=len(root)
 queue=collections.deque([root]);seen={digest_words(root)};rows=[];complete=True;started=time.monotonic();nativeCPU=0
 def save():
  (out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"mode":a.mode,"radius":k,"processed":len(rows),"discovered":len(seen),
   "frontier_codes":list(queue),"rows":rows,"component_complete":not queue and complete,"best_verified":best,"native_cpu_seconds":nativeCPU,"wall_seconds":time.monotonic()-started,
   "scope":"Primitive connected neutral moves generate the ordinary neutral component when there is no strict improvement. Node/time/neighbor caps prevent a closure claim."},indent=2))
 while queue and len(rows)<256 and time.monotonic()-started<650:
  C=queue.popleft();i=len(rows);p=out/("state_"+str(i)+".txt");p.write_text(canonical(C));accepted=verify(p)
  sec=10 if k<8 else 15
  r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(sec),"1000000000000","192"],input=p.read_text(),text=True,capture_output=True,check=True,timeout=sec+60,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1")).stdout)
  pool=r.pop("candidate_pool");neighbors=r.pop("neighbors");nativeCPU+=r["cpu_seconds"];complete&=r["complete"]
  r.update(incumbent_witness_sha256=digest_words(C),incumbent_file=p.name,verification=accepted,canonical_pool_sha256=pool_hash(sorted(pool)),
   seconds_limit=sec,neighbor_cap=192,primitive_neighbors_returned=len(neighbors),ordering="descending blocker count then descendant size")
  if r["found"]:
   candidate=set(C)-set(r["removed"])|set(r["added"]);q=out/"improvement.txt";q.write_text(canonical(candidate));r["independent_verification"]=verify(q);best=max(best,len(candidate))
  for A in neighbors:
   h=digest_words(A)
   if h not in seen:seen.add(h);queue.append(A)
  rows.append(r);save()
  print("PRIMITIVE_PROGRESS",json.dumps({"mode":a.mode,"processed":len(rows),"discovered":len(seen),"frontier":len(queue),"best":best,"complete_neighborhood":r["complete"]}),flush=True)
  if best>=227:break
 if a.mode=="control5" and not queue and complete:
  expected=json.loads((ROOT/"artifacts/phase3/bundle_004/component5/report.json").read_text())
  hashes={x["incumbent_witness_sha256"] for x in expected["rows"]};assert seen==hashes,"Primitive-component regression differs from full radius-five component"
 save()
if __name__=="__main__":main()
