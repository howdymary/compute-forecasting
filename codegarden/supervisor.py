"""Protected export acceptance. The proposer supplies bounded JSON, never verifier code."""
import hashlib,importlib.util,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parent
def check_integrity():
    manifest=json.loads((ROOT/"protected/manifest.json").read_text())
    for rel,expected in manifest["files"].items():
        actual=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()
        if actual!=expected:raise RuntimeError("Protected verifier changed: "+rel)
    return manifest
def verify(path):
    check_integrity();reports=[]
    for name in ["verify_descendants.py","verify_lcs.py"]:
        p=subprocess.run([sys.executable,"-B",str(ROOT/"protected"/name),str(path)],capture_output=True,text=True)
        report=json.loads(p.stdout)
        if p.returncode or not report["valid"]:raise ValueError(report)
        reports.append(report)
    if reports[0]["witness_sha256"]!=reports[1]["witness_sha256"]:raise RuntimeError("Independent verifiers disagree")
    return {"accepted":True,"cardinality":reports[0]["cardinality"],"reports":reports}
if __name__=="__main__":print(json.dumps(verify(sys.argv[1]),indent=2))
