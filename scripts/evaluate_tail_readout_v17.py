"""Matched frozen median-preserving tail calibration. No model or network clients."""
from __future__ import annotations
import collections,csv,hashlib,json,math,os,pathlib,statistics
from compute_forecast.direct_forecast_v12 import cell_loss
from compute_forecast.verify_evidence_v14 import verify
def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+"\n")
def mean(v):return statistics.mean(v)
def mapped(q,lower,upper):
    if not 0<q[0]<=q[1]<=q[2]:raise ValueError("Invalid source quantiles")
    if not 0<lower or not 0<upper:raise ValueError("Positive multipliers required")
    if lower==upper==1:return list(q),False
    try:
        low=q[0] if lower==1 or q[0]==q[1] else q[1]*math.exp(lower*math.log(q[0]/q[1]))
        high=q[2] if upper==1 or q[2]==q[1] else q[1]*math.exp(upper*math.log(q[2]/q[1]))
        out=[low,q[1],high]
        if not all(math.isfinite(x) for x in out) or not 0<low<=q[1]<=high:raise ValueError("Nonpositive or crossed result")
        return out,False
    except (OverflowError,ValueError):return list(q),True
def score(rows,lower=1,upper=1):
    out=[]
    for row in rows:
        q,failed=mapped([row[k] for k in ("q10","q50","q90")],lower,upper)
        out.append({**row,"q10":q[0],"q50":q[1],"q90":q[2],"loss":cell_loss(row["outcome"],q),"calibration_failure":failed})
    return out
def summary(rows):
    return {"n":len(rows),"loss":mean(r["loss"] for r in rows),"coverage":mean(r["q10"]<=r["outcome"]<=r["q90"] for r in rows),"width":mean(r["q90"]-r["q10"] for r in rows),"median_mae":mean(abs(r["outcome"]-r["q50"]) for r in rows),"failures":sum(r.get("calibration_failure",False) for r in rows)}
def choose(dev,grid):
    candidates=[]
    for lower in grid:
        for upper in grid:
            s=summary(score(dev,lower,upper));candidates.append({"lower":lower,"upper":upper,**s})
    best=min(candidates,key=lambda c:(c["loss"],(c["lower"],c["upper"])!=(1,1),abs(math.log(c["lower"]))+abs(math.log(c["upper"])),c["lower"],c["upper"]))
    return best,candidates
def keys(rows):return {(r["task_id"],r["origin"],r["horizon_days"]) for r in rows}
def tests():
    for q in ([1,1,1],[2.204,2.204,2.204],[1.757,1.757,1.8155],[1.8155,3.949,3.949],[.01,1,100],[.9,1,1.1],[1e-100,1e-50,1]):
        original,failed=mapped(q,1,1)
        assert original==list(q) and not failed,"Identity must preserve exact values"
        for a in (.5,1,2):
            for b in (.5,1,2):
                changed,failed=mapped(q,a,b)
                assert not failed and changed[1]==q[1] and 0<changed[0]<=changed[1]<=changed[2]
    flat,_=mapped([2,2,2],.5,2);assert flat==[2,2,2]
    x=[{"task_id":"synthetic","origin":"2000-01-01","horizon_days":7,"q10":.9,"q50":1.,"q90":1.1,"outcome":1.,"loss":cell_loss(1,[.9,1,1.1])}]
    chosen,_=choose(x,[.5,1,2])
    assert chosen["lower"]==chosen["upper"]==.5
    tie=[{**x[0],"q10":1.,"q90":1.,"loss":0.}]
    picked,_=choose(tie,[.5,1,2]);assert picked["lower"]==picked["upper"]==1
