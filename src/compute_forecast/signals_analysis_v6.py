"""Fixed final-panel analysis; no interim significance claims or automatic promotion."""
import random,statistics
from datetime import date,timedelta
from .signals_v6 import config,utc,paired
def block_interval(values,weights=None):
    weights=weights or [1]*len(values)
    if len(values)<16:return {"status":"insufficient_origins","interval":None,"p_one_sided":None}
    rng=random.Random(17);n=len(values);means=[]
    for _ in range(2000):
        sample=[]
        while len(sample)<n:
            start=rng.randrange(n);sample.extend((start+i)%n for i in range(4))
        chosen=sample[:n];means.append(sum(values[i]*weights[i] for i in chosen)/sum(weights[i] for i in chosen))
    means.sort();observed=sum(v*w for v,w in zip(values,weights))/sum(weights)
    return {"status":"descriptive_moving_block_bootstrap","block_origins":4,"replicates":2000,"seed":17,"interval":[means[int(.025*1999)],means[int(.975*1999)]],"p_one_sided":(1+sum(m-observed<=observed for m in means))/2001,"limitations":"Origin clusters can remain dependent; a finite registered panel does not establish universal gains."}
def holm(pvalues):
    ranked=sorted((v if v is not None else 1,k) for k,v in pvalues.items());out={k:None for k in pvalues};running=0
    for i,(value,key) in enumerate(ranked):
        running=max(running,(len(ranked)-i)*value);out[key]=min(1,running) if pvalues[key] is not None else None
    return out
def summarize(scores,snapshots,at):
    p=config();last=(date.fromisoformat(p["origins"][-1])+timedelta(days=8)).isoformat()+"T00:00:00+00:00";final=utc(at)>=utc(last)
    comparisons=[("signals_111","signals_000"),("signals_111","drift"),("signals_111","signals_011"),("signals_111","signals_101"),("signals_111","signals_110")]
    collected={a+"__"+b:[] for a,b in comparisons};trajectory=[];exclusions=[]
    for report in scores:
        if report.get("classification")!="primary_factorial":continue
        rows=[c for c in report["cells"] if c["horizon_days"]==7]
        masks={m:{(c["series_id"],c["target_date"],c["horizon_days"]) for c in rows if c["forecaster"]=="signals_"+m} for m in p["learner"]["feature_masks"]}
        common=set.intersection(*masks.values()) if masks else set()
        common&={(c["series_id"],c["target_date"],c["horizon_days"]) for c in rows if c["forecaster"]=="drift"}
        matched=[c for c in rows if (c["series_id"],c["target_date"],c["horizon_days"]) in common]
        if not common:exclusions.append({"origin":report["origin_date"],"reason":"No complete matched eight-arm plus drift cells"});continue
        point={"origin":report["origin_date"],"matched_cells":len(common),"comparisons":[]}
        for a,b in comparisons:
            result=paired(matched,a,b);point["comparisons"].append(result);collected[a+"__"+b].append(result)
        trajectory.append(point)
    totals=[]
    for a,b in comparisons:
        values=collected[a+"__"+b];n=sum(v["cells"] for v in values)
        item={"candidate":a,"reference":b,"origins":len(values),"matched_cells":n,"weighted_difference":sum(v["difference"]*v["cells"] for v in values)/n if n else None,"interval_status":"pending_fixed_final_analysis"}
        if final:item["uncertainty"]=block_interval([v["difference"] for v in values],[v["cells"] for v in values])
        totals.append(item)
    periods={s["bls"]["latest_period"] for s in snapshots if s.get("bls")};events={e["id"]:e for s in snapshots for e in s.get("events",[]) if e.get("publication_verified")}
    variation={"news":len(events)>=8,"infrastructure":len([e for e in events.values() if e["kind"] in ("capacity_plan","hardware_announcement")])>=5,"bls":len(periods)>=3 and len({s["bls"]["observations"][0]["value"] for s in snapshots if s.get("bls")})>=2}
    raw_p={group:(totals[i+2].get("uncertainty",{}).get("p_one_sided") if variation[group] else None) for i,group in enumerate(("news","infrastructure","bls"))};adjusted=holm(raw_p) if final else {g:None for g in variation};support={}
    for i,g in enumerate(("news","infrastructure","bls")):
        t=totals[i+2];interval=t.get("uncertainty",{}).get("interval")
        support[g]={"variation_screen_passed":variation[g],"holm_adjusted_p":adjusted[g],"improvement_established":bool(final and variation[g] and adjusted[g] is not None and adjusted[g]<.05 and interval and interval[1]<0 and t["weighted_difference"]<0)}
    primary=totals[0];interval=primary.get("uncertainty",{}).get("interval");established=bool(final and interval and interval[1]<0 and primary["weighted_difference"]<0)
    return {"analysis_at":at,"final_analysis_after":last,"final_gate_open":final,"primary_horizon":7,"trajectory":trajectory,"comparisons":totals,"exclusions":exclusions,"group_effects":support,"prospective_improvement_established":established,"promotion":"No automatic promotion during registered panel; successor deployment requires separately registered future comparison","claim":"Registered-panel evidence supports an all-signals gain on the matched cohort." if established else "The experiment is running; prospective improvement is not yet established.","independence":"Weekly origins and GPU series can remain correlated. Cells are not independent market samples."}
