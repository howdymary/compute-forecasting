"""Separate prospective issuer. Frozen v2 date guards are never modified."""
from __future__ import annotations
import asyncio,hashlib,json,math,random,statistics,time,uuid
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from .review_v4 import INITIAL,TREE,digest,encoded
from .vintage_v4 import TARGET,permitted,select_snapshot,utc,validate_snapshot
def protocol():return json.loads(Path("configs/prospective-selector-v4.json").read_bytes())
def experiment_protocol():return json.loads(Path("configs/review-v4-experiments.json").read_bytes())
def origin_gate(origin,now,p):
    if origin not in p["origins"]:raise ValueError("Unregistered prospective origin")
    start=utc(origin+"T00:00:00+00:00");deadline=start+timedelta(hours=p["issuance_deadline_hours_utc"])
    if not start<=now<=deadline:raise ValueError("Outside issuance window; no retrospective issuance")
def values_for(snapshot,sid,cutoff):
    s=next((s for s in snapshot["series"] if s["id"]==sid),None)
    if s is None:return {},{}
    values={date.fromisoformat(p["date"]):float(p["value"]) for p in s["points"] if p["date"]<=cutoff}
    extra={k:{date.fromisoformat(d):{field:(float("nan") if v is None else v) for field,v in row.items()} for d,row in panel.items() if d<=cutoff} for k,panel in s.get("auxiliary",{}).items()}
    return values,extra
def reference(values,at,lead,method):
    from .interval_v4 import quantile
    if at not in values:return None,"missing_latest_input"
    last=values[at]
    if method=="last_value":return [last]*3,None
    pairs=[values[d+timedelta(days=lead)]-y for d,y in values.items() if at-timedelta(days=180)<=d+timedelta(days=lead)<=at and d+timedelta(days=lead) in values]
    if len(pairs)<8:return None,"insufficient_matured_reference_pairs"
    if method=="last_value_empirical":qs=[last+quantile(pairs,q) for q in (.1,.5,.9)]
    else:
        if method=="drift":
            daily=[values[d]-values[d-timedelta(days=1)] for d in values if d-timedelta(days=1) in values and at-timedelta(days=180)<=d<=at]
            if not daily:return None,"insufficient_drift_history"
            center=last+lead*statistics.mean(daily)
        elif method=="seasonal_naive":
            back=7-((lead-1)%7+1)
            d=at-timedelta(days=back)
            if d not in values:return None,"missing_seasonal_anchor"
            center=values[d]
        else:raise ValueError("Unknown reference")
        bias=statistics.mean(pairs);qs=[center+quantile([r-bias for r in pairs],q) for q in (.1,.5,.9)]
    if qs!=sorted(qs) or any(not math.isfinite(v) or v<=0 for v in qs):return None,"invalid_reference_quantiles"
    return qs,None
def numerical(snapshot,sid,origin):
    from .campaign_v2 import REGISTRY,predict_custom
    cutoff=(date.fromisoformat(origin)-timedelta(days=1)).isoformat();at=date.fromisoformat(cutoff)
    values,extras=values_for(snapshot,sid,cutoff);outputs={};failures=[]
    if not values or at not in values:return None,[{"series_id":sid,"reason":"missing_latest_input","origin":origin}]
    recent=[d for d in values if d>=at-timedelta(days=119)]
    if len(recent)<56:return None,[{"series_id":sid,"reason":"insufficient_observed_history","origin":origin,"observed":len(recent)}]
    for config in REGISTRY:
        identifier=config["id"];rows=[]
        for h in (1,3,7):
            target=date.fromisoformat(origin)+timedelta(days=h);lead=(target-at).days
            base,why=reference(values,at,lead,"last_value_empirical")
            if base is None:failures.append({"series_id":sid,"config_id":identifier,"horizon_days":h,"reason":why});continue
            reason=None;repair=False
            if config["family"]=="reference":qs,reason=reference(values,at,lead,identifier)
            else:qs,reason,repair=predict_custom(values,cutoff,lead,config,extras,base,{})
            fallback=None
            if qs is None:
                fallback=reason;qs=base
            if qs!=sorted(qs) or any(not math.isfinite(float(v)) or v<=0 for v in qs):raise ValueError("Invalid numerical quantiles")
            rows.append({"series_id":sid,"origin":origin,"target_date":target.isoformat(),"horizon_days":h,"effective_lead_days":lead,"q10":float(qs[0]),"q50":float(qs[1]),"q90":float(qs[2]),"fallback":fallback,"quantile_order_repair":repair})
        if len(rows)==3:outputs[identifier]=rows
    if len(outputs)!=42:return None,failures+[{"series_id":sid,"reason":"incomplete_fixed_candidate_pool","available":len(outputs)}]
    return outputs,failures