def run():
    tests();cfg=read(pathlib.Path("configs/direct-tail-readout-v17.json"))
    root=pathlib.Path(cfg["source_report"]["report_path"]).parent
    raw=(root/"report.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest()==cfg["source_report"]["report_sha256"],"Frozen report changed"
    verify(root);report=json.loads(raw)
    output=pathlib.Path("artifacts/tail-readout-v17");output.mkdir(parents=True,exist_ok=True)
    all_rows=[];runs=[];cohort=None
    for run in report["runs"]:
        arm,seed=run["arm"],run["seed"];selected=run["selected"]["update"];directory=root/arm/("seed-"+str(seed))
        model_rows={};choices={};candidates={}
        for model,update,filename in (("base",0,"evaluation-base.json"),("sft",selected,"evaluation-selected.json")):
            dev=[r for r in read(directory/("development-"+str(update)+".json"))["cells"] if r["horizon_days"]==7]
            retrospective=[r for r in read(directory/filename)["cells"] if r["horizon_days"]==7]
            assert len(dev)==20 and len(retrospective)==22
            assert keys(dev).isdisjoint(keys(retrospective))
            if cohort is None:cohort=keys(retrospective)
            assert keys(retrospective)==cohort
            choice,grid=choose(dev,cfg["multipliers"]);choices[model]=choice;candidates[model]=grid
            adjusted=score(retrospective,choice["lower"],choice["upper"])
            for old,new in zip(retrospective,adjusted):
                assert old["task_id"]==new["task_id"] and old["q50"]==new["q50"],"Median must not change"
            model_rows[model+"_original"]=retrospective;model_rows[model+"_calibrated"]=adjusted
            # Evaluation outcomes cannot enter the development-only chooser.
            poisoned=[{**r,"outcome":r["outcome"]*1000+123} for r in retrospective]
            assert keys(poisoned)==keys(retrospective) and choose(dev,cfg["multipliers"])[0]==choice
            for version,rows in (("original",retrospective),("calibrated",adjusted)):
                for row in rows:
                    all_rows.append({"arm":arm,"seed":seed,"model":model,"version":version,"task_id":row["task_id"],"series_id":row["series_id"],"origin":row["origin"],"horizon_days":7,"target_date":row["target_date"],"outcome":row["outcome"],**{k:row[k] for k in ("q10","q50","q90","loss")},"failure":row.get("calibration_failure",False),"lower":1 if version=="original" else choice["lower"],"upper":1 if version=="original" else choice["upper"]})
        summaries={key:summary(rows) for key,rows in model_rows.items()}
        gap=summaries["sft_original"]["loss"]-summaries["base_original"]["loss"]
        adjusted_gap=summaries["sft_calibrated"]["loss"]-summaries["base_calibrated"]["loss"]
        origins=[]
        for origin in sorted({r["origin"] for r in model_rows["base_original"]}):
            s={name:summary([r for r in rows if r["origin"]==origin]) for name,rows in model_rows.items()}
            origins.append({"origin":origin,"n":s["base_original"]["n"],"original_gap":s["sft_original"]["loss"]-s["base_original"]["loss"],"calibrated_gap":s["sft_calibrated"]["loss"]-s["base_calibrated"]["loss"]})
        runs.append({"arm":arm,"seed":seed,"selected_update":selected,"development_choices":choices,"development_candidates":candidates,"retrospective":summaries,"original_gap":gap,"calibrated_gap":adjusted_gap,"gap_reduction":gap-adjusted_gap,"by_origin":origins})
    aggregates={name:{metric:mean(r["retrospective"][name][metric] for r in runs) for metric in ("loss","coverage","width","median_mae","failures")} for name in runs[0]["retrospective"]}
    original_gap=aggregates["sft_original"]["loss"]-aggregates["base_original"]["loss"]
    calibrated_gap=aggregates["sft_calibrated"]["loss"]-aggregates["base_calibrated"]["loss"]
    by_origin=[]
    for origin in sorted({x["origin"] for r in runs for x in r["by_origin"]}):
        rr=[x for r in runs for x in r["by_origin"] if x["origin"]==origin]
        by_origin.append({"origin":origin,"original_gap":mean(x["original_gap"] for x in rr),"calibrated_gap":mean(x["calibrated_gap"] for x in rr)})
    enough=original_gap-calibrated_gap>=.5*original_gap and sum(x["calibrated_gap"]<x["original_gap"] for x in by_origin)>=2
    result={"study_id":cfg["study_id"],"classification":cfg["classification"],"source_report_sha256":cfg["source_report"]["report_sha256"],"config":cfg,"new_optimizer_updates":0,"new_inference_requests":0,"new_outcomes_retrieved":0,"runs":runs,"aggregates":aggregates,"original_gap":original_gap,"calibrated_gap":calibrated_gap,"gap_reduction":original_gap-calibrated_gap,"prespecified_descriptive_repair_criterion_met":enough,"by_origin":by_origin,"distinct_market_cases":22,"series":10,"market_origins":3,"prospective_accuracy":"not established","limits":["Multiplier grid was chosen after earlier outcome analysis: this remains a post-hoc diagnostic","Base and SFT both receive the same development-selection budget","Original checkpoint selections and all original scores remain unchanged","Repeated models and horizons are not independent market observations"]}
    save(output/"report.json",result)
    with (output/"predictions.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(all_rows[0]));w.writeheader();w.writerows(all_rows)
    text=["# Frozen tail-readout diagnostic","","Post-hoc retrospective comparison; no training or inference was performed.","","Both base and selected SFT receive the same nine-candidate development-only calibration selection.","","| Model | Seven-day loss | Coverage | Width |","|---|---:|---:|---:|"]
    for name,v in aggregates.items():text.append(f'| {name} | {v["loss"]:.10f} | {v["coverage"]:.2%} | {v["width"]:.6f} |')
    text.extend(["",f"Original SFT-minus-base gap: {original_gap:+.10f}.",f"Calibrated SFT-minus-base gap: {calibrated_gap:+.10f}.",f"Prespecified descriptive repair criterion met: {enough}.","","These results cannot establish prospective improvement or repair the original training claim. Original frozen outputs and future protocols remain unchanged."])
    (output/"findings.md").write_text("\n".join(text)+"\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":12,"figure.facecolor":"#f8f5ee","axes.facecolor":"#f8f5ee","text.color":"#21313d","axes.labelcolor":"#21313d","xtick.color":"#21313d","ytick.color":"#21313d"})
    fig,ax=plt.subplots(figsize=(10,5),layout="constrained")
    for i,r in enumerate(runs):
        ax.plot([r["original_gap"],r["calibrated_gap"]],[i,i],color="#9a988f",lw=1.5)
        ax.scatter(r["original_gap"],i,facecolors="none",edgecolors="#214fbd",s=65,zorder=3)
        ax.scatter(r["calibrated_gap"],i,color="#32735b",s=65,zorder=3)
    ax.axvline(0,color="#333b42",lw=1);ax.set_yticks(range(6),[("Price" if r["arm"]=="price_only" else "Price + BLS")+" / "+str(r["seed"]) for r in runs]);ax.invert_yaxis()
    ax.set_xlabel("SFT minus corresponding base seven-day pinball · positive = worse")
    ax.set_title("Does equal-budget tail calibration change the training comparison?",loc="left",pad=34)
    ax.text(0,1.03,"Open: original forecasts     Filled: both models calibrated on development data",transform=ax.transAxes,fontsize=10)
    ax.spines[["top","right"]].set_visible(False)
    fig.savefig(output/"matched-tail-gap.png",dpi=180);fig.savefig(output/"matched-tail-gap.svg");plt.close(fig)
    files=[{"path":p.name,"bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(output.iterdir()) if p.is_file() and p.name!="manifest.json"]
    save(output/"manifest.json",{"study_id":cfg["study_id"],"source_sha":os.environ.get("GITHUB_SHA"),"input_report_sha256":cfg["source_report"]["report_sha256"],"files":files})
    print(json.dumps({"status":"completed","new_optimizer_updates":0,"original_gap":original_gap,"calibrated_gap":calibrated_gap,"repair_criterion_met":enough}))
if __name__=="__main__":run()
