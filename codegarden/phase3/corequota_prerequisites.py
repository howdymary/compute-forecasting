"""Audit source-pinned local completion receipts before conditional core cuts."""
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import check_integrity
check_integrity();receipts=[]
for prefix,cases,source in [("core3_repair_001",4,"294ecfa8f9b70b6356f862d84ce30c7c605a5c6d"),("core4_repair_001",4,"201693e19aaf506da5c7ec94ef31c35bb5c2db5c"),("core5_repair_001",16,"5a8a73aa81dab29045c4e2a9cc0502e6c3e879f7")]:
 for i in range(cases):
  p=ROOT/"artifacts/phase3"/prefix/str(i);r=json.loads((p/"report.json").read_text());n=r["native"];expected=source if prefix!="core5_repair_001" or i!=9 else "18c345022edf0cd43b68435c557216fc07af7e6f"
  assert r["source_sha"]==expected and n["planned"]==n["processed"]==n["primary_complete_no227"] and n["primary_timeouts"]==n["pool_cap_skips"]==0
  codes="".join(x.read_text() for x in sorted(p.glob("primary_statuses_*.txt")));assert len(codes)==n["processed"] and set(codes)=={"I"}
  receipts.append({"prefix":prefix,"case":i,"source":expected,"queries":len(codes),"report_sha256":hashlib.sha256((p/"report.json").read_bytes()).hexdigest(),"primary_statuses_sha256":hashlib.sha256(codes.encode()).hexdigest()})
allcore=json.loads((ROOT/"artifacts/phase3/audits_001/core_all/report.json").read_text());assert allcore["complete"] and allcore["fixed_core_optimum"]==226 and allcore["count"]==38
out=ROOT/"artifacts/phase3/corequota_001";out.mkdir(parents=True,exist_ok=True)
(out/"prerequisites.json").write_text(json.dumps({"passed":True,"receipts":receipts,"cut":"For exact227 target, <=210 selected words in each symmetry image of shared216-core, conditional on completed native local computations, rank4/5 reinsertion support lemma and exhaustive support generators. Complement and reversal commute bijectively with deleting two positions, so transfer the same exclusion to each image.","assurance":"Receipt/coverage audit with small exhaustive kernel tests; not a formal independent absence certificate.","new226_target":"The same cuts exclude the known38x4 component; known-full-core maxima and secondary negative queries establish the conditional distinction."},indent=2));print("COREQUOTA_PREREQUISITES",len(receipts),flush=True)
