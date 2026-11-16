"""Nonforce publication of new direct-study artifacts; preserves shared branch work."""
import base64,hashlib,json,os,pathlib,subprocess,time
repo=os.environ["GITHUB_REPOSITORY"];run=os.environ["PUBLICATION_ID"];root=pathlib.Path("artifacts/evidence-v14-public")
def api(path,body=None,method=None):
    command=["gh","api","repos/"+repo+"/"+path]
    if method:command+=["-X",method]
    if body is not None:command+=["--input","-"]
    return json.loads(subprocess.check_output(command,input=json.dumps(body) if body is not None else None,text=True))
payloads={"results/evidence-v14/runs/"+run+"/"+str(p.relative_to(root)):p.read_text() for p in root.rglob("*") if p.is_file()}
report=json.loads((root/"report.json").read_text())
payloads["results/evidence-v14/latest.json"]=json.dumps({"study_id":"direct-evidence-v14","run_id":run,"status":report["status"],"report_path":"results/evidence-v14/runs/"+run+"/report.json","report_sha256":hashlib.sha256((root/"report.json").read_bytes()).hexdigest()},indent=2)+"\n"
payloads["results/evidence-v14/README.md"]="# Matched price and BLS forecasts\n\n[Current report](runs/"+run+"/report.json) · [Findings](../../docs/evidence-v14-findings.md) · [Methods](../../docs/evidence-v14.md) · [Protocol](../../configs/direct-evidence-v14-final.json)\n\nFresh matched Tinker LoRA models predict GPU-price returns with price history alone or original BLS release-vintage features. Quantiles derive from64 unseeded stochastic samples. Results remain retrospective; news and infrastructure are excluded.\n\nApproved Pacific component derivatives only, with source metadata and CC BY 4.0 attribution. Raw offers, marketplace-ask histories and private model resources are excluded.\n"
payloads["docs/evidence-v14-findings.md"]=(root/"findings.md").read_text()
for attempt in range(4):
    branch=api("git/ref/heads/compute-observatory");head=branch["object"]["sha"];commit=api("git/commits/"+head)
    # Existing versioned results are immutable; publication may only add missing bytes.
    for path,content in list(payloads.items()):
        if "/runs/" not in path:continue
        try:old=api("contents/"+path+"?ref="+head)
        except subprocess.CalledProcessError:continue
        previous=base64.b64decode(old["content"]).decode()
        if previous!=content:raise RuntimeError("Immutable result conflict: "+path)
    entries=[]
    for path,content in payloads.items():
        if len(content.encode())>150000:
            blob=api("git/blobs",{"content":content,"encoding":"utf-8"},"POST")
            entries.append({"path":path,"mode":"100644","type":"blob","sha":blob["sha"]})
        else:entries.append({"path":path,"mode":"100644","type":"blob","content":content})
    index=api("contents/docs/README.md?ref="+head)
    text=base64.b64decode(index["content"]).decode()
    link="\n## Matched price and BLS models\n\n[Methods](evidence-v14.md) · [Measured findings](evidence-v14-findings.md) · [Versioned artifacts](../results/evidence-v14/README.md). This matched two-arm study preserves the earlier direct and selector studies.\n"
    if "[Methods](evidence-v14.md)" not in text:entries.append({"path":"docs/README.md","mode":"100644","type":"blob","content":text+link})
    tree=api("git/trees",{"base_tree":commit["tree"]["sha"],"tree":entries},"POST")
    made=api("git/commits",{"message":"Publish matched price and BLS forecasting study","tree":tree["sha"],"parents":[head]},"POST")
    if api("git/ref/heads/compute-observatory")["object"]["sha"]!=head:continue
    try:api("git/refs/heads/compute-observatory",{"sha":made["sha"],"force":False},"PATCH")
    except subprocess.CalledProcessError:
        time.sleep(1);continue
    print("DIRECT_PUBLICATION_COMMIT "+made["sha"]);break
else:raise RuntimeError("Branch advanced repeatedly; publication refused")
