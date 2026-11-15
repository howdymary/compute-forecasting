"""Avoid promising-code starvation and false frontier exhaustion in persistent walks."""
import argparse,collections,functools,hashlib,heapq,json,os,pathlib,random,select,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import Incidence,canonical
from phase3.refine import minimum_covers
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--lineage",required=True);a=ap.parse_args();names=["arena225","projected225","arena224","arena223"];seed=1030001+names.index(a.lineage);rng=random.Random(seed)
 out=ROOT/"artifacts/phase3/frontier_001"/a.lineage;out.mkdir(parents=True,exist_ok=True)
 rev=[int(format(w,"016b")[::-1],2) for w in range(65536)]
 @functools.lru_cache(maxsize=16000)
 def orbit(C):
  R=tuple(sorted(rev[w] for w in C));return min(C,tuple(65535-w for w in reversed(C)),R,tuple(65535-w for w in reversed(R)))
 def digest(C):return hashlib.sha256(canonical(C).encode()).hexdigest()
 comp=ROOT/"artifacts/phase3/bundle_004/component5";cr=json.loads((comp/"report.json").read_text())
 known={orbit(tuple(sorted(int(w,2) for w in (comp/r["incumbent_file"]).read_text().split()))) for r in cr["rows"]}
 if a.lineage=="projected225":
  native=json.loads((ROOT/"artifacts/phase3/modal_pair_001/workers/2.json").read_text())["native"];inc=Incidence(16);starts=[]
  for item in sorted(native["near_archive"],key=lambda r:(r["energy"],-r["outside_original"]))[:8]:
   covers,edges=minimum_covers(inc,item["words"]);C=tuple(sorted(set(item["words"])-covers[0]))
   if len(C)>=224:starts.append(C)
 else:
  size=int(a.lineage[-3:]);p=next((ROOT/"artifacts/baselines").glob("arena_"+str(size)+"_*.txt"));starts=[tuple(sorted(int(w,2) for w in p.read_text().split()))]
 assert starts
 heap=[];elite=[];enqueued=set();seen=set();complete=set();partials={};rows=[];switches=[];best=max(starts,key=len);counter=0;dropped=0;recoveries=0;novel226=set();last_commit=time.monotonic();started=last_commit;cpu=0;process_cpu=0;retry_count=0
 def enqueue(C,forced=None,reason="unseen neutral state"):
  nonlocal counter,dropped
  C=tuple(sorted(C));key=orbit(C)
  if forced is None and (key in seen or key in enqueued):return
  if forced is not None and (key,forced) in complete:return
  if len(C)>=226 and key not in known:
   elite.append((C,forced,reason));return
  heapq.heappush(heap,(-len(C),rng.random(),counter,C,forced,reason));counter+=1;enqueued.add(key)
  if len(heap)>800:
   keep=heapq.nsmallest(600,heap);old={orbit(x[3]) for x in heap};new={orbit(x[3]) for x in keep};dropped+=len(heap)-len(keep);enqueued.difference_update(old-new);heap[:]=keep;heapq.heapify(heap)
 for i,C in enumerate(starts):
  p=out/("starting_"+str(i)+".txt");p.write_text(canonical(C));verify(p);enqueue(C)
 p=out/"best.txt";p.write_text(canonical(best));best_verified=verify(p)
 stderr=(out/"native_stderr.log").open("w");server=subprocess.Popen([str(ROOT/".build/bundle"),"--server"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True)
 def checkpoint(final=False):
  p=out/"best.txt";p.write_text(canonical(best))
  (out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"lineage":a.lineage,"seed":seed,"status":"completed" if final else "running",
   "best_exported":best_verified["cardinality"],"global_retained_best":max(226,best_verified["cardinality"]),"best_verification":best_verified,
   "processed":len(rows),"native_cpu_seconds":cpu,"process_cpu_seconds":process_cpu,"wall_seconds":time.monotonic()-started,
   "ordinary_frontier":len(heap),"priority_frontier":len(elite),"partial_neighborhoods":len(partials),"complete_neighborhoods":len(complete),
   "frontier_discarded":dropped,"known_component_recoveries":recoveries,"novel226_orbits_verified":len(novel226),"radius_changes":switches,
   "retries":retry_count,"scope":"A dropped frontier or capped neighborhood is not exhaustion. Every mathematical score is a protected export.",
   "provider_calls":0},indent=2))
  (out/"frontier_checkpoint.json").write_text(json.dumps({"ordinary":[{"code":list(x[3]),"forced":x[4],"reason":x[5]} for x in heap],
   "priority":[{"code":list(x[0]),"forced":x[1],"reason":x[2]} for x in elite],"partial":[{"code":list(C),"k":k,"attempts":attempts} for (key,k),(C,attempts) in partials.items()]}))
  for j in range(0,len(rows),256):
   dest=out/"shards"/(str(j)+".json");dest.parent.mkdir(exist_ok=True);dest.write_text(json.dumps(rows[j:j+256]))
 try:
  while (heap or elite or partials) and len(rows)<7000 and cpu<450 and time.monotonic()-started<750:
   if elite:C,forced,reason=elite.pop()
   elif heap:
    _,_,_,C,forced,reason=heapq.heappop(heap);enqueued.discard(orbit(C))
   else:
    keyk=rng.choice(list(partials));C,attempts=partials.pop(keyk);forced=min(7 if len(C)>=226 else 5,keyk[1]+1);reason="partial frontier emptied; increase radius rather than declare exhaustion";retry_count+=1
   key=orbit(C)
   if forced is None and key in seen:continue
   seen.add(key);k=forced or (6 if len(C)>=226 else 3)
   if (key,k) in complete:continue
   if len(rows)%128==127 and partials:
    kk=rng.choice(list(partials));PC,attempts=partials.pop(kk);enqueue(PC,min(7 if len(PC)>=226 else 5,kk[1]+1),"budgeted larger repair after capped neighborhood");retry_count+=1
   seconds=min(25 if k>=5 else 6 if k==4 else 2,450-cpu);requestseed=seed*100000+len(rows)+1
   switches.append({"step":len(rows),"k":k,"reason":reason}) if not switches or switches[-1]["k"]!=k else None
   server.stdin.write("16 "+str(k)+" "+str(seconds)+" 100000000000 128 "+str(requestseed)+" "+str(len(C))+"\n"+canonical(C));server.stdin.flush()
   ready,_,_=select.select([server.stdout],[],[],seconds+90)
   if not ready:raise TimeoutError("native request")
   line=server.stdout.readline()
   if not line:raise RuntimeError("native server exited")
   r=json.loads(line);cpu+=r["cpu_seconds"];process_cpu=r["process_cpu_total"];pool=r.pop("candidate_pool");neighbors=r.pop("neighbors")
   r.update(incumbent=list(C),incumbent_sha256=digest(C),candidate_pool_sha256=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in sorted(pool))).hexdigest(),
    candidate_pool_definition="All outside words with at most k distinct incumbent blockers; logged shuffle seed",decision_reason=reason,seconds_limit=seconds,intermediate_neutral_validity="native invariant; no new cardinality claim")
   if r["complete"]:complete.add((key,k));partials.pop((key,k),None)
   else:
    attempts=partials.get((key,k),(C,0))[1]+1
    if attempts<4:partials[(key,k)]=(C,attempts)
    if len(partials)>1600:partials.pop(next(iter(partials)))
   if r["found"]:
    candidate=tuple(sorted(set(C)-set(r["removed"])|set(r["added"])));q=out/("candidate_"+str(len(rows))+".txt");q.write_text(canonical(candidate));r["independent_verification"]=verify(q)
    if len(candidate)>len(best):best=candidate;best_verified=r["independent_verification"]
    ck=orbit(candidate)
    if len(candidate)>=226:
     if ck in known:recoveries+=1;r["classification"]="Recovery into already known 38-code orbit archive; not a record"
     else:novel226.add(ck);enqueue(candidate,None,"new verified 226-word orbit gets priority");r["classification"]="New to our orbit archive; cardinality remains 226 unless size is at least 227"
    else:enqueue(candidate,3,"verified higher-cardinality lineage result gets priority")
   for A in neighbors:enqueue(tuple(A))
   rows.append(r)
   if time.monotonic()-last_commit>15 or len(best)>=227:checkpoint();last_commit=time.monotonic()
   if len(best)>=227:break
 finally:
  try:server.stdin.close();server.wait(timeout=15)
  except Exception:server.kill();server.wait(timeout=15)
  stderr.close();p=out/"best.txt";p.write_text(canonical(best));best_verified=verify(p);checkpoint(True)
 print("FRONTIER_FINAL",json.dumps({"lineage":a.lineage,"best":len(best),"processed":len(rows),"recoveries":recoveries,"novel226":len(novel226),"cpu":cpu}),flush=True)
if __name__=="__main__":main()
