"""Publish only vetted public readiness reports using a fresh nonforce branch update."""
import hashlib,json,os,pathlib,subprocess,time
repo=os.environ["GITHUB_REPOSITORY"];run=os.environ["GITHUB_RUN_ID"];root=pathlib.Path("artifacts/evidence-v14-audit")
def api(path,body=None,method=None):
    c=["gh","api","repos/"+repo+"/"+path]
    if method:c+=["-X",method]
    if body is not None:c+=["--input","-"]
    return json.loads(subprocess.check_output(c,input=json.dumps(body) if body is not None else None,text=True))
prefix="results/evidence-v14/audits/"+run+"/";payload={}
for f in root.glob("*.json"):
    raw=f.read_text();assert "tinker://" not in raw
    payload[prefix+f.name]=raw
assert payload,"No retained audit"
manifest={"files":[{"path":k[len(prefix):],"sha256":hashlib.sha256(v.encode()).hexdigest()} for k,v in payload.items()]}
payload[prefix+"manifest.json"]=json.dumps(manifest,indent=2)+"\n"
for attempt in range(4):
    head=api("git/ref/heads/compute-observatory")["object"]["sha"];commit=api("git/commits/"+head)
    tree=api("git/trees",{"base_tree":commit["tree"]["sha"],"tree":[{"path":p,"mode":"100644","type":"blob","content":v} for p,v in payload.items()]},"POST")
    made=api("git/commits",{"parents":[head],"tree":tree["sha"],"message":"Publish evidence-study source and capacity audit"},"POST")
    if api("git/ref/heads/compute-observatory")["object"]["sha"]!=head:continue
    try:api("git/refs/heads/compute-observatory",{"sha":made["sha"],"force":False},"PATCH")
    except subprocess.CalledProcessError:time.sleep(1);continue
    print("EVIDENCE_AUDIT_COMMIT "+made["sha"]);break
else:raise RuntimeError("Concurrent head update; publication refused")
