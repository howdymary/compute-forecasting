"""Independent read-only market-state routes using the shared serving lock."""
import asyncio,json,time
from .market_ui_v19 import HTML
def mount(api,headers,public_volume,lock,clock):
    from fastapi.responses import HTMLResponse,JSONResponse,Response
    cache={}
    @api.get("/market")
    def page():return HTMLResponse(HTML,headers=headers)
    async def read(study):
        from .artifact_snapshot_v18 import read_public_snapshot
        async with lock:
            if not cache.get(study) or time.monotonic()-cache[study]["at"]>=15:
                if time.monotonic()-clock["at"]>15:
                    await asyncio.wait_for(public_volume.reload.aio(),timeout=10);clock["at"]=time.monotonic()
                value,pointer=read_public_snapshot(study);value["public_report_sha256"]=pointer["report_sha256"]
                cache[study]={"at":time.monotonic(),"raw":json.dumps(value,allow_nan=False,separators=(",",":")).encode(),"sha":pointer["report_sha256"]}
            item=cache[study]
        return Response(item["raw"],media_type="application/json",headers={**headers,"X-Source-Artifact-SHA256":item["sha"]})
    @api.get("/api/market-v19")
    async def result():
        try:return await read("market-state-v19")
        except Exception as error:return JSONResponse({"status":"pending_publication","error_type":type(error).__name__},status_code=503,headers=headers)
    @api.get("/api/market-v19/future")
    async def future():
        try:return await read("market-state-v19-prospective")
        except FileNotFoundError:return JSONResponse({"study_id":"market-state-v19-prospective","status":"pending_initial_readiness","issued_origins":0,"first_eligible_origin":"2026-12-20","final_analysis_not_before":"2027-04-12T00:00:00+00:00","prospective_accuracy":"not established"},headers=headers)
        except Exception as error:return JSONResponse({"status":"unavailable","error_type":type(error).__name__},status_code=503,headers=headers)
