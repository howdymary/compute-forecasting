"""Read-only dependency wait; no experiment or provider reservation."""
import json,subprocess,time
start=time.monotonic()
while True:
 p=subprocess.run(["gh","api","repos/howdymary/compute-forecasting/actions/runs/43724017012"],text=True,capture_output=True,check=True);r=json.loads(p.stdout);assert r["head_sha"]=="e5b3aa1c0a6bd69fd2107c79d7506e5f619a5435"
 if r["status"]=="completed":print("SOURCE_UNION_RUN_COMPLETED",r["conclusion"],flush=True);break
 if time.monotonic()-start>1000:raise RuntimeError("Dependency remains active; no result inferred")
 time.sleep(15)
