"""Read-only confirmation that the complete Pacific pack remains accessible."""
import hashlib,json,os
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone
import modal
from .starter_probe import PACK_SHA256,PACK_NAME,verify_manifest
app=modal.App("compute-forecast-data-access-audit-v4")
volume=modal.Volume.from_name("compute-forecast-data",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
@app.function(image=image,cpu=1,memory=512,timeout=300,volumes={"/data":volume})
def audit():
    root=Path("/data/pacific")/PACK_NAME;archive=Path("/data/pacific/pack.zip")
    with archive.open("rb") as f:sha=hashlib.file_digest(f,"sha256").hexdigest()
    if sha!=PACK_SHA256:raise ValueError("Pacific archive changed")
    count=verify_manifest(root)
    if count!=672:raise ValueError("Pacific pack incomplete")
    members=[p for p in root.rglob("*") if p.is_file()]
    headings=Counter(str(p.relative_to(root)).split("/")[0] for p in members)
    docs={}
    for name in ("README.md","DATA.md","LICENSE.md"):
        p=root/name
        if p.is_file():docs[name]={"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size}
    return {"schema_version":4,"status":"verified_full_pack_access","checked_at":datetime.now(timezone.utc).isoformat(),"pack_name":PACK_NAME,"archive_sha256":sha,"archive_bytes":archive.stat().st_size,"verified_manifest_entries":count,"top_level_inventory":dict(headings),"documentation":docs,"new_forecasts":0,"new_training_updates":0,"outcomes_loaded":False,"note":"Read-only archive and member checksum verification; no numerical data rows or protected future outcomes loaded"}
@app.local_entrypoint()
def main():
    r=audit.remote();out=Path("artifacts");out.mkdir(exist_ok=True);(out/"pacific-access-v4.json").write_text(json.dumps(r,indent=2));print("PACIFIC_ACCESS_V4:"+json.dumps(r),flush=True)
