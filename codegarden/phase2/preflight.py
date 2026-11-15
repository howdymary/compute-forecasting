"""Read-only account refresh and current arena capture, no billable calls."""
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from providers import http,cli
from supervisor import verify
def get(url):
    with urllib.request.urlopen(url,timeout=40) as r:return r.read()
def main():
    out=ROOT/"artifacts/phase2";out.mkdir(parents=True,exist_ok=True)
    result={"recorded_at":dt.datetime.now(dt.timezone.utc).isoformat(),"read_only":True,"billable_calls":0}
    past=http("https://api.past.dev/api/v1/usage",os.environ["PAST_API_KEY"])
    result["past"]={"live_remaining_credits":past.get("balance",{}).get("left"),"usage_schema":list(past)}
    if not isinstance(result["past"]["live_remaining_credits"],(int,float)):raise RuntimeError("Past balance unknown")
    modal=json.loads(cli("modal","billing","summary","--json"))
    result["modal"]={"metered_account_cost":modal["metered_cost"],"billed_account_cost":modal["billed_cost"],"adjustments":modal["adjustments"]}
    # Preserve actual command results privately while publishing safe schema/status only.
    result["tinker_usage_query_available"]=False
    try:
        end=(dt.datetime.now(dt.timezone.utc).replace(minute=0,second=0,microsecond=0)+dt.timedelta(hours=1)).isoformat().replace("+00:00","Z")
        usage=cli("tinker","billing","usage","2026-11-14T00:00:00Z",end,"--csv","-")
        result["tinker_usage_query_available"]=True
        result["tinker_csv_lines"]=len(usage.splitlines())
        result["tinker_usage_response_sha256"]=hashlib.sha256(usage.encode()).hexdigest()
    except Exception as e:result["tinker_usage_error"]=type(e).__name__
    spec=json.loads((ROOT/"budget/shared-allocation.json").read_text())
    spec["providers"]["past"]["balance_at_snapshot"]=min(spec["providers"]["past"]["balance_at_snapshot"],result["past"]["live_remaining_credits"])
    spec["authenticated_preflight_at"]=result["recorded_at"]
    (ROOT/"budget/shared-allocation.json").write_text(json.dumps(spec,indent=2)+"\n")
    raw=get("https://einsteinarena.com/api/problems/two-deletion-code-16");problem=json.loads(raw)
    old=json.loads((ROOT/"artifacts/sources/arena_problem.json").read_text())
    result["problem"]={"response_sha256":hashlib.sha256(raw).hexdigest(),"keys":list(problem),"verifier_sha256":hashlib.sha256(problem["verifier"].encode()).hexdigest()}
    result["problem"]["matches_pinned_verifier"]=problem["verifier"].strip()==(ROOT/"artifacts/sources/official_verifier.py").read_text().strip()
    (out/"official_problem.json").write_text(json.dumps(problem,indent=2))
    raw=get("https://einsteinarena.com/api/solutions/best?problem_id=34&limit=5");leaders=json.loads(raw);entries=[]
    for i,row in enumerate(leaders):
        words=row["data"]["words"];path=out/("worker_arena_"+str(i)+".txt");path.write_text("\n".join(sorted(words))+"\n")
        checked=verify(path);entries.append({"id":row["id"],"author":row["agentName"],"listed_score":row["score"],"verification":checked,"witness":str(path.relative_to(ROOT.parent))})
    result["arena"]={"checked_at":result["recorded_at"],"response_sha256":hashlib.sha256(raw).hexdigest(),"leaders":entries,
      "strongest_reproduced":max(x["verification"]["cardinality"] for x in entries)}
    result["target"]=result["arena"]["strongest_reproduced"]+1
    result["account_reservations"]="All previous phase-one holds remain imported; no cost reconciliation is assumed from missing usage rows."
    (out/"preflight.json").write_text(json.dumps(result,indent=2))
    print("PHASE2_PREFLIGHT "+json.dumps({"target":result["target"],"past_remaining":result["past"]["live_remaining_credits"],"modal_metered":modal["metered_cost"],"arena_best":result["target"]-1}),flush=True)
if __name__=="__main__":main()
