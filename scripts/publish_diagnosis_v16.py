"""Publish diagnostic-only artifacts with fresh-head nonforce updates."""
import base64,concurrent.futures,hashlib,json,os,pathlib,subprocess,time
repo=os.environ["GITHUB_REPOSITORY"];run=os.environ["GITHUB_RUN_ID"];root=pathlib.Path("artifacts/diagnosis-v16")
def api(path,body=None,method=None):
    args=["gh","api","repos/"+repo+"/"+path]
    if method:args+=["-X",method]
    if body is not None:args+=["--input","-"]
    return json.loads(subprocess.check_output(args,input=json.dumps(body) if body is not None else None,text=True))
payloads={"results/direct-v16/runs/"+run+"/"+f.name:f.read_bytes() for f in root.iterdir() if f.is_file()}
raw=(root/"diagnosis.json").read_bytes()
payloads["results/direct-v16/latest.json"]=(json.dumps({"study_id":"direct-v14-diagnosis-v16","run_id":run,"report_path":"results/direct-v16/runs/"+run+"/diagnosis.json","report_sha256":hashlib.sha256(raw).hexdigest()},indent=2)+"\n").encode()
payloads["results/direct-v16/README.md"]=("# Direct-forecasting diagnosis\n\n[Current diagnosis](runs/"+run+"/diagnosis.json) · [Numerical findings](../../docs/direct-v16-diagnostic-findings.md) · [Manifest](runs/"+run+"/manifest.json)\n\nPost-hoc reconstruction from saved samples, not another training or forecasting campaign. All training, development selections and future protocols remain unchanged.\n").encode()
payloads["docs/direct-v16-diagnostic-findings.md"]=(root/"findings.md").read_bytes()
def blob(item):
    path,raw=item
    result=api("git/blobs",{"content":base64.b64encode(raw).decode(),"encoding":"base64"},"POST")
    return {"path":path,"mode":"100644","type":"blob","sha":result["sha"]}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:entries=list(pool.map(blob,payloads.items()))
for attempt in range(5):
    head=api("git/ref/heads/compute-observatory")["object"]["sha"];commit=api("git/commits/"+head)
    tree_state=api("git/trees/"+commit["tree"]["sha"]+"?recursive=1");assert not tree_state.get("truncated")
    existing={r["path"]:r["sha"] for r in tree_state["tree"] if r["type"]=="blob"}
    for e in entries:
        if "/runs/" in e["path"] and e["path"] in existing:assert existing[e["path"]]==e["sha"],"Immutable diagnostic collision"
    tree=api("git/trees",{"base_tree":commit["tree"]["sha"],"tree":entries},"POST")
    made=api("git/commits",{"message":"Publish saved-sample forecasting diagnosis","tree":tree["sha"],"parents":[head]},"POST")
    if api("git/ref/heads/compute-observatory")["object"]["sha"]!=head:continue
    try:api("git/refs/heads/compute-observatory",{"sha":made["sha"],"force":False},"PATCH")
    except subprocess.CalledProcessError:time.sleep(1);continue
    print("DIAGNOSIS_PUBLICATION_COMMIT "+made["sha"]);break
else:raise RuntimeError("Branch advanced repeatedly; diagnostic publication refused")
