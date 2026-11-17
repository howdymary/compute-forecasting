"""Read-only paired-study web service; no private data or model credentials."""
import asyncio,hashlib,json,os,re,threading,time,urllib.request,uuid
from pathlib import Path
import modal
STATIC_ASSET_BUILD="python - <<'PY'\nfrom pathlib import Path\nfrom urllib.request import urlopen\nimport hashlib\nbase=\"https://raw.githubusercontent.com/google/fonts/a85fc09e44c70c7159761adfdc9d5dd007792c15/ofl/caveat/\"\nroot=Path(\"/opt/notebook-static\");root.mkdir(parents=True,exist_ok=True)\nfor source,name,expected in [(\"Caveat%5Bwght%5D.ttf\",\"caveat-f84acf2c.ttf\",\"f84acf2ce2d1b3329b194749530dbaec047e6df6\"),(\"OFL.txt\",\"OFL.txt\",\"6e5220c9576d98dfc684e550ddf0d87f68b3edc5\")]:\n    raw=urlopen(base+source,timeout=60).read()\n    assert hashlib.sha1(b\"blob \"+str(len(raw)).encode()+b\"\\0\"+raw).hexdigest()==expected,\"Unverified static asset\"\n    (root/name).write_bytes(raw)\nPY"
from .evidence_ui_v14 import HTML
app=modal.App("compute-forecast-evidence-v14")
future_public=modal.Volume.from_name("compute-forecast-public",create_if_missing=False,version=2)
image=modal.Image.debian_slim(python_version="3.11").pip_install("fastapi[standard]>=0.115,<1").run_commands(STATIC_ASSET_BUILD).env({"EVIDENCE_UI_SHA":os.environ.get("EVIDENCE_SOURCE_SHA",os.environ.get("GITHUB_SHA","unknown"))}).add_local_python_source("compute_forecast")
BASE="https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/"
@app.function(image=image,cpu=1,memory=1024,timeout=120,min_containers=1,max_containers=2,volumes={"/public":future_public})
@modal.concurrent(max_inputs=32)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse,JSONResponse,Response
    api=FastAPI(docs_url=None,redoc_url=None,openapi_url=None);cache={};lock=threading.Lock();future_lock=asyncio.Lock();future_cache={"at":time.monotonic()}
    headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'self';script-src 'self' 'unsafe-inline';style-src 'self' 'unsafe-inline';object-src 'none';base-uri 'none';frame-ancestors 'none'"}
    @api.middleware("http")
    async def request_timing(request,call_next):
        trace=uuid.uuid4().hex;started=time.monotonic();path=request.url.path
        print(json.dumps({"event":"forecast_http","phase":"start","request_id":trace,"path":path}),flush=True)
        try:
            response=await asyncio.wait_for(call_next(request),timeout=20)
        except asyncio.TimeoutError:
            response=JSONResponse({"status":"unavailable","error_type":"RequestDeadline","request_id":trace},status_code=503,headers=headers)
        response.headers["X-Compute-Request-ID"]=trace
        print(json.dumps({"event":"forecast_http","phase":"end","request_id":trace,"path":path,"status":response.status_code,"seconds":time.monotonic()-started}),flush=True)
        return response
    @api.get("/")
    def page():return HTMLResponse(HTML,headers=headers)
    @api.get("/assets/{name}")
    def asset(name:str):
        names={"note.ttf":("caveat-f84acf2c.ttf","font/ttf"),"OFL.txt":("OFL.txt","text/plain")}
        if name not in names:return Response(status_code=404)
        file,kind=names[name];raw=(Path("/opt/notebook-static")/file).read_bytes()
        return Response(raw,media_type=kind,headers={**headers,"Cache-Control":"public,max-age=31536000,immutable"})
    @api.get("/health")
    def health():return {"status":"ok","study_id":"direct-evidence-v14","ui_revision":os.environ.get("EVIDENCE_UI_SHA")}
    @api.get("/api/evidence-v14")
    async def report():
        from .artifact_snapshot_v18 import read_public_snapshot
        try:
            async with future_lock:
                if not cache or time.monotonic()-cache["at"]>=15:
                    if time.monotonic()-future_cache["at"]>15:
                        await asyncio.wait_for(future_public.reload.aio(),timeout=10);future_cache["at"]=time.monotonic()
                    value,pointer=read_public_snapshot("direct-evidence-v14")
                    if value.get("news_used"):raise ValueError("Study boundary mismatch")
                    cache.update(at=time.monotonic(),value=value,pointer=pointer,raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode())
                value=cache["value"];identity=cache["pointer"]["report_sha256"]
            return Response(cache["raw"],media_type="application/json",headers={**headers,"X-Source-Artifact-SHA256":identity})
        except Exception as error:return JSONResponse({"status":"unavailable","error_type":type(error).__name__},status_code=503,headers=headers)
    @api.get("/api/evidence-future")
    async def future_index():
        try:
            async with future_lock:
                if time.monotonic()-future_cache["at"]>15:
                    await asyncio.wait_for(future_public.reload.aio(),timeout=10);future_cache["at"]=time.monotonic()
                path=Path("/public/evidence-v14-future/index.json")
                if not path.exists():return JSONResponse({"status":"pending_initial_readiness_audit","issued_origins":0},headers=headers)
                value=json.loads(path.read_bytes());assert value["study_id"]=="direct-evidence-v14-prospective"
                return JSONResponse(value,headers=headers)
        except Exception as error:return JSONResponse({"status":"unavailable","error_type":type(error).__name__},status_code=503,headers=headers)
    @api.get("/api/evidence-future/artifacts/{identity}.json")
    async def future_artifact(identity:str):
        if not re.fullmatch("[0-9a-f]{64}",identity):return Response(status_code=404)
        async with future_lock:
            if time.monotonic()-future_cache["at"]>15:
                await asyncio.wait_for(future_public.reload.aio(),timeout=10);future_cache["at"]=time.monotonic()
            path=Path("/public/evidence-v14-future/artifacts")/(identity+".json")
            if not path.exists():return Response(status_code=404)
            raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=identity:return Response(status_code=503)
        return Response(raw,media_type="application/json",headers=headers)
    from .probability_web_v18 import mount
    mount(api,headers,future_public,future_lock,future_cache)
    from .market_web_v19 import mount as mount_market
    mount_market(api,headers,future_public,future_lock,future_cache)
    from .quantile_web_v20 import mount as mount_quantile
    mount_quantile(api,headers,future_public,future_lock,future_cache)
    return api
