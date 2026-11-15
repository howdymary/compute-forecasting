"""Verify each distinct exported byte sequence in fresh protected subprocesses."""
import json,pathlib,sys,os
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
reports=[];cache={}
for path in sorted((ROOT/"artifacts").rglob("*.txt")):
 if path.name=="environment.txt":continue
 if path.name.startswith(("arena_","best_","cp_","modal_","worker_")):
  raw=path.read_bytes();entry={"path":str(path)}
  if raw in cache:
   previous=cache[raw];entry.update({k:v for k,v in previous.items() if k in ["verification","error"]})
   entry["reused_identical_bytes_from"]=previous["path"]
  else:
   try:entry["verification"]=verify(path)
   except Exception as e:entry["error"]=str(e)
   cache[raw]=entry
  reports.append(entry)
best=max((r for r in reports if "verification" in r),key=lambda r:r["verification"]["cardinality"])
result={"source_sha":os.getenv("GITHUB_SHA"),"best":best,"all_exports_verified":all("verification" in r for r in reports),
 "exported_files":len(reports),"distinct_byte_sequences_verified":len(cache),
 "reuse_rule":"Only byte-for-byte identical exported data shares verification; search scores and model claims are never trusted.","reports":reports}
(ROOT/"artifacts/final_verification.json").write_text(json.dumps(result,indent=2))
print("FINAL_INDEPENDENT "+json.dumps({"best":best["verification"]["cardinality"],"all_exports_verified":result["all_exports_verified"],
 "exported_files":len(reports),"distinct_byte_sequences":len(cache)}))
if not result["all_exports_verified"]:raise SystemExit(1)
