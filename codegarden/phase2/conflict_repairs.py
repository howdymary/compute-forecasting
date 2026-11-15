"""Conflict-driven 5..12-word repairs with independently checked matching bounds."""
import hashlib,importlib.util,json,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import Incidence,canonical,pool_hash,digest_words
from supervisor import verify
from cp_sat import solve
spec=importlib.util.spec_from_file_location("hall_strings",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
def main():
 out=ROOT/"artifacts/phase2/conflict_repairs";out.mkdir(parents=True,exist_ok=True)
 words=(ROOT/"artifacts/best_code.txt").read_text().splitlines();accepted=verify(ROOT/"artifacts/best_code.txt");code=[int(w,2) for w in words]
 inc=Incidence(16);owner=[-1]*16384
 for i,w in enumerate(code):
  for d in inc.desc[w]:owner[d]=i
 groups={};selected=set(code)
 for w in range(65536):
  if w in selected:continue
  mask=0
  for d in inc.desc[w]:
   if owner[d]>=0:mask|=1<<owner[d]
  if mask.bit_count()<=12:groups.setdefault(mask,[]).append(w)
 rng=random.Random(501612);masks=[]
 for k in range(5,13):
  items=[m for m in groups if m.bit_count()==k];rng.shuffle(items);masks.extend(items[:256])
 allm=list(groups)
 for _ in range(3000):
  if len(allm)<2:break
  a,b=rng.sample(allm,2);m=a|b
  if 5<=m.bit_count()<=12:masks.append(m)
 masks=sorted(set(masks));ranked=[]
 for m in masks:
  new=[];sub=m
  while sub:
   new.extend(groups.get(sub,[]));sub=(sub-1)&m
  new.extend(groups.get(0,[]));ranked.append((len(new)-m.bit_count(),m,new))
 ranked.sort(key=lambda x:(-x[0],x[1]));ranked=ranked[:512]
 metadata={"incumbent_witness_sha256":accepted["reports"][0]["witness_sha256"],"source_sha":os.environ["GITHUB_SHA"],
  "candidate_universe_sha256":pool_hash(range(65536)),"removal_set_generation":"Blocker sets of sampled excluded words, plus sampled pairwise unions, cardinalities 5..12; seed 501612; rank by freed-new-word count minus removed count; retain at most 512",
  "generated_removal_sets":len(masks),"selected_removal_sets":len(ranked),"proof_scope":"Only each explicit fixed-outside/candidate-pool repair; not all radius-5..12 exchanges"}
 rows=[];start=time.perf_counter();best=code
 dcache={}
 def ds(w):
  if w not in dcache:dcache[w]=set(D.descendants(format(w,"016b")))
  return dcache[w]
 for i,(surplus,mask,new) in enumerate(ranked):
  if time.perf_counter()-start>180:break
  removed=[w for j,w in enumerate(code) if mask&(1<<j)];fixed=[w for j,w in enumerate(code) if not mask&(1<<j)]
  old=set(removed);adj={w:[v for v in removed if inc.masks[w]&inc.masks[v]] for w in new};match={}
  def augment(w,seen):
   for v in adj[w]:
    if v in seen:continue
    seen.add(v)
    if v not in match or augment(match[v],seen):match[v]=w;return True
   return False
  for w in new:augment(w,set())
  pool=sorted(set(removed)|set(new));r={"id":i,"removed":removed,"fixed_outside":fixed,"candidate_pool":pool,
    "candidate_pool_sha256":pool_hash(pool),"target":len(removed)+1,"freed_new_words":len(new),"matching_size":len(match),
    "incumbent_witness_sha256":metadata["incumbent_witness_sha256"],"proof_artifact":None}
  if len(match)==len(new):
   certificate=[{"old":v,"new":w,"shared_descendant":sorted(ds(v)&ds(w))[0]} for v,w in match.items()]
   assert len({e["old"] for e in certificate})==len(certificate) and {e["new"] for e in certificate}==set(new)
   r.update({"status":"INFEASIBLE_BY_VERIFIED_MATCHING_COVER","proof_artifact":certificate,
    "proof":"Pair each new candidate with a distinct conflicting old candidate. These pairs plus unmatched old singletons cover the pool with k cliques, so at most k can be chosen."})
  else:
   trial,report=solve(inc,pool,len(removed)+1,removed,seconds=2,seed=501612+i,workers=1);r["solver"]=report;r["status"]=report["status"]
   if trial:
    result=fixed+trial;p=out/("worker_conflict_"+str(i)+".txt");p.write_text(canonical(result));r["verification"]=verify(p)
    if len(result)>len(best):best=result
  rows.append(r)
  (out/"report.json").write_text(json.dumps({"metadata":metadata,"completed":len(rows),"rows":rows,"best_size":len(best),"wall_seconds":time.perf_counter()-start},indent=2))
  if len(best)>226:break
 repo=os.environ["GITHUB_REPOSITORY"];branch="codegarden-radius34";head=os.environ["SOURCE_SHA"]
 def api(path,payload=None,method=None):
  args=["gh","api",path]
  if payload is not None:args+=["--method",method or "POST","--input","-"]
  p=subprocess.run(args,input=json.dumps(payload) if payload is not None else None,text=True,capture_output=True,check=True);return json.loads(p.stdout)
 assert api("repos/"+repo+"/git/ref/heads/"+branch)["object"]["sha"]==head
 parent=api("repos/"+repo+"/git/commits/"+head);entries=[{"path":str(p.relative_to(ROOT.parent)),"mode":"100644","type":"blob","content":p.read_text()} for p in list(out.glob("*.json"))+list(out.glob("*.txt"))]
 t=api("repos/"+repo+"/git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries});c=api("repos/"+repo+"/git/commits",{"parents":[head],"tree":t["sha"],"message":"Record conflict-driven larger repairs and independently checked matching-cover certificates"})
 api("repos/"+repo+"/git/refs/heads/"+branch,{"sha":c["sha"],"force":False},"PATCH");print("CONFLICT_REPAIRS "+json.dumps({"best":len(best),"completed":len(rows),"statuses":{s:sum(r["status"]==s for r in rows) for s in {r["status"] for r in rows}}}))
if __name__=="__main__":main()
