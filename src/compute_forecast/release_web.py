"""Public observatory: derived results only, without raw data mounts or account secrets."""
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
import modal
from .release_payload import build,validate
from .explore_ui import HTML
from .experimental_ui_v2 import HTML as EXPERIMENTAL_HTML
from .pricing_contract import validate as validate_pricing
app=modal.App("compute-forecast-observatory")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=True,version=2)
image=modal.Image.debian_slim(python_version="3.11").pip_install("fastapi[standard]>=0.115,<1").env({"OBSERVATORY_UI_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_python_source("compute_forecast")
FILES={"forecasts.csv":"text/csv","outlook.md":"text/markdown","outlook-scenarios.json":"application/json","demo.mp4":"video/mp4"}

@app.function(image=image,cpu=.25,memory=256,timeout=90,volumes={"/public":public})
def publish_release(payload:dict,files:dict):
    validate(payload)
    if set(files)-set(FILES) or not {"forecasts.csv","outlook.md","outlook-scenarios.json"}<=set(files):raise ValueError("Unexpected public files")
    if hashlib.sha256(files["forecasts.csv"]).hexdigest()!=payload["submission"]["forecast_csv_sha256"]:raise ValueError("Forecast export hash mismatch")
    encoded=json.dumps(payload,indent=2,allow_nan=False).encode();root=Path("/public/release");root.mkdir(exist_ok=True)
    for name,data in files.items():
        if not isinstance(data,bytes) or len(data)>100_000_000:raise ValueError("Unexpected public file size")
        temporary=root/(name+".pending");temporary.write_bytes(data);temporary.replace(root/name)
    temporary=root/"results.pending";temporary.write_bytes(encoded);temporary.replace(root/"results.json");public.commit()
    return {"sha256":hashlib.sha256(encoded).hexdigest(),"bytes":len(encoded),"code_sha":payload["code_sha"],"files":{name:{"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()} for name,b in files.items()},"published_at":datetime.now(timezone.utc).isoformat()}

@app.function(image=image,cpu=.25,memory=256,timeout=60,scaledown_window=60,volumes={"/public":public})
@modal.concurrent(max_inputs=20)
@modal.asgi_app()
def web():
    import threading
    from fastapi import FastAPI,Request
    from fastapi.responses import HTMLResponse,JSONResponse,Response
    api=FastAPI(docs_url=None,redoc_url=None,openapi_url=None);lock=threading.Lock();archive_cache={"sha":None,"bytes":None};asset_cache={}
    headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"strict-origin-when-cross-origin","Content-Security-Policy":"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"}
    def read(name):
        with lock:
            public.reload();file=Path("/public/release")/name
            return file.read_bytes() if file.is_file() else None
    @api.get("/")
    def index():return HTMLResponse(HTML,headers=headers)
    @api.get("/experimental")
    def experimental_index():return HTMLResponse(EXPERIMENTAL_HTML,headers=headers)
    @api.get("/api/experimental")
    def experimental_results():
        with lock:
            public.reload();root=Path("/public/experimental-v2");summary=root/"summary.json"
            payload=json.loads(summary.read_text()) if summary.is_file() else {"schema_version":2,"campaign_status":"running","policy_reports":[],"checkpoint_runs":[],"status":"awaiting_publication"}
            payload["autonomy_runs"]=[json.loads(p.read_text()) for p in sorted((root/"autonomy").glob("*.json"))[-20:]]
            for key,name in (("prospective","prospective-manifest.json"),("provider_usage","usage.json"),("price_free_ablation","price-free.json"),("analysis","analysis.json"),("matched_price_ablation","matched-price-ablation.json"),("feature_summary","feature-summary.json"),("artifact_archive","archive-manifest.json"),("training_progress","training-progress.json")):
                file=root/name
                if file.is_file():payload[key]=json.loads(file.read_text())
        payload["policy_execution_semantics"]={"numerical_feedback_cache_hit":True,"new_numerical_execution":False,"budget":"six revealed results from the registered numerical grid per task","inference":"actual Tinker sampler calls; distinct from fresh Modal autonomy executions"}
        encoded=json.dumps(payload,allow_nan=False)
        if any(token in encoded for token in ("tinker://","TINKER_API_KEY","MODAL_TOKEN_SECRET","Authorization","permitted_private_method_context")):
            return JSONResponse({"error":"Publication failed privacy validation"},status_code=503,headers=headers)
        return Response(encoded,media_type="application/json",headers=headers)
    @api.get("/experimental/downloads/{run_id}.zip")
    def experimental_archive(run_id:str):
        if run_id!="latest" and not run_id.isdigit():return Response(status_code=404,headers=headers)
        with lock:
            public.reload();root=Path("/public/experimental-v2")
            meta=root/"archive-manifest.json" if run_id=="latest" else root/"archives"/run_id/"manifest.json"
            if not meta.is_file():return Response(status_code=404,headers=headers)
            manifest=json.loads(meta.read_text());identifier=manifest["release_run_id"]
            if not identifier.isdigit():return Response(status_code=503,headers=headers)
            if archive_cache["sha"]!=manifest["sha256"]:
                file=root/"archives"/identifier/"research-bundle.zip"
                if not file.is_file() or file.stat().st_size>20_000_000:return Response(status_code=503,headers=headers)
                raw=file.read_bytes()
                if hashlib.sha256(raw).hexdigest()!=manifest["sha256"]:return Response(status_code=503,headers=headers)
                archive_cache.update(sha=manifest["sha256"],bytes=raw)
            raw=archive_cache["bytes"]
        return Response(raw,media_type="application/zip",headers={**headers,"ETag":manifest["sha256"],"Content-Disposition":'attachment; filename="compute-forecast-v2-'+identifier+'.zip"'})
    @api.get("/api/notebook")
    def notebook_diagnostics():
        from .notebook_diagnostics import build as build_diagnostics
        response=experimental_results()
        if response.status_code!=200:return response
        try:
            payload=build_diagnostics(json.loads(response.body))
            return JSONResponse(payload,headers=headers)
        except (ValueError,KeyError,TypeError):
            return JSONResponse({"error":"Notebook diagnostics await verified artifacts"},status_code=503,headers=headers)

    @api.get("/notebook-assets/{name}")
    def notebook_asset(name:str):
        allowed={"caveat-f84acf2c.ttf":"font/ttf","OFL.txt":"text/plain","peer-studies.json":"application/json"}
        if name not in allowed:return Response(status_code=404,headers=headers)
        with lock:
            raw=asset_cache.get(name) if name!="peer-studies.json" else None
            if raw is None:
                public.reload();path=Path("/public/notebook")/name
                if not path.is_file():return Response(status_code=404,headers=headers)
                raw=path.read_bytes()
                if len(raw)>1_000_000:return Response(status_code=503,headers=headers)
                if name!="peer-studies.json":asset_cache[name]=raw
        return Response(raw,media_type=allowed[name],headers={**headers,"Cache-Control":"public, max-age=31536000, immutable" if name.endswith(".ttf") else "no-store","ETag":hashlib.sha256(raw).hexdigest()})

    @api.get("/api/release")
    def results():
        raw=read("results.json")
        if raw is None:return JSONResponse({"error":"Measured release is not yet published"},status_code=503,headers=headers)
        validate(json.loads(raw));return Response(raw,media_type="application/json",headers={**headers,"ETag":hashlib.sha256(raw).hexdigest()})
    @api.get("/api/pricing")
    def pricing():
        raw=read("pricing.json")
        if raw is None:return JSONResponse({"error":"Verified pricing adapter is not yet published"},status_code=503,headers=headers)
        validate_pricing(json.loads(raw))
        return Response(raw,media_type="application/json",headers={**headers,"ETag":hashlib.sha256(raw).hexdigest()})
    @api.get("/health")
    def health():
        raw=read("results.json");r=json.loads(raw) if raw else None
        return JSONResponse({"ui_revision":os.environ.get("OBSERVATORY_UI_SHA"),"status":"ok" if r else "awaiting_results","release_sha256":hashlib.sha256(raw).hexdigest() if raw else None,"code_sha":r["code_sha"] if r else None,"training_updates":r["development"]["actual_training_updates"] if r else None,"final_origins":r["final"]["temporal_origins"] if r else None,"actual_cross_agent_use":r["memory"]["actual_cross_agent_use"] if r else None},headers=headers)
    @api.get("/files/{name}")
    def download(name:str,request:Request):
        if name not in FILES:return Response(status_code=404,headers=headers)
        raw=read(name)
        if raw is None:return Response(status_code=404,headers=headers)
        download_headers={**headers,"Content-Disposition":'inline; filename="'+name+'"',"Accept-Ranges":"bytes"}
        range_header=request.headers.get("range")
        if range_header and name=="demo.mp4":
            import re
            match=re.fullmatch(r"bytes=(\d+)-(\d*)",range_header)
            if not match:return Response(status_code=416,headers={**download_headers,"Content-Range":f"bytes */{len(raw)}"})
            start=int(match.group(1));end=min(int(match.group(2)) if match.group(2) else len(raw)-1,len(raw)-1)
            if start>end or start>=len(raw):return Response(status_code=416,headers={**download_headers,"Content-Range":f"bytes */{len(raw)}"})
            return Response(raw[start:end+1],status_code=206,media_type=FILES[name],headers={**download_headers,"Content-Range":f"bytes {start}-{end}/{len(raw)}"})
        return Response(raw,media_type=FILES[name],headers=download_headers)
    return api

@app.function(image=image,cpu=.25,memory=512,timeout=90,volumes={"/public":public})
def publish_video(data:bytes,release_sha256:str):
    root=Path("/public/release");raw=(root/"results.json").read_bytes()
    if hashlib.sha256(raw).hexdigest()!=release_sha256:raise ValueError("Video refers to a different public release")
    if not isinstance(data,bytes) or not 10000<len(data)<100_000_000 or b"ftyp" not in data[:32]:raise ValueError("Invalid MP4 payload")
    temporary=root/"demo.pending";temporary.write_bytes(data);temporary.replace(root/"demo.mp4");public.commit()
    return {"video_sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data),"release_sha256":release_sha256,"url":"https://howdymary--compute-forecast-observatory-web.us-east.modal.run/files/demo.mp4","mode":"recorded_actual_public_results"}

@app.local_entrypoint()
def main(inputs:str="inputs"):
    payload=build(inputs,os.environ["GITHUB_SHA"])
    root=Path(inputs)/"submission";files={}
    for name in ("forecasts.csv","outlook.md","outlook-scenarios.json"):
        found=list(root.rglob(name))
        if len(found)!=1:raise ValueError("Missing submission file: "+name)
        files[name]=found[0].read_bytes()
    receipt=publish_release.remote(payload,files);out=Path("artifacts");out.mkdir(exist_ok=True)
    (out/"release.json").write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
    (out/"release-publication.json").write_text(json.dumps(receipt,indent=2)+"\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write("# Published measured final release\n\n~~~json\n"+json.dumps(receipt,indent=2)+"\n~~~\n")
