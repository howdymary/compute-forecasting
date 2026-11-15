"""Certified descendant inclusion prunes outside candidates without changing strict feasibility."""
import argparse,hashlib,importlib.util,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,pool_hash
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",required=True);a=ap.parse_args();k=int(a.mode.removeprefix("full").removeprefix("reduced"));reduced=a.mode.startswith("reduced")
 out=ROOT/"artifacts/phase3/dominance_native_002"/a.mode;out.mkdir(parents=True,exist_ok=True);check_integrity()
 spec=importlib.util.spec_from_file_location("protected_dom",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 certificates=json.loads((ROOT/"artifacts/phase3/soft_global_001/dominance.json").read_text())["certificates"]
 for c in certificates:
  assert set(D.descendants(format(c["replacement"],"016b")))<=set(D.descendants(format(c["removed"],"016b")))
 mask=ROOT/".build/dominated.txt";mask.write_text("\n".join(str(c["removed"]) for c in certificates)+"\n")
 base=ROOT/"artifacts/phase3/dominance_native_002/preflight/baseline.txt";accepted=verify(base);env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER=str(mask) if reduced else "")
 result=subprocess.run([str(ROOT/".build/bundle"),"16",str(k),"450","1000000000000","0"],input=base.read_text(),text=True,capture_output=True,check=True,timeout=530,env=env)
 r=json.loads(result.stdout);pool=r.pop("candidate_pool");r.update(source_sha=os.environ["GITHUB_SHA"],mode=a.mode,starting_verification=accepted,canonical_pool_sha256=pool_hash(sorted(pool)),
  dominance_filter_enabled=reduced,independent_string_certificates_checked=len(certificates),filter_sha256=hashlib.sha256(mask.read_bytes()).hexdigest(),
  lemma="Replace any dominated outside word v in an improving code by retained u with D2(u) subset D2(v). If u belonged to the incumbent this restores one incumbent word; otherwise the removal count is unchanged. Validity and cardinality are preserved, so strict improvements with at most k removals remain detectable.",
  scope="Strict cardinality improvements only. This reduction is not claimed to preserve the full labeled neutral graph.")
 if r["found"]:
  C={int(w,2) for w in base.read_text().split()};C=C-set(r["removed"])|set(r["added"]);p=out/"candidate.txt";p.write_text(canonical(C));r["independent_verification"]=verify(p)
 (out/"report.json").write_text(json.dumps(r,indent=2));print("DOMINANCE_NATIVE",json.dumps({"mode":a.mode,"complete":r["complete"],"found":r["found"],"cpu":r["cpu_seconds"],"pool":len(pool),"nodes":r["nodes"],"score":r.get("independent_verification",{}).get("cardinality",226)}),flush=True)
if __name__=="__main__":main()
