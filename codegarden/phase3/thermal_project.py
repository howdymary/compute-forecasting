"""Independently project archived thermal states; collision energy is not code cardinality."""
import argparse,collections,hashlib,importlib.util,itertools,json,os,pathlib,select,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,pool_hash
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--seed",type=int,required=True);a=ap.parse_args();out=ROOT/"artifacts/phase3/thermal_projection_001"/str(a.seed);out.mkdir(parents=True,exist_ok=True);check_integrity()
 spec=importlib.util.spec_from_file_location("protected_projection",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 rev=lambda w:int(format(w,"016b")[::-1],2)
 def orbit(C):
  C=tuple(sorted(C));R=tuple(sorted(rev(w) for w in C));return min(C,tuple(65535-w for w in reversed(C)),R,tuple(65535-w for w in reversed(R)))
 comp=ROOT/"artifacts/phase3/bundle_004/component5";cr=json.loads((comp/"report.json").read_text());known=set();knownsets=[]
 for r in cr["rows"]:
  C={int(w,2) for w in (comp/r["incumbent_file"]).read_text().split()};known.add(orbit(C))
  R={rev(w) for w in C};knownsets.extend([C,{65535-w for w in C},R,{65535-w for w in R}])
 report=json.loads((ROOT/"artifacts/phase3/tempering_flow_001"/str(a.seed)/"report.json").read_text());rows=[];novel={};hist=collections.Counter();energy_agrees=True
 for native in report["experiments"]:
  for i,state in enumerate(native["near_states"]):
   words=[format(w,"016b") for w in state];D.parse(words);owners={};edges=set();E=0
   for w in state:
    for d in D.descendants(format(w,"016b")):
     for v in owners.get(d,[]):edges.add(tuple(sorted((v,w))));E+=1
     owners.setdefault(d,[]).append(w)
   energy_agrees&=E==native["minimum_pair_energy"];vertices=sorted({v for edge in edges for v in edge});assert len(vertices)<=16
   covers=[]
   for k in range(len(vertices)+1):
    for cover in itertools.combinations(vertices,k):
     C=set(cover)
     if all(x in C or y in C for x,y in edges):covers.append(C)
    if covers:break
   hist[227-len(covers[0])]+=1;row={"mode":native["mode"],"near_state_index":i,"native_energy":native["minimum_pair_energy"],"protected_string_energy":E,
    "distinct_conflict_edges":sorted(edges),"minimum_cover_size":len(covers[0]),"largest_valid_projection":227-len(covers[0]),"minimum_covers":len(covers)}
   if len(covers[0])<=1:
    for cover in covers:
     code=set(state)-cover;key=orbit(code);p=out/("projection_"+native["mode"]+"_"+str(i)+"_"+str(len(novel))+".txt");p.write_text(canonical(code));accepted=verify(p)
     row.setdefault("accepted",[]).append({"witness":p.name,"verification":accepted,"known_orbit":key in known})
     if key not in known:
      distance=226-max(len(code&K) for K in knownsets)
      assert distance>=6,"Contradiction with prior radius-five component: independently audit before reusing its exclusions"
      novel.setdefault(key,{"code":sorted(code),"witness":p.name,"verification":accepted,"distance_from_known":distance})
   rows.append(row)
 assert energy_agrees,"Native energy differs from protected string calculation"
 ordered=sorted(novel.values(),key=lambda x:(-x["distance_from_known"],x["verification"]["reports"][0]["witness_sha256"]))[:4];trials=[];best=226
 def save():
  (out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"seed":a.seed,"projections":rows,"projection_histogram":dict(hist),
   "native_energy_independently_agrees":energy_agrees,"novel226_orbits_verified":len(novel),"novel_codes":list(novel.values()),
   "native_followups":trials,"best_verified":best,"scope":"Projection and bounded follow-ups only; no global optimality or record unless cardinality exceeds baseline."},indent=2))
 save()
 if ordered:
  server=subprocess.Popen([str(ROOT/".build/bundle"),"--server"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
  try:
   for i,item in enumerate(ordered):
    for k in [6,7]:
     C=item["code"];seed=a.seed*100+i*10+k;server.stdin.write("16 "+str(k)+" 30 100000000000 0 "+str(seed)+" "+str(len(C))+"\n"+canonical(C));server.stdin.flush()
     if not select.select([server.stdout],[],[],120)[0]:raise TimeoutError("native follow-up")
     trial=json.loads(server.stdout.readline());pool=trial.pop("candidate_pool");trial["pool_sha256"]=pool_hash(sorted(pool));trial["starting_sha256"]=item["verification"]["reports"][0]["witness_sha256"]
     if trial["found"]:
      candidate=set(C)-set(trial["removed"])|set(trial["added"]);p=out/("followup_"+str(i)+"_"+str(k)+".txt");p.write_text(canonical(candidate));trial["independent_verification"]=verify(p);best=max(best,len(candidate))
     trials.append(trial);save()
     if best>=227:break
    if best>=227:break
  finally:
   try:server.stdin.close();server.wait(timeout=15)
   except Exception:server.kill();server.wait(timeout=15)
 print("THERMAL_PROJECTION",json.dumps({"seed":a.seed,"histogram":dict(hist),"novel226":len(novel),"best":best}),flush=True)
if __name__=="__main__":main()
