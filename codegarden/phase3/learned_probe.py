"""Certified descendant inclusion prunes outside candidates without changing strict feasibility."""
import argparse,hashlib,importlib.util,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify,check_integrity
from search import canonical,pool_hash
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",required=True);a=ap.parse_args();k=int(a.mode.removeprefix("base").removeprefix("learned"));reduced=True;learned=a.mode.startswith("learned")
 out=ROOT/"artifacts/phase3/learned_native_001"/a.mode;out.mkdir(parents=True,exist_ok=True);check_integrity()
 spec=importlib.util.spec_from_file_location("protected_dom",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 certificates=json.loads((ROOT/"artifacts/phase3/soft_global_001/dominance.json").read_text())["certificates"]
 for c in certificates:
  assert set(D.descendants(format(c["replacement"],"016b")))<=set(D.descendants(format(c["removed"],"016b")))
 mask=ROOT/".build/dominated.txt";mask.write_text("\n".join(str(c["removed"]) for c in certificates)+"\n")
 base=ROOT/"artifacts/phase3/learned_native_001/preflight/baseline.txt";accepted=verify(base)
 info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());assert accepted["reports"][0]["witness_sha256"]==info["root_hash"],"New incumbent requires fresh certificates"
 current={int(w,2) for w in base.read_text().split()};proofs={r["incumbent_witness_sha256"]:r for r in info["report"]["rows"]};clauses=[];audits=[]
 def canon(C):return "\n".join(format(w,"016b") for w in sorted(C))+"\n"
 for C0 in info["codes"]:
  C=set(C0);h=hashlib.sha256(canon(C).encode()).hexdigest();r=proofs[h];assert r["complete"] and not r["found"] and r["k"]==7
  added=C-current;removed=current-C;assert len(C)==len(current) and len(added)==len(removed)
  if not added or k-len(added)>7:continue
  occupied={d:w for w in current for d in D.descendants(format(w,"016b"))};blocks={occupied[d] for w in added for d in D.descendants(format(w,"016b")) if d in occupied}
  assert blocks==removed
  clauses.append(sorted(added));audits.append({"neighbor_hash":h,"added":sorted(added),"removed":sorted(removed),"radius":7,"proof_source":info["proof_source"],"pool_hash":r["canonical_pool_sha256"],"complete":True})
 clausepath=ROOT/".build/learned.txt";clausepath.write_text("".join(str(len(g))+" "+" ".join(map(str,g))+"\n" for g in clauses))
 (out/"certificates.json").write_text(json.dumps({"root_hash":info["root_hash"],"k":k,"groups":audits,"lemma":"If T contains balanced U, the improving code differs from the neutral code C-Ublock+U by at most k-|U| removals. A completed no-improvement radius covering that distance forbids T."},indent=2))
 env=dict(os.environ,CODEGARDEN_LEARNED_NOGOODS=str(clausepath) if learned else "",CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER=str(mask) if reduced else "")
 result=subprocess.run([str(ROOT/".build/bundle"),"16",str(k),"450","1000000000000","0"],input=base.read_text(),text=True,capture_output=True,check=True,timeout=530,env=env)
 r=json.loads(result.stdout);pool=r.pop("candidate_pool");r.update(source_sha=os.environ["GITHUB_SHA"],mode=a.mode,starting_verification=accepted,canonical_pool_sha256=pool_hash(sorted(pool)),
  learned_enabled=learned,certified_groups=len(clauses),dominance_filter_enabled=reduced,independent_string_certificates_checked=len(certificates),filter_sha256=hashlib.sha256(mask.read_bytes()).hexdigest(),
  lemma="Replace any dominated outside word v in an improving code by retained u with D2(u) subset D2(v). If u belonged to the incumbent this restores one incumbent word; otherwise the removal count is unchanged. Validity and cardinality are preserved, so strict improvements with at most k removals remain detectable.",
  scope="Strict cardinality improvements only. This reduction is not claimed to preserve the full labeled neutral graph.")
 if r["found"]:
  C={int(w,2) for w in base.read_text().split()};C=C-set(r["removed"])|set(r["added"]);p=out/"candidate.txt";p.write_text(canonical(C));r["independent_verification"]=verify(p)
 (out/"report.json").write_text(json.dumps(r,indent=2));print("LEARNED_NATIVE",json.dumps({"mode":a.mode,"complete":r["complete"],"found":r["found"],"cpu":r["cpu_seconds"],"pool":len(pool),"nodes":r["nodes"],"score":r.get("independent_verification",{}).get("cardinality",226)}),flush=True)
if __name__=="__main__":main()
