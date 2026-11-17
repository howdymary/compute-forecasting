"""Post-hoc arithmetic diagnosis from retained forecasts only; no model or outcome retrieval."""
import hashlib,json,pathlib,statistics
from compute_forecast.probability_v18 import digest
from compute_forecast.quantile_v20 import decompose
from compute_forecast.verify_quantile_v20 import verify
p=json.loads(pathlib.Path("results/quantile-training-v20/latest.json").read_bytes());raw=pathlib.Path(p["report_path"]).read_bytes()
assert hashlib.sha256(raw).hexdigest()==p["report_sha256"];r=json.loads(raw);verify(r)
run=next(v for v in r["runs"] if v["state"]["seed"]==17)
parent=json.loads(pathlib.Path(r["protocol"]["parent"]["report_path"]).read_bytes())
reference=next(v for v in parent["runs"] if v["arm"]=="price" and v["seed"]==17)["retrospective"]["cells"]
d=decompose(run["retrospective"]["cells"],reference);cells=[v for v in run["retrospective"]["cells"] if v["horizon_days"]==7]
primary=[v for v in d["cells"] if v["horizon_days"]==7]
parts=[statistics.mean(v["quantile_contributions"][j] for v in primary) for j in range(3)]
assert abs(sum(parts)-d["difference"])<1e-12
groups=[]
for changed in (False,True):
    rows=[v for v in cells if v["changed_price"]==changed]
    groups.append({"changed_price":changed,"n":len(rows),"pinball":statistics.mean(v["loss"] for v in rows),"covered":sum(v["q10"]<=v["outcome"]<=v["q90"] for v in rows),"mean_width":statistics.mean(v["q90"]-v["q10"] for v in rows),"median_mae":statistics.mean(abs(v["q50"]-v["outcome"]) for v in rows),"weighted_delta":next(v["weighted_contribution"] for v in d["groups"]["changed_price"] if v["value"]==changed)})
result={"study_id":"quantile-training-v20-diagnostic","classification":"Post-hoc descriptive analysis of the frozen pilot; no retuning","source_report_path":p["report_path"],"source_report_sha256":p["report_sha256"],"selected_update":run["state"]["selected"]["update"],"primary_cells":len(cells),"origins":sorted({v["origin"] for v in cells}),"quantile_delta_contributions":dict(zip(("q10","q50","q90"),parts)),"aggregate_delta":d["difference"],"groups":groups,"direction_counts":{"down":sum(v["outcome"]<v["anchor"] for v in cells),"up":sum(v["outcome"]>v["anchor"] for v in cells),"unchanged":sum(v["outcome"]==v["anchor"] for v in cells)},"new_optimizer_updates":0,"new_model_calls":0,"causal_explanation_established":False,"limitations":["Three reused dependent dates, not independent future validation","Interval collapse describes the failure; its cause is not isolated","Strict coverage is sensitive to microscopic misses on unchanged-price atoms","Additional training is not assumed to fix the problem"]}
out=pathlib.Path("artifacts/quantile-training-v20-diagnostics");out.mkdir(parents=True,exist_ok=True);(out/"diagnostics.json").write_text(json.dumps(result,indent=2)+"\n")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(10,6),layout="constrained");fig.set_facecolor("#f8f4ea");ax.set_facecolor("#f8f4ea")
ax.bar(["Lower quantile\nq10","Median\nq50","Upper quantile\nq90"],parts,color=["#a77222","#2858c6","#39836c"],width=.48)
ax.axhline(0,color="#26384b",linewidth=.9)
for i,v in enumerate(parts):ax.annotate(f"{v:+.7f}",(i,v),xytext=(0,7 if v>=0 else -18),textcoords="offset points",ha="center",fontsize=11,color="#26384b")
ax.set_ylim(min(parts)-.0014,max(parts)+.0018);ax.set_ylabel("Contribution to mean pinball-loss difference\nUSD per GPU-hour",labelpad=14)
ax.set_title("Where the quantile head lost to its parent",loc="left",fontsize=20,pad=24,color="#202c3b")
ax.text(0,1.02,"Positive = worse  ·  contributions sum to "+format(sum(parts),".7f"),transform=ax.transAxes,color="#536074",fontsize=11)
ax.text(0,-.19,"24 seven-day cases · 3 reused, dependent origins · selected update 64\n9 prices changed (8 down, 1 up); 15 were unchanged. Post-hoc diagnosis.",transform=ax.transAxes,color="#536074",fontsize=10)
for k in ("top","right"):ax.spines[k].set_visible(False)
for k in ("left","bottom"):ax.spines[k].set_color("#aab0b2")
ax.tick_params(colors="#3f5064");ax.yaxis.grid(True,color="#d9d9d1",linewidth=.6);ax.set_axisbelow(True)
fig.savefig(out/"loss-contributions.png",dpi=160);fig.savefig(out/"loss-contributions.svg")
text="""# Quantile-head failure analysis

The frozen pilot completed 64 updates. On 24 seven-day cases across three reused, dependent dates, selected-head loss was 0.02287759 versus 0.01555766 for its categorical parent. It failed the registered development expansion gate. The incumbent was retained.

Almost all additional loss came from the nine changed-price cases (eight declines and one increase). The 15 unchanged cases had negligible absolute errors, but microscopic one-sided misses in extremely narrow intervals explain why literal coverage was low even there.

The q10, q50 and q90 contributions to trained-minus-parent mean pinball were +0.00774203, +0.00058503 and -0.00100713. They sum to +0.00731993. The upper quantile helped slightly while the lower quantile deteriorated substantially.

The selected head's seven-day interval covered 2/24 outcomes and had mean width 0.00026079 USD per GPU-hour, versus parent coverage 20/24 and width 0.11702519. All nine changed outcomes lay outside the head's interval. This describes a persistence-like, extremely concentrated forecast; it does not establish which training mechanism caused that behavior.

The head interface's own update-zero loss was 0.03790731. Improving from that starting point did not make it better than the original representation. Raw internal head coefficients are not predictive probability mass.

The next modeling proposal should explicitly test preservation of unchanged-price mass and useful downside quantiles, with fixed controls and future evaluation. More updates, another seed or a different prompt are not established remedies. No new optimization was run for this diagnosis.

The figure shows contributions scaled by 1/3 and averaged across all 24 primary cells. Positive means worse. Every value is reconstructed from the source report recorded in diagnostics.json. These are post-hoc historical observations, not prospective improvement.
"""
(out/"findings.md").write_text(text)
print(json.dumps(result))
