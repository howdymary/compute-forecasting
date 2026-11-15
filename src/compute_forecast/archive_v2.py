"""Durable, allowlisted derived research artifacts; no raw pack or private model paths."""
from __future__ import annotations
import hashlib,io,json,os,zipfile
from pathlib import Path
from urllib.request import urlopen
import modal
from .campaign_v2 import now,write
from .starter_probe import volume,PACK_SHA256
app=modal.App("compute-forecast-v2-archive")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
ALLOWED={"grid.json","policy-report.json","checkpoints.json","selection-freeze.json","updates.json","training-examples.json","rl-trajectories.json","reward-audit.json","trained-evaluation.json","starting-evaluation.json","sft-parent-evaluation.json","no-observation.json","with-criticism.json","with-evidence.json","controls.json","starting-development.json","rl-parent-freeze.json","evidence.json"}
def validate_public(value):
    if isinstance(value,dict):
        if {str(k).lower() for k in value}&{"state_path","sampler_path","weights_access_token","api_key","access_token","refresh_token","authorization"}:raise ValueError("Private field in derived bundle")
        for v in value.values():validate_public(v)
    elif isinstance(value,list):
        for v in value:validate_public(v)
    elif isinstance(value,str) and "tinker://" in value:raise ValueError("Private checkpoint URI in derived bundle")
@app.function(image=image,cpu=.25,memory=512,timeout=150,volumes={"/data":volume,"/public":public})
def publish(data,manifest):
    if len(data)>20_000_000 or hashlib.sha256(data).hexdigest()!=manifest["sha256"]:raise ValueError("Invalid derived archive")
    run=manifest["release_run_id"]
    if not run.isdigit():raise ValueError("Invalid archive release ID")
    private_root=Path("/data/campaign-v2/releases")/run;private_root.mkdir(parents=True,exist_ok=True)
    (private_root/"research-bundle.zip").write_bytes(data);write(private_root/"manifest.json",manifest);volume.commit()
    public.reload();root=Path("/public/experimental-v2/archives")/run;root.mkdir(parents=True,exist_ok=True)
    (root/"research-bundle.zip").write_bytes(data);write(root/"manifest.json",manifest)
    write(Path("/public/experimental-v2/archive-manifest.json"),manifest);public.commit()
    return {"sha256":manifest["sha256"],"bytes":len(data),"members":len(manifest["members"]),"release_run_id":run}
@app.local_entrypoint()
def main(inputs:str="inputs"):
    root=Path(inputs);members={}
    for path in root.rglob("*.json"):
        if path.is_symlink():raise ValueError("Unexpected symbolic artifact")
        if path.name in ALLOWED or path.name.startswith("development-"):
            value=json.loads(path.read_text());validate_public(value)
            members["runs/"+path.relative_to(root).as_posix()]=path.read_bytes()
    analysis=Path("artifacts/v2-analysis/analysis.json")
    if analysis.is_file():validate_public(json.loads(analysis.read_text()));members["analysis/analysis.json"]=analysis.read_bytes()
    for filename in ("campaign-v2.json","campaign-v2-rl-gate-amendment.json","campaign-v2-additional-controls.json"):
        path=Path("configs")/filename;value=json.loads(path.read_text());validate_public(value);members["protocol/"+filename]=path.read_bytes()
    url="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
    snapshot=urlopen(url+"/api/experimental",timeout=90).read();value=json.loads(snapshot);validate_public(value)
    if len(value["policy_reports"])!=9:raise ValueError("Complete campaign required before archiving")
    members["public-snapshot.json"]=snapshot
    forecast=urlopen(url+"/files/forecasts.csv",timeout=90).read()
    if hashlib.sha256(forecast).hexdigest()!="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80":raise ValueError("Official forecast changed")
    members["archived-official-forecasts.csv"]=forecast
    members["README.txt"]=("Compute Forecast v2 derived research release\n\nRaw offer tables, the private pack, restricted source excerpts, API credentials and private Tinker checkpoint paths are excluded.\nThe official CSV is the unchanged archived November6 submission.\nNumerical reproduction requires authorized pack access. Tinker weights remain in the owner's account. Training is stochastic; the saved action/outcome traces support exact recorded replays.\nThe evaluation reuses previously inspected dates and is not an untouched or prospective test.\nSource: https://github.com/howdymary/compute-forecasting/tree/"+os.environ["GITHUB_SHA"]+"\n").encode()
    index={name:{"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()} for name,data in sorted(members.items())}
    manifest={"schema_version":2,"released_at":now(),"source_sha":os.environ["GITHUB_SHA"],"release_run_id":os.environ["GITHUB_RUN_ID"],"dataset_sha256":PACK_SHA256,"scope":"Derived scores, configurations, training examples and recorded action/outcome traces; raw inputs and private provider resources excluded","members":index}
    members["member-manifest.json"]=(json.dumps(manifest,sort_keys=True,indent=2)+"\n").encode()
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(members.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,11,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
    data=buffer.getvalue();manifest.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),url=url+"/experimental/downloads/"+manifest["release_run_id"]+".zip",hash_basis="sha256 is over exact ZIP bytes; member hashes are over exact uncompressed member bytes")
    receipt=publish.remote(data,manifest);write(Path("artifacts/v2-archive/manifest.json"),manifest)
    print("V2_ARCHIVE:"+json.dumps(receipt),flush=True)
