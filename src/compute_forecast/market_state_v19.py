"""Source-specific market state and direct-price inputs. No model or network calls."""
from __future__ import annotations
import json,math,statistics
from datetime import date,datetime,timedelta,timezone
from .probability_v18 import digest,support,bin_index
MARKET_FIELDS=("observed_provider_count","observed_quote_count","unknown_region_fraction","unknown_node_fraction","observed_provider_concentration","comparable_provider_count","log_anchor_to_peer_median","peer_log_iqr","log_anchor_to_peer_min","log_anchor_to_peer_max","peer_price_rank","peer_log_step_7d","peer_return_median_1d","peer_return_median_3d","peer_return_median_7d","peer_return_iqr_7d","peer_up_fraction_7d","peer_down_fraction_7d","peer_unchanged_fraction_7d","peer_return_provider_count_7d")
SHARED_FIELDS=("days_since_observed_repricing","observed_change_fraction_14d","observed_log_step_sd_14d","log_change_7d","context_missing_fraction","origin_observation_age_hours")
CONTRACT_FIELDS=("provider","gpu","vram_gb","kind","region","min_gpus","gpu_count_reported","instance","vcpus","ram_gib","ram_label","disk_label","rate_basis","commitment","reservation_months","source_url")
def utc(value):
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("Timezone required")
    return t.astimezone(timezone.utc)
def allowed(day):return not "2026-11-07"<=day<="2026-11-13"
def contract(row):return {k:row.get(k) for k in CONTRACT_FIELDS}
def quantile(values,q):
    a=sorted(values)
    if not a:return None
    position=(len(a)-1)*q;lo=math.floor(position);hi=math.ceil(position)
    return a[lo]+(a[hi]-a[lo])*(position-lo)
def check_asof(rows,origin):
    bound=utc(origin+"T23:59:59.999999+00:00")
    for r in rows:
        if r["date"]>origin or not allowed(r["date"]):raise ValueError("Future or protected observation")
        if r.get("available_at") and utc(r["available_at"])>bound:raise ValueError("Observation became available after origin")
        if not math.isfinite(r["value"]) or r["value"]<=0:raise ValueError("Invalid price")
def shared_features(task):
    rows=task["context"];origin=task["origin"];check_asof(rows,origin)
    pairs=[(a,b) for a,b in zip(rows,rows[1:]) if b["date"]>=(date.fromisoformat(origin)-timedelta(days=14)).isoformat()]
    steps=[math.log(b["value"]/a["value"]) for a,b in pairs]
    changes=[b["date"] for a,b in zip(rows,rows[1:]) if a["value"]!=b["value"]]
    past=[r for r in rows if r["date"]<=(date.fromisoformat(origin)-timedelta(days=7)).isoformat()]
    latest=rows[-1];stamp=latest.get("available_at") or latest["date"]+"T23:59:59+00:00"
    return {"days_since_observed_repricing":(date.fromisoformat(origin)-date.fromisoformat(changes[-1])).days if changes else None,"observed_change_fraction_14d":sum(a["value"]!=b["value"] for a,b in pairs)/len(pairs) if pairs else None,"observed_log_step_sd_14d":statistics.pstdev(steps) if len(steps)>1 else None,"log_change_7d":math.log(task["anchor"]/past[-1]["value"]) if past else None,"context_missing_fraction":task.get("context_missing_days",0)/42,"origin_observation_age_hours":max(0,(utc(origin+"T23:59:59+00:00")-utc(stamp)).total_seconds()/3600)}
