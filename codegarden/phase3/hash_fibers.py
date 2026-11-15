"""Finite-length experiment inspired by random linear hashing of substring-count parities.
This is an exploratory adaptation, not an implementation of the asymptotic theorem.
Each hash class still requires exact deletion packing and independent witness checks.
"""
import argparse,collections,hashlib,json,os,pathlib,random,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.revisit_frontiers import orbit
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;check_integrity();out=ROOT/"artifacts/phase3/hash_fibers_001"/str(case);out.mkdir(parents=True,exist_ok=True)
 k,r=[(5,5),(6,5),(7,6),(8,6)][case];seed=1351001+case;rng=random.Random(seed);coeff=[rng.randrange(1<<r) for _ in range(1<<k)];groups=[[] for _ in range(1<<r)];mask=(1<<k)-1
 def label(w):
  value=0
  for p in range(17-k):value^=coeff[(w>>p)&mask]
  return value
 for w in range(65536):groups[label(w)].append(w)
 tests=[]
 for w in rng.sample(range(65536),64):
  bits=format(w,"016b");counts=collections.Counter(bits[i:i+k] for i in range(17-k));value=0
  for substring,count in counts.items():
   if count%2:value^=coeff[int(substring,2)]
  assert value==label(w);tests.append({"word":w,"label":value})
 selected=sorted(range(len(groups)),key=lambda q:(-len(groups[q]),q))[:8]
 if 0 not in selected and groups[0]:selected[-1]=0
 plan={"source_sha":os.environ["GITHUB_SHA"],"case":case,"seed":seed,"substring_length":k,"hash_bits":r,"coefficients":coeff,"class_sizes":[len(g) for g in groups],"selected_classes":selected,"hash_crosschecks":tests,
  "source":"https://arxiv.org/html/2609.19493v2","method":"Use random binary linear maps of substring-count parities to generate candidate pools. Pack each pool with the native sparse kernel, then release the pool restriction for full-universe search.",
  "attribution":"Inspired by the paper's hashing representation; does not reproduce its uniqueness restriction, odd-cycle argument or asymptotic construction. No deletion property is assumed from equal hash labels."}
 (out/"plan.json").write_text(json.dumps(plan,indent=2));info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());known={orbit(C) for C in info["codes"]};rows=[];best=226;polished=set()
 def native(C,seconds,policy,runseed,labelname,poolpath=""):
  checkpoint=out/(labelname+"_checkpoint.txt");t=time.monotonic();z=json.loads(subprocess.run([str(ROOT/".build/hash_pool"),str(seconds),str(runseed),policy,str(checkpoint),"227"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+80,env=dict(os.environ,CODEGARDEN_POOL=poolpath)).stdout)
  C=sorted(z["best"]);p=out/(labelname+".txt");p.write_text(canonical(C));v=verify(p);entry={"label":labelname,"policy":policy,"seed":runseed,"native":z,"verification":v,"witness":p.name,"wall_including_verification":time.monotonic()-t};return C,entry
 for index,label_id in enumerate(selected):
  pool=groups[label_id];poolpath=out/("class_"+str(label_id)+".txt");poolpath.write_text("\n".join(map(str,pool)));C,warm=native([pool[0]],3,"adaptive",seed+index*1009,"fiber_"+str(label_id),str(poolpath));assert all(label(w)==label_id for w in C);warm["candidate_pool_sha256"]=pool_hash(pool)
  for policy in ["fixed","adaptive"]:
   B,entry=native(C,30,policy,seed+index*1009+200003,"global_"+str(label_id)+"_"+policy);best=max(best,len(B));steps=[]
   h=digest_words(B)
   if len(B)==226 and orbit(B) not in known and h not in polished and len(polished)<2:
    polished.add(h)
    for radius,seconds in [(7,20),(8,60),(9,120)]:
     a=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(radius),str(seconds),"1000000000000","0"],input=canonical(B),text=True,capture_output=True,check=True,timeout=seconds+90,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="")).stdout);a["pool_sha256"]=pool_hash(a.pop("candidate_pool"));a.pop("neighbors");a["starting_hash"]=digest_words(B)
     if a["found"]:
      B=sorted(set(B)-set(a["removed"])|set(a["added"]));p=out/("augmented_"+str(label_id)+"_"+policy+".txt");p.write_text(canonical(B));a["verification"]=verify(p);best=max(best,len(B))
     steps.append(a)
     if best>=227:break
   rows.append({"class":label_id,"warm":warm,"full_universe":entry,"polish":steps,"ending_size":len(B)})
   (out/"report.json").write_text(json.dumps({"source_sha":os.environ["GITHUB_SHA"],"case":case,"plan":plan,"rows":rows,"best_verified":best,"novel226_polished":len(polished),"scope":"Eight selected hash fibers with bounded heuristic packing, followed by matched fixed/adaptive full-universe searches. No exhaustive or global-optimality conclusion; positive hash membership never substitutes for independent validity."},indent=2))
   print("HASH_FIBER",json.dumps({"case":case,"class":label_id,"warm_size":len(C),"policy":policy,"ending":len(B),"global_best_verified":best}),flush=True)
   if best>=227:return
if __name__=="__main__":main()
