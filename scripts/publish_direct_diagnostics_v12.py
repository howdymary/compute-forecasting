"""Add only versioned, allowlisted public diagnostic files with a nonforce update."""
import hashlib,json,os,pathlib,subprocess,time
repo=os.environ["GITHUB_REPOSITORY"];run=os.environ["GITHUB_RUN_ID"];root=pathlib.Path("artifacts/direct-v12-diagnostics")
def api(path,body=None,method=None):
    c=["gh","api","repos/"+repo+"/"+path]
    if method:c+=["-X",method]
    if body is not None:c+=["--input","-"]
    return json.loads(subprocess.check_output(c,input=json.dumps(body) if body is not None else None,text=True))
payload={}
for name in ("sampling.json","source-access.json"):
    file=root/name
    if not file.exists():continue
    raw=file.read_text()
    if "tinker://" in raw:raise ValueError("Private checkpoint path refused")
    payload["results/direct-v12/diagnostics/"+run+"/"+name]=raw
assert payload,"No retained diagnostic artifacts"
manifest={"workflow_run_id":run,"files":[{"path":p,"sha256":hashlib.sha256(v.encode()).hexdigest()} for p,v in sorted(payload.items())]}
payload["results/direct-v12/diagnostics/"+run+"/manifest.json"]=json.dumps(manifest,indent=2)+"\n"
for attempt in range(4):
    head=api("git/ref/heads/compute-observatory")["object"]["sha"];commit=api("git/commits/"+head)
    tree=api("git/trees",{"base_tree":commit["tree"]["sha"],"tree":[{"path":p,"type":"blob","mode":"100644","content":v} for p,v in payload.items()]},"POST")
    made=api("git/commits",{"parents":[head],"tree":tree["sha"],"message":"Publish bounded sampling and source-access diagnostics"},"POST")
    if api("git/ref/heads/compute-observatory")["object"]["sha"]!=head:continue
    try:api("git/refs/heads/compute-observatory",{"sha":made["sha"],"force":False},"PATCH")
    except subprocess.CalledProcessError:time.sleep(1);continue
    print("DIAGNOSTICS_COMMIT "+made["sha"]);break
else:raise RuntimeError("Shared branch advanced; publication refused")
