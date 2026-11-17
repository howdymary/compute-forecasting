"""Read-only v18 routes with an independent cache and no model credentials."""
import asyncio,hashlib,json,threading,time,urllib.error,urllib.request
from .probability_ui_v18 import HTML
BASE="https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/"
def mount(api,headers,public_volume,future_lock,future_cache):
    from fastapi.responses import HTMLResponse,JSONResponse,Response
    lock=threading.Lock();cache={}
    @api.get("/probability")
    def page():return HTMLResponse(HTML,headers=headers)
    @api.get("/api/probability-v18")
    async def result():
        from .artifact_snapshot_v18 import read_public_snapshot
        try:
            async with future_lock:
                if not cache or time.monotonic()-cache["at"]>=15:
                    if time.monotonic()-future_cache["at"]>15:
                        await asyncio.wait_for(public_volume.reload.aio(),timeout=10);future_cache["at"]=time.monotonic()
                    value,pointer=read_public_snapshot("direct-probability-v18")
                    value["public_report_sha256"]=pointer["report_sha256"];cache.update(at=time.monotonic(),value=value,pointer=pointer,raw=json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode())
                value=cache["value"];identity=cache["pointer"]["report_sha256"]
            return Response(cache["raw"],media_type="application/json",headers={**headers,"X-Source-Artifact-SHA256":identity})
        except FileNotFoundError:return JSONResponse({"study_id":"direct-probability-v18","status":"awaiting_serving_publication","runs":[]},status_code=503,headers=headers)
        except Exception as error:return JSONResponse({"status":"unavailable","error_type":type(error).__name__},status_code=503,headers=headers)
    @api.get("/api/probability-v18/future")
    async def future_index():
        from pathlib import Path
        try:
            async with future_lock:
                if time.monotonic()-future_cache["at"]>15:
                    await asyncio.wait_for(public_volume.reload.aio(),timeout=10);future_cache["at"]=time.monotonic()
                path=Path("/public/probability-v18-future/index.json")
                if not path.exists():
                    return JSONResponse({"study_id":"direct-probability-v18-prospective","status":"pending_initial_readiness_audit","issued_origins":0,"prospective_accuracy":"not established"},headers=headers)
                value=json.loads(path.read_bytes())
                assert value["study_id"]=="direct-probability-v18-prospective"
                return JSONResponse(value,headers=headers)
        except Exception as error:return JSONResponse({"status":"unavailable","error_type":type(error).__name__},status_code=503,headers=headers)
    @api.get("/api/probability-v18/future/artifacts/{identity}.json")
    async def future_artifact(identity:str):
        import re
        from pathlib import Path
        from fastapi.responses import Response
        if not re.fullmatch("[0-9a-f]{64}",identity):return Response(status_code=404)
        async with future_lock:
            if time.monotonic()-future_cache["at"]>15:
                await asyncio.wait_for(public_volume.reload.aio(),timeout=10);future_cache["at"]=time.monotonic()
            path=Path("/public/probability-v18-future/artifacts")/(identity+".json")
            if not path.exists():return Response(status_code=404)
            raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=identity:return Response(status_code=503)
        return Response(raw,media_type="application/json",headers=headers)
