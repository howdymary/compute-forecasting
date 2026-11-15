"""Read-only provider billing probes. Never launches paid compute/search/training."""
import datetime as dt
import json, os, pathlib, subprocess, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
def request(url, key, header="Authorization"):
    value = ("Bearer " if header == "Authorization" else "") + key
    req = urllib.request.Request(url, headers={header: value, "User-Agent":"BoundForge/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return {"status":r.status, "data":json.load(r)}
    except urllib.error.HTTPError as e:
        return {"status":e.code, "reason":"account endpoint rejected credentials"}
    except Exception as e:
        return {"status":"unavailable", "reason":type(e).__name__}
def cli(*args):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=45)
        if p.returncode:
            return {"status":"unavailable","returncode":p.returncode}
        try: return {"status":200,"data":json.loads(p.stdout)}
        except ValueError: return {"status":"unparsed","reason":"non-JSON output"}
    except Exception as e:
        return {"status":"unavailable","reason":type(e).__name__}
def main():
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    result={"timestamp":now, "policy":"Existing credits only; disabled until balance AND safe billing boundary are verified.", "providers":{}}
    keys={"exa":"EXA_API_KEY","past":"PAST_API_KEY","tinker":"TINKER_API_KEY","modal":"MODAL_TOKEN_ID"}
    for provider,key in keys.items():
        result["providers"][provider]={"credential_present":bool(os.environ.get(key)), "enabled":False, "initial_cap":None, "reserved":0, "actual":0, "expiration":None}
    exakey=os.environ.get("EXA_SERVICE_KEY") or os.environ.get("EXA_API_KEY")
    if exakey:
        r=request("https://admin-api.exa.ai/team-management/credits",exakey,"x-api-key")
        if r.get("status")==200:
            d=r["data"]
            r={"status":200,"credits_usd":d.get("credits_usd"),"expiring_credits":d.get("expiring_credits"),"metadata":d.get("metadata")}
        result["providers"]["exa"]["probe"]=r
    if os.environ.get("PAST_API_KEY"):
        r=request("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])
        if r.get("status")==200:
            d=r["data"]
            r={"status":200,"month":d.get("month"),"balance":d.get("balance"),"project":{k:v for k,v in d.get("project",{}).items() if k!="slug"},"metered":d.get("metered")}
        result["providers"]["past"]["probe"]=r
    if os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET"):
        result["providers"]["modal"]["probe"]=cli("modal","billing","summary","--json")
    if os.environ.get("TINKER_API_KEY"):
        result["providers"]["tinker"]["reason"]="Official CLI exposes gross usage, not remaining prepaid balance. No training/sampling enabled."
    for provider,d in result["providers"].items():
        d.setdefault("reason","Balance, expiration and no-overage boundary require verification; no paid operations were launched.")
    (OUT/"budget-preflight.json").write_text(json.dumps(result,indent=2))
    print("BOUNDFORGE_PREFLIGHT "+json.dumps(result),flush=True)
if __name__=="__main__": main()
