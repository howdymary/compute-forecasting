"""Use real Tinker-selected deep bundles on distinct valid projected basins."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import Ledger
from supervisor import verify
OUT=ROOT/"artifacts/phase3/modal_bundle_001";OUT.mkdir(parents=True,exist_ok=True)
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2));return p
def publish():subprocess.run([sys.executable,"-B",str(ROOT/"phase3/publish_modal_bundle.py")],check=True)
def main():
 import modal
 # Fresh serialized research receipts supersede older cumulative carries.
 prior=json.loads((ROOT/"artifacts/phase3/research_002/status.json").read_text())["budget"]
 history={"source_run":"phase3-research-002-complete","conservative_totals":{p:v["reserved"]+v["provider_reported_or_estimated"] for p,v in prior.items()},"reason":"Carry every earlier hold; no previous unknown charge released."}
 (ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2))
 ledger=Ledger(OUT);calls=[];status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"started_at":dt.datetime.now(dt.timezone.utc).isoformat()}
 try:
  from search import Incidence
  from phase3.refine import minimum_covers
  inc=Incidence(16);native=json.loads((ROOT/"artifacts/phase3/modal_pair_001/workers/3.json").read_text())["native"]
  projections=[];seen=set()
  for item in sorted(native["near_archive"],key=lambda x:(x["energy"],-x["outside_original"])):
   covers,edges=minimum_covers(inc,item["words"])
   for cover in covers[:2]:
    words=sorted(set(item["words"])-cover);key=tuple(words)
    if len(words)==225 and key not in seen:seen.add(key);projections.append(words)
  assert len(projections)>=8
  proposal=json.loads((ROOT/"artifacts/phase3/research_002/strategy_proposals.json").read_text())[-1]
  assert proposal["decision"]["action"]=="deep_bundle" and proposal["decision"]["valid_action"]
  save("plan.json",{"hypothesis":"Neutral moves on distant valid 225-word projections may reach a new 226 basin and permit augmentation.",
   "actual_tinker_proposal":proposal,"starting_projections":projections[:16],"max_workers":2,"resources":{"cpu":1,"memory_mb":1024,"hard_timeout_seconds":900},
   "total_native_cpu_per_worker":400,"wall_limit_per_worker":600,"case_seeds":[1001001,1001002],"no_training":"No verified differential learning signal yet"})
  ledger.reserve("modal","codegarden",1)
  image=modal.Image.debian_slim(python_version="3.11").apt_install("g++")
  image=image.add_local_file(str(ROOT/"phase3/bundle_fast.cpp"),"/opt/codegarden/bundle_fast.cpp",copy=True)
  image=image.run_commands("g++ -O3 -std=c++17 /opt/codegarden/bundle_fast.cpp -o /opt/codegarden/bundle")
  for rel in ["supervisor.py","protected/verify_descendants.py","protected/verify_lcs.py","protected/manifest.json"]:
   image=image.add_local_file(str(ROOT/rel),"/opt/codegarden/"+rel)
  app=modal.App("codegarden-phase3-distant-bundles",tags={"project":"codegarden","hypothesis":"distant-neutral-bundles"})
  volume=modal.Volume.from_name("codegarden-phase3-bundle-checkpoints",create_if_missing=True)
  @app.function(serialized=True,image=image,cpu=1,memory=1024,timeout=900,max_containers=2,volumes={"/codegarden/results":volume})
  def worker(starts,seed,source):
   import hashlib,json,pathlib,random,subprocess,sys,time,uuid
   sys.path.insert(0,"/opt/codegarden");from supervisor import verify
   path=pathlib.Path("/codegarden/results")/uuid.uuid4().hex;path.mkdir();rng=random.Random(seed);queue=[sorted(c) for c in starts];seen=set();rows=[];best=[];cpu=0;started=time.monotonic()
   def canonical(C):return "".join(format(w,"016b")+"\n" for w in sorted(C))
   def digest(C):return hashlib.sha256(canonical(C).encode()).hexdigest()
   def orbit(C):
    rev=lambda w:int(format(w,"016b")[::-1],2)
    return min(tuple(sorted(C)),tuple(sorted(65535^w for w in C)),tuple(sorted(rev(w) for w in C)),tuple(sorted(65535^rev(w) for w in C)))
   while queue and cpu<400 and time.monotonic()-started<600 and len(rows)<96:
    at=rng.randrange(len(queue));code=queue.pop(at);key=orbit(code)
    if key in seen:continue
    seen.add(key);i=len(rows);p=path/("state_"+str(i)+".txt");p.write_text(canonical(code));accepted=verify(p)
    if len(code)>len(best):best=code
    k=3 if len(code)<226 else 5;seconds=min(8 if len(code)<226 else 30,400-cpu)
    r=json.loads(subprocess.run(["/opt/codegarden/bundle","16",str(k),str(seconds),"100000000000","96"],input=canonical(code),text=True,capture_output=True,check=True,timeout=seconds+90).stdout)
    pool=r.pop("candidate_pool");neighbors=r.pop("neighbors");cpu+=r["cpu_seconds"]
    r.update(incumbent_words=code,incumbent_witness_sha256=digest(code),k=k,parameters={"seconds":seconds,"nodes":100000000000,"neutral_cap":96},
     pool_hash=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest(),
     pool_definition="All outside words with at most k distinct incumbent blockers",independent_input_verification=accepted)
    if r["found"]:
     candidate=sorted(set(code)-set(r["removed"])|set(r["added"]));p=path/("improvement_"+str(i)+".txt");p.write_text(canonical(candidate));r["independent_winner_verification"]=verify(p)
     if len(candidate)>len(best):best=candidate
     queue.insert(0,candidate)
    fresh=[c for c in neighbors if orbit(c) not in seen];rng.shuffle(fresh);queue+=fresh[:32]
    if len(queue)>400:rng.shuffle(queue);queue=queue[:400]
    r["fresh_neutral_neighbors"]=len(fresh);r["frontier_after_cap"]=len(queue);rows.append(r)
    (path/"checkpoint.json").write_text(json.dumps({"seed":seed,"source_sha":source,"rows":rows,"best":best,"frontier":queue,"cpu_seconds":cpu}));volume.commit()
    if len(best)>=227:break
   p=path/"best.txt";p.write_text(canonical(best));result={"metadata":{"seed":seed,"source_sha":source,"start_codes":starts,"resources":{"cpu":1,"memory_mb":1024,"hard_timeout":900}},
    "best_words":[format(w,"016b") for w in best],"verification":verify(p),"experiments":rows,"native_cpu_seconds":cpu,"runtime_seconds":time.monotonic()-started,
    "durable_path":str(path),"unprocessed_frontier":len(queue),"negative_scope":"Only completed explicitly logged neighborhoods; capped neighborhoods/components are unresolved."}
   (path/"result.json").write_text(json.dumps(result));volume.commit();return result
  ledger.reserve("modal","codegarden",2*900*.002);save("ledger_progress.json",ledger.summary());publish()
  rows=[]
  with app.run():
   calls=[worker.spawn(projections[i:16:2],1001001+i,os.environ["GITHUB_SHA"]) for i in range(2)]
   for i,call in enumerate(calls):
    r=call.get(timeout=1200);p=OUT/("worker_best_"+str(i)+".txt");p.write_text("\n".join(sorted(r["best_words"]))+"\n");r["host_verification"]=verify(p)
    save("workers/"+str(i)+".json",r);rows.append(r);publish()
    if len(r["best_words"])>=227:
     for other in calls[i+1:]:
      try:other.cancel()
      except Exception:pass
     break
  status.update(status="completed",workers_collected=len(rows),best_verified=max([226]+[len(r["best_words"]) for r in rows]))
 except Exception as e:
  status.update(status="failed_or_partial",error=str(e)[:1000]);traceback.print_exc()
  for call in calls:
   try:call.cancel()
   except Exception:pass
 finally:
  status.update(budget=ledger.summary(),finished_at=dt.datetime.now(dt.timezone.utc).isoformat());save("status.json",status);publish();print("MODAL_BUNDLE_FINAL",json.dumps(status),flush=True)
if __name__=="__main__":main()