def pinball(y,row):return sum(max(q*(y-row[k]),(q-1)*(y-row[k])) for q,k in ((.1,"q10"),(.5,"q50"),(.9,"q90")))/3
def matured_task(root,current,sid,origin,p,scale):
    from .campaign_v2 import REGISTRY
    validation={c["id"]:[] for c in REGISTRY};audits=[]
    for lag in p["validation_lags_days"]:
        fold=(date.fromisoformat(origin)-timedelta(days=lag)).isoformat();past=select_snapshot(root,fold,p["issuance_deadline_hours_utc"])
        if not past:return None,{"reason":"missing_actual_validation_vintage","validation_origin":fold}
        fits,failures=numerical(past["value"],sid,fold)
        if fits is None:return None,{"reason":"ineligible_validation_fit","validation_origin":fold,"failures":failures}
        actual,_=values_for(current,sid,(date.fromisoformat(origin)-timedelta(days=1)).isoformat())
        for c,rows in fits.items():
            for row in rows:
                day=date.fromisoformat(row["target_date"])
                if day>=date.fromisoformat(origin) or not permitted(day.isoformat()):raise ValueError("Nonmature or protected validation label")
                if day not in actual:return None,{"reason":"missing_validation_outcome","date":day.isoformat()}
                validation[c].append(pinball(actual[day],row))
        audits.append({"origin":fold,"snapshot_id":past["snapshot_id"],"last_label_date":max(r["target_date"] for r in next(iter(fits.values())))})
    values,_=values_for(current,sid,(date.fromisoformat(origin)-timedelta(days=1)).isoformat());days=sorted(values)
    task={"task_id":digest({"origin":origin,"series_id":sid})[:20],"origin":origin,"phase":"prospective_selection","group":sid,"series_ids":[sid],"scale":scale,"observation":{"n_series":1,"mean_history_observations":len(values),"mean_price_changes":sum(values[a]!=values[b] for a,b in zip(days,days[1:])),"mean_missing_calendar_days":(days[-1]-days[0]).days+1-len(days),"measurement":"independently licensed advertised offers; current retained vintage"},"validation":{c:{"loss":statistics.mean(v),"n_cells":len(v),"last_label_date":max(a["last_label_date"] for a in audits)} for c,v in validation.items()},"validation_vintages":audits}
    return task,None
async def policy_clients():
    import tinker
    from tinker_cookbook import model_info,renderers
    from tinker_cookbook.recipes.decisions import DecisionRenderer
    from .policy_v2 import MODEL,load_private,app as original_app
    # Loading preserved private resources does not create, delete or retrain them.
    resource=Path("/data/campaign-v2/policies/c24ee0b5943f48c2bfa17032598f42f4.json")
    if resource.is_file():private=json.loads(resource.read_bytes())
    else:
        with original_app.run():private=load_private.remote("c24ee0b5943f48c2bfa17032598f42f4")
    checkpoint=private["selected"]
    if checkpoint["checkpoint_id"]!="ef9cf57b88d0bbe9ef3d":raise ValueError("Frozen sampler identity changed")
    service=tinker.ServiceClient(display_name="Compute Forecast v4 frozen-policy inference")
    base=await service.create_sampling_client(base_model=MODEL)
    trained=await service.create_sampling_client(model_path=checkpoint["sampler_path"])
    renderer=DecisionRenderer(renderers.get_renderer(model_info.get_recommended_renderer_name(MODEL),base.get_tokenizer()))
    return {"starting_policy":base,"frozen_operational_sft":trained},renderer
