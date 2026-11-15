"""Public observatory: derived results only, without raw data mounts or account secrets."""
import hashlib,json,os,time
from datetime import datetime,timezone
from pathlib import Path
import modal
from .release_payload import build,validate
from .explore_ui import HTML
from .experimental_ui_v2 import HTML as EXPERIMENTAL_HTML
from .pricing_contract import validate as validate_pricing
app=modal.App("compute-forecast-observatory")
public=modal.Volume.from_name("compute-forecast-public",create_if_missing=True,version=2)
STATIC_ASSET_BUILD="python - <<'PY'\nfrom pathlib import Path\nfrom urllib.request import urlopen\nimport hashlib\nbase=\"https://raw.githubusercontent.com/google/fonts/a85fc09e44c70c7159761adfdc9d5dd007792c15/ofl/caveat/\"\nroot=Path(\"/opt/notebook-static\");root.mkdir(parents=True,exist_ok=True)\nfor source,name,expected in [(\"Caveat%5Bwght%5D.ttf\",\"caveat-f84acf2c.ttf\",\"f84acf2ce2d1b3329b194749530dbaec047e6df6\"),(\"OFL.txt\",\"OFL.txt\",\"6e5220c9576d98dfc684e550ddf0d87f68b3edc5\")]:\n    raw=urlopen(base+source,timeout=60).read()\n    assert hashlib.sha1(b\"blob \"+str(len(raw)).encode()+b\"\\0\"+raw).hexdigest()==expected,\"Unverified static asset\"\n    (root/name).write_bytes(raw)\nPY"
image=modal.Image.debian_slim(python_version="3.11").pip_install("fastapi[standard]>=0.115,<1").run_commands(STATIC_ASSET_BUILD).env({"OBSERVATORY_UI_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_file("results/review-v4/findings.json","/opt/review-v4/findings.json",copy=True).add_local_file("configs/prospective-selector-v4.json","/opt/review-v4/prospective.json",copy=True).add_local_file("configs/review-v4-experiments.json","/opt/review-v4/experiments.json",copy=True).add_local_python_source("compute_forecast")
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

@app.function(image=image,cpu=1,memory=512,timeout=60,scaledown_window=60,max_containers=8,volumes={"/public":public})
@modal.concurrent(max_inputs=8,target_inputs=4)
@modal.asgi_app()
def web():
    import threading
    from fastapi import FastAPI,Request
    from fastapi.responses import HTMLResponse,JSONResponse,Response
    api=FastAPI(docs_url=None,redoc_url=None,openapi_url=None);lock=threading.Lock();archive_cache={"sha":None,"bytes":None};asset_cache={name:(Path("/opt/notebook-static")/name).read_bytes() for name in ("caveat-f84acf2c.ttf","OFL.txt")};release_cache={};notebook_cache={};notebook_lock=threading.Lock()
    headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Referrer-Policy":"strict-origin-when-cross-origin","Content-Security-Policy":"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"}
    def read(name):
        with lock:
            cached=release_cache.get(name)
            if cached and time.monotonic()-cached["at"]<5:return cached["raw"]
            public.reload();file=Path("/public/release")/name
            raw=file.read_bytes() if file.is_file() else None
            if raw is not None:release_cache[name]={"at":time.monotonic(),"raw":raw}
            return raw
    @api.get("/")
    def index():return HTMLResponse(HTML,headers=headers)
    @api.get("/experimental")
    def experimental_index():return HTMLResponse(EXPERIMENTAL_HTML,headers=headers)
    @api.get("/api/experimental")
    def experimental_results():
        for attempt in range(3):
            try:
                with lock:
                    public.reload();root=Path("/public/experimental-v2");summary=root/"summary.json"
                    payload=json.loads(summary.read_text()) if summary.is_file() else {"schema_version":2,"campaign_status":"running","policy_reports":[],"checkpoint_runs":[],"status":"awaiting_publication"}
                    payload["autonomy_runs"]=[json.loads(p.read_text()) for p in sorted((root/"autonomy").glob("*.json"))[-20:]]
                    for key,name in (("prospective","prospective-manifest.json"),("provider_usage","usage.json"),("price_free_ablation","price-free.json"),("analysis","analysis.json"),("matched_price_ablation","matched-price-ablation.json"),("feature_summary","feature-summary.json"),("artifact_archive","archive-manifest.json"),("training_progress","training-progress.json")):
                        file=root/name
                        if file.is_file():payload[key]=json.loads(file.read_text())
                break
            except json.JSONDecodeError:
                if attempt==2:return JSONResponse({"error":"Experimental publication is updating; retry shortly"},status_code=503,headers={**headers,"Retry-After":"1"})
                time.sleep(.1)
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
        with notebook_lock:
            if notebook_cache and time.monotonic()-notebook_cache["at"]<5:
                return JSONResponse(notebook_cache["payload"],headers=headers)
            response=experimental_results()
            if response.status_code!=200:return response
            try:
                payload=build_diagnostics(json.loads(response.body))
                notebook_cache.update(at=time.monotonic(),payload=payload)
                return JSONResponse(payload,headers=headers)
            except (ValueError,KeyError,TypeError):
                return JSONResponse({"error":"Notebook diagnostics await verified artifacts"},status_code=503,headers=headers)

    @api.get("/notebook-assets/{name}")
    def notebook_asset(name:str):
        allowed={"caveat-f84acf2c.ttf":"font/ttf","OFL.txt":"text/plain","peer-studies.json":"application/json"}
        if name not in allowed:return Response(status_code=404,headers=headers)
        raw=asset_cache.get(name)
        if raw is None:
            with lock:
                public.reload();path=Path("/public/notebook")/name
                if not path.is_file():return Response(status_code=404,headers=headers)
                raw=path.read_bytes()
                if len(raw)>1_000_000:return Response(status_code=503,headers=headers)
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

    @api.get("/api/research-assets")
    def research_assets():
        from .history_contract_v3 import validate_assets
        with lock:
            public.reload();file=Path("/public/phase3/explorer.json")
            if not file.is_file():return JSONResponse({"error":"Verified historical context and traces are not yet published"},status_code=503,headers=headers)
            raw=file.read_bytes()
        try:validate_assets(json.loads(raw))
        except (ValueError,KeyError,TypeError,json.JSONDecodeError):
            return JSONResponse({"error":"Research assets failed validation"},status_code=503,headers=headers)
        return Response(raw,media_type="application/json",headers={**headers,"ETag":hashlib.sha256(raw).hexdigest()})
    @api.get("/api/chronos-control")
    def chronos_control():
        with lock:
            public.reload();file=Path("/public/phase3/chronos-control.json")
            if not file.is_file():return JSONResponse({"status":"pending","metrics":None},headers=headers)
            raw=file.read_bytes()
        payload=json.loads(raw)
        if payload["scope"]["cells"]!=12 or payload["official_export_changed"] or payload["selector_registry_changed"] or payload["future_competition_truth_loaded"]:return JSONResponse({"error":"Comparator boundary validation failed"},status_code=503,headers=headers)
        return Response(raw,media_type="application/json",headers={**headers,"ETag":hashlib.sha256(raw).hexdigest()})

    @api.get("/api/review-v4")
    def review_v4():
        from .review_v4 import validate as validate_review
        raw=Path("/opt/review-v4/findings.json").read_bytes()
        try:validate_review(json.loads(raw))
        except (ValueError,KeyError,TypeError):
            return JSONResponse({"error":"Review artifact failed validation"},status_code=503,headers=headers)
        return Response(raw,media_type="application/json",headers={**headers,"ETag":hashlib.sha256(raw).hexdigest()})
    @api.get("/api/review-v4/protocols")
    def review_protocols():
        return JSONResponse({"schema_version":4,"prospective":json.loads(Path("/opt/review-v4/prospective.json").read_bytes()),"experiments":json.loads(Path("/opt/review-v4/experiments.json").read_bytes())},headers=headers)

    @api.get("/api/review-v4/operations")
    def review_operations():
        with lock:
            public.reload();path=Path("/public/review-v4/operations.json")
            if not path.is_file():return JSONResponse({"schema_version":4,"operations":{},"status":"pending_remote_execution"},headers=headers)
            raw=path.read_bytes()
        from .public_results import private_guard
        payload=json.loads(raw);private_guard(payload)
        return Response(raw,media_type="application/json",headers={**headers,"ETag":hashlib.sha256(raw).hexdigest()})


    @api.get("/api/review-v4/artifacts/{name}")
    def review_operation_artifact(name:str):
        import re
        if not re.fullmatch(r"(initialize|feedback|capture|issuance|scoring|learning|market)-[0-9a-f]{32}\.json",name):return Response(status_code=404,headers=headers)
        with lock:
            public.reload();path=Path("/public/review-v4")/name
            if not path.is_file():return Response(status_code=404,headers=headers)
            raw=path.read_bytes()
        from .public_results import private_guard
        private_guard(json.loads(raw))
        return Response(raw,media_type="application/json",headers={**headers,"ETag":hashlib.sha256(raw).hexdigest()})


    @api.get("/api/value-v5")
    def value_study_v5():
        with lock:
            public.reload();path=Path("/public/value-v5/current.json")
            if not path.is_file():return JSONResponse({"error":"Value study is pending publication"},status_code=503,headers=headers)
            raw=path.read_bytes()
        v=json.loads(raw)
        from .pricing_contract import FORECAST_SHA
        from .capability_v5 import rental_pairs
        if v["schema_version"]!=5 or v["official_csv_sha256"]!=FORECAST_SHA or v["protected_outcomes_loaded"]:return JSONResponse({"error":"Value study identity failed"},status_code=503,headers=headers)
        approved={r["series_id"] for r in v["history"]["publication_decisions"] if r["approved"]}
        if any(s["id"] not in approved or any(p["date"]>"2026-11-06" for p in s["points"]) for s in v["history"]["series"]):return JSONResponse({"error":"History publication boundary failed"},status_code=503,headers=headers)
        # Normalize human catalog labels into the registered canonical pairing IDs.
        v["capability"]["rental_pairs"]=rental_pairs(v)
        v["adapter_source_sha"]=os.environ.get("OBSERVATORY_UI_SHA")
        v["stored_artifact_sha256"]=hashlib.sha256(raw).hexdigest()
        return JSONResponse(v,headers=headers)

    @api.get("/api/value-v5/memory")
    def value_memory_v5():
        with lock:
            public.reload();path=Path("/public/value-v5/memory.json")
            if not path.is_file():return JSONResponse({"schema_version":5,"status":"pending","steps":[],"verified_cross_role_reads":0,"actual_tinker_decisions":0,"outcome_claim":"Pending actual execution"},headers=headers)
            raw=path.read_bytes()
        from .public_results import private_guard
        private_guard(json.loads(raw));return Response(raw,media_type="application/json",headers=headers)

    @api.get("/value-notices/{name}")
    def value_notice_v5(name:str):
        import re
        if not re.fullmatch(r"[A-Za-z0-9_.-]+",name) or name in (".",".."):return Response(status_code=404,headers=headers)
        with lock:
            public.reload();path=Path("/public/value-v5/notices")/name
            if not path.is_file():return Response(status_code=404,headers=headers)
            raw=path.read_bytes()
        return Response(raw,media_type="text/plain",headers=headers)

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
