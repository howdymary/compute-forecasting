"""Exact bipartite-union recombination of the saved independently verified portfolio."""
import argparse,hashlib,importlib.util,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from search import canonical,digest_words,pool_hash
from supervisor import verify,check_integrity
from phase3.revisit_frontiers import orbit
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;check_integrity();out=ROOT/"artifacts/phase3/fusion3_001"/str(case);out.mkdir(parents=True,exist_ok=True)
 data=json.loads((ROOT/"artifacts/phase3/revisit_frontiers_001/plan.json").read_text());info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());long=json.loads((ROOT/"phase3/recombine_long_inputs.json").read_text());base=[C for C in info["codes"]]+[r["words"] for r in data["cases"]]+long["parents"];rev=lambda w:int(format(w,"016b")[::-1],2);codes={}
 for C in base:
  O=[C,[65535^w for w in C],[rev(w) for w in C],[65535^rev(w) for w in C]][case]
  codes[tuple(sorted(O))]=sorted(O)
 # Keep all four root symmetries in each disjoint orientation shard.
 for C in info["codes"]:
  for O in [C,[65535^w for w in C],[rev(w) for w in C],[65535^rev(w) for w in C]]:codes[tuple(sorted(O))]=sorted(O)
 parents=sorted(codes.values(),key=lambda C:(-len(C),digest_words(C)));spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 for C in parents:D.verify([format(w,"016b") for w in C],16)
 inputtext="".join(str(len(C))+" "+" ".join(map(str,C))+"\n" for C in parents);(out/"parents.txt").write_text(inputtext);manifest={"source_sha":os.environ["GITHUB_SHA"],"case":case,"parents_sha256":hashlib.sha256(inputtext.encode()).hexdigest(),"parent_hashes":[digest_words(C) for C in parents],"parent_count":len(parents),"long_input_sha256":hashlib.sha256((ROOT/"phase3/recombine_long_inputs.json").read_bytes()).hexdigest(),"source_manifest_sha256":hashlib.sha256((ROOT/"artifacts/phase3/revisit_frontiers_001/plan.json").read_bytes()).hexdigest(),"scope":"Explicit sampled three-parent unions in this orientation shard; not all triples. All parent validity independently checked by literal descendants; positives use both protected verifiers."}
 (out/"manifest.json").write_text(json.dumps(manifest,indent=2));r=json.loads(subprocess.run([str(ROOT/".build/fusion3"),"300",str(1331001+case),str(case),str(out/"checkpoint.txt")],input=inputtext,text=True,capture_output=True,check=True,timeout=420).stdout);
 for item in r["sampled_repairs"]:item["fixed_sha256"]=digest_words(item["fixed"]);item["candidate_pool_sha256"]=pool_hash(item["pool"]);item["proof_artifact"]=None
 (out/"native.json").write_text(json.dumps(r,indent=2));winner=out/"best.txt";winner.write_text(canonical(r["winner"]));best=verify(winner);known={orbit(C) for C in info["codes"]};novel=[];steps=[]
 for i,C in enumerate(r["novel226_candidates"]):
  p=out/("novel_"+str(i)+".txt");p.write_text(canonical(C));v=verify(p)
  if orbit(C) in known:continue
  novel.append({"witness":p.name,"verification":v})
  if len(novel)>8 or best["cardinality"]>=227:continue
  for k,seconds in [(6,5),(7,10),(8,30),(9,60)]:
   a=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16",str(k),str(seconds),"1000000000000","0"],input=canonical(C),text=True,capture_output=True,check=True,timeout=seconds+80,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER="",CODEGARDEN_LEARNED_NOGOODS="")).stdout);a["pool_sha256"]=pool_hash(a.pop("candidate_pool"));a.pop("neighbors");a["starting_hash"]=digest_words(C)
   if a["found"]:
    C=sorted(set(C)-set(a["removed"])|set(a["added"]));p=out/("augmented_"+str(i)+".txt");p.write_text(canonical(C));a["verification"]=verify(p)
    if len(C)>best["cardinality"]:best=a["verification"]
   steps.append(a)
   if best["cardinality"]>=227:break
 report={"source_sha":os.environ["GITHUB_SHA"],"manifest":manifest,"native_status":{k:v for k,v in r.items() if k not in ["winner","novel226_candidates","sampled_repairs"]},"best_verification":best,"novel226":novel,"polish":steps,"best_verified":best["cardinality"],"scope":"Individual repair completeness is local to its fixed common code and complete parent-union pool. Clique repair checked on64 independent brute-force examples; the random triple batch is not exhaustive. Any new code passes literal descendants and pairwise LCS."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("FUSION3",json.dumps({"case":case,"best":best["cardinality"],"novel226":len(novel),"pairs":r["trials"],"scope":"Sampled triple unions; not exhaustive all triples"}),flush=True)
if __name__=="__main__":main()
