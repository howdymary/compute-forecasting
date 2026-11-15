"""Publish a pinned OFL font and the authored peer review; no raw price data."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from urllib.request import urlopen
import modal

app=modal.App("compute-forecast-notebook-assets")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").add_local_python_source("compute_forecast")
ASSETS={"caveat-f84acf2c.ttf":"font/ttf","OFL.txt":"text/plain","peer-studies.json":"application/json"}
FONT_COMMIT="a85fc09e44c70c7159761adfdc9d5dd007792c15"
def git_blob_sha(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

@app.function(image=image,cpu=.25,memory=256,timeout=90,volumes={"/public":public})
def publish(files):
    if set(files)!=set(ASSETS):raise ValueError("Unexpected notebook assets")
    if any(not isinstance(v,bytes) or len(v)>1_000_000 for v in files.values()):raise ValueError("Unexpected asset size")
    if git_blob_sha(files["caveat-f84acf2c.ttf"])!="f84acf2ce2d1b3329b194749530dbaec047e6df6":raise ValueError("Font changed")
    if git_blob_sha(files["OFL.txt"])!="6e5220c9576d98dfc684e550ddf0d87f68b3edc5":raise ValueError("Font license changed")
    if "SIL OPEN FONT LICENSE" not in files["OFL.txt"].decode():raise ValueError("Missing license")
    review=json.loads(files["peer-studies.json"])
    if len(review["sources"])!=15 or review["historical_input_use"] is not False:raise ValueError("Unexpected review scope")
    public.reload();root=Path("/public/notebook");root.mkdir(exist_ok=True)
    receipt={}
    for name,raw in files.items():
        temporary=root/(name+".pending");temporary.write_bytes(raw);temporary.replace(root/name)
        receipt[name]={"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
    public.commit()
    return {"font_upstream_commit":FONT_COMMIT,"assets":receipt,"private_inputs_used":False}

@app.local_entrypoint()
def main():
    base="https://raw.githubusercontent.com/google/fonts/"+FONT_COMMIT+"/ofl/caveat/"
    files={"caveat-f84acf2c.ttf":urlopen(base+"Caveat%5Bwght%5D.ttf",timeout=60).read(),"OFL.txt":urlopen(base+"OFL.txt",timeout=60).read(),"peer-studies.json":Path("docs/notebook-peer-studies.json").read_bytes()}
    receipt=publish.remote(files)
    out=Path("artifacts");out.mkdir(exist_ok=True)
    (out/"notebook-assets.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print("NOTEBOOK_ASSETS:"+json.dumps(receipt),flush=True)
