"""Resume only the still-open suffixes of the prior radius-ten canonical root partitions."""
import argparse,hashlib,importlib.util,json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
from search import canonical
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--case",type=int,required=True);case=ap.parse_args().case;out=ROOT/"artifacts/phase3/resume10_001"/str(case);out.mkdir(parents=True,exist_ok=True);plan=json.loads((ROOT/"phase3/resume10_plan.json").read_text());info=json.loads((ROOT/"phase3/learned_certificates_input.json").read_text());baseline=next((ROOT/"artifacts/baselines").glob("arena_226_*.txt"));checked=verify(baseline);C={int(w,2) for w in baseline.read_text().split()}
 spec=importlib.util.spec_from_file_location("protected",ROOT/"protected/verify_descendants.py");D=importlib.util.module_from_spec(spec);spec.loader.exec_module(D)
 # Recheck every safe dominance replacement directly with string descendants.
 dom=json.loads((ROOT/"artifacts/phase3/soft_global_001/dominance.json").read_text())
 certs=dom["certificates"]
 mask=[]
 for row in certs:
  v,u=row["removed"],row["replacement"];assert v!=u and set(D.descendants(format(u,"016b")))<=set(D.descendants(format(v,"016b")));mask.append(v)
 dp=out/"dominated.txt";dp.write_text("\n".join(map(str,mask)))
 proofs={r["incumbent_witness_sha256"]:r for r in info["report"]["rows"]};occupied={d:w for w in C for d in D.descendants(format(w,"016b"))};clauses=[]
 for other in info["codes"]:
  U=set(other)-C;R=C-set(other);h=hashlib.sha256(canonical(other).encode()).hexdigest();r=proofs[h]
  assert r["complete"] and not r["found"] and r["k"]==7
  if not U or 10-len(U)>7:continue
  assert len(U)==len(R) and {occupied[d] for w in U for d in D.descendants(format(w,"016b")) if d in occupied}==R;clauses.append(sorted(U))
 ng=out/"learned.txt";ng.write_text("".join(str(len(g))+" "+" ".join(map(str,g))+"\n" for g in clauses));begin=plan["root_starts"][case%8]
 r=json.loads(subprocess.run([str(ROOT/".build/bundle"),"16","10",str(plan["cpu_seconds"]),"1000000000000","0"],input=baseline.read_text(),text=True,capture_output=True,check=True,timeout=plan["cpu_seconds"]+160,env=dict(os.environ,CODEGARDEN_ROOT_SHARDS="32",CODEGARDEN_ROOT_SHARD=str(case),CODEGARDEN_ROOT_BEGIN=str(begin),CODEGARDEN_BLOCK_ORDER="1",CODEGARDEN_DOMINANCE_FILTER=str(dp),CODEGARDEN_LEARNED_NOGOODS=str(ng))).stdout)
 pool=r.pop("candidate_pool");ph=hashlib.sha256(b"".join(w.to_bytes(4,"big") for w in pool)).hexdigest();assert ph==plan["previous_pool_hash"],"Cannot join old and new coverage with changed ordered candidate pool"
 if r["found"]:C=C-set(r["removed"])|set(r["added"])
 p=out/"best.txt";p.write_text(canonical(C));accepted=verify(p)
 report={"source_sha":os.environ["GITHUB_SHA"],"case":case,"previous_source":plan["previous_source"],"previous_run":plan["previous_run"],"root_begin":begin,"root_shard":case,"root_shards":32,"candidate_pool_sha256":ph,"starting_verification":checked,"native":r,"verification":accepted,"best_verified":accepted["cardinality"],"scope":"Only the logged minimum-root residue and suffix. The prior interrupted root is replayed, not assumed complete. All suffix candidates retained. Both old and new complete coverage audits required for radius-ten exhaustion."}
 (out/"report.json").write_text(json.dumps(report,indent=2));print("RESUME10",json.dumps({k:report[k] for k in ["case","root_begin","best_verified"]}),json.dumps({k:r[k] for k in ["complete","found","completed_roots","active_root","cpu_seconds"]}),flush=True)
if __name__=="__main__":main()
