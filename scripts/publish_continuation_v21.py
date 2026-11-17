"""Publish new-study artifacts using fresh-head nonforce updates."""
import base64,concurrent.futures,hashlib,json,os,pathlib,subprocess,time
repo=os.environ["GITHUB_REPOSITORY"];run=os.environ["GITHUB_RUN_ID"]
if int(os.environ.get("GITHUB_RUN_ATTEMPT","1"))>1:run+="-attempt-"+os.environ["GITHUB_RUN_ATTEMPT"]
source=pathlib.Path(os.environ.get("V21_PUBLIC_ROOT","artifacts/ce-continuation-v21-audit"));kind=os.environ.get("V21_PUBLIC_KIND","audits")
def api(path,body=None,method=None):
    args=["gh","api","repos/"+repo+"/"+path]
    if method:args+=["-X",method]
    if body is not None:args+=["--input","-"]
    return json.loads(subprocess.check_output(args,input=json.dumps(body) if body is not None else None,text=True))
payloads={"results/ce-continuation-v21/"+kind+"/"+run+"/"+str(f.relative_to(source)):f.read_bytes() for f in source.rglob("*") if f.is_file()}
if not payloads:raise ValueError("No completed public artifacts")
manifest={"study_id":"ce-continuation-v21","source_sha":os.environ.get("PUBLICATION_SOURCE_SHA",os.environ.get("VALIDATION_SOURCE_SHA",os.environ["GITHUB_SHA"])),"trigger_sha":os.environ["GITHUB_SHA"],"files":[{"path":p.split("/"+kind+"/"+run+"/",1)[1],"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()} for p,raw in sorted(payloads.items())]}
payloads["results/ce-continuation-v21/"+kind+"/"+run+"/manifest.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
if kind=="progress" and (source/"report.json").exists():
    raw=(source/"report.json").read_bytes()
    payloads["results/ce-continuation-v21/progress/latest.json"]=(json.dumps({"study_id":"ce-continuation-v21-progress","report_path":"results/ce-continuation-v21/progress/"+run+"/report.json","report_sha256":hashlib.sha256(raw).hexdigest()},indent=2)+"\n").encode()
if kind=="future" and (source/"index.json").exists():
    raw=(source/"index.json").read_bytes()
    payloads["results/ce-continuation-v21/future/latest.json"]=(json.dumps({"study_id":"ce-continuation-v21-prospective","report_path":"results/ce-continuation-v21/future/"+run+"/index.json","report_sha256":hashlib.sha256(raw).hexdigest()},indent=2)+"\n").encode()
if kind=="runs" and (source/"report.json").exists():
    raw=(source/"report.json").read_bytes()
    payloads["results/ce-continuation-v21/latest.json"]=(json.dumps({"study_id":"ce-continuation-v21","run_id":run,"report_path":"results/ce-continuation-v21/runs/"+run+"/report.json","report_sha256":hashlib.sha256(raw).hexdigest()},indent=2)+"\n").encode()
    if (source/"findings.md").exists():payloads["docs/ce-continuation-v21-findings.md"]=(source/"findings.md").read_bytes()
def blob(item):
    path,raw=item;r=api("git/blobs",{"content":base64.b64encode(raw).decode(),"encoding":"base64"},"POST")
    return {"path":path,"mode":"100644","type":"blob","sha":r["sha"]}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:entries=list(pool.map(blob,payloads.items()))
for attempt in range(5):
    head=api("git/ref/heads/compute-observatory")["object"]["sha"];parent=api("git/commits/"+head)
    state=api("git/trees/"+parent["tree"]["sha"]+"?recursive=1");assert not state.get("truncated")
    exists={r["path"]:r["sha"] for r in state["tree"] if r["type"]=="blob"}
    for e in entries:
        if e["path"].startswith("results/ce-continuation-v21/"+kind+"/"+run+"/") and e["path"] in exists:assert exists[e["path"]]==e["sha"],"Immutable study artifact collision"
    tree=api("git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries},"POST")
    made=api("git/commits",{"message":"Publish market-state forecasting "+kind,"tree":tree["sha"],"parents":[head]},"POST")
    if api("git/ref/heads/compute-observatory")["object"]["sha"]!=head:continue
    try:api("git/refs/heads/compute-observatory",{"sha":made["sha"],"force":False},"PATCH")
    except subprocess.CalledProcessError:time.sleep(1);continue
    print("PUBLICATION_COMMIT "+made["sha"])
    if os.environ.get("GITHUB_ENV"):
        with open(os.environ["GITHUB_ENV"],"a") as f:f.write("V21_PUBLICATION_COMMIT="+made["sha"]+"\n")
    break
else:raise RuntimeError("Branch advanced repeatedly; publication refused")
