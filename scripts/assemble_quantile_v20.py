"""Preserve completed, interrupted and gated outcomes without rewriting prior studies."""
import hashlib,json,os,pathlib
from compute_forecast.probability_v18 import digest,summarize
from compute_forecast.quantile_v20 import decompose
from compute_forecast.train_market_v19 import write
from compute_forecast.verify_quantile_v20 import verify
def read(p):return json.loads(pathlib.Path(p).read_bytes())
root=pathlib.Path("artifacts/quantile-training-v20");pre=root/"preflight";out=root/"public";p=read("configs/quantile-training-v20.json")
parent=read(p["parent"]["report_path"]);ensembles=read(pre/"ensembles.json");ready=read(pre/"readiness.json")
runs=[];incomplete=[]
for seed in (17,29,43):
    d=root/"models"/str(seed)
    if (d/"result.json").exists():
        state=read(d/"result.json")
        assert state["status"]=="completed" and state["protocol_sha256"]==digest(p)
        dev={str(c["update"]):read(d/("development-"+str(c["update"])+".json")) for c in state["checkpoints"]}
        for c in state["checkpoints"]:assert summarize(dev[str(c["update"])]["cells"])==c["development"]
        runs.append({"state":state,"development":dev,"retrospective":read(d/"evaluation-selected.json"),"head_zero":read(d/"evaluation-zero.json")})
    elif (d/"progress.json").exists():incomplete.append(read(d/"progress.json"))
comparisons=[]
for run in runs:
    seed=run["state"]["seed"];original=next(r for r in parent["runs"] if r["arm"]=="price" and r["seed"]==seed)
    references={"head_zero":run["head_zero"]["cells"],"frozen_parent":original["retrospective"]["cells"],"selected_ensemble":ensembles["retrospective"][ensembles["selection"]["method"]]["cells"],"official_drift":parent["controls"]["results"]["retrospective"]["drift"]["cells"]}
    comparisons.append({"seed":seed,"scopes":"24 seven-day cases across eight provider groups and three reused dependent dates; exploratory","comparisons":{k:decompose(run["retrospective"]["cells"],v) for k,v in references.items()}})
cases=[]
for c in parent["cases"]:
    value={k:v for k,v in c.items() if k not in ("checkpoints","market_state","market_input_identity")}
    value["checkpoints"]=[{"seed":r["state"]["seed"],"update":int(update),"selected":int(update)==r["state"]["selected"]["update"],"rows":[z for z in dev["cells"] if z["task_id"]==c["task_id"]]} for r in runs for update,dev in r["development"].items()]
    cases.append(value)
status="completed_pilot" if any(r["state"]["seed"]==17 for r in runs) else "gated" if not ready["training_ready"] else "interrupted"
report={"study_id":p["study_id"],"status":status,"protocol":p,"protocol_sha256":digest(p),"parent_report_sha256":p["parent"]["report_sha256"],"readiness":ready,"ensembles":ensembles,"parent_diagnostics":read(pre/"diagnostics.json"),"runs":runs,"incomplete_runs":incomplete,"comparisons":comparisons,"cases":cases,"new_optimizer_updates":sum(r["state"]["optimizer_updates"] for r in runs),"uncompleted_confirmed_updates":sum(r.get("optimizer_updates",0) for r in incomplete),"prospective_accuracy":"not established","future_protocol":read("configs/quantile-training-v20-prospective.json"),"future_status":{"issued_origins":0,"outcomes":"pending","dependency":"Fresh compatible daily quotes and eligible issuance schedule; no retrospective data relabeled current"},"source_hashes":{name:hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() for name in ("src/compute_forecast/quantile_v20.py","src/compute_forecast/train_quantile_v20.py","configs/quantile-training-v20.json")},"source_sha":os.environ["GITHUB_SHA"],"provider_cost_usd":None,"limitations":p["limitations"],"source_attribution":parent["source_attribution"]}
check=verify(report);write(out/"report.json",report);write(out/"verification.json",check)
lines=["# Direct quantile training v20","","Status: "+status+". Prospective improvement is not established.","","Fixed equal-weight ensembles combine the three frozen v19 price-only models. They are postprocessing controls, not additional weight training. The ensemble was selected on reused development cases before the new retrospective ensemble arithmetic.","","| Method | Development seven-day pinball | Exploratory seven-day pinball |","|---|---:|---:|"]
for k in ensembles["development"]:lines.append("| "+k+" | "+str(ensembles["development"][k]["summary"]["primary_pinball"])+" | "+str(ensembles["retrospective"][k]["summary"]["primary_pinball"])+" |")
if runs:
    lines+=["","| Seed | Optimizer updates | Selected update | Selected retrospective pinball | Head-zero pinball | Frozen parent pinball |","|---|---:|---:|---:|---:|---:|"]
    for r in runs:
        s=r["state"];lines.append("| "+str(s["seed"])+" | "+str(s["optimizer_updates"])+" | "+str(s["selected"]["update"])+" | "+str(s["retrospective"]["primary_pinball"])+" | "+str(s["head_zero"]["primary_pinball"])+" | "+str(s["frozen_parent"]["primary_pinball"])+" |")
    lines+=["","The three internal head softmaxes encode scalar quantiles. They are not a predictive probability distribution. Quantiles are sorted during both optimization and evaluation. Head zero uses the same parent weights with this new interface; it differs from the parent categorical forecast.","","Training effects are measured against head zero. Comparisons with the original parent change both representation and objective. Warm starts and development dates were already selected and reused. The retrospective comparison has 24 seven-day cases on three dependent dates and is exploratory."]
else:lines+=["","Training readiness: "+json.dumps(ready["reasons"])+". No checkpoint deletion or billing change was performed."]
lines+=["","All original official forecasts and studies are preserved. New future outcomes must mature under the separate registered panel before an accuracy claim. No news, BLS or availability feature effect is tested here.","","Public arithmetic: run python -m compute_forecast.verify_quantile_v20 after installing the package. See docs/quantile-training-v20.md for provenance, limits and reproduction."]
(out/"findings.md").write_text("\n".join(lines)+"\n")
print(json.dumps(check))