async def select_policy(task,sampler,renderer,evidence=None):
    from .policy_v2 import choose
    revealed=list(INITIAL);steps=[]
    for i in range(4):
        choice,decisions=await choose(task,revealed,sampler,renderer,evidence=evidence)
        steps.append({"step":i,"selected_config_id":choice,"decisions":[{k:v for k,v in d.items() if k!="decision"} for d in decisions]});revealed.append(choice)
    selected=min(revealed,key=lambda c:task["validation"][c]["loss"])
    return selected,revealed,steps
def chronos_rows(snapshot,sid,origin,p):
    import numpy as np
    import torch
    from chronos import Chronos2Pipeline
    cutoff=(date.fromisoformat(origin)-timedelta(days=1));values,_=values_for(snapshot,sid,cutoff.isoformat())
    days=[min(values)+timedelta(days=i) for i in range((cutoff-min(values)).days+1)]
    context=torch.tensor([values.get(d,float("nan")) for d in days],dtype=torch.float32)
    pipeline=Chronos2Pipeline.from_pretrained(p["chronos"]["model"],revision=p["chronos"]["revision"],device_map="cpu")
    q,_=pipeline.predict_quantiles(inputs=[context],prediction_length=8,quantile_levels=[.1,.5,.9],cross_learning=False)
    out=[]
    for h in (1,3,7):
        qs=q[0][h].tolist()
        if qs!=sorted(qs) or any(not math.isfinite(v) or v<=0 for v in qs):raise ValueError("Invalid native Chronos quantiles")
        out.append({"series_id":sid,"origin":origin,"target_date":(date.fromisoformat(origin)+timedelta(days=h)).isoformat(),"horizon_days":h,"effective_lead_days":h+1,"q10":qs[0],"q50":qs[1],"q90":qs[2]})
    return out
