"""Publish only the new pricing payload; preserve frozen forecasts and all existing assets."""
import hashlib,json,os,urllib.request
from pathlib import Path
import modal
from .pricing_contract import build,validate,FORECAST_SHA
app=modal.App("compute-forecast-pricing-publication")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
URL="https://howdymary--compute-forecast-observatory-web.us-east.modal.run"
@app.function(image=image,cpu=.25,memory=256,timeout=90,volumes={"/public":public})
def publish(payload):
    validate(payload)
    root=Path("/public/release")
    if hashlib.sha256((root/"forecasts.csv").read_bytes()).hexdigest()!=FORECAST_SHA:raise ValueError("Existing official forecast changed")
    encoded=json.dumps(payload,indent=2,allow_nan=False).encode()
    pending=root/"pricing.pending";pending.write_bytes(encoded);pending.replace(root/"pricing.json")
    public.commit()
    return {"pricing_sha256":hashlib.sha256(encoded).hexdigest(),"bytes":len(encoded),"code_sha":payload["code_sha"],"forecast_csv_sha256":FORECAST_SHA,"files_modified":["pricing.json"]}
@app.local_entrypoint()
def main(metadata_file:str="inputs/metadata/pricing-metadata.json"):
    metadata=json.loads(Path(metadata_file).read_text())
    def get(path):return urllib.request.urlopen(URL+path,timeout=90).read()
    csv_bytes=get("/files/forecasts.csv")
    outlook=json.loads(get("/files/outlook-scenarios.json"))
    payload=build(metadata,csv_bytes,outlook,os.environ["GITHUB_SHA"])
    receipt=publish.remote(payload)
    if hashlib.sha256(get("/files/forecasts.csv")).hexdigest()!=FORECAST_SHA:raise ValueError("Official forecast changed during publication")
    out=Path("artifacts");out.mkdir(exist_ok=True)
    (out/"pricing.json").write_text(json.dumps(payload,indent=2)+"\n")
    (out/"pricing-publication.json").write_text(json.dumps(receipt,indent=2)+"\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("# Verified pricing adapter publication\n\n~~~json\n"+json.dumps(receipt,indent=2)+"\n~~~\n\nNo historical prices or existing assets were modified.\n")
