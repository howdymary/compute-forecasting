"""Fetch hash-verified public research only; never loads model or account secrets."""
import hashlib,json,threading,time,urllib.error,urllib.request
BASE="https://raw.githubusercontent.com/howdymary/mochi-demo/compute-observatory/"
_lock=threading.Lock();_cache={}
def read_report():
    with _lock:
        if _cache and time.monotonic()-_cache["at"]<15:return _cache["value"]
        try:
            with urllib.request.urlopen(BASE+"results/direct-v12/latest.json",timeout=30) as response:index=json.load(response)
        except urllib.error.HTTPError as e:
            if e.code==404:return {"study_id":"direct-forecast-v12","status":"running","runs":[],"cases":[],"pending_reason":"No evaluation report has been published"}
            raise
        path=index["report_path"]
        if not path.startswith("results/direct-v12/runs/") or ".." in path:raise ValueError("Invalid public report pointer")
        with urllib.request.urlopen(BASE+path,timeout=60) as response:raw=response.read(15_000_001)
        if len(raw)>15_000_000 or hashlib.sha256(raw).hexdigest()!=index["report_sha256"]:raise ValueError("Public report hash mismatch")
        value=json.loads(raw)
        if value.get("study_id")!="direct-forecast-v12":raise ValueError("Unexpected study")
        _cache.update(at=time.monotonic(),value=value);return value
