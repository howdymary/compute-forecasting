"""Read-only account inspection. Never creates models, apps, topups, or paid searches."""
import json,os,subprocess,sys,datetime,pathlib
def command(argv):
    try:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=90)
        if p.returncode:return {"available":False,"exit_code":p.returncode}
        return {"available":True,"data":json.loads(p.stdout)}
    except Exception as e:return {"available":False,"error_type":type(e).__name__}
def main():
    now=datetime.datetime.now(datetime.timezone.utc)
    result={"project":"codegarden","checked_at":now.isoformat(),"read_only":True,
      "credentials_present":{k:bool(os.getenv(k)) for k in ["EXA_API_KEY","PAST_API_KEY","TINKER_API_KEY","MODAL_TOKEN_ID","MODAL_TOKEN_SECRET"]},
      "modal_billing_summary":command(["modal","billing","summary","--json"]),
      "modal_running_apps":command(["modal","app","list","--json"]),
      "actual_codegarden_billable_calls":0,"balance_is_not_gross_spend":True}
    public={"project":"codegarden","checked_at":result["checked_at"],"credentials_present":result["credentials_present"],
      "modal_summary_available":result["modal_billing_summary"]["available"],
      "modal_summary_schema":list(result["modal_billing_summary"].get("data",{})) if isinstance(result["modal_billing_summary"].get("data"),dict) else None,
      "modal_apps_available":result["modal_running_apps"]["available"],
      "billable_enabled":False,"reason":"Balance and shared reservations need explicit verified interpretation."}
    out=pathlib.Path("codegarden/artifacts/provider_preflight.json");out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(public,indent=2)+"\n")
    print(json.dumps(public));return 0
if __name__=="__main__":sys.exit(main())
