"""Read-only direct-forecast study; no private data volume or service secrets."""
import hashlib,json,os,threading,time,urllib.request
import modal
from .direct_ui_v12 import HTML
app=modal.App("compute-forecast-direct-v12")
image=modal.Image.debian_slim(python_version="3.11").pip_install("fastapi[standard]>=0.115,<1").env({"DIRECT_UI_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_python_source("compute_forecast")
@app.function(image=image,cpu=.5,memory=512,timeout=120,max_containers=4)
@modal.concurrent(max_inputs=8)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse,JSONResponse
    api=FastAPI(docs_url=None,redoc_url=None,openapi_url=None);cache={};lock=threading.Lock()
    base="https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/"
    headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"}
    @api.get("/")
    def index():return HTMLResponse(HTML,headers=headers)
    @api.get("/health")
    def health():return {"status":"ok","ui_revision":os.environ.get("DIRECT_UI_SHA"),"study_id":"direct-forecast-v12"}
    @api.get("/api/direct-v12")
    def report():
        with lock:
            if cache and time.monotonic()-cache["at"]<15:return JSONResponse(cache["value"],headers=headers)
            try:
                with urllib.request.urlopen(base+"results/direct-v12/latest.json",timeout=30) as r:index=json.load(r)
                path=index["report_path"]
                if not path.startswith("results/direct-v12/runs/") or ".." in path:raise ValueError("Invalid public pointer")
                with urllib.request.urlopen(base+path,timeout=60) as r:raw=r.read(15_000_001)
                if len(raw)>15_000_000 or hashlib.sha256(raw).hexdigest()!=index["report_sha256"]:raise ValueError("Report hash mismatch")
                value=json.loads(raw);cache.update(at=time.monotonic(),value=value)
                return JSONResponse(value,headers=headers)
            except Exception as e:
                if getattr(e,"code",None)==404:
                    return JSONResponse({"study_id":"direct-forecast-v12","status":"running","runs":[],"cases":[],"pending_reason":"Training artifacts have not been published yet"},headers=headers)
                return JSONResponse({"status":"unavailable","error_type":type(e).__name__},status_code=503,headers=headers)
    return api
