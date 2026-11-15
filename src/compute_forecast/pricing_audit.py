"""Inspect only metadata from the existing private November 6 export."""
import csv,hashlib,json,os
from pathlib import Path
import modal
from .starter_probe import image,volume,PACK_SHA256
app=modal.App("compute-forecast-pricing-metadata")
FIELDS=("series_id","table","source_id","instrument_class","statistic","gpu_model","pricing_tier","instance_type","az_global_id","product_description","source_url","licence_id")
@app.function(image=image,cpu=1,memory=2048,timeout=300,volumes={"/data":volume})
def inspect():
    root=Path("/data/submissions/af851700dad544dcbfe1328465fc14a7")
    archive=Path("/data/pacific/pack.zip")
    with archive.open("rb") as f:
        if hashlib.file_digest(f,"sha256").hexdigest()!=PACK_SHA256:raise ValueError("Archive mismatch")
    with (root/"catalog.csv").open() as f:catalog=list(csv.DictReader(f))
    rows=[{k:r.get(k,"") for k in FIELDS} for r in catalog if r["tier"]=="headline"]
    if len(rows)!=37:raise ValueError("Wrong headline catalog")
    return {"schema_version":1,"dataset_sha256":PACK_SHA256,"origin_date":"2026-11-06","series":rows,"history_publication_permitted":False,"history_reason":"Compilation permission remains pending owner confirmation and upstream terms apply. No historical price values are published by this adapter.","source_catalog_sha256":hashlib.sha256((root/"catalog.csv").read_bytes()).hexdigest(),"scope":"Metadata only; no historical prices, offers or future outcomes read","code_sha":os.environ.get("GITHUB_SHA")}
@app.local_entrypoint()
def main():
    r=inspect.remote();r["code_sha"]=os.environ["GITHUB_SHA"]
    p=Path("artifacts/pricing-metadata.json");p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(r,indent=2)+"\n")
    print(json.dumps(r,indent=2))
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("# Verified pricing metadata\n\n~~~json\n"+json.dumps(r,indent=2)+"\n~~~\n")
