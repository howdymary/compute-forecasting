"""Load only hash-bound private preparation output; never print private paths or model resources."""
import json,pathlib,subprocess
from compute_forecast.probability_v18 import digest
root=pathlib.Path("inputs/ce-continuation-v21");root.mkdir(parents=True,exist_ok=True)
pointer=json.loads(pathlib.Path("artifacts/ce-continuation-v21-preflight/input-key.json").read_bytes());key=pointer["input_key"]
assert len(key)==64 and all(c in "0123456789abcdef" for c in key)
for name in ("dataset.json","audit.json"):
    r=subprocess.run(["modal","volume","get","compute-forecast-data","/ce-continuation-v21/inputs/"+key+"/"+name,str(root/name),"--force"],capture_output=True,text=True)
    if r.returncode:raise RuntimeError("Unable to retrieve registered private input")
data=json.loads((root/"dataset.json").read_bytes());audit=json.loads((root/"audit.json").read_bytes());p=json.loads(pathlib.Path("configs/ce-continuation-v21.json").read_bytes())
assert digest(data)==audit["dataset_sha256"]==pointer["dataset_sha256"] and data["protocol_sha256"]==digest(p)
assert data["parent_dataset_sha256"]==p["parent"]["dataset_sha256"]
for arm in ("same","expanded"):assert digest(data["training"][arm])==audit["training_corpus_sha256"][arm]
print(json.dumps({"status":"validated","dataset_sha256":digest(data),"same_windows":len(data["training"]["same"]),"expanded_windows":len(data["training"]["expanded"]),"expanded_ready":data["expanded_ready"]}))
