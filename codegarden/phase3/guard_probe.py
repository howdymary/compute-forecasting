"""Equivalent blocker guard benchmark and larger whole-root repairs."""
import argparse,hashlib,importlib.util,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import pool_hash,canonical
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mode",required=True);mode=ap.parse_args().mode;out=ROOT/"artifacts/phase3/guard_001"/mode;out.mkdir(parents=True,exist_ok=True)
 base=ROOT/"artifacts/phase3/guard_001/preflight/baseline.txt";v=verify(base)
 spec=importlib.util.spec_from_file_location("protected_d2",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 cert=json.loads((ROOT/"artifacts/phase3/soft_global_001/dominance.json").read_text())["certificates"]
 for r in cert:assert set(D.descendants(format(r["replacement"],"016b")))<=set(D.descendants(format(r["removed"],"016b")))
 mask=ROOT/".build/guard_dom.txt";mask.write_text("\n".join(str(c["removed"]) for c in cert)+"\n")
 env=dict(os.environ,CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER=str(mask),CODEGARDEN_LEARNED_NOGOODS="",CODEGARDEN_ROOT_SHARDS="1",CODEGARDEN_ROOT_SHARD="0")
 rows=[]
 for binary,k,seconds in ([("guard_old",8,450),("bundle",8,450)] if mode=="benchmark8" else [("bundle",int(mode.removeprefix("strict")),600)]):
  r=json.loads(subprocess.run([str(ROOT/".build"/binary),"16",str(k),str(seconds),"1000000000000","0"],input=base.read_text(),text=True,capture_output=True,check=True,timeout=seconds+90,env=env).stdout)
  r["pool_order_sha256"]=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in r.pop("candidate_pool"))).hexdigest()
  r["binary"]=binary
  if r["found"]:
   C={int(w,2) for w in base.read_text().split()};C=C-set(r["removed"])|set(r["added"]);p=out/("candidate_"+binary+".txt");p.write_text(canonical(C));r["verification"]=verify(p)
  rows.append(r)
 if mode=="benchmark8":
  assert all(r["complete"] and not r["found"] for r in rows)
  for key in ["nodes","closed_blocker_sets","cache_hits","cache_evictions","candidate_count","pool_order_sha256"]:assert rows[0][key]==rows[1][key],key
 report={"source_sha":os.environ["GITHUB_SHA"],"mode":mode,"starting_verification":v,"rows":rows,"best_verified":max([226]+[r.get("verification",{}).get("cardinality",0) for r in rows]),
  "scope":"The early union-size guard is semantically identical. Sequential old/new benchmark on one runner; one case only, no broad speed claim. Larger timeouts remain open."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("GUARD",json.dumps({"mode":mode,"best":report["best_verified"],"runs":[{"binary":r["binary"],"cpu":r["cpu_seconds"],"complete":r["complete"],"nodes":r["nodes"]} for r in rows]}),flush=True)
if __name__=="__main__":main()
