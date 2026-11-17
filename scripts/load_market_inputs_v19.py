"""Download only the engine-bound audited input; never publish private resource paths."""
import hashlib,json,pathlib,subprocess
from compute_forecast.probability_v18 import digest
root=pathlib.Path("inputs/market-state-v19");root.mkdir(parents=True,exist_ok=True)
pointer=json.loads((root/"input-key.json").read_bytes());key=pointer["private_key"]
assert len(key)==64 and all(c in "0123456789abcdef" for c in key)
for name in ("dataset.json","audit.json"):
    subprocess.run(["modal","volume","get","compute-forecast-data","/market-state-v19/inputs/"+key+"/"+name,str(root/name),"--force"],check=True,capture_output=True)
data=json.loads((root/"dataset.json").read_bytes());audit=json.loads((root/"audit.json").read_bytes())
assert digest(data)==audit["dataset_sha256"]==pointer["dataset_sha256"]
assert audit["training_ready"],"Registered readiness gate failed"
assert data["protocol_sha256"]==digest(json.loads(pathlib.Path("configs/market-state-v19.json").read_bytes()))
print("Validated identical input hash for both arms")