def market_features(target,quotes,origin,past_quotes=None,past_by_horizon=None):
    check_asof(quotes,origin)
    meta=target["metadata"];same=[r for r in quotes if r["metadata"].get("source_id")==meta.get("source_id") and r["metadata"].get("gpu_model")==meta.get("gpu_model") and r["metadata"].get("pricing_tier")==meta.get("pricing_tier") and r["metadata"].get("instrument_class")==meta.get("instrument_class")]
    counts={}
    for r in same:counts[r["metadata"]["provider"]]=counts.get(r["metadata"]["provider"],0)+1
    n=len(same);result={k:None for k in MARKET_FIELDS}
    if not n:return result
    result.update(observed_provider_count=len(counts),observed_quote_count=n,unknown_region_fraction=sum(not r["metadata"].get("region") for r in same)/n,unknown_node_fraction=sum(not r["metadata"].get("gpu_count") for r in same)/n,observed_provider_concentration=sum((v/n)**2 for v in counts.values()))
    # Unknown region/node identity never establishes comparable competing contracts.
    peers=[]
    if meta.get("region") and meta.get("gpu_count"):
        peers=[r for r in same if r["metadata"]["provider"]!=meta["provider"] and r["metadata"].get("region")==meta["region"] and r["metadata"].get("gpu_count")==meta["gpu_count"] and r["metadata"].get("gpu_memory_gb")==meta.get("gpu_memory_gb")]
    providers={}
    for r in peers:providers.setdefault(r["metadata"]["provider"],[]).append(r["value"])
    values=[statistics.median(v) for v in providers.values()];result["comparable_provider_count"]=len(values)
    if len(values)>=2:
        logs=[math.log(v) for v in values];anchor=target["anchor"]
        result.update(log_anchor_to_peer_median=math.log(anchor/statistics.median(values)),peer_log_iqr=quantile(logs,.75)-quantile(logs,.25),log_anchor_to_peer_min=math.log(anchor/min(values)),log_anchor_to_peer_max=math.log(anchor/max(values)),peer_price_rank=sum(v<=anchor for v in values)/len(values))
        if past_quotes:
            check_asof(past_quotes,origin);prior={r["series_id"]:r for r in past_quotes}
            steps=[math.log(r["value"]/prior[r["series_id"]]["value"]) for r in peers if r["series_id"] in prior]
            if steps:result["peer_log_step_7d"]=statistics.median(steps)
    # A return is calculated within the same source-defined group first.
    # This is an indirect market signal, not a cross-contract dollar comparison.
    history=past_by_horizon or ({7:past_quotes} if past_quotes else {})
    for horizon in (1,3,7):
        old=history.get(horizon,[]);check_asof(old,origin);prior={r["series_id"]:r for r in old};paired={}
        for r in same:
            if r["metadata"]["provider"]==meta["provider"] or r["series_id"] not in prior:continue
            before=prior[r["series_id"]]
            if before["metadata"]!=r["metadata"]:raise ValueError("Return context identity changed")
            paired.setdefault(r["metadata"]["provider"],[]).append(math.log(r["value"]/before["value"]))
        changes=[statistics.median(v) for v in paired.values()]
        if len(changes)>=2:
            result["peer_return_median_"+str(horizon)+"d"]=statistics.median(changes)
            if horizon==7:
                result.update(peer_return_iqr_7d=quantile(changes,.75)-quantile(changes,.25),peer_up_fraction_7d=sum(v>0 for v in changes)/len(changes),peer_down_fraction_7d=sum(v<0 for v in changes)/len(changes),peer_unchanged_fraction_7d=sum(v==0 for v in changes)/len(changes),peer_return_provider_count_7d=len(changes))
        elif horizon==7:result["peer_return_provider_count_7d"]=len(changes)
    return result
