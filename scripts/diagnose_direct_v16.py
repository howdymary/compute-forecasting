"""Artifact-only diagnosis. No model clients, inference, optimization or outcome fetching."""
from __future__ import annotations
import collections,csv,hashlib,json,math,os,pathlib,statistics
import numpy as np
from compute_forecast.direct_forecast_v12 import digest,cell_loss,summarize,price_quantiles
from compute_forecast.verify_evidence_v14 import verify
def read(p):return json.loads(pathlib.Path(p).read_text())
def mean(values):return statistics.mean(values) if values else None
def pin(y,q,t):return max(t*(y-q),(t-1)*(y-q))
def describe(values):
    a=np.asarray(values,dtype=float)
    return {"n":len(a),"mean":float(a.mean()),"min":float(a.min()),"p25":float(np.quantile(a,.25)),"median":float(np.median(a)),"p75":float(np.quantile(a,.75)),"max":float(a.max()),"p95_abs":float(np.quantile(np.abs(a),.95))} if len(a) else {"n":0}
def save(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
def csvfile(path,rows):
    if not rows:return
    with path.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def aggregate(rows,field):
    groups=collections.defaultdict(list)
    for row in rows:groups[str(row[field])].append(row)
    total=len(rows);result=[]
    for group,items in sorted(groups.items()):
        result.append({"group":group,"n":len(items),"weight":len(items)/total,"base":mean(r["base_loss"] for r in items),"trained":mean(r["trained_loss"] for r in items),"difference":mean(r["difference"] for r in items),"weighted_contribution":sum(r["difference"] for r in items)/total,"median_mae_difference":mean(r["trained_median_ae"]-r["base_median_ae"] for r in items)})
    assert abs(sum(r["weighted_contribution"] for r in result)-mean(r["difference"] for r in rows))<1e-12
    return result
def dist(tasks,anchor_by_id,h):
    ix={1:0,3:1,7:2}[h];vectors=[t["sample_returns"] for t in tasks]
    returns=[v[ix] for group in vectors for v in group]
    qs=[row for t in tasks for row in t["cells"] if row["horizon_days"]==h]
    return {"tasks":len(tasks),"valid":sum(t["valid_samples"] for t in tasks),"invalid":sum(t["invalid_samples"] for t in tasks),"fallback_tasks":sum(t["fallback"] for t in tasks),"collapsed_vector_tasks":sum(t["sample_collapse"] for t in tasks),"distinct_vectors":describe([t["distinct_vectors"] for t in tasks]),"median_equals_anchor_cells":sum(r["q50"]==anchor_by_id[r["task_id"]] for r in qs),"all_quantiles_equal_anchor_cells":sum(r["q10"]==r["q50"]==r["q90"]==anchor_by_id[r["task_id"]] for r in qs),"zero_width_cells":sum(r["q10"]==r["q90"] for r in qs),"sample_zero_fraction":mean(float(x==0) for x in returns),"sample_near_zero_fraction":mean(float(abs(x)<=1e-8) for x in returns),"sample_negative_fraction":mean(float(x<0) for x in returns),"sample_positive_fraction":mean(float(x>0) for x in returns),"sample_abs_return_above_10pct_fraction":mean(float(abs(x)>math.log(1.1)) for x in returns),"sample_return_summary":describe(returns),"mean_sample_return_per_task":mean(mean(v[ix] for v in group) for group in vectors),"median_mae":mean(abs(r["outcome"]-r["q50"]) for r in qs),"coverage":mean(r["q10"]<=r["outcome"]<=r["q90"] for r in qs),"width":mean(r["q90"]-r["q10"] for r in qs),"pinball":mean(r["loss"] for r in qs),"lower_misses":sum(r["outcome"]<r["q10"] for r in qs),"upper_misses":sum(r["outcome"]>r["q90"] for r in qs),"mean_log_quantiles":{k:mean(math.log(r[k]/anchor_by_id[r["task_id"]]) for r in qs) for k in ("q10","q50","q90")}}
def main():
    cfg=read("configs/direct-v14-diagnosis-v16.json");report_path=pathlib.Path(cfg["source_report"]["report_path"]);root=report_path.parent
    assert hashlib.sha256(report_path.read_bytes()).hexdigest()==cfg["source_report"]["report_sha256"]
    verify(root)
    report=read(report_path);data=read("inputs/diagnosis/dataset.json")
    assert digest(data)==cfg["expected_dataset_sha256"]==report["dataset_sha256"]
    groups=data["groups"];tasks_by_id={t["task_id"]:t for phase in groups.values() for t in phase}
    anchors={k:t["anchor"] for k,t in tasks_by_id.items()}
    for phase,tasks in groups.items():
        for t in tasks:
            assert max(r["date"] for r in t["context"])<=t["origin"]
            assert t["target_dates"]==[( __import__("datetime").date.fromisoformat(t["origin"])+__import__("datetime").timedelta(days=h)).isoformat() for h in (1,3,7)]
            if phase=="training":assert max(t["target_dates"])<="2026-09-19" and t["origin"]<="2026-09-12"
    out=pathlib.Path("artifacts/diagnosis-v16");out.mkdir(parents=True,exist_ok=True)
    composition={};target_distributions={};overlap={}
    for phase,tasks in groups.items():
        composition[phase]={"tasks":len(tasks),"origins":len({t["origin"] for t in tasks}),"series":len({t["series_id"] for t in tasks}),"source":dict(collections.Counter(t["metadata"]["source_id"] for t in tasks)),"gpu":dict(collections.Counter("H100" if t["metadata"]["gpu_model"].startswith("H100") else "A100" for t in tasks)),"instrument":dict(collections.Counter(t["metadata"]["instrument_class"] for t in tasks))}
        target_distributions[phase]={str(h):{**describe([math.log(t["outcomes"][i]/t["anchor"]) for t in tasks]),"zero":sum(t["outcomes"][i]==t["anchor"] for t in tasks),"negative":sum(t["outcomes"][i]<t["anchor"] for t in tasks),"positive":sum(t["outcomes"][i]>t["anchor"] for t in tasks)} for i,h in enumerate((1,3,7))}
    for sid in sorted({t["series_id"] for t in groups["training"]}):
        tt=sorted([t for t in groups["training"] if t["series_id"]==sid],key=lambda t:t["origin"])
        shared=[]
        for a,b in zip(tt,tt[1:]):
            da={(r["date"],r["value"]) for r in a["context"]};db={(r["date"],r["value"]) for r in b["context"]}
            shared.append(len(da&db)/len(da|db))
        overlap[sid]=describe(shared)
    context_shapes={}
    phase_by_source={}
    for phase,tasks in groups.items():
        counts=collections.Counter(tuple(round(math.log(r["value"]/t["anchor"]),8) for r in t["context"]) for t in tasks)
        context_shapes[phase]={"tasks":len(tasks),"distinct_value_only_shapes":len(counts),"most_repeated_value_only_shape":max(counts.values()),"note":"Ignores dates and metadata; pattern repetition, not a claim of identical full prompts"}
        phase_by_source[phase]={}
        for source in sorted({t["metadata"]["source_id"] for t in tasks}):
            selected_tasks=[t for t in tasks if t["metadata"]["source_id"]==source]
            phase_by_source[phase][source]={str(h):{**describe([math.log(t["outcomes"][i]/t["anchor"]) for t in selected_tasks]),"zero":sum(t["outcomes"][i]==t["anchor"] for t in selected_tasks),"negative":sum(t["outcomes"][i]<t["anchor"] for t in selected_tasks),"positive":sum(t["outcomes"][i]>t["anchor"] for t in selected_tasks)} for i,h in enumerate((1,3,7))}
    training_series={t["series_id"] for t in groups["training"]}
    allrows=[];runs=[];boot=[];case_payload={};hybrids=[];dev_diagnostics=[]
    rng=np.random.default_rng(cfg["bootstrap"]["seed"])
    for state in report["runs"]:
        arm,seed=state["arm"],state["seed"];directory=root/arm/("seed-"+str(seed))
        base=read(directory/"evaluation-base.json");trained=read(directory/"evaluation-selected.json")
        selected=state["selected"]["update"];assert selected==min(state["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))["update"]
        bykey=lambda value:{(r["task_id"],r["horizon_days"]):r for r in value["cells"]}
        ba,tr=bykey(base),bykey(trained);assert ba.keys()==tr.keys()
        for key,b in ba.items():
            t=tr[key];task=tasks_by_id[b["task_id"]];m=task["metadata"];qparts=[]
            for q,name in zip((.1,.5,.9),("q10","q50","q90")):qparts.append((pin(t["outcome"],t[name],q)-pin(b["outcome"],b[name],q))/3)
            assert b["outcome"]==t["outcome"]==task["outcomes"][(1,3,7).index(key[1])]
            assert abs(sum(qparts)-(t["loss"]-b["loss"]))<1e-12
            center_b,center_t=b["q50"],t["q50"]
            base_shape=[b[q]-center_b for q in ("q10","q50","q90")];trained_shape=[t[q]-center_t for q in ("q10","q50","q90")]
            tc_bs=[center_t+v for v in base_shape];bc_ts=[center_b+v for v in trained_shape]
            valid=min(tc_bs+bc_ts)>0
            if valid:
                hybrid_t=cell_loss(t["outcome"],tc_bs);hybrid_b=cell_loss(t["outcome"],bc_ts)
                center_effect=.5*((hybrid_t-b["loss"])+(t["loss"]-hybrid_b))
                shape_effect=.5*((hybrid_b-b["loss"])+(t["loss"]-hybrid_t))
                assert abs(center_effect+shape_effect-(t["loss"]-b["loss"]))<1e-12
            else:hybrid_t=hybrid_b=center_effect=shape_effect=None
            hybrids.append({"arm":arm,"seed":seed,"task_id":key[0],"horizon":key[1],"valid_positive_quantiles":valid,"base":b["loss"],"trained":t["loss"],"trained_center_base_shape":hybrid_t,"base_center_trained_shape":hybrid_b,"center_shapley":center_effect,"shape_shapley":shape_effect})
            observed_return=math.log(t["outcome"]/task["anchor"]);bounds=target_distributions["training"][str(key[1])]
            outside=not bounds["min"]<=observed_return<=bounds["max"]
            allrows.append({"arm":arm,"seed":seed,"task_id":key[0],"series":b["series_id"],"origin":b["origin"],"horizon":key[1],"family":"H100" if m["gpu_model"].startswith("H100") else "A100","source":m["source_id"],"instrument":m["instrument_class"],"seen_in_training":b["series_id"] in training_series,"changed":t["outcome"]!=task["anchor"],"outside_training_return_range":outside,"base_loss":b["loss"],"trained_loss":t["loss"],"difference":t["loss"]-b["loss"],"q10_contribution":qparts[0],"q50_contribution":qparts[1],"q90_contribution":qparts[2],"base_median_ae":abs(b["outcome"]-b["q50"]),"trained_median_ae":abs(t["outcome"]-t["q50"]),"anchor":task["anchor"],"outcome":t["outcome"],"relative_difference":(t["loss"]-b["loss"])/task["anchor"]})
        dev_outputs={cp["update"]:read(directory/("development-"+str(cp["update"])+".json")) for cp in state["checkpoints"]}
        dev_base=bykey(dev_outputs[0]);dev_selected=bykey(dev_outputs[selected]);dev_rows=[]
        for key,b in dev_base.items():
            if key[1]!=7:continue
            t=dev_selected[key];task=tasks_by_id[key[0]]
            dev_rows.append({"task_id":key[0],"series":task["series_id"],"origin":task["origin"],"source":task["metadata"]["source_id"],"base_loss":b["loss"],"trained_loss":t["loss"],"difference":t["loss"]-b["loss"],"base_median_ae":abs(b["outcome"]-b["q50"]),"trained_median_ae":abs(t["outcome"]-t["q50"])})
        leave_case=[];leave_origin=[]
        for omit in [r["task_id"] for r in dev_rows]:
            losses={str(cp):mean(r["loss"] for r in val["cells"] if r["horizon_days"]==7 and r["task_id"]!=omit) for cp,val in dev_outputs.items()}
            chosen=min(losses,key=lambda k:(losses[k],int(k)));leave_case.append({"omitted":omit,"chosen_update":int(chosen)})
        for omit in sorted({r["origin"] for r in dev_rows}):
            losses={str(cp):mean(r["loss"] for r in val["cells"] if r["horizon_days"]==7 and r["origin"]!=omit) for cp,val in dev_outputs.items()}
            chosen=min(losses,key=lambda k:(losses[k],int(k)));leave_origin.append({"omitted":omit,"chosen_update":int(chosen),"losses":losses})
        B=cfg["bootstrap"]["replicates"];dev_boot={}
        for cp,value in dev_outputs.items():
            totals=np.zeros(B)
            for task in value["tasks"]:
                x=np.asarray(task["sample_returns"])[:,2];sample=x[rng.integers(0,len(x),size=(B,len(x)))]
                qq=np.quantile(anchors[task["task_id"]]*np.exp(sample),[.1,.5,.9],axis=1).T
                yy=next(r["outcome"] for r in task["cells"] if r["horizon_days"]==7);ee=yy-qq
                totals+=np.maximum(np.asarray([.1,.5,.9])*ee,(np.asarray([.1,.5,.9])-1)*ee).mean(axis=1)
            dev_boot[cp]=totals/len(value["tasks"])
        cp_order=sorted(dev_boot);winners=np.argmin(np.stack([dev_boot[cp] for cp in cp_order]),axis=0)
        dev_diagnostics.append({"arm":arm,"seed":seed,"original_selected":selected,"source_contributions":aggregate(dev_rows,"source"),"origin_contributions":aggregate(dev_rows,"origin"),"case_contributions":aggregate(dev_rows,"task_id"),"leave_one_case_selection_counts":dict(collections.Counter(v["chosen_update"] for v in leave_case)),"leave_one_origin":leave_origin,"conditional_mc_selection_frequencies":{str(cp):float(np.mean(winners==i)) for i,cp in enumerate(cp_order)},"scope":"Post-hoc stability analysis only; original checkpoint selection is preserved"})
        runrows=[r for r in allrows if r["arm"]==arm and r["seed"]==seed]
        perh={}
        for h in (1,3,7):
            rr=[r for r in runrows if r["horizon"]==h]
            perh[str(h)]={"base":dist(base["tasks"],anchors,h),"trained":dist(trained["tasks"],anchors,h),"difference":mean(r["difference"] for r in rr),"q_contributions":{q:mean(r[q+"_contribution"] for r in rr) for q in ("q10","q50","q90")},"improved":sum(r["difference"]<0 for r in rr),"worsened":sum(r["difference"]>0 for r in rr),"equal":sum(r["difference"]==0 for r in rr),"grouped":{field:aggregate(rr,field) for field in ("origin","series","family","source","instrument","changed","seen_in_training","outside_training_return_range")}}
        ce=[r["completion_cross_entropy"] for r in state["updates"]]
        dev=state["checkpoints"];z=dev[0]["development"]["primary_pinball"];chosen=state["selected"]["development"]["primary_pinball"]
        runs.append({"arm":arm,"seed":seed,"updates":state["optimizer_updates"],"selected_update":selected,"development_base":z,"development_selected":chosen,"development_difference":chosen-z,"dev_trajectory":[{"update":c["update"],"pinball":c["development"]["primary_pinball"]} for c in dev],"training_ce_first10":mean(ce[:10]),"training_ce_last10":mean(ce[-10:]),"by_horizon":perh})
        # Sampling-only bootstrap: fixed tasks and observed outcomes, resample valid vectors.
        B=cfg["bootstrap"]["replicates"];scores={}
        for label,value in (("base",base),("trained",trained)):
            totals=np.zeros(B)
            for t in value["tasks"]:
                x=np.asarray(t["sample_returns"])[:,2];anchor=anchors[t["task_id"]]
                resampled=x[rng.integers(0,len(x),size=(B,len(x)))]
                prices=anchor*np.exp(resampled);quantiles=np.quantile(prices,[.1,.5,.9],axis=1).T
                y=next(r["outcome"] for r in t["cells"] if r["horizon_days"]==7)
                errors=y-quantiles
                totals+=np.maximum(np.asarray([.1,.5,.9])*errors,(np.asarray([.1,.5,.9])-1)*errors).mean(axis=1)
            scores[label]=totals/len(value["tasks"])
        delta=scores["trained"]-scores["base"];boot.append({"arm":arm,"seed":seed,"replicates":B,"fixed_outcomes":len(base["tasks"]),"observed_difference":perh["7"]["difference"],"conditional_mc_bootstrap_percentiles":[float(np.quantile(delta,p)) for p in (.025,.5,.975)],"fraction_resamples_positive":float(np.mean(delta>0)),"scope":cfg["bootstrap"]["scope"]})
        if arm=="price_only" and seed==17:
            case_payload={t["task_id"]:{"base":t,"trained":next(s for s in trained["tasks"] if s["task_id"]==t["task_id"]),"task":{"series_id":tasks_by_id[t["task_id"]]["series_id"],"origin":tasks_by_id[t["task_id"]]["origin"],"anchor":anchors[t["task_id"]]}} for t in base["tasks"]}
    primary=[r for r in allrows if r["horizon"]==7]
    mean_base=mean(r["base_loss"] for r in primary);mean_trained=mean(r["trained_loss"] for r in primary);difference=mean(r["difference"] for r in primary)
    pooled={field:aggregate(primary,field) for field in ("arm","seed","source","series","origin","family","instrument","changed","seen_in_training","outside_training_return_range")}
    qcontrib={q:mean(r[q+"_contribution"] for r in primary) for q in ("q10","q50","q90")}
    assert abs(sum(qcontrib.values())-difference)<1e-12
    loss_rank=sorted(primary,key=lambda r:r["difference"],reverse=True)
    global_result={"base":mean_base,"trained":mean_trained,"difference":difference,"relative_increase":mean_trained/mean_base-1,"mean_anchor_normalized_difference":mean(r["relative_difference"] for r in primary),"q_contributions":qcontrib,"n_primary_cells_per_run":22,"repeated_cells":len(primary),"distinct_market_origins":3,"distinct_series":10,"groups":pooled,"top10_harm_contribution":sum(r["difference"] for r in loss_rank[:10])/len(primary),"top10_harm_fraction_of_net":sum(r["difference"] for r in loss_rank[:10])/sum(r["difference"] for r in primary),"positive_cells":sum(r["difference"]>0 for r in primary),"negative_cells":sum(r["difference"]<0 for r in primary),"equal_cells":sum(r["difference"]==0 for r in primary),"leave_one_origin_out":[{"omitted":o,"difference":mean(r["difference"] for r in primary if r["origin"]!=o)} for o in sorted({r["origin"] for r in primary})]}
    primary_hybrids=[r for r in hybrids if r["horizon"]==7]
    shape_summary={"cells":len(primary_hybrids),"invalid":sum(not r["valid_positive_quantiles"] for r in primary_hybrids),"scope":"Loss-function counterfactual at fixed saved predictions; not causal attribution to a training mechanism"}
    if not shape_summary["invalid"]:
        shape_summary.update({k:mean(r[k] for r in primary_hybrids) for k in ("base","trained","trained_center_base_shape","base_center_trained_shape","center_shapley","shape_shapley")})
        assert abs(shape_summary["center_shapley"]+shape_summary["shape_shapley"]-difference)<1e-12
    native={name:value["summary"] for name,value in report["runs"][0]["references"].items()}
    result={"study_id":cfg["study_id"],"classification":cfg["classification"],"input_ref":cfg["source_ref"],"input_report":cfg["source_report"],"dataset_sha256":digest(data),"protocol_sha256":report["protocol_sha256"],"new_optimizer_updates":0,"new_inference_requests":0,"new_outcomes_retrieved":False,"composition":composition,"target_returns":target_distributions,"adjacent_context_overlap":overlap,"context_shapes":context_shapes,"location_shape":shape_summary,"development_selection":dev_diagnostics,"target_returns_by_source":phase_by_source,"runs":runs,"global_primary":global_result,"conditional_mc":boot,"native_references":native,"limits":{"no_population_confidence_interval":True,"no_new_checkpoint_reselection":True,"missing_raw_malformed_completions":True,"tokenizer_revision_was_not_recorded":True,"pretraining_cutoff_not_verified":True}}
    save(out/"diagnosis.json",result);csvfile(out/"cell-contributions.csv",allrows);csvfile(out/"location-shape-counterfactuals.csv",hybrids)
    for field,rows in pooled.items():csvfile(out/("contribution-"+field+".csv"),rows)
    lines=["# Diagnosis of the frozen direct-forecasting comparison","",f"All six saved results were independently reconstructed. Across six paired runs on the same22 seven-day cases, mean untuned loss was{mean_base:.10f}; selected SFT loss was{mean_trained:.10f}, a{(mean_trained/mean_base-1):.2%} increase.","","Three reused dates remain three market origins;132 repeated cells are not132 independent forecasts.","","| Arm | Seed | Selected | Untuned loss | SFT loss | Difference | Median MAE change |","| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in runs:
        h=r["by_horizon"]["7"];lines.append(f"|{r['arm']}|{r['seed']}|{r['selected_update']}|{h['base']['pinball']:.8f}|{h['trained']['pinball']:.8f}|{h['difference']:.8f}|{h['trained']['median_mae']-h['base']['median_mae']:.8f}|")
    lines+=["","## Exact primary-loss contributions","","Each contribution is the subgroup's summed trained-minus-base loss divided by all132 repeated primary cells. Contributions within each grouping sum to the aggregate difference.","","| Collector | Repeated cells | Mean difference | Weighted contribution |","| --- | ---: | ---: | ---: |"]
    for r in pooled["source"]:lines.append(f"|{r['group']}|{r['n']}|{r['difference']:.8f}|{r['weighted_contribution']:.8f}|")
    lines+=["","| Quantile | Contribution after the scorer's one-third quantile weighting |","| --- | ---: |"]
    for q,value in qcontrib.items():lines.append(f"|{q}|{value:.10f}|")
    lines+=["","## Interpretation boundaries","","This is an artifact-based diagnosis, not a new model comparison on untouched dates. Conditional sample bootstraps condition on the retained vectors and fixed outcomes; they do not estimate market-population uncertainty. No inference or optimizer updates were requested. Source-mix, representation and objective explanations require interventions before causal attribution.","","Raw malformed completions and the original tokenizer commit were not retained. Those limitations cannot be repaired retrospectively by inventing missing records."]
    (out/"findings.md").write_text("\n".join(lines)+"\n")
    figures(out,result,case_payload)
    save(out/"manifest.json",{"study_id":cfg["study_id"],"source_sha":os.environ["GITHUB_SHA"],"inputs":{"report_sha256":cfg["source_report"]["report_sha256"],"dataset_sha256":digest(data)},"files":[{"path":f.name,"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size} for f in sorted(out.glob("*")) if f.is_file() and f.name!="manifest.json"]})
    print(json.dumps({"status":"reconstructed","runs":len(runs),"global_primary":global_result,"composition":composition,"conditional_mc":boot},indent=2),flush=True)
def figures(out,result,cases):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False,"figure.facecolor":"#f8f5ee","axes.facecolor":"#f8f5ee","text.color":"#23323d","axes.labelcolor":"#23323d","savefig.facecolor":"#f8f5ee"})
    runs=result["runs"];fig,ax=plt.subplots(figsize=(8,4.8),layout="constrained")
    for i,r in enumerate(runs):
        b=r["by_horizon"]["7"]["base"]["pinball"];t=r["by_horizon"]["7"]["trained"]["pinball"];col="#2657b4" if r["arm"]=="price_only" else "#34725b"
        ax.plot([b,t],[i,i],color=col,lw=1.8);ax.scatter([b],[i],facecolor="#f8f5ee",edgecolor=col,s=45,zorder=3);ax.scatter([t],[i],color=col,s=45,zorder=3)
    ax.set_yticks(range(6),[("Price" if r["arm"]=="price_only" else "Price + BLS")+" / "+str(r["seed"]) for r in runs]);ax.invert_yaxis();ax.set_xlabel("Seven-day quantile pinball · USD per GPU-hour · lower is better");ax.set_title("Every selected fine-tuned model lost to its untuned control",loc="left",pad=18)
    ax.text(0,1.01,"Open marker: untuned   Filled marker: selected SFT",transform=ax.transAxes,fontsize=9)
    for ext in ("png","svg"):fig.savefig(out/("paired-loss."+ext),dpi=190)
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout="constrained")
    for ax,field,title in zip(axes,("source","q"),("Contribution by collector","Contribution by forecast quantile")):
        rows=result["global_primary"]["groups"]["source"] if field=="source" else [{"group":k,"weighted_contribution":v} for k,v in result["global_primary"]["q_contributions"].items()]
        vals=[r["weighted_contribution"] for r in rows];ax.barh([r["group"] for r in rows],vals,color=["#a36923" if x>0 else "#34725b" for x in vals]);ax.axvline(0,color="#7c858a",lw=.7);ax.set_title(title,loc="left");ax.set_xlabel("Contribution to trained minus base mean loss")
    fig.suptitle("Where the loss increase came from · three reused dates, six paired runs",x=.04,ha="left")
    for ext in ("png","svg"):fig.savefig(out/("loss-contributions."+ext),dpi=190)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.5),layout="constrained");phases=["training","development","retrospective"];sources=sorted({s for p in result["composition"].values() for s in p["source"]});bottom=np.zeros(3)
    for source,color in zip(sources,["#2657b4","#a36923","#34725b"]):
        counts=np.asarray([result["composition"][p]["source"].get(source,0) for p in phases]);totals=np.asarray([result["composition"][p]["tasks"] for p in phases]);v=counts/totals
        ax.bar(phases,v,bottom=bottom,label=source,color=color,width=.55);bottom+=v
    ax.set_ylim(0,1);ax.set_ylabel("Share of series-origin tasks");ax.set_title("Training and evaluation used different collector mixtures",loc="left");ax.legend(frameon=False,loc="upper left",bbox_to_anchor=(1,1))
    for ext in ("png","svg"):fig.savefig(out/("source-mixture."+ext),dpi=190)
    plt.close(fig)
    rr=[r for r in result["global_primary"]["groups"]["series"]]
    # Post-hoc failure illustration, explicitly not a representative case.
    pairs=[]
    for tid,c in cases.items():
        b=next(r for r in c["base"]["cells"] if r["horizon_days"]==7);t=next(r for r in c["trained"]["cells"] if r["horizon_days"]==7);pairs.append((t["loss"]-b["loss"],tid))
    chosen=[max(pairs)[1],min(pairs)[1]];fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout="constrained")
    for ax,tid,label in zip(axes,chosen,("Largest harm","Lowest difference")):
        c=cases[tid];anchor=c["task"]["anchor"]
        for kind,color in (("base","#23323d"),("trained","#2657b4")):
            vals=np.sort(np.asarray(c[kind]["sample_returns"])[:,2]);ax.step(vals,np.arange(1,len(vals)+1)/len(vals),where="post",color=color,label=kind)
        y=next(r["outcome"] for r in c["base"]["cells"] if r["horizon_days"]==7);ax.axvline(math.log(y/anchor),color="#a36923",ls="--",lw=1,label="observed return")
        ax.set_title(label+" · "+c["task"]["origin"],loc="left");ax.set_xlabel("Sampled seven-day log return");ax.set_ylabel("Empirical cumulative probability");ax.legend(frameon=False)
    fig.suptitle("Post-hoc illustrations · operational price-only seed17 · not representative",x=.04,ha="left")
    for ext in ("png","svg"):fig.savefig(out/("sample-distributions."+ext),dpi=190)
    plt.close(fig)
if __name__=="__main__":main()
