"""Delete only checkpoints created on/before Nov14 in America/Los_Angeles."""
import asyncio,hashlib,json,os,pathlib
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
def hashed(value):return hashlib.sha256(str(value).encode()).hexdigest()
def stamp(c):
    obj=c.model_dump(mode="json")
    for key in ("time","created_at","createdAt"):
        value=obj.get(key)
        if value:
            if isinstance(value,(int,float)):return datetime.fromtimestamp(value,timezone.utc)
            dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
            if dt.tzinfo is None:raise ValueError("Unzoned checkpoint creation time")
            return dt
    return None
async def main():
    import tinker
    rest=tinker.RestClient();checkpoints=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);checkpoints.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    rows=[];deleted=[];failures=[];out=pathlib.Path("artifacts/evidence-v14-audit");out.mkdir(parents=True,exist_ok=True)
    for c in checkpoints:
        time=stamp(c);local=time.astimezone(ZoneInfo("America/Los_Angeles")) if time else None
        selected=bool(local and local.date().isoformat()<="2026-11-14")
        rows.append({"checkpoint_sha256":hashed(c.tinker_path),"checkpoint_type":c.checkpoint_type,"created_at":time.isoformat() if time else None,"created_date_los_angeles":local.date().isoformat() if local else None,"eligible_for_authorized_cleanup":selected,"metadata":{k:v for k,v in (c.user_metadata or {}).items() if k in ("study_id","seed","arm","update")}})
    def write(after=None):
        value={"study_id":"direct-evidence-v14-storage-cleanup","authorization":"User requested older checkpoints from two days ago","checked_at":datetime.now(timezone.utc).isoformat(),"cutoff_local_date_inclusive":"2026-11-14","timezone":"America/Los_Angeles","before_count":len(checkpoints),"after_count":after,"records":rows,"deleted":deleted,"failures":failures,"private_paths_exposed":False,"billing_changed":False}
        (out/"older-checkpoint-cleanup.json").write_text(json.dumps(value,indent=2)+"\n");return value
    write()
    for c,row in zip(checkpoints,rows):
        if not row["eligible_for_authorized_cleanup"]:continue
        try:
            await rest.delete_checkpoint_from_tinker_path(c.tinker_path)
            deleted.append({"checkpoint_sha256":row["checkpoint_sha256"],"created_date_los_angeles":row["created_date_los_angeles"],"checkpoint_type":row["checkpoint_type"]})
        except Exception as e:failures.append({"checkpoint_sha256":row["checkpoint_sha256"],"error_type":type(e).__name__})
        write()
    after=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);after.extend(hashed(c.tinker_path) for c in page.checkpoints)
        if len(page.checkpoints)<100:break
    preserved={r["checkpoint_sha256"] for r in rows if not r["eligible_for_authorized_cleanup"]}
    assert preserved<=set(after),"Newer or undated checkpoint missing"
    assert not any(r["checkpoint_sha256"] in after for r in deleted),"Deleted checkpoint still listed"
    write(len(after));print(json.dumps({"before":len(checkpoints),"eligible":sum(r["eligible_for_authorized_cleanup"] for r in rows),"deleted":len(deleted),"after":len(after),"newer_preserved":len(preserved),"failure_count":len(failures),"unknown_timestamps":sum(r["created_at"] is None for r in rows)}),flush=True)
if __name__=="__main__":asyncio.run(main())
