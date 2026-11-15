import json,os,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/"artifacts/phase3/orbit_lp_001";rows=[]
for i in range(2):
 p=OUT/str(i)/"report.json"
 if p.exists():
  r=json.loads(p.read_text());assert r["source_sha"]==os.environ["GITHUB_SHA"] and r["case"]==i;rows.append(r)
bounds=[];fresh=[]
for r in rows:
 case=r["case"];cert=OUT/str(case)/"dual_certificate.json"
 if cert.exists():
  checked=subprocess.run([sys.executable,"-B",str(ROOT/"phase3/verify_dual_certificate.py"),str(cert)],text=True,capture_output=True,check=True,timeout=300);v=json.loads(checked.stdout);assert v["valid_dual_certificate"] and v["certificate_sha256"]==r["dual_certificate_sha256"] and v["integer_upper_bound"]==r["independently_verified_integer_upper_bound"];(OUT/("fresh_dual_verification_"+str(case)+".json")).write_text(json.dumps(v,indent=2));bounds.append(v["integer_upper_bound"]);fresh.append(v)
report={"source_sha":os.environ["GITHUB_SHA"],"rows":rows,"fresh_verifier_only_receipts":fresh,"best_independently_verified_upper_bound":min(bounds) if bounds else None,"best_construction_verified":226,"target227_achieved":False,"global_record_claim":False,"scope":"Supporting global fractional analysis and exact upper certificates only. No code construction or improvement is inferred from an LP bound."}
(OUT/"summary.json").write_text(json.dumps(report,indent=2));print("ORBIT_LP_SUMMARY",json.dumps({"verified_upper_bound":report["best_independently_verified_upper_bound"],"best_construction":226,"target_achieved":False}),flush=True)
