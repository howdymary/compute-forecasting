"""Rebind retained preflight inputs after an API-only compatibility correction; no pack rerun."""
import json,pathlib,statistics
from compute_forecast.probability_v18 import digest,levels,support,bin_index
root=pathlib.Path("inputs/probability-v18")
data=json.loads((root/"dataset.json").read_text());audit=json.loads((root/"audit.json").read_text())
old=json.loads(pathlib.Path("configs/direct-probability-v18-preflight-v1.json").read_text());p=json.loads(pathlib.Path("configs/direct-probability-v18.json").read_text())
assert digest(data)==audit["dataset_sha256"] and data["protocol_sha256"]==digest(old)
assert old["data"]==p["data"] and old["model"]==p["model"]
previous=digest(data);inputs_hash=digest({"groups":data["groups"],"references":data["references"],"coverage":data["coverage"]})
data["protocol_sha256"]=digest(p);data["log_levels"]=levels(data["groups"]["training"],p)
for phase,tasks in data["groups"].items():
    nearest=[];outside=0;total=0
    for task in tasks:
        z=support(task["anchor"],data["log_levels"])
        for h,y in zip(p["data"]["horizons"],task["outcomes"]):
            outside+=int(y<z[0] or y>z[-1]);total+=1
            if h==7:nearest.append(abs(z[bin_index(z,y)]-y))
    audit["phases"][phase]["out_of_support"]=outside;audit["phases"][phase]["in_support_fraction"]=1-outside/total
    audit["phases"][phase]["median_seven_day_quantization_ae"]=statistics.median(nearest)
assert inputs_hash==digest({"groups":data["groups"],"references":data["references"],"coverage":data["coverage"]})
dev=audit["phases"]["development"];assert dev["in_support_fraction"]>=.95 and dev["median_seven_day_quantization_ae"]<=dev["median_seven_day_persistence_ae"]+1e-12
audit.update(parent_dataset_sha256=previous,unchanged_numerical_inputs_sha256=inputs_hash,protocol_sha256=digest(p),dataset_sha256=digest(data),log_levels=data["log_levels"],compatibility_revision=p["compatibility_revision"],training_ready=True)
for name,value in (("dataset.json",data),("audit.json",audit)):(root/name).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
out=pathlib.Path("artifacts/probability-v18-audit");out.mkdir(parents=True,exist_ok=True);(out/"audit.json").write_text(json.dumps(audit,indent=2)+"\n")
print(json.dumps({"status":"rebound_unchanged_windows","new_levels":len(data["log_levels"]),"dataset_sha256":digest(data),"phases":{k:{"windows":v["windows"],"series":v["series"],"source_windows":v["source_windows"]} for k,v in audit["phases"].items()}}),flush=True)
