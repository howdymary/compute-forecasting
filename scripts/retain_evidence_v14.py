"""Retain only the two development-selected operational states; no training or copies."""
import asyncio,hashlib,json,math,os,pathlib
from datetime import datetime,timezone
from compute_forecast.direct_forecast_v12 import digest
async def main():
    import tinker
    root=pathlib.Path(".");pointer=json.loads((root/"results/evidence-v14/latest.json").read_text())
    raw=(root/pointer["report_path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
    report=json.loads(raw);protocol=report["protocol"];assert digest(protocol)==report["protocol_sha256"]
    selected=[r for r in report["runs"] if r["seed"]==17];assert {r["arm"] for r in selected}==set(protocol["arms"])
    rest=tinker.RestClient();available=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);available.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    requested_expiry=datetime(2027,3,15,tzinfo=timezone.utc)
    ttl=math.ceil((requested_expiry-datetime.now(timezone.utc)).total_seconds());assert 3600<=ttl<=150*86400
    rows=[]
    for run in selected:
        cp=run["selected"]
        if cp["is_base"]:
            rows.append({"arm":run["arm"],"seed":17,"selected_update":0,"status":"public_base_requires_no_storage"});continue
        matches=[c for c in available if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==cp["checkpoint_id"]]
        assert len(matches)==1,"Selected checkpoint identity is missing or ambiguous"
        c=matches[0];meta=c.user_metadata or {}
        assert meta.get("study_id")==protocol["study_id"] and meta.get("arm")==run["arm"] and meta.get("seed")=="17"
        assert c.checkpoint_type=="training","Operational state must retain optimizer-compatible training format"
        await rest.set_checkpoint_ttl_from_tinker_path(c.tinker_path,ttl_seconds=ttl)
        rows.append({"arm":run["arm"],"seed":17,"selected_update":cp["update"],"checkpoint_id":cp["checkpoint_id"],"requested_expiration_utc":requested_expiry.isoformat(),"status":"ttl_update_accepted","private_path_published":False})
    value={"study_id":"direct-evidence-v14-model-lock","protocol_sha256":report["protocol_sha256"],"dataset_sha256":report["dataset_sha256"],"source_report_path":pointer["report_path"],"source_report_sha256":pointer["report_sha256"],"selected_by":"Original development seven-day loss, operational seed17 fixed in prospective registration","checked_at":datetime.now(timezone.utc).isoformat(),"records":rows,"new_optimizer_updates":0,"new_checkpoints":0,"billing_changed":False,"public_weights":False,"prospective_forecasts_issued":0,"documentation":"https://tinker-docs.thinkingmachines.ai/tinker/howto/checkpoints/"}
    out=pathlib.Path("artifacts/evidence-v14-audit");out.mkdir(parents=True,exist_ok=True);(out/"model-lock.json").write_text(json.dumps(value,indent=2)+"\n");print(json.dumps(value),flush=True)
if __name__=="__main__":asyncio.run(main())
