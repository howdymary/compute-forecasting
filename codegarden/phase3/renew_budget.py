"""Refresh read-only account evidence and allocate disjoint existing credits, no billing changes."""
import base64,datetime as dt,json,os,pathlib,subprocess,sys,traceback
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import Ledger,cli,http
OUT=ROOT/"artifacts/phase3/budget_renewal_002";OUT.mkdir(parents=True,exist_ok=True)
def api(path):
 p=subprocess.run(["gh","api",path],capture_output=True,text=True,check=True);return json.loads(p.stdout)
def read(path,ref):
 r=api("repos/"+os.environ["GITHUB_REPOSITORY"]+"/contents/"+path+"?ref="+ref);return json.loads(base64.b64decode(r["content"]))
def main():
 status={"status":"running","source_sha":os.environ["GITHUB_SHA"],"at":dt.datetime.now(dt.timezone.utc).isoformat()}
 try:
  prev=read("codegarden/artifacts/phase3/persistent_bundle_001/ledger_progress.json","codegarden-modal-005")
  try:
   latest=read("codegarden/artifacts/phase3/persistent_bundle_001/status.json","codegarden-modal-005")
   if latest.get("budget"):
    for p,v in latest["budget"].items():
     if v["reserved"]+v["provider_reported_or_estimated"]>prev[p]["reserved"]+prev[p]["provider_reported_or_estimated"]:prev[p]=v
  except Exception:pass
  history={"source_run":"renewal2-carried-"+os.environ["GITHUB_SHA"],"conservative_totals":{p:v["reserved"]+v["provider_reported_or_estimated"] for p,v in prev.items()},
   "reason":"Every previous charge and unresolved reservation retained; last persistent batch includes failed-launch hold."}
  modal=json.loads(cli("modal","billing","summary","--json"))
  gross=float(modal["metered_cost"]);floor=248.87-max(0,gross-1.64005948)
  past=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])
  balance=past.get("balance",{}).get("left");assert isinstance(balance,(int,float))
  # Fresh UI evidence; no auto-reload, plan or provider limit changed.
  ui=json.loads((ROOT/"phase3/balance_snapshot_0720.json").read_text())
  spec=json.loads((ROOT/"phase3/renewal_001.json").read_text())
  spec.update(source_observed_at=status["at"],expires_at="2026-11-15T12:00:00Z",no_new_billable_after="2026-11-15T11:45:00Z",
   authenticated_preflight_at=ui["observed_at"],source_note="Read-only refreshed Tinker/Exa dashboard evidence plus current Modal gross usage and live past balance. Increase only internal CodeGarden Modal allocation; no provider billing settings changed.")
  spec["providers"]["exa"]["balance_at_snapshot"]=ui["exa_remaining_usd"]
  spec["providers"]["tinker"]["balance_at_snapshot"]=ui["tinker_remaining_usd"]
  spec["providers"]["past"]["balance_at_snapshot"]=balance
  # Keep the older lower Modal baseline: Ledger already deducts gross growth from that snapshot on each reservation.
  spec["providers"]["modal"]["codegarden_cap"]=100
  guard=sum(spec["providers"]["modal"][k] for k in ["boundforge_reserved","forecasting_pending_guard","verification_reserve"])
  assert floor>=guard+100,"Insufficient known floor after full other-project reserves"
  spec["coordination"]="One serialized CodeGarden provider coordinator; cumulative holds imported. Full BoundForge operational caps and forecasting pending guards remain reserved. Modal internal allocation raised 50 to 100 only after account-wide usage and prepaid-credit floor check."
  (ROOT/"budget/shared-allocation.json").write_text(json.dumps(spec,indent=2));(ROOT/"budget/historical-usage.json").write_text(json.dumps(history,indent=2))
  ledger=Ledger(OUT)
  status.update(status="renewed",live_past_balance=balance,modal_account_summary=modal,
   modal_remaining_credit_conservative_floor=floor,modal_other_and_verification_reserves=guard,modal_cumulative_operational_cap=100,
   modal_unallocated_floor_after_all_caps=floor-guard-100,dashboard_evidence=ui,budget=ledger.summary(),
   no_provider_settings_changed=True,no_new_billable_calls=True)
 except Exception as e:status.update(status="failed_no_new_spending",error=str(e)[:1000]);traceback.print_exc()
 (OUT/"receipt.json").write_text(json.dumps(status,indent=2));print("BUDGET_RENEWAL",json.dumps(status),flush=True)
if __name__=="__main__":main()