def normalize_latest(payload,health,retrieved_at,raw_sha256,health_sha256):
    at=utc(retrieved_at);day=payload.get("date")
    if not day or not allowed(day) or day>at.date().isoformat() or day!=health.get("snapshot_date"):raise ValueError("Invalid source day or health vintage")
    if utc(payload["generated_at"])>at:raise ValueError("Future source publication")
    groups={};excluded=[];fresh=health.get("provider_freshness",{})
    variants={"a100-pcie-40","a100-pcie-80","a100-sxm-40","a100-sxm-80","h100-pcie","h100-sxm","h100-nvl"}
    for row in payload.get("offers",[]):
        if row.get("gpu") not in variants or row.get("kind")!="on-demand":continue
        c=contract(row);sid="market-v19-grp-"+digest(c)[:20]
        try:
            fetched=utc(row["fetched_at"]);price=float(row["usd_hr"])
            if fetched>at or fetched.date().isoformat()!=day or fresh.get(row["provider"],{}).get("status")!="current":raise ValueError("Stale or unverified provider check")
            if not math.isfinite(price) or price<=0:raise ValueError("Nonpositive price")
        except (KeyError,TypeError,ValueError) as error:
            excluded.append({"series_id":sid,"reason":str(error)});continue
        groups.setdefault(sid,{"contract":c,"prices":[],"times":[]})["prices"].append(price);groups[sid]["times"].append(row["fetched_at"])
    rows=[]
    for sid,g in sorted(groups.items()):
        if len(set(g["prices"]))>1:excluded.append({"series_id":sid,"reason":"ambiguous_same_contract_prices"});continue
        c=g["contract"];family="H100" if c["gpu"].startswith("h100") else "A100"
        meta={"source_id":"gpurentalprices-current-v19","provider":c["provider"],"gpu_model":c["gpu"],"family":family,"pricing_tier":"on_demand","instrument_class":"provider_rate_card","region":c.get("region"),"gpu_count":c.get("min_gpus") if c.get("gpu_count_reported") else None,"gpu_memory_gb":c.get("vram_gb"),"benchmark_contract":json.dumps(c,sort_keys=True)}
        rows.append({"series_id":sid,"date":day,"available_at":retrieved_at,"value":g["prices"][0],"metadata":meta,"contract":c,"provider_checked_at":max(g["times"]),"source_sha256":raw_sha256,"health_sha256":health_sha256,"unit":"USD per GPU-hour","quote_update_timestamp_verified":False})
    return {"date":day,"captured_at":retrieved_at,"rows":rows,"excluded":excluded,"source_sha256":raw_sha256,"health_sha256":health_sha256,"license":"CC-BY-4.0","permission_url":"https://gpurentalprices.com/data","credit":"GPU Rental Prices"}
def prompt(task,h):
    from .probability_v18 import prompt as base_prompt
    value=json.loads(base_prompt(task,h));value["shared_history_summary"]=shared_features(task)
    arm=task.get("arm")
    if arm not in ("price","market"):raise ValueError("Unknown matched arm")
    block=task.get("market_state",{});features={}
    for key in MARKET_FIELDS:
        v=block.get(key) if arm=="market" else None
        if v is not None and (not isinstance(v,(int,float)) or not math.isfinite(v)):raise ValueError("Nonfinite market feature")
        features[key]=v
    value["market_state"]={"values":features,"availability":"observed source-specific price context" if arm=="market" else "withheld by study","scope":"Observed collector composition and within-group return context; comparable-price fields require recorded region and node agreement; no stock, utilization or transaction claims"}
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)
def decision(task,h,log_levels):
    from tinker_cookbook.recipes.decisions import Decision
    z=support(task["anchor"],log_levels)
    return Decision(prompt(task,h),[(str(i),"Future price "+format(v,".10g")+" USD per GPU-hour; log change "+format(log_levels[i],".8g")+("; unchanged price" if log_levels[i]==0 else "")) for i,v in enumerate(z)])
def datum(task,h,log_levels,renderer):
    import torch,tinker
    from tinker_cookbook.recipes.decisions import decision_dist_datums
    z=support(task["anchor"],log_levels);y=task["outcomes"][(1,3,7).index(h)]
    result=decision_dist_datums(renderer,[(decision(task,h,log_levels),{str(bin_index(z,y)):1.})])[0]
    result.loss_fn_inputs["price_levels"]=tinker.TensorData.from_torch(torch.tensor(z,dtype=torch.float32))
    result.loss_fn_inputs["outcome_price"]=tinker.TensorData.from_torch(torch.tensor([y],dtype=torch.float32))
    return result
