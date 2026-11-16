"""Project-scoped storage cleanup; ambiguous and forecasting resources are retained."""
from __future__ import annotations
import asyncio,hashlib,json,os,pathlib,re
from datetime import datetime,timezone
ALLOWED={"codegarden":"CodeGarden","boundforge":"BoundForge","mochi":"Mochi"}
PROTECTED=re.compile(r"compute[\s_-]*forecast|gpu[\s_-]*(forecast|price)|pacific|direct[\s_-]*(forecast|v12)|campaign[\s_-]*v2",re.I)
META_KEYS={"project","project_name","project_slug","application","app","app_name","study_id","experiment_project"}
def hashed(s):return hashlib.sha256(str(s).encode()).hexdigest()
def classify(run,session,checkpoint):
    fields=[]
    for prefix,obj in (("run",run),("session",session),("checkpoint",checkpoint)):
        if obj is None:continue
        name=getattr(obj,"display_name",None)
        if name:fields.append((prefix+".display_name",str(name)))
        for k,v in (getattr(obj,"user_metadata",None) or {}).items():
            # Repository names are deliberately excluded: this GPU project shares mochi-demo.
            if k.lower() in META_KEYS:fields.append((prefix+".metadata."+k,str(v)))
    checkpoint_name=str(getattr(checkpoint,"checkpoint_id",""))
    if checkpoint_name:fields.append(("checkpoint.name",checkpoint_name))
    if any(PROTECTED.search(value) for _,value in fields):return None,"forecasting_protected",[]
    matches=[]
    for field,value in fields:
        for slug,label in ALLOWED.items():
            if re.match(r"^"+re.escape(slug)+r"(?:$|[\s_:/-])",value.strip(),re.I):
                matches.append({"project":label,"proof_field":field,"proof_sha256":hashed(value)})
    labels={m["project"] for m in matches}
    if len(labels)==1:return next(iter(labels)),"explicit_project_identity",matches
    return None,"ambiguous_or_unidentified",[]
async def main():
    import tinker
    rest=tinker.RestClient();checkpoints=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset)
        checkpoints.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    else:raise RuntimeError("Inventory exceeds registered 2000-checkpoint safety bound")
    runs={};sessions={};records=[];private={}
    for c in checkpoints:
        rid=c.training_run_id
        if rid not in runs:runs[rid]=await rest.get_training_run(rid)
        run=runs[rid];sid=getattr(run,"session_id",None) or rid.split(":train:")[0]
        if sid not in sessions:
            try:sessions[sid]=await rest.get_session(sid)
            except Exception:sessions[sid]=None
        project,reason,proof=classify(run,sessions[sid],c)
        key=hashed(c.tinker_path)
        record={"checkpoint_sha256":key,"project":project,"classification":reason,"proof":proof,"checkpoint_type":c.checkpoint_type,"bytes":getattr(c,"size_bytes",None),"created_at":str(getattr(c,"time",None))}
        records.append(record);private[key]=c.tinker_path
    apply=os.environ.get("APPLY_DELETE","false").lower()=="true";deleted=[];failed=[]
    # Preserve a hash-only inventory before mutations. No private resource paths are published.
    out=pathlib.Path("artifacts/tinker-storage-v12");out.mkdir(parents=True,exist_ok=True)
    def write():
        report={"created_at":datetime.now(timezone.utc).isoformat(),"apply_delete":apply,"authorized_projects":list(ALLOWED.values()),"repository_name_matching":False,"inventory_count":len(records),"matched_counts":{label:sum(r["project"]==label for r in records) for label in ALLOWED.values()},"forecasting_protected":sum(r["classification"]=="forecasting_protected" for r in records),"ambiguous_retained":sum(r["classification"]=="ambiguous_or_unidentified" for r in records),"records":records,"deleted":deleted,"failures":failed,"private_paths_exposed":False}
        (out/"audit.json").write_text(json.dumps(report,indent=2)+"\n")
        return report
    write()
    if apply:
        for r in records:
            if r["project"] not in ALLOWED.values():continue
            try:
                await rest.delete_checkpoint_from_tinker_path(private[r["checkpoint_sha256"]])
                deleted.append({"checkpoint_sha256":r["checkpoint_sha256"],"project":r["project"],"checkpoint_type":r["checkpoint_type"]})
            except Exception as e:failed.append({"checkpoint_sha256":r["checkpoint_sha256"],"project":r["project"],"error_type":type(e).__name__})
            write()
        # Re-read after deletion and prove every unselected original checkpoint remains.
        after=set()
        for offset in range(0,2000,100):
            page=await rest.list_user_checkpoints(limit=100,offset=offset)
            after.update(hashed(c.tinker_path) for c in page.checkpoints)
            if len(page.checkpoints)<100:break
        protected={r["checkpoint_sha256"] for r in records if r["project"] is None}
        if not protected<=after:raise RuntimeError("Unselected checkpoint missing after cleanup")
        if any(r["checkpoint_sha256"] in after for r in deleted):raise RuntimeError("Deletion verification failed")
    report=write()
    print(json.dumps({k:v for k,v in report.items() if k not in ("records","deleted","failures")},indent=2))
    print(json.dumps({"deleted_counts":{label:sum(r["project"]==label for r in deleted) for label in ALLOWED.values()},"failed_deletions":len(failed)}))
if __name__=="__main__":asyncio.run(main())
