"""Finish interrupted checkpoint evaluation without repeating optimizer updates."""
from __future__ import annotations
import argparse,asyncio,hashlib,json,os,pathlib,statistics,time,urllib.request
from datetime import datetime,timezone
from .direct_forecast_v12 import digest,summarize,matched
from .train_direct_v12 import evaluate,reference_cells,write,now,cfg
async def recover(inputs,output,seed):
    import tinker
    from tinker_cookbook.renderers import get_renderer
    p=cfg();root=pathlib.Path(inputs);out=pathlib.Path(output);out.mkdir(parents=True,exist_ok=True)
    dataset=json.loads((root/"dataset.json").read_text());audit=json.loads((root/"audit.json").read_text())
    assert digest(dataset)==audit["dataset_sha256"] and dataset["protocol_sha256"]==digest(p)
    # Reuse an already published evaluation rather than repeating sampling.
    public_base="https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/"
    try:
        with urllib.request.urlopen(public_base+"results/direct-v12/latest.json",timeout=15) as response:index=json.load(response)
        with urllib.request.urlopen(public_base+index["report_path"],timeout=15) as response:published=json.load(response)
        existing=next((r for r in published.get("runs",[]) if r["seed"]==seed and r["protocol_sha256"]==digest(p) and r["dataset_sha256"]==digest(dataset)),None)
        if existing:
            directory=index["report_path"].rsplit("/",1)[0]+"/seed-"+str(seed)+"/"
            names=["result.json","progress.json","selection.json","evaluation-selected.json","evaluation-base.json"]+["development-"+str(c["update"])+".json" for c in existing["checkpoints"]]
            for name in names:
                with urllib.request.urlopen(public_base+directory+name,timeout=30) as response:value=json.load(response)
                write(out/name,value)
            print("DIRECT_EVALUATION_REUSED "+json.dumps({"seed":seed,"new_optimizer_updates":0,"new_samples":0}),flush=True)
            return
    except Exception:
        pass
    progress=next(f for f in root.rglob("progress.json") if json.loads(f.read_text()).get("seed")==seed)
    state=json.loads(progress.read_text())
    assert state["optimizer_updates"]==p["model"]["max_updates"]==100,"Recovery never repeats missing optimization"
    for f in progress.parent.glob("*.json"):write(out/f.name,json.loads(f.read_text()))
    rest=tinker.RestClient();matches=[]
    for offset in range(0,500,100):
        page=await rest.list_training_runs(limit=100,offset=offset)
        for r in page.training_runs:
            m=r.user_metadata or {}
            if m.get("study_id")==p["study_id"] and m.get("protocol_sha256")==digest(p) and m.get("seed")==str(seed) and m.get("arm")=="price_only" and m.get("github_run_id")==state["github_run_id"]:matches.append(r)
        if len(page.training_runs)<100:break
    if len(matches)!=1:raise ValueError("Original training-run identity is not unique")
    checkpoints=(await rest.list_checkpoints(matches[0].training_run_id)).checkpoints
    training=[c for c in checkpoints if c.checkpoint_type=="training" and (c.user_metadata or {}).get("update")=="100"]
    if len(training)!=1:raise ValueError("Original update-100 optimizer state missing")
    meta={"study_id":p["study_id"],"seed":str(seed),"purpose":"evaluation_only_storage_recovery","parent_state_sha256":hashlib.sha256(training[0].tinker_path.encode()).hexdigest(),"optimizer_updates":"0"}
    client=tinker.ServiceClient(display_name="Compute Forecast v12 evaluation recovery seed"+str(seed),user_metadata=meta)
    try:trainer=await client.create_training_client_from_state_with_optimizer(training[0].tinker_path)
    except tinker.BillingError:
        write(out/"recovery-pending.json",{"seed":seed,"status":"blocked","reason":"Tinker checkpoint storage still prevents loading an existing training state","actual_optimizer_updates_preserved":100,"new_optimizer_updates":0});return
    renderer=get_renderer(p["model"]["renderer"],trainer.get_tokenizer())
    # Snapshot clients are ephemeral and fixed; no new persistent checkpoint is needed.
    sampler100=await trainer.save_weights_and_get_sampling_client()
    dev=dataset["groups"]["development"];test=dataset["groups"]["retrospective"]
    measured100=await evaluate(dev,sampler100,renderer,p,seed,"price_only","dev_update_100",out/"development-100.json")
    cp={"update":100,"checkpoint_id":hashlib.sha256(training[0].tinker_path.encode()).hexdigest()[:24],"checkpoint_identity_type":"retained_training_state","development":measured100["summary"],"is_base":False}
    state["checkpoints"]=[r for r in state["checkpoints"] if r["update"]!=100]+[cp]
    selected=min(state["checkpoints"],key=lambda r:(r["development"]["primary_pinball"],r["update"]))
    write(out/"selection.json",{"selected":selected,"rule":p["evaluation"]["selection"],"locked_before_retrospective_evaluation":True,"selected_at":now(),"eligible_updates":[r["update"] for r in state["checkpoints"]]})
    base=await client.create_sampling_client(base_model=p["model"]["base"])
    if selected["update"]==0:sampler=base
    elif selected["update"]==100:sampler=sampler100
    else:
        saved=[c for c in checkpoints if c.checkpoint_type=="sampler" and (c.user_metadata or {}).get("update")==str(selected["update"])]
        if len(saved)!=1:raise ValueError("Selected original sampler is not unique")
        sampler=await client.create_sampling_client(model_path=saved[0].tinker_path)
    measured=await evaluate(test,sampler,renderer,p,seed,"price_only","selected_direct",out/"evaluation-selected.json")
    initial=await evaluate(test,base,renderer,p,seed,"price_only","base_direct",out/"evaluation-base.json")
    references={}
    for method in p["evaluation"]["references"]:
        cells=reference_cells(test,dataset["baselines"],method)
        references[method]={"summary":summarize(cells),"cells":cells,"comparison":matched(measured["cells"],cells)}
    state.update(status="completed",completed_at=now(),selected=selected,retrospective=measured["summary"],base=initial["summary"],comparison_to_base=matched(measured["cells"],initial["cells"]),references=references,recovery={"reason":"Persistent sampler creation hit the free checkpoint-storage limit after 100 optimizer updates","original_workflow_run_id":state["github_run_id"],"recovery_workflow_run_id":os.environ["GITHUB_RUN_ID"],"parent_training_state_sha256":meta["parent_state_sha256"],"new_optimizer_updates":0,"sampling_kind":"ephemeral_fixed_snapshot","original_checkpoints_and_scores_preserved":True},source_attribution="Pacific Machines (2026), gpu-price-pack v0.1.1-handover, CC BY 4.0 compilation; exact approved component identities retained")
    case=sorted(test,key=lambda t:(t["series_id"],t["origin"]))[0]
    state["illustrative_case"]={"selection":"Lexicographically first eligible retrospective task, independent of performance","task_id":case["task_id"],"metadata":case["metadata"],"origin":case["origin"],"history":case["context"],"target_dates":case["target_dates"],"outcomes":case["outcomes"]}
    write(out/"result.json",state);write(out/"progress.json",state)
    print("DIRECT_RECOVERY_COMPLETED "+json.dumps({"seed":seed,"new_optimizer_updates":0,"selected_update":selected["update"],"evaluation":measured["summary"]}),flush=True)
def main():
    p=argparse.ArgumentParser();p.add_argument("--inputs",required=True);p.add_argument("--output",required=True);p.add_argument("--seed",type=int,required=True);a=p.parse_args();asyncio.run(recover(a.inputs,a.output,a.seed))
if __name__=="__main__":main()
