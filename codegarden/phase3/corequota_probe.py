"""Use source-audited core exclusions to avoid known226 attraction basins."""
import argparse,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.revisit_frontiers import orbit
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;check_integrity();out=ROOT/"artifacts/phase3/corequota_001"/str(case);out.mkdir(parents=True,exist_ok=True)
 info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());core=set.intersection(*(set(C) for C in info["codes"]));rev=lambda w:int(format(w,"016b")[::-1],2);images=[sorted(core),sorted(65535^w for w in core),sorted(rev(w) for w in core),sorted(65535^rev(w) for w in core)];cp=out/"cores.txt";cp.write_text("".join("216 "+" ".join(map(str,C))+"\n" for C in images))
 known=[sorted(T(C)) for C in info["codes"] for T in [lambda c:c,lambda c:[65535^w for w in c],lambda c:[rev(w) for w in c],lambda c:[65535^rev(w) for w in c]]];kp=out/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,C))+"\n" for C in known))
 target=226 if case<4 or case>=6 else 227;quota=210 if case<6 else 206;mode="fixed" if case%2==0 else "adaptive";seed=1421001+case//2
 if case<2 or case>=4:C=info["codes"][0]
 else:
  plan=json.loads((ROOT/"artifacts/phase3/revisit_frontiers_001/plan.json").read_text());choices=[r["words"] for r in plan["cases"] if len(r["words"])==225];C=min(choices,key=lambda c:len(set(c)&core))
 start=out/"starting.txt";start.write_text(canonical(C));starting=verify(start);starting_hash=digest_words(C)
 r=json.loads(subprocess.run([str(ROOT/".build/corequota"),"600",str(seed),mode,str(out/"checkpoint.txt"),str(cp),str(quota),str(target),str(kp)],input=canonical(C),text=True,capture_output=True,check=True,timeout=900).stdout);(out/"native.json").write_text(json.dumps(r,indent=2))
 candidates=r["novel226_candidates"][:]
 if r["minimum_pair_conflicts"]==0:candidates.append(r["best"])
 best=226;novel=[];steps=[]
 for i,C in enumerate(candidates):
  p=out/("candidate_"+str(i)+".txt");p.write_text(canonical(C));v=verify(p);best=max(best,v["cardinality"])
  if len(C)==226 and tuple(sorted(C)) in {tuple(c) for c in known}:continue
  novel.append({"path":p.name,"verification":v,"core_counts":[len(set(C)&set(F)) for F in images]})
  if best>=227:break
  for k,seconds in [(6,5),(7,20),(8,60),(9,120),(10,180)]:
   z=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+100,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0")).stdout);z["pool_sha256"]=pool_hash(z.pop("candidate_pool"));z.pop("neighbors");z["starting_sha256"]=digest_words(C)
   if z["found"]:
    C=sorted(set(C)-set(z["removed"])|set(z["added"]));p=out/("augmented_"+str(i)+".txt");p.write_text(canonical(C));z["verification"]=verify(p);best=max(best,len(C))
   steps.append(z)
   if best>=227:break
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"mode":mode,"seed":seed,"target":target,"core_quota":quota,"starting_verification":starting,"starting_sha256":starting_hash,"best_verified":best,"novel":novel,"polish":steps,"minimum_pair_conflicts":r["minimum_pair_conflicts"],"cpu_seconds":r["cpu_seconds"],"iterations":r["iterations"],"scope":"Quota210 follows conditional local exclusions; quota206 cases are deliberately stronger heuristic diversification, not safe global cuts.600nativeCPU each. Pair-energy states with positive score remain invalid. No absence claim from bounded heuristics; no matched total-CPU claim when polish differs."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("COREQUOTA",json.dumps({"case":case,"best":best,"novel":len(novel),"energy":r["minimum_pair_conflicts"],"cpu":r["cpu_seconds"]}),flush=True)
if __name__=="__main__":main()
