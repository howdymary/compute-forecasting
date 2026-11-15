import hashlib,json,pathlib,sys,os
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from supervisor import verify
reports=[]
for path in sorted((ROOT/"artifacts").rglob("*.txt")):
    if path.name=="environment.txt":continue
    if path.name.startswith("arena_") or path.name.startswith("best_") or path.name.startswith("cp_") or path.name.startswith("modal_"):
        try:reports.append({"path":str(path),"verification":verify(path)})
        except Exception as e:reports.append({"path":str(path),"error":str(e)})
best=max((r for r in reports if "verification" in r),key=lambda r:r["verification"]["cardinality"])
result={"source_sha":os.getenv("GITHUB_SHA"),"best":best,"all_exports_verified":all("verification" in r for r in reports),"reports":reports}
(ROOT/"artifacts/final_verification.json").write_text(json.dumps(result,indent=2))
print("FINAL_INDEPENDENT "+json.dumps({"best":best["verification"]["cardinality"],"all_exports_verified":result["all_exports_verified"]}))
if not result["all_exports_verified"]:raise SystemExit(1)
