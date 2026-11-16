"""Publish immutable PNG validation evidence without changing application code."""
import base64,json,os,pathlib,subprocess,time
repo=os.environ["GITHUB_REPOSITORY"];root=pathlib.Path("artifacts/evidence-v14-ui");identifier=os.environ["GITHUB_RUN_ID"]
def api(path,body=None,method=None):
    cmd=["gh","api","repos/"+repo+"/"+path]
    if method:cmd+=["-X",method]
    if body is not None:cmd+=["--input","-"]
    return json.loads(subprocess.check_output(cmd,input=json.dumps(body) if body is not None else None,text=True))
files=[p for p in root.iterdir() if p.name.endswith(".png") or p.name=="validation.json"]
assert any(p.name=="validation.json" for p in files)
entries=[]
for p in files:
    raw=p.read_bytes()
    if p.suffix==".png":assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    b=api("git/blobs",{"content":base64.b64encode(raw).decode(),"encoding":"base64"},"POST")
    entries.append({"path":"results/evidence-v14/validation/"+identifier+"/"+p.name,"mode":"100644","type":"blob","sha":b["sha"]})
for attempt in range(4):
    head=api("git/ref/heads/compute-observatory")["object"]["sha"];commit=api("git/commits/"+head)
    tree=api("git/trees",{"base_tree":commit["tree"]["sha"],"tree":entries},"POST")
    made=api("git/commits",{"message":"Publish PNG-only matched forecasting validation","tree":tree["sha"],"parents":[head]},"POST")
    if api("git/ref/heads/compute-observatory")["object"]["sha"]!=head:continue
    try:api("git/refs/heads/compute-observatory",{"sha":made["sha"],"force":False},"PATCH")
    except subprocess.CalledProcessError:time.sleep(1);continue
    print("DIRECT_PNG_VALIDATION_COMMIT "+made["sha"]);break
else:raise RuntimeError("Shared branch advanced repeatedly")