async def issue(root,origin,scale,now=None):
    now=now or datetime.now(timezone.utc);p=protocol();origin_gate(origin,now,p);begin=time.perf_counter();snapshot=select_snapshot(root,origin,p["issuance_deadline_hours_utc"])
    record={"schema_version":4,"study_id":p["study_id"],"origin":origin,"issued_at":now.isoformat(),"registration_sha256":digest(p),"target_definition_sha256":digest(TARGET),"source_sha":__import__("os").environ.get("GITHUB_SHA"),"status":"pending","rows":[],"failures":[],"decisions":[],"snapshot_id":snapshot["snapshot_id"] if snapshot else None,"training_updates":0,"provider_cost_usd":None}
    if not snapshot:record["failures"].append({"reason":"no_retained_source_vintage"});return record
    clients=None;renderer=None;policy_error=None
    try:clients,renderer=await policy_clients()
    except Exception as e:policy_error=type(e).__name__
    from .controls_v2 import select_trials
    from .interval_v4 import empirical_interval
    for cohort,sids in p["cohorts"].items():
        for sid in sids:
            fits,failures=numerical(snapshot["value"],sid,origin);record["failures"].extend(failures)
            if fits is None:continue
            for label in ("last_value","last_value_empirical"):
                record["rows"].extend({**r,"forecaster":"direct_"+label,"cohort":cohort} for r in fits[label])
            try:record["rows"].extend({**r,"forecaster":"direct_chronos2","cohort":cohort} for r in chronos_rows(snapshot["value"],sid,origin,p))
            except Exception as e:record["failures"].append({"forecaster":"direct_chronos2","series_id":sid,"reason":type(e).__name__})
            at=date.fromisoformat(origin)-timedelta(days=1);values,_=values_for(snapshot["value"],sid,at.isoformat())
            for h in (1,3,7):
                v=empirical_interval(values,at,h+1)
                if v["status"]!="completed":record["failures"].append({"forecaster":"interval_recency_weighted","series_id":sid,"horizon_days":h,"reason":v["status"]});continue
                record["rows"].append({"forecaster":"interval_recency_weighted","cohort":cohort,"series_id":sid,"origin":origin,"target_date":(date.fromisoformat(origin)+timedelta(days=h)).isoformat(),"horizon_days":h,"q10":v["quantiles"][0],"q50":v["quantiles"][1],"q90":v["quantiles"][2],"calibration":{k:x for k,x in v.items() if k!="quantiles"}})
            task,error=matured_task(root,snapshot["value"],sid,origin,p,scale)
            if error:record["failures"].append({"series_id":sid,**error});continue
            static={"four_tree_portfolio":TREE,"training_selected_static":p["training_selected_static"],"random_seed_17":random.Random(17+int(task["task_id"][:8],16)).sample([c for c in fits if c not in INITIAL],4)}
            gp=select_trials(task);static["gp_complete_metadata"]=gp[len(INITIAL):] if gp[:2]==INITIAL else gp
            for label,additional in static.items():
                revealed=INITIAL+additional
                if len(revealed)!=6 or len(set(revealed))!=6:raise ValueError("Unequal selector budget")
                choice=min(revealed,key=lambda c:task["validation"][c]["loss"]);record["rows"].extend({**r,"forecaster":label,"cohort":cohort} for r in fits[choice]);record["decisions"].append({"forecaster":label,"task_id":task["task_id"],"selected":choice,"revealed":revealed,"validation_vintages":task["validation_vintages"]})
            for label in ("starting_policy","frozen_operational_sft"):
                if clients is None:record["failures"].append({"forecaster":label,"series_id":sid,"reason":"sampler_unavailable_"+str(policy_error)});continue
                try:
                    choice,revealed,steps=await select_policy(task,clients[label],renderer)
                    record["rows"].extend({**r,"forecaster":label,"cohort":cohort} for r in fits[choice]);record["decisions"].append({"forecaster":label,"task_id":task["task_id"],"selected":choice,"revealed":revealed,"steps":steps,"validation_vintages":task["validation_vintages"]})
                except Exception as e:record["failures"].append({"forecaster":label,"series_id":sid,"reason":type(e).__name__})
            from .market_context_v4 import load_for_issue
            market=load_for_issue("/data/review-v4/market",now.isoformat())
            if clients is not None and market is not None:
                try:
                    choice,revealed,steps=await select_policy(task,clients["frozen_operational_sft"],renderer,evidence=market)
                    record["rows"].extend({**r,"forecaster":"exploratory_sft_market_context","cohort":cohort} for r in fits[choice])
                    record["decisions"].append({"forecaster":"exploratory_sft_market_context","classification":"Separate exploratory extra-information treatment","selected":choice,"revealed":revealed,"steps":steps,"market_context_sha256":market["source_sha256"],"market_available_at":market["available_at"]})
                except Exception as e:record["failures"].append({"forecaster":"exploratory_sft_market_context","series_id":sid,"reason":type(e).__name__})
            else:record["failures"].append({"forecaster":"exploratory_sft_market_context","series_id":sid,"reason":"missing_fresh_market_context_or_sampler"})
    import importlib.metadata
    record["packages"]={name:importlib.metadata.version(name) for name in ("numpy","pandas","scikit-learn","scipy","torch","tinker","tinker-cookbook","chronos-forecasting")}
    record["checkpoint"]=p["checkpoint"]
    from .campaign_v2 import REGISTRY
    record["candidate_registry_sha256"]=digest(REGISTRY)
    record["status"]="issued_with_failures" if record["failures"] else "issued"
    if not record["rows"]:record["status"]="pending_no_eligible_cases"
    record["issued_at"]=datetime.now(timezone.utc).isoformat()
    record["runtime_seconds"]=time.perf_counter()-begin;record["outcome_status"]="pending"
    return record
