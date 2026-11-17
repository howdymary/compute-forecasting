"""Learning-rate selection consumes development fields only; pilot optimization is reused."""
import json,pathlib
root=pathlib.Path("artifacts/probability-v18-pilot");out=pathlib.Path("artifacts/probability-v18-selection");out.mkdir(parents=True,exist_ok=True)
choices={}
for objective in ("ce","crps"):
    candidates=[]
    for rate in ("low","high"):
        r=json.loads((root/objective/rate/"result.json").read_text())
        assert r["status"]=="completed" and r["seed"]==17
        candidates.append({"rate_key":rate,"learning_rate":r["learning_rate"],"selected_update":r["selected"]["update"],"development_pinball":r["selected"]["development"]["primary_pinball"],"protocol_sha256":r["protocol_sha256"],"dataset_sha256":r["dataset_sha256"]})
    chosen=min(candidates,key=lambda x:(x["development_pinball"],x["selected_update"],x["learning_rate"]))
    choices[objective]={"selected":chosen,"candidates":candidates}
value={"study_id":"direct-probability-v18","selection_use":"Development only; no retrospective metric enters this computation","pilot_seed":17,"choices":choices}
(out/"learning-rates.json").write_text(json.dumps(value,indent=2)+"\n");print(json.dumps(value),flush=True)
