"""Read-only paired-study web service; no private data or model credentials."""
import hashlib,json,os,threading,time,urllib.request
from pathlib import Path
import modal
STATIC_ASSET_BUILD="python - <<'PY'\nfrom pathlib import Path\nfrom urllib.request import urlopen\nimport hashlib\nbase=\"https://raw.githubusercontent.com/google/fonts/a85fc09e44c70c7159761adfdc9d5dd007792c15/ofl/caveat/\"\nroot=Path(\"/opt/notebook-static\");root.mkdir(parents=True,exist_ok=True)\nfor source,name,expected in [(\"Caveat%5Bwght%5D.ttf\",\"caveat-f84acf2c.ttf\",\"f84acf2ce2d1b3329b194749530dbaec047e6df6\"),(\"OFL.txt\",\"OFL.txt\",\"6e5220c9576d98dfc684e550ddf0d87f68b3edc5\")]:\n    raw=urlopen(base+source,timeout=60).read()\n    assert hashlib.sha1(b\"blob \"+str(len(raw)).encode()+b\"\\0\"+raw).hexdigest()==expected,\"Unverified static asset\"\n    (root/name).write_bytes(raw)\nPY"
from .evidence_ui_v14 import HTML
app=modal.App("compute-forecast-evidence-v14")
image=modal.Image.debian_slim(python_version="3.11").pip_install("fastapi[standard]>=0.115,<1").run_commands(STATIC_ASSET_BUILD).env({"EVIDENCE_UI_SHA":os.environ.get("GITHUB_SHA","unknown")}).add_local_python_source("compute_forecast")
BASE="https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/"
@app.function(image=image,cpu=.5,memory=512,timeout=120,max_containers=4)
@modal.concurrent(max_inputs=8)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse,JSONResponse,Response
    api=FastAPI(docs_url=None,redoc_url=None,openapi_url=None);cache={};lock=threading.Lock()
    headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff","Content-Security-Policy":"default-src 'self';script-src 'self' 'unsafe-inline';style-src 'self' 'unsafe-inline';object-src 'none';base-uri 'none';frame-ancestors 'none'"}
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
    def report():
        with lock:
            if cache and time.monotonic()-cache["at"]<15:return JSONResponse(cache["value"],headers=headers)
            try:
                with urllib.request.urlopen(BASE+"results/evidence-v14/latest.json",timeout=30) as response:index=json.load(response)
                path=index["report_path"]
                if not path.startswith("results/evidence-v14/runs/") or ".." in path:raise ValueError("Invalid public pointer")
                with urllib.request.urlopen(BASE+path,timeout=60) as response:raw=response.read(18000001)
                if len(raw)>18000000 or hashlib.sha256(raw).hexdigest()!=index["report_sha256"]:raise ValueError("Report hash mismatch")
                value=json.loads(raw)
                if value.get("study_id")!="direct-evidence-v14" or value.get("news_used"):raise ValueError("Study boundary mismatch")
                cache.update(at=time.monotonic(),value=value);return JSONResponse(value,headers=headers)
            except Exception as error:return JSONResponse({"status":"unavailable","error_type":type(error).__name__},status_code=503,headers=headers)
    return api
