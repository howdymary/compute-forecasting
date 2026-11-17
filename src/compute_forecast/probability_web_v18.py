"""Read-only v18 routes with an independent cache and no model credentials."""
import hashlib,json,threading,time,urllib.error,urllib.request
from .probability_ui_v18 import HTML
BASE="https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/"
def mount(api,headers):
    from fastapi.responses import HTMLResponse,JSONResponse
    lock=threading.Lock();cache={}
    @api.get("/probability")
    def page():return HTMLResponse(HTML,headers=headers)
    @api.get("/api/probability-v18")
    def result():
        with lock:
            if cache and time.monotonic()-cache["at"]<15:return JSONResponse(cache["value"],headers=headers)
            try:
                with urllib.request.urlopen(BASE+"results/probability-v18/latest.json",timeout=30) as r:pointer=json.load(r)
                path=pointer["report_path"]
                if not path.startswith("results/probability-v18/runs/") or ".." in path:raise ValueError("Invalid report pointer")
                with urllib.request.urlopen(BASE+path,timeout=60) as r:raw=r.read(20000001)
                if len(raw)>20000000 or hashlib.sha256(raw).hexdigest()!=pointer["report_sha256"]:raise ValueError("Report identity mismatch")
                value=json.loads(raw)
                if value.get("study_id")!="direct-probability-v18":raise ValueError("Wrong study")
                value["public_report_sha256"]=pointer["report_sha256"];cache.update(at=time.monotonic(),value=value)
                return JSONResponse(value,headers=headers)
            except urllib.error.HTTPError as error:
                if error.code==404:return JSONResponse({"study_id":"direct-probability-v18","status":"pending_campaign","runs":[],"prospective_accuracy":"not established"},headers=headers)
                return JSONResponse({"status":"unavailable","error_type":type(error).__name__},status_code=503,headers=headers)
            except Exception as error:return JSONResponse({"status":"unavailable","error_type":type(error).__name__},status_code=503,headers=headers)
