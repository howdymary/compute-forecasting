"""Resolve a successful permission-filtered audit and lock SDK versions."""
import hashlib,importlib.metadata,json,os,pathlib,shutil,subprocess,time
from compute_forecast.direct_forecast_v12 import digest
p=json.loads(pathlib.Path("configs/direct-forecast-v12.json").read_text());repo=os.environ["GITHUB_REPOSITORY"];destination=pathlib.Path("inputs/direct-v12")
destination.mkdir(parents=True,exist_ok=True)
for attempt in range(30):
    runs=json.loads(subprocess.check_output(["gh","api",f"repos/{repo}/actions/workflows/audit-direct-v12.yml/runs?branch=compute-observatory&per_page=12"],text=True))["workflow_runs"]
    found=False
    for run in runs:
        if run["conclusion"]!="success":continue
        target=pathlib.Path(os.environ["RUNNER_TEMP"])/("direct-audit-"+str(run["id"]))
        if not target.exists():
            r=subprocess.run(["gh","run","download",str(run["id"]),"--repo",repo,"--name","direct-v12-audit-"+str(run["id"]),"--dir",str(target)],capture_output=True)
            if r.returncode:continue
        audit_file=target/"audit.json"
        if not audit_file.exists():continue
        audit=json.loads(audit_file.read_text())
        if audit["protocol_sha256"]!=digest(p):continue
        payload=json.loads((target/"dataset.json").read_text())
        assert digest(payload)==audit["dataset_sha256"] and payload["protocol_sha256"]==digest(p)
        assert audit["price_only_ready"] and not audit["protected_outcomes_loaded"]
        assert all(x["metadata"]["instrument_class"] in p["data"]["instrument_classes"] for x in audit["series"])
        for name in ("audit.json","dataset.json","ATTRIBUTION.txt"):shutil.copyfile(target/name,destination/name)
        receipt={"audit_run_id":run["id"],"audit_source_sha":run["head_sha"],"protocol_sha256":digest(p),"dataset_sha256":digest(payload),"resolved_at":time.time(),"packages":{n:importlib.metadata.version(n) for n in ("tinker","tinker-cookbook","torch","transformers","numpy")}}
        (destination/"input-receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        found=True;break
    if found:break
    time.sleep(10)
else:raise RuntimeError("No successful permission-filtered audit matches the registered protocol")
lock=subprocess.check_output(["python","-m","pip","freeze","--exclude-editable"],text=True)
(destination/"requirements-lock.txt").write_text(lock)
print("DIRECT_INPUTS_READY "+json.dumps({"audit":receipt["audit_run_id"],"training":audit["phase_tasks"]["training"],"development":audit["phase_tasks"]["development"],"retrospective":audit["phase_tasks"]["retrospective"],"packages":receipt["packages"]}))
