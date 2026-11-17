"""Register fixed ensemble arithmetic and validate a bounded Tinker quantile-head pilot."""
import asyncio,hashlib,json,os,pathlib,statistics
from compute_forecast.quantile_v20 import *
from compute_forecast.verify_market_v19 import verify
from compute_forecast.train_market_v19 import load_inputs,write
def read(p):return json.loads(pathlib.Path(p).read_bytes())
async def main():
    import tinker
    import torch
    p=read("configs/quantile-training-v20.json");parent=p["parent"]
    raw=pathlib.Path(parent["report_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==parent["report_sha256"]
    report=json.loads(raw);verify(report)
    data,old,audit=load_inputs("inputs/market-state-v19")
    assert digest(data)==parent["dataset_sha256"]
    runs=[r for r in report["runs"] if r["arm"]=="price"];assert [r["seed"] for r in runs]==[17,29,43]
    development=[]
    for run in runs:
        rows=[r for case in report["cases"] for cp in case["checkpoints"] if cp["arm"]=="price" and cp["seed"]==run["seed"] and cp["update"]==run["selected"]["update"] for r in cp["rows"]]
        assert summarize(rows)==run["selected"]["development"];development.append(rows)
    dev={k:{"cells":ensemble(development,k)} for k in ("quantile_average","probability_pool")}
    for v in dev.values():v["summary"]=summarize(v["cells"])
    choice=min(dev,key=lambda k:(dev[k]["summary"]["primary_pinball"],0 if k=="quantile_average" else 1))
    root=pathlib.Path("artifacts/quantile-training-v20/preflight")
    selection={"method":choice,"development":{k:v["summary"] for k,v in dev.items()},"selected_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),"before_additional_retrospective_ensemble_calculation":True,"weights_fitted":False}
    write(root/"ensemble-selection.json",selection)
    retrospective={k:{"cells":ensemble([r["retrospective"]["cells"] for r in runs],k)} for k in dev}
    for v in retrospective.values():v["summary"]=summarize(v["cells"])
    diagnostics={"market_minus_price":[{"seed":r["seed"],**decompose(next(v for v in report["runs"] if v["arm"]=="market" and v["seed"]==r["seed"])["retrospective"]["cells"],r["retrospective"]["cells"])} for r in runs],"ensemble_minus_parent":{k:decompose(v["cells"],runs[0]["retrospective"]["cells"]) for k,v in retrospective.items()}}
    scale=statistics.median(t["anchor"] for t in data["groups"]["training"])
    rest=tinker.RestClient();items=[]
    for offset in range(0,2000,100):
        page=await rest.list_user_checkpoints(limit=100,offset=offset);items.extend(page.checkpoints)
        if len(page.checkpoints)<100:break
    found={}
    for seed,identifier in parent["checkpoint_ids"].items():
        matches=[c for c in items if hashlib.sha256(c.tinker_path.encode()).hexdigest()[:24]==identifier and (c.user_metadata or {}).get("study_id")=="market-state-v19"]
        found[seed]=len(matches)==1
    count=len(items);capacity=count+3<=p["limits"]["checkpoint_preservation_limit"]
    readiness={"study_id":p["study_id"],"protocol_sha256":digest(p),"parent_report_sha256":parent["report_sha256"],"dataset_sha256":digest(data),"training_ready":capacity and all(found.values()),"storage_preservation":{"current_states":count,"pilot_new_states":3,"limit":100,"deletion_performed":False},"frozen_parent_availability":found,"loss_scale":scale,"training_windows":len(data["groups"]["training"]),"horizon_examples":sum(len(p["data"]["horizons"]) for _ in data["groups"]["training"]),"development_cases":len(data["groups"]["development"]),"new_optimizer_updates":0,"reasons":([] if capacity else ["Insufficient checkpoint preservation capacity; no deletion or billing change authorized"])+([] if all(found.values()) else ["Frozen parent checkpoint unavailable"]),"prospective_accuracy":"not established"}
    write(root/"ensembles.json",{"study_id":p["study_id"],"development":dev,"selection":selection,"retrospective":retrospective,"classification":"Additional exploratory analysis of already opened periods; no new training or future accuracy"})
    write(root/"diagnostics.json",diagnostics);write(root/"readiness.json",readiness)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a") as f:f.write("ready="+str(readiness["training_ready"]).lower()+"\n")
    print(json.dumps(readiness),flush=True)
if __name__=="__main__":asyncio.run(main())
