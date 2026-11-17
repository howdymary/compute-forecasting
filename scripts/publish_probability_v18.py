"""Publish new-study artifacts using fresh-head nonforce updates."""
import base64,concurrent.futures,hashlib,json,os,pathlib,subprocess,time
repo=os.environ["GITHUB_REPOSITORY"];run=os.environ["GITHUB_RUN_ID"]
source=pathlib.Path(os.environ.get("V18_PUBLIC_ROOT","artifacts/probability-v18-audit"));kind=os.environ.get("V18_PUBLIC_KIND","audits")
def api(path,body=None,method=None):
    args=["gh","api","repos/"+repo+"/"+path]
    if method:args+=["-X",method]
    if body is not None:args+=["--input","-"]
    return json.loads(subprocess.check_output(args,input=json.dumps(body) if body is not None else None,text=True))
payloads={"results/probability-v18/"+kind+"/"+run+"/"+f.name:f.read_bytes() for f in source.iterdir() if f.is_file()}
if not payloads:raise ValueError("No completed public artifacts")
manifest={"study_id":"direct-probability-v18","source_sha":os.environ["GITHUB_SHA"],"files":[{"path":p.rsplit("/",1)[-1],"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()} for p,raw in sorted(payloads.items())]}
payloads["results/probability-v18/"+kind+"/"+run+"/manifest.json"]=(json.dumps(manifest,indent=2)+"\n").encode()
if kind=="runs" and (source/"report.json").exists():
    raw=(source/"report.json").read_bytes()
    payloads["results/probability-v18/latest.json"]=(json.dumps({"study_id":"direct-probability-v18","run_id":run,"report_path":"results/probability-v18/runs/"+run+"/report.json","report_sha256":hashlib.sha256(raw).hexdigest()},indent=2)+"\n").encode()
    if (source/"findings.md").exists():payloads["docs/probability-v18-findings.md"]=(source/"findings.md").read_bytes()
def blob(item):
    path,raw=item;r=api("git/blobs",{"content":base64.b64encode(raw).decode(),"encoding":"base64"},"POST")
    return {"path":path,"mode":"100644","type":"blob","sha":r["sha"]}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:entries=list(pool.map(blob,payloads.items()))
for attempt in range(5):
    head=api("git/ref/heads/compute-observatory")["object"]["sha"];parent=api("git/commits/"+head)
    state=api("git/trees/"+parent["tree"]["sha"]+"?recursive=1");assert not state.get("truncated")
    exists={r["path"]:r["sha"] for r in state["tree"] if r["type"]=="blob"}
    for e in entries:
        if ("/runs/" in e["path"] or "/audits/" in e["path"]) and e["path"] in exists:assert exists[e["path"]]==e["sha"],"Immutable study artifact collision"
    tree=api("git/trees",{"base_tree":parent["tree"]["sha"],"tree":entries},"POST")
    made=api("git/commits",{"message":"Publish direct probability forecasting "+kind,"tree":tree["sha"],"parents":[head]},"POST")
    if api("git/ref/heads/compute-observatory")["object"]["sha"]!=head:continue
    try:api("git/refs/heads/compute-observatory",{"sha":made["sha"],"force":False},"PATCH")
    except subprocess.CalledProcessError:time.sleep(1);continue
    print("PUBLICATION_COMMIT "+made["sha"]);break
else:raise RuntimeError("Branch advanced repeatedly; publication refused")
