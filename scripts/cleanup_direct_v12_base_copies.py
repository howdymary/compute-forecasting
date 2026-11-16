"""Delete exactly four approved untrained copies; preserve all learned checkpoints."""
import asyncio,hashlib,json,pathlib
from datetime import datetime,timezone
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
async def inventory(rest):
    items=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);items.extend(page.checkpoints)
        if len(page.checkpoints)<100:return items
    raise RuntimeError("Checkpoint inventory bound exceeded")
async def main():
    import tinker
    p=json.loads(pathlib.Path("configs/direct-v12-base-copy-cleanup.json").read_text())
    assert p["status"]=="approved_by_user"
    rest=tinker.RestClient();before=await inventory(rest);lookup={sha(c.tinker_path):c for c in before}
    selected=[]
    for expected in p["candidates"]:
        c=lookup.get(expected["sha256"])
        if c is None:continue
        m=c.user_metadata or {}
        assert m.get("study_id")=="direct-forecast-v12" and m.get("update")=="0"
        assert m.get("seed")==str(expected["seed"]) and c.checkpoint_type==expected["type"]
        selected.append((expected,c))
    authorized={r["sha256"] for r in p["candidates"]};protected=set(lookup)-authorized
    deleted=[]
    for expected,c in selected:
        await rest.delete_checkpoint_from_tinker_path(c.tinker_path);deleted.append(expected)
    after={sha(c.tinker_path) for c in await inventory(rest)}
    assert protected<=after,"A nonselected checkpoint disappeared"
    assert not authorized&after,"An authorized base copy remains"
    report={"study_id":p["study_id"],"created_at":datetime.now(timezone.utc).isoformat(),"deleted":deleted,"already_absent":sorted(authorized-set(lookup)),"count_before":len(before),"count_after":len(after),"all_nonselected_checkpoints_preserved":True,"all_learned_checkpoint_states_preserved":True,"private_paths_exposed":False}
    out=pathlib.Path("artifacts/direct-v12-base-cleanup");out.mkdir(parents=True,exist_ok=True);(out/"audit.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
asyncio.run(main())
