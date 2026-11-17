"""Durable publication evidence; use verified Sigstore timestamps, never predicate dates."""
import hashlib,json,os,pathlib,subprocess,sys
from datetime import datetime,timezone
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False)+"\n")
def build(root):
    commitments=sorted(root.glob("commitment-*.json"));files=commitments or [root/"index.json"]
    manifest={"study_id":"market-state-v19-prospective","kind":"forecast_publication" if commitments else "readiness_no_forecasts","execution_source_sha":os.environ.get("PUBLICATION_SOURCE_SHA",os.environ.get("GITHUB_SHA")),"workflow_trigger_sha":os.environ.get("GITHUB_SHA"),"files":[{"name":f.name,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()} for f in files]}
    write(root/"commitment-manifest.json",manifest)
def verify(root,repo=None):
    repo=repo or os.environ["GITHUB_REPOSITORY"]
    command=["gh","attestation","verify",str(root/"commitment-manifest.json"),"--bundle",str(root/"attestation.bundle.json"),"--repo",repo,"--source-ref","refs/heads/compute-observatory","--signer-workflow",repo+"/.github/workflows/future-market-v19.yml","--format","json"]
    result=json.loads(subprocess.check_output(command,text=True))
    times=[]
    for r in result:
        for t in r["verificationResult"].get("verifiedTimestamps",[]):
            value=t["timestamp"]
            at=datetime.fromisoformat(value.replace("Z","+00:00"))
            assert at.tzinfo is not None;times.append(at.astimezone(timezone.utc))
    assert times,"No cryptographically verified publication timestamp"
    manifest=json.loads((root/"commitment-manifest.json").read_bytes());receipts={}
    for entry in manifest["files"]:
        path=root/entry["name"];assert path.name==entry["name"] and path.parent==root
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry["sha256"]
        if not entry["name"].startswith("commitment-"):continue
        from compute_forecast.probability_v18 import digest
        value=json.loads(path.read_bytes());receipts[value["origin"]]={"created_at":min(times).isoformat(),"commitment_sha256":digest(value),"manifest_sha256":hashlib.sha256((root/"commitment-manifest.json").read_bytes()).hexdigest(),"proof":"Verified signer/ref, artifact digest and signed transparency timestamp"}
    write(root/"attestation-verification.json",{"verified":result,"publication_timestamps":[t.isoformat() for t in sorted(times)],"forecast_receipts":receipts,"kind":manifest["kind"]})
    if receipts:
        index_path=root/"index.json";index=json.loads(index_path.read_bytes());index["verified_publication_receipts"]=receipts
        for case in index.get("forecast_cases",[]):case["publication_receipt"]=receipts.get(case["origin"],case.get("publication_receipt"))
        write(index_path,index)
    return receipts
if __name__=="__main__":
    operation,root=sys.argv[1],pathlib.Path(sys.argv[2])
    if operation=="build":build(root)
    elif operation=="verify":verify(root)
    else:raise ValueError("Unknown operation")
