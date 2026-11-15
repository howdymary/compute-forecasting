"""Read-only provider inspection. No model creation, search, topup, or app launch."""
import json,os,subprocess,sys,datetime,pathlib,urllib.request,urllib.error
def command(argv):
    try:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=90)
        if p.returncode:return {"available":False,"exit_code":p.returncode,"error_tail":p.stderr[-300:]}
        return {"available":True,"data":json.loads(p.stdout)}
    except Exception as e:return {"available":False,"error_type":type(e).__name__}
def get(url,key,header):
    if not key:return {"available":False,"reason":"credential_absent"}
    try:
        r=urllib.request.Request(url,headers={header:key})
        with urllib.request.urlopen(r,timeout=30) as response:return {"available":True,"data":json.load(response)}
    except urllib.error.HTTPError as e:return {"available":False,"http_status":e.code}
    except Exception as e:return {"available":False,"error_type":type(e).__name__}
def main():
    now=datetime.datetime.now(datetime.timezone.utc);bin=pathlib.Path(sys.executable).parent
    modal=command([str(bin/"modal"),"billing","summary","--json"])
    apps=command([str(bin/"modal"),"app","list","--json"])
    exa=get("https://admin-api.exa.ai/team-management/credits",
      os.getenv("EXA_SERVICE_KEY") or os.getenv("EXA_API_KEY"),"x-api-key")
    past=get("https://api.past.dev/api/v1/usage","Bearer "+os.getenv("PAST_API_KEY",""),"Authorization")
    result={"project":"codegarden","checked_at":now.isoformat(),"read_only":True,
      "credentials_present":{k:bool(os.getenv(k)) for k in ["EXA_API_KEY","PAST_API_KEY","TINKER_API_KEY","MODAL_TOKEN_ID","MODAL_TOKEN_SECRET"]},
      "modal_summary_available":modal["available"],
      "modal_summary_schema":list(modal.get("data",{})) if isinstance(modal.get("data"),dict) else None,
      "modal_summary_structure":{k:type(v).__name__ for k,v in modal.get("data",{}).items()} if isinstance(modal.get("data"),dict) else None,
      "modal_error":{k:v for k,v in modal.items() if k!="data"} if not modal["available"] else None,
      "modal_apps_available":apps["available"],
      "modal_apps_schema":list(apps.get("data",{})) if isinstance(apps.get("data"),dict) else type(apps.get("data")).__name__,
      "exa_balance_available":exa["available"],"exa_error":{k:v for k,v in exa.items() if k!="data"},
      "exa_can_cover_5usd":isinstance(exa.get("data",{}).get("credits_usd"),(int,float)) and exa["data"]["credits_usd"]>=5,
      "past_balance_available":past["available"],"past_error":{k:v for k,v in past.items() if k!="data"},
      "past_can_cover_5000credits":isinstance(past.get("data",{}).get("balance",{}).get("left"),(int,float)) and past["data"]["balance"]["left"]>=5000,
      "billable_calls_in_this_preflight":0,"billable_enabled_for_this_preflight":False,
      "reason":"Read-only diagnostic only. Billable stages separately require a valid explicit Ledger allocation and reservation."}
    out=pathlib.Path("codegarden/artifacts/provider_preflight_v2.json");out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2)+"\n");print(json.dumps(result))
if __name__=="__main__":main()
