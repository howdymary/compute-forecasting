"""Read-only dependency wait; no experiment or provider reservation."""
import json,subprocess,time
start=time.monotonic()
while True:
 p=subprocess.run(["gh","api","repos/howdymary/compute-forecasting/actions/runs/43725457546"],text=True,capture_output=True,check=True);r=json.loads(p.stdout);assert r["head_sha"]=="005ce3f7bdbfb470ffa011a28716b76009ed24be"
 if r["status"]=="completed":print("SOURCE_UNION_RUN_COMPLETED",r["conclusion"],flush=True);break
 if time.monotonic()-start>1000:raise RuntimeError("Dependency remains active; no result inferred")
 time.sleep(15)
