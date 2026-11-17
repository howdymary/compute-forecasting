"""Check private cloud recovery transport before any new optimizer update."""
import hashlib,json,pathlib,subprocess
from compute_forecast.probability_v18 import digest
p=json.loads(pathlib.Path("configs/direct-probability-v18.json").read_text())
source=pathlib.Path("inputs/probability-v18/audit.json");destination=pathlib.Path("private/probability-v18/transport-check.json");destination.parent.mkdir(parents=True,exist_ok=True)
remote="/probability-v18/"+digest(p)+"/transport-check.json"
for args in (["modal","volume","put","compute-forecast-data",str(source),remote,"--force"],["modal","volume","get","compute-forecast-data",remote,str(destination),"--force"]):
    r=subprocess.run(args,capture_output=True,text=True)
    if r.returncode:raise RuntimeError("Private volume transport preflight failed: "+r.stderr[-1000:])
assert source.read_bytes()==destination.read_bytes()
print(json.dumps({"status":"verified","transport":"private Modal volume","new_optimizer_updates":0}))
