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
if os.environ.get("V21_DIAGNOSTIC_PLOTS")=="1" and runs:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    entries=[]
    for run in runs:
        c=next(c["result"] for c in r["comparisons"] if c["arm"]==run["arm"] and c["seed"]==run["ordering_seed"] and c["reference"]=="incumbent")
        primary=[v for v in c["cells"] if v["horizon_days"]==7]
        parts=[sum(v["quantile_contributions"][i] for v in primary)/len(primary) for i in range(3)]
        assert abs(sum(parts)-c["difference"])<1e-12
        entries.append({"arm":run["arm"],"ordering_seed":run["ordering_seed"],"selected_additional_update":run["selected_additional_update"],"parts":parts,"net_difference":c["difference"]})
    fig,ax=plt.subplots(figsize=(11,max(4.6,2.8+.57*len(entries))));paper="#f8f4ea";ink="#202c3b"
    fig.set_facecolor(paper);ax.set_facecolor(paper);fig.subplots_adjust(left=.24,right=.81,top=.76,bottom=.34)
    palette=["#2858c6","#647182","#39836c"];span=max(sum(v for v in e["parts"] if v>0) for e in entries)
    span=max(span,max(-sum(v for v in e["parts"] if v<0) for e in entries),1e-6)
    for i,e in enumerate(entries):
        positive=negative=0.
        for color,value in zip(palette,e["parts"]):
            start=positive if value>=0 else negative
            ax.barh(i,value,left=start,height=.55,color=color)
            if value>=0:positive+=value
            else:negative+=value
        ax.text(span*1.07,i,format(e["net_difference"],"+.7f"),ha="left",va="center",fontsize=10,color=ink,fontfamily="monospace")
    ax.axvline(0,color=ink,linewidth=.9);ax.set_xlim(-span*1.05,span*1.65)
    ax.set_yticks(range(len(entries)),[("Original" if e["arm"]=="same" else "Expanded")+" /"+str(e["ordering_seed"])+"  ·  +"+str(e["selected_additional_update"]) for e in entries])
    ax.invert_yaxis();ax.set_xlabel("Contribution to mean seven-day pinball loss (USD/GPU-hour)",fontsize=10,labelpad=10)
    ax.xaxis.grid(True,color="#d9d9d1",linewidth=.6);ax.set_axisbelow(True);ax.tick_params(colors="#465264",labelsize=10)
    for key in ("top","right","left"):ax.spines[key].set_visible(False)
    ax.spines["bottom"].set_color("#b8bab5")
    fig.suptitle("Where continued training changed forecast error",x=.04,y=.96,ha="left",fontsize=19,color=ink)
    fig.text(.04,.87,"Relative to the frozen incumbent. Left: lower loss; right: higher loss. Row labels show ordering and selected update.",fontsize=10,color="#536074")
    legend=fig.legend(handles=[Patch(color=c,label=t) for c,t in zip(palette,["Lower quantile · q10","Median · q50","Upper quantile · q90"])],loc="lower center",bbox_to_anchor=(.5,.12),ncol=3,frameon=False,fontsize=10)
    fig.text(.04,.055,"24 matched seven-day cases · 3 reused, dependent origins · retrospective diagnosis",fontsize=10,color="#536074")
    fig.text(.04,.025,"Source report SHA-256: "+pointer["report_sha256"],fontsize=8,color="#536074")
    fig.canvas.draw()
    assert not ax.xaxis.label.get_window_extent().overlaps(legend.get_window_extent()),"Figure legend overlaps the loss axis label"
    for extension in ("png","svg"):fig.savefig(out/("loss-contributions."+extension),dpi=160,facecolor=paper)
    plt.close(fig)
    (out/"figure-data.json").write_text(json.dumps({"source_report_sha256":pointer["report_sha256"],"entries":entries,"matplotlib_version":matplotlib.__version__},indent=2,allow_nan=False)+"\n")
    lines+=["","![Quantile contributions to loss change](loss-contributions.png)","","The contributions reconstruct the exact aggregate difference. These are not confidence intervals."]
(out/"findings.md").write_text("\n".join(lines)+"\n");print(json.dumps({"status":"passed","source_report_sha256":pointer["report_sha256"],"completed_orderings":len(runs),"new_optimizer_updates":0,"new_inference_calls":0}))
