"""Exact connected exchanges; compare ordering under fixed CPU budgets."""
import argparse,hashlib,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",required=True);a=ap.parse_args();k=int(a.mode[-1]);ordered=a.mode.startswith("ordered")
 out=ROOT/"artifacts/phase3/connected_001"/a.mode;out.mkdir(parents=True,exist_ok=True)
 base=ROOT/"artifacts/phase3/connected_001/preflight/baseline.txt";accepted=verify(base)
 p=subprocess.run([str(ROOT/".build/bundle"),"16",str(k),"450","1000000000000","0"],input=base.read_text(),text=True,capture_output=True,check=True,timeout=530,env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1" if ordered else "0"))
 r=json.loads(p.stdout);pool=r.pop("candidate_pool");r.update(source_sha=os.environ["GITHUB_SHA"],starting_verification=accepted,ordering="descending blocker count then descendant size" if ordered else "ascending binary integer",
  candidate_order_sha256=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest(),
  canonical_candidate_pool_sha256=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in sorted(pool))).hexdigest(),
  proof_lemma="A deficient compatible bundle has a deficient blocker-connected component. A connected bundle has a unique parent obtained by deleting its largest non-root non-articulation vertex.")
 if r["found"]:
  C={int(w,2) for w in base.read_text().split()};C=C-set(r["removed"])|set(r["added"]);q=out/"candidate.txt";q.write_text("\n".join(format(w,"016b") for w in sorted(C))+"\n");r["independent_verification"]=verify(q)
 (out/"report.json").write_text(json.dumps(r,indent=2));print("CONNECTED_FINAL",json.dumps({"mode":a.mode,"found":r["found"],"complete":r["complete"],"cpu":r["cpu_seconds"],"nodes":r["nodes"],"score":r.get("independent_verification",{}).get("cardinality",226)}),flush=True)
if __name__=="__main__":main()
