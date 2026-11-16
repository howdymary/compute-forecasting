"""Nonforce publication of new direct-study artifacts; preserves shared branch work."""
import base64,hashlib,json,os,pathlib,subprocess,time
repo=os.environ["GITHUB_REPOSITORY"];run=os.environ.get("TRAINING_RUN_ID","43952200479");root=pathlib.Path("artifacts/direct-v12-public")
def api(path,body=None,method=None):
    command=["gh","api","repos/"+repo+"/"+path]
    if method:command+=["-X",method]
    if body is not None:command+=["--input","-"]
    return json.loads(subprocess.check_output(command,input=json.dumps(body) if body is not None else None,text=True))
payloads={"results/direct-v12/runs/"+run+"/"+str(p.relative_to(root)):p.read_text() for p in root.rglob("*") if p.is_file()}
report=json.loads((root/"report.json").read_text())
payloads["results/direct-v12/latest.json"]=json.dumps({"study_id":"direct-forecast-v12","run_id":run,"status":report["status"],"report_path":"results/direct-v12/runs/"+run+"/report.json","report_sha256":hashlib.sha256((root/"report.json").read_bytes()).hexdigest()},indent=2)+"\n"
payloads["results/direct-v12/README.md"]="# Direct GPU-price forecasts v12\n\n[Current report](runs/"+run+"/report.json) · [Findings](../../docs/direct-v12-findings.md) · [Methods](../../docs/direct-forecast-v12.md) · [Protocol](../../configs/direct-forecast-v12.json)\n\nThe model learns observed future log-price vectors through Tinker SFT. Quantiles derive from 64 fixed-budget samples. The retrospective study does not establish prospective accuracy or supplementary-signal value.\n\nApproved Pacific component derivatives only, with source metadata and CC BY 4.0 attribution. Raw offers, marketplace-ask histories and private model resources are excluded.\n"
payloads["docs/direct-v12-findings.md"]=(root/"findings.md").read_text()
for attempt in range(4):
    branch=api("git/ref/heads/compute-observatory");head=branch["object"]["sha"];commit=api("git/commits/"+head)
    # Existing versioned results are immutable; publication may only add missing bytes.
    for path,content in list(payloads.items()):
        if "/runs/" not in path:continue
        try:old=api("contents/"+path+"?ref="+head)
        except subprocess.CalledProcessError:continue
        previous=base64.b64decode(old["content"]).decode()
        if previous!=content:raise RuntimeError("Immutable result conflict: "+path)
    entries=[{"path":p,"mode":"100644","type":"blob","content":s} for p,s in payloads.items()]
    index=api("contents/docs/README.md?ref="+head)
    text=base64.b64decode(index["content"]).decode()
    link="\n## Direct price model v12\n\n[Methods](direct-forecast-v12.md) · [Measured findings](direct-v12-findings.md) · [Versioned artifacts](../results/direct-v12/README.md). This separately trains forecast outputs, preserving the earlier selector studies.\n"
    if "[Methods](direct-forecast-v12.md)" not in text:entries.append({"path":"docs/README.md","mode":"100644","type":"blob","content":text+link})
    tree=api("git/trees",{"base_tree":commit["tree"]["sha"],"tree":entries},"POST")
    made=api("git/commits",{"message":"Publish reproducible direct GPU forecasting study v12","tree":tree["sha"],"parents":[head]},"POST")
    if api("git/ref/heads/compute-observatory")["object"]["sha"]!=head:continue
    try:api("git/refs/heads/compute-observatory",{"sha":made["sha"],"force":False},"PATCH")
    except subprocess.CalledProcessError:
        time.sleep(1);continue
    print("DIRECT_PUBLICATION_COMMIT "+made["sha"]);break
else:raise RuntimeError("Branch advanced repeatedly; publication refused")
