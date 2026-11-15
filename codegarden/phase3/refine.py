"""Project near-feasible states, polish valid subsets and solve bounded exact repairs."""
import hashlib,itertools,json,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash,digest_words
from supervisor import verify
def minimum_covers(inc,state):
 owners={};edges=set()
 for w in state:
  for d in inc.desc[w]:
   for v in owners.get(d,[]):edges.add(tuple(sorted((v,w))))
   owners.setdefault(d,[]).append(w)
 vertices=sorted(set(v for e in edges for v in e))
 if len(vertices)>12:raise ValueError("Refinement only accepts bounded low-conflict states")
 for k in range(len(vertices)+1):
  answer=[]
  for cover in itertools.combinations(vertices,k):
   cc=set(cover)
   if all(a in cc or b in cc for a,b in edges):answer.append(cc)
  if answer:return answer,edges
 raise RuntimeError("No cover")
def refine(native,reference,target,seed,out):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
 inc=Incidence(16);base={int(w,2) for w in reference}
 near=sorted(native.get("near_archive",[]),key=lambda r:(r["energy"],-r["outside_original"]))[:12]
 if not near:near=[{"words":native["closest_state"],"energy":native["minimum_pair_energy"],"outside_original":0}]
 projections={};repair_states=[]
 for item in near:
  state=item["words"];assert len(state)==target and len(set(state))==target
  if item["energy"]>6:continue
  covers,edges=minimum_covers(inc,state);covers.sort(key=lambda c:(len(c),sum(w not in base for w in c)))
  for cover in covers[:2]:
   code=sorted(set(state)-cover);key=digest_words(code)
   projections.setdefault(key,{"words":code,"cover":sorted(cover),"edges":[list(e) for e in sorted(edges)],"parent":state,
    "distance":len(set(code)-base),"energy":item["energy"]})
  repair_states.append((state,covers[0]))
 ordered=sorted(projections.values(),key=lambda p:(-len(p["words"]),-p["distance"]))[:8]
 valid=[];polished=[];exact=[]
 for i,p in enumerate(ordered):
  path=out/("worker_projected_"+str(i)+".txt");path.write_text(canonical(p["words"]));checked=verify(path)
  valid.append({"words":p["words"],"verification":checked,"witness":path.name,"distance_outside_reference":p["distance"]})
  q=subprocess.run([os.environ.get("CODEGARDEN_VALID_KERNEL","/opt/codegarden/kernel_v2"),"2",str(seed+i),"fixed",str(out/("polish_checkpoint_"+str(i)+".txt")),str(target),"4"],
    input=canonical(p["words"]),text=True,capture_output=True,check=True,timeout=20)
  r=json.loads(q.stdout);result=r["best"];path=out/("worker_polished_"+str(i)+".txt");path.write_text(canonical(result));accepted=verify(path)
  polished.append({"seed":seed+i,"starting_sha256":digest_words(p["words"]),"search_cpu_seconds":r["cpu_seconds"],"iterations":r["iterations"],
   "verification":accepted,"witness":path.name,"words":result})
  if accepted["cardinality"]>=target:return {"valid_projections":valid,"polished":polished,"exact":exact,"winner":result}
 from cp_sat import solve
 for i,(state,cover) in enumerate(repair_states[:2]):
  for extra in [16,64,128]:
   rng=random.Random(seed*1000+i*200+extra);available=sorted(set(state)-cover);removed=set(cover)|set(rng.sample(available,min(extra,len(available))))
   fixed=sorted(set(state)-removed);inc.occupied(fixed)
   full=inc.compatible_pool(fixed);pool=full
   if len(pool)>5000:
    keep=set(state)&set(pool);rest=[w for w in pool if w not in keep];rng.shuffle(rest);pool=sorted(keep|set(rest[:5000-len(keep)]))
   requested=target-len(fixed);hint=sorted((set(state)-set(fixed))&set(pool));trial,receipt=solve(inc,pool,requested,hint,seconds=2,seed=seed+i+extra,workers=1)
   receipt.update({"fixed_outside":fixed,"candidate_pool":pool,"fixed_outside_sha256":digest_words(fixed),"pool_before_cap":len(full),
    "definition":{"near_state":state,"mandatory_cover":sorted(cover),"additional_removed":extra,"rng_seed":seed*1000+i*200+extra,
      "cap":5000,"selection":"Include all compatible current-state words; seeded sample of the remaining compatible universe if the pool exceeds cap"},
    "global_target":target,"near_state_kind":"infeasible diagnostic","proof_artifact":None})
   if trial:
    result=fixed+trial;path=out/("worker_exact_"+str(i)+"_"+str(extra)+".txt");path.write_text(canonical(result));receipt["independent_verification"]=verify(path)
    exact.append(receipt);return {"valid_projections":valid,"polished":polished,"exact":exact,"winner":result}
   exact.append(receipt)
 return {"valid_projections":valid,"polished":polished,"exact":exact,"winner":None}
