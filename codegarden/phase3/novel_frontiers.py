"""Search fresh225 frontiers while continuing beyond explicitly known226 arrays."""
import argparse,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.revisit_frontiers import orbit
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;check_integrity();out=ROOT/"artifacts/phase3/novel_frontiers_001"/str(case);out.mkdir(parents=True,exist_ok=True)
 plan=json.loads((ROOT/"artifacts/phase3/quota_frontiers_001/plan.json").read_text())
 if case>=len(plan["selected"]):(out/"report.json").write_text(json.dumps({"case":case,"status":"no_selected_frontier","best_verified":226}));return
 C=plan["selected"][case]["words"];starting=C[:];p=out/"starting.txt";p.write_text(canonical(C));accepted=verify(p);info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());rev=lambda w:int(format(w,"016b")[::-1],2);known=[sorted(O) for c in info["codes"] for O in [c,[65535^w for w in c],[rev(w) for w in c],[65535^rev(w) for w in c]]];kp=out/"known226.txt";kp.write_text("".join("226 "+" ".join(map(str,c))+"\n" for c in known))
 for K in known:
  if len(K)!=226:raise ValueError("known goal cardinality")
 best=226;steps=[];todo=[(6,30),(7,60),(8,120),(9,180),(10,210)];novel=None
 while todo:
  k,seconds=todo.pop(0);filtered=len(C)==225;env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0",CODEGARDEN_KNOWN_GOAL_CODES=str(kp) if filtered else "")
  r=json.loads(subprocess.run([str(ROOT/".build/bundle_novel"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+100,env=env).stdout);r["pool_sha256"]=pool_hash(r.pop("candidate_pool"));r.pop("neighbors");r["incumbent_sha256"]=digest_words(C);r["goal_filter_enabled"]=filtered
  if r["found"]:
   C=sorted(set(C)-set(r["removed"])|set(r["added"]));p=out/("candidate_"+str(len(steps))+".txt");p.write_text(canonical(C));r["verification"]=verify(p);best=max(best,len(C))
   if len(C)==226:
    assert tuple(C) not in {tuple(c) for c in known},"Known goal filter failed";novel={"witness":p.name,"verification":r["verification"]};todo=[(6,5),(7,20),(8,60),(9,120),(10,180)]
  steps.append(r)
  if best>=227:break
 final=out/"ending.txt";final.write_text(canonical(C));ending=verify(final);report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"starting_sha256":digest_words(starting),"starting_verification":accepted,"novel226":novel,"ending_verification":ending,"best_verified":best,"steps":steps,"scope":"Goal-filtered connected bundles and saturated pools only. A completed filtered search does not prove that all novel codes within this removal radius are absent: disconnected combinations may be missed. Known226 exclusions change search goals only; protected validity is unchanged. Unfiltered strict augmentation follows any independently verified novel226."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("NOVEL_FRONTIER",json.dumps({"case":case,"ending":len(C),"best":best,"novel226":novel is not None,"statuses":[{"k":r["k"],"found":r["found"],"complete":r["complete"],"known_hits":r.get("filtered_known_goals")} for r in steps]}),flush=True)
 if best>=227:print("VERIFIED_227_WITNESS",final.read_text(),flush=True)
if __name__=="__main__":main()