def retain_commitment(root,record,now=None):
    now=now or datetime.now(timezone.utc);origin_gate(record["origin"],now,protocol())
    if utc(record["issued_at"])>now:raise ValueError("Future issuance")
    root=Path(root)/"commitments";root.mkdir(parents=True,exist_ok=True);path=root/(record["origin"]+".json");raw=encoded(record)
    if path.exists() and path.read_bytes()!=raw:raise ValueError("An origin is already committed; forecasts cannot be replaced")
    if not path.exists():
        with path.open("xb") as f:f.write(raw)
    receipt={"record_sha256":digest(record),"bytes_sha256":hashlib.sha256(raw).hexdigest(),"origin":record["origin"],"issued_at":record["issued_at"],"rows":len(record["rows"]),"status":record["status"],"registration_sha256":record["registration_sha256"]}
    return receipt
def score_locked(record,expected_sha,truth,now=None):
    now=now or datetime.now(timezone.utc)
    if digest(record)!=expected_sha:raise ValueError("Commitment changed")
    if record["registration_sha256"]!=digest(protocol()):raise ValueError("Registered protocol changed")
    if not record["rows"]:return {"status":"pending_no_issued_rows","scores":None}
    end=max(date.fromisoformat(r["target_date"]) for r in record["rows"])+timedelta(days=1)
    if now<datetime.combine(end,datetime.min.time(),timezone.utc):raise ValueError("Outcomes have not matured")
    validate_snapshot(truth,now)
    if digest(truth["target_definition"])!=record["target_definition_sha256"]:raise ValueError("Truth identity differs")
    actual={(s["id"],p["date"]):p["value"] for s in truth["series"] for p in s["points"]}
    groups={}
    for r in record["rows"]:
        label=r["forecaster"]+("|"+r["cohort"] if "cohort" in r else "")
        groups.setdefault(label,[]).append(r)
    baseline={ (r["series_id"],r["target_date"],r["horizon_days"]):r for r in record["rows"] if r["forecaster"]=="direct_last_value"}
    scores={};missing=[]
    for label,rows in groups.items():
        keys=[(r["series_id"],r["target_date"],r["horizon_days"]) for r in rows]
        if len(set(keys))!=len(keys):raise ValueError("Duplicate issued cell")
        absent=[k for k in keys if (k[0],k[1]) not in actual or k not in baseline]
        if absent:missing.extend(absent);continue
        loss=[];base=[];covered=[];width=[]
        for r in rows:
            qs=[r[k] for k in ("q10","q50","q90")]
            if qs!=sorted(qs) or any(not math.isfinite(v) or v<=0 for v in qs):raise ValueError("Invalid committed quantiles")
            k=(r["series_id"],r["target_date"],r["horizon_days"]);y=actual[k[:2]]
            loss.append(pinball(y,r));base.append(pinball(y,baseline[k]));covered.append(qs[0]<=y<=qs[2]);width.append(qs[2]-qs[0])
        scores[label]={"forecaster":rows[0]["forecaster"],"cohort":rows[0].get("cohort","synthetic_fixture"),"pinball":statistics.mean(loss),"baseline_pinball":statistics.mean(base),"coverage":statistics.mean(covered),"covered":sum(covered),"n_cells":len(rows),"mean_width":statistics.mean(width),"cell_keys":[list(k) for k in sorted(keys)]}
    return {"schema_version":4,"status":"pending_missing_outcomes" if missing else "scored_locked_commitment","scores":scores or None,"missing_keys":[list(k) for k in sorted(set(missing))],"commitment_sha256":expected_sha,"truth_sha256":digest(truth),"limitations":["Pairwise scored cohorts can differ after declared issuance failures; compare only exact cell keys","Weekly dates and series remain dependent; no population calibration claim"],"issued_failures":record["failures"]}
