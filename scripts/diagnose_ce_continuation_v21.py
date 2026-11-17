"""Public, credential-free distribution audit of completed continuation runs."""
import hashlib,json,os,pathlib,statistics
from compute_forecast.verify_continuation_v21 import verify
from compute_forecast.continuation_diagnostics_v21 import evaluate
def read(p):return json.loads(pathlib.Path(p).read_bytes())
pointer=read("results/ce-continuation-v21/latest.json");raw=pathlib.Path(pointer["report_path"]).read_bytes()
assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"]
r=json.loads(raw);verification=verify(r);levels=r["log_levels"];runs=[]
for run in r["runs"]:
    s=run["state"];dev=run["development"];ret=run["retrospective"]
    runs.append({"arm":s["arm"],"ordering_seed":s["seed"],"selected_additional_update":s["selected"]["update"],"actual_additional_updates":s["optimizer_updates"],"unique_horizon_presentations":s["unique_horizon_examples_presented"],"repeated_presentations":s["repeated_horizon_presentations"],"effective_corpus_passes":s["effective_corpus_passes"],"development":[{"additional_update":int(u),"summary":v["summary"],"distribution":evaluate(v["cells"],r["baseline"]["development"]["cells"],levels)} for u,v in sorted(dev.items(),key=lambda item:int(item[0]))],"retrospective":{"summary":ret["summary"],"distribution":evaluate(ret["cells"],r["baseline"]["retrospective"]["cells"],levels)}})
base=r["baseline"]["retrospective"];parent=base["summary"]["primary_pinball"]
grouped={}
for arm in ("same","expanded"):
    xs=[v for v in runs if v["arm"]==arm]
    grouped[arm]={"n_orderings":len(xs),"mean_primary_pinball":statistics.mean(v["retrospective"]["summary"]["primary_pinball"] for v in xs) if xs else None,"orderings_better_than_incumbent":sum(v["retrospective"]["summary"]["primary_pinball"]<parent for v in xs),"independence":"Ordering seeds reuse the same parent and market outcomes"}
d={"study_id":"ce-continuation-v21-distribution-audit","source_report_path":pointer["report_path"],"source_report_sha256":pointer["report_sha256"],"arithmetic_verification":verification,"baseline_summary":base["summary"],"baseline_distribution":evaluate(base["cells"],base["cells"],levels),"runs":runs,"ordering_summaries":grouped,"new_optimizer_updates":0,"new_inference_calls":0,"new_forecasts":0,"limitations":["Retrospective diagnostics on three reused dependent origins; no new test or causal mechanism established","No additional retrospective checkpoint evaluations; only originally selected checkpoints are used","NLL is a discretized class diagnostic, separate from official dollar pinball","Averages over ordering seeds are descriptive, not independent market evidence"],"provider_cost_usd":None}
out=pathlib.Path("artifacts/ce-continuation-v21-diagnostics");out.mkdir(parents=True,exist_ok=True)
(out/"diagnostics.json").write_text(json.dumps(d,indent=2,allow_nan=False)+"\n")
lines=["# Continuation distribution audit","","This read-only audit uses retained probabilities. No training, model inference, new forecasts, checkpoint selection or prospective outcome retrieval occurred.","","Source report: ["+pointer["report_path"]+"](../../../../"+pointer["report_path"]+") · SHA-256 "+pointer["report_sha256"],"","| Arm / ordering | Selected update | 7d pinball | Coverage | Width | Median MAE | Entropy | Probability of no change |","|---|---:|---:|---:|---:|---:|---:|---:|"]
def row(name,update,summary,dist):
    q=summary["by_horizon"]["7"]
    return "| "+name+" | "+str(update)+" | "+format(q["pinball"],".8f")+" | "+format(q["coverage"],".3f")+" | "+format(q["width"],".8f")+" | "+format(q["median_mae"],".8f")+" | "+format(dist["all"]["entropy_nats"],".5f")+" | "+format(dist["all"]["unchanged_probability"],".5f")+" |"
lines.append(row("Frozen incumbent",0,base["summary"],d["baseline_distribution"]))
for v in runs:lines.append(row(v["arm"]+" /"+str(v["ordering_seed"]),v["selected_additional_update"],v["retrospective"]["summary"],v["retrospective"]["distribution"]))
lines+=["","## Reading the result","","Lower development loss did not automatically transfer. Checkpoints remain the ones selected before retrospective evaluation. Narrower intervals alone are not better uncertainty; inspect coverage, width, median error and pinball together.","","All ordering seeds share the same market outcomes. The source report retains paired loss contributions by origin, series, GPU and changed-price status. Probability drift, entropy and no-change mass show how predictions changed, but do not prove why generalization succeeded or failed.","","| Arm | Completed orderings | Mean 7d loss | Orderings better than incumbent |","|---|---:|---:|---:|"]
for arm,v in grouped.items():lines.append("| "+arm+" | "+str(v["n_orderings"])+" | "+str(v["mean_primary_pinball"])+" | "+str(v["orderings_better_than_incumbent"])+" |")
lines+=["","## In plain language","","We gave the already-trained forecasting model more practice. One condition reused its original price histories; the other drew from a broader verified pool. Model architecture, output levels, starting weights and optimization budgets were matched.",""]
for arm,v in grouped.items():
    if v["n_orderings"]:
        change=100*(v["mean_primary_pinball"]/parent-1)
        lines.append(("Original-data" if arm=="same" else "Expanded-data")+" continuation had "+format(abs(change),".2f")+"% "+("higher" if change>0 else "lower" if change<0 else "equal")+" mean seven-day loss than the incumbent across "+str(v["n_orderings"])+" completed ordering runs. "+str(v["orderings_better_than_incumbent"])+" had lower aggregate loss. Lower loss is better; this is an average over the same historical cases.")
lines+=["","A good practice score did not establish better forecasts on another period. The originally selected checkpoints remain unchanged. We do not pick a seed or replace the official export using these retrospective scores.","","The retained distributions show where confidence, interval width, coverage and errors changed. These observations can identify a behavioral failure, but cannot by themselves prove overfitting or establish that a proposed remedy works.","","The recommended next step is a separately registered, short matched continuation with an incumbent-probability constraint, plus later observations for evaluation. See docs/ce-continuation-v21-next-steps.md. No further optimization is launched by this audit."]
lines+=["","Public reconstruction: python -m compute_forecast.verify_continuation_v21; python scripts/diagnose_ce_continuation_v21.py.","","Prospective improvement is not yet established."]
(out/"findings.md").write_text("\n".join(lines)+"\n");print(json.dumps({"status":"passed","source_report_sha256":pointer["report_sha256"],"completed_orderings":len(runs),"new_optimizer_updates":0,"new_inference_calls":0}))
