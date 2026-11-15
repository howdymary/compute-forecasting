"""Bounded exact ruin-and-recreate from two verified length16 families."""
import argparse,hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical,pool_hash,digest_words
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;out=ROOT/"artifacts/phase3/exact_lns_001"/str(case);out.mkdir(parents=True,exist_ok=True)
 size=226 if case<4 else 225;baseline=next((ROOT/"artifacts/baselines").glob("arena_"+str(size)+"_*.txt"));accepted=verify(baseline);mode="random" if case%2==0 else "opportunity";seed=1251001+case//2
 r=json.loads(subprocess.run([str(ROOT/".build/exact_lns"),"180",str(seed),mode,str(out/"checkpoint.txt")],input=baseline.read_text(),text=True,capture_output=True,check=True,timeout=290).stdout)
 p=out/"best.txt";p.write_text(canonical(r["best"]));v=verify(p);archives=[]
 known=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());rev=lambda w:int(format(w,"016b")[::-1],2);hashes={digest_words(O) for C in known["codes"] for O in [C,[65535^w for w in C],[rev(w) for w in C],[65535^rev(w) for w in C]]}
 for i,C in enumerate(r["archive"]):
  if len(C)<226:continue
  q=out/("archive_"+str(i)+".txt");q.write_text(canonical(C));checked=verify(q);archives.append({"file":q.name,"verification":checked,"novel_to_known226_orbits":checked["reports"][0]["witness_sha256"] not in hashes})
 for row in r["sampled_scoped_negatives"]:
  row["incumbent_sha256"]=digest_words(row["incumbent"]);row["fixed_sha256"]=digest_words(row["fixed"]);row["candidate_pool_sha256"]=pool_hash(row["pool"])
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"mode":mode,"seed":seed,"starting_verification":accepted,"native":r,"verification":v,"archive_verifications":archives,"best_verified":max(226,v["cardinality"]),
  "scope":"Each exact target-negative concerns its logged fixed code, full compatible pool and target. Pool-cap skips and timeouts give no infeasibility result. New cardinality is accepted only by both protected verifiers."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("EXACT_LNS",json.dumps({"case":case,"best":report["best_verified"],"iterations":r["iterations"],"exact_negatives":r["complete_target_negatives"],"timeouts":r["timeouts"],"novel226":sum(x["novel_to_known226_orbits"] for x in archives)}),flush=True)
if __name__=="__main__":main()
