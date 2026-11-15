"""Point-in-time signal experiment. All future scores require actual retained truth."""
from __future__ import annotations
import hashlib,itertools,json,math,statistics
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from .review_v4 import digest,encoded
GROUPS=("news","infrastructure","bls")
FEATURES={"news":["official_announcement_count_7d","gpu_price_announcement_count_7d","newly_observed_evidence_age_days"],"infrastructure":["capacity_plan_count_30d","operational_capacity_confirmed_count_30d","hardware_announcement_count_30d"],"bls":["electricity_ppi_index","latest_available_month_change","days_since_new_period_first_seen"]}
def utc(value):
    t=datetime.fromisoformat(value.replace("Z","+00:00"))
    if t.tzinfo is None:raise ValueError("Timezone required")
    return t.astimezone(timezone.utc)
def allowed(day):return not "2026-11-07"<=day<="2026-11-13"
def config():return json.loads(Path("configs/prospective-signals-v6.json").read_bytes())
def retain(root,kind,record,key=None):
    root=Path(root)/kind;root.mkdir(parents=True,exist_ok=True);raw=encoded(record);identity=key or hashlib.sha256(raw).hexdigest();path=root/(identity+".json")
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError("Immutable record already exists")
    else:
        with path.open("xb") as out:out.write(raw)
    return {"path":str(path),"sha256":hashlib.sha256(raw).hexdigest(),"id":identity}
def contract(row):
    fields=("provider","gpu","vram_gb","kind","region","min_gpus","instance","cpu","vcpus","ram_gb","commitment","reservation_months","source_url")
    return {key:row.get(key) for key in fields}
def normalize_prices(payload,health,captured_at,frozen=None):
    p=config();at=utc(captured_at);day=payload.get("date")
    if not day or not allowed(day) or day!=at.date().isoformat():raise ValueError("Current-only quote snapshot required")
    if utc(payload["generated_at"])>at:raise ValueError("Future source snapshot")
    groups={};excluded=[];freshness=health.get("provider_freshness",{})
    for row in payload.get("offers",[]):
        if row.get("gpu") not in p["price_source"]["known_variants"] or row.get("kind")!="on-demand":continue
        c=contract(row);sid="grp-v6-"+digest(c)[:20];reason=None
        try:
            fetched=utc(row["fetched_at"])
            if fetched>at or fetched.date().isoformat()!=day:reason="provider_check_not_current"
            if freshness.get(row["provider"],{}).get("status")!="current":reason="collector_did_not_verify_provider"
            price=float(row["usd_hr"])
            if not math.isfinite(price) or price<=0:reason="invalid_price"
        except (KeyError,ValueError,TypeError):reason="invalid_provider_metadata"
        if reason:excluded.append({"series_id":sid,"reason":reason});continue
        groups.setdefault(sid,{"id":sid,"contract":c,"family":"H100" if row["gpu"].startswith("h100") else "A100","values":[],"fetched_at":[]})
        groups[sid]["values"].append(price);groups[sid]["fetched_at"].append(row["fetched_at"])
    if frozen is None:
        selected=[]
        for family in ("A100","H100"):
            candidates=sorted((v for v in groups.values() if v["family"]==family),key=lambda v:json.dumps(v["contract"],sort_keys=True))
            selected.extend(candidates[:2])
        cohort=[{k:v[k] for k in ("id","contract","family")} for v in selected]
    else:cohort=frozen
    rows=[]
    for target in cohort:
        found=groups.get(target["id"])
        if not found:excluded.append({"series_id":target["id"],"reason":"frozen_contract_missing_or_stale"});continue
        if found["contract"]!=target["contract"]:raise ValueError("Contract identity changed")
        rows.append({**target,"date":day,"value":statistics.median(found["values"]),"fetched_at":max(found["fetched_at"]),"n_offers":len(found["values"]),"unit":"USD per GPU-hour","availability":"Advertised; not independently verified rentable"})
    return {"date":day,"captured_at":captured_at,"source_generated_at":payload["generated_at"],"source_sha256":digest(payload),"health_sha256":digest(health),"cohort":cohort,"rows":rows,"exclusions":excluded,"license":p["price_source"]["license"],"attribution":p["price_source"]["credit"],"source_url":p["price_source"]["url"],"permission_url":p["price_source"]["permission_url"]}
def feature_vector(events,bls,at):
    bound=utc(at);valid=[e for e in events if utc(e["first_observed_at"])<=bound and e.get("published_at") and utc(e["published_at"])<=bound and e.get("publication_verified")]
    def count(kind,days):
        selected=[e for e in valid if bound-timedelta(days=days)<=utc(e["published_at"])<=bound and (kind is None or e["kind"]==kind)]
        return len({e["id"] for e in selected})
    news=[e for e in valid if bound-timedelta(days=7)<=utc(e["published_at"])<=bound]
    b=bls if bls and utc(bls["first_observed_at"])<=bound else None
    observations=b.get("observations",[]) if b else []
    latest=observations[0] if observations else None;previous=observations[1] if len(observations)>1 else None
    return {"official_announcement_count_7d":count(None,7),"gpu_price_announcement_count_7d":count("price_announcement",7),"newly_observed_evidence_age_days":min([(bound-utc(e["first_observed_at"])).total_seconds()/86400 for e in news],default=None),"capacity_plan_count_30d":count("capacity_plan",30),"operational_capacity_confirmed_count_30d":None,"hardware_announcement_count_30d":count("hardware_announcement",30),"electricity_ppi_index":latest["value"] if latest else None,"latest_available_month_change":(latest["value"]/previous["value"]-1) if previous and previous["value"] else None,"days_since_new_period_first_seen":(bound-utc(b["period_first_observed_at"])).total_seconds()/86400 if b else None}
def asof_snapshots(snapshots,cutoff):
    bound=utc(cutoff);by_day={}
    for s in sorted(snapshots,key=lambda s:s["captured_at"]):
        if utc(s["captured_at"])>bound:continue
        day=s["prices"]["date"]
        if not allowed(day):raise ValueError("Protected quote date")
        # First retained vintage per UTC observation date; never replace by revised history.
        by_day.setdefault(day,s)
    return [by_day[d] for d in sorted(by_day)]
def row_for(snapshot,sid):return next((r for r in snapshot["prices"]["rows"] if r["id"]==sid),None)
def price_features(values,day):
    current=values[day];out=[math.log(current)]
    for lag in (1,7,14):
        prior=values.get((date.fromisoformat(day)-timedelta(days=lag)).isoformat());out.append(math.log(current/prior) if prior else None)
    out.append(sum((date.fromisoformat(day)-timedelta(days=i)).isoformat() not in values for i in range(7)))
    out.append(date.fromisoformat(day).weekday()/6)
    return out
def masked_features(values,snapshot,sid,mask):
    if mask not in config()["learner"]["feature_masks"]:raise ValueError("Unregistered feature mask")
    day=snapshot["prices"]["date"];out=price_features(values,day)
    for enabled,group in zip(mask,GROUPS):
        if enabled=="1":out.extend(snapshot["features"].get(k) for k in FEATURES[group])
    return out
def predict_arm(snapshots,sid,cutoff,horizon,mask):
    import numpy as np
    from sklearn.linear_model import Ridge
    p=config();snaps=asof_snapshots(snapshots,cutoff);lookup={s["prices"]["date"]:s for s in snaps if row_for(s,sid)};values={d:row_for(s,sid)["value"] for d,s in lookup.items()}
    if len(values)<p["learner"]["min_price_observations"]:return None,{"reason":"insufficient_retained_price_days","observed":len(values),"required":p["learner"]["min_price_observations"]}
    latest=max(values);bound=utc(cutoff)
    if latest!=bound.date().isoformat():return None,{"reason":"missing_current_quote"}
    xs=[];ys=[];dates=[]
    for day,s in sorted(lookup.items()):
        if day<(bound.date()-timedelta(days=p["learner"]["window_days"])).isoformat():continue
        target=(date.fromisoformat(day)+timedelta(days=horizon)).isoformat()
        if target not in values or utc(target+"T23:59:59.999999+00:00")>=bound:continue
        xs.append(masked_features(values,s,sid,mask));ys.append(math.log(values[target]/values[day]));dates.append(day)
    if len(ys)<p["learner"]["min_matured_examples"]:return None,{"reason":"insufficient_matured_pairs","pairs":len(ys),"required":p["learner"]["min_matured_examples"]}
    X=np.array([[np.nan if v is None else v for v in r] for r in xs],dtype=float);Y=np.array(ys)
    fit=X[:-8];cal=X[-8:];yf=Y[:-8];yc=Y[-8:]
    med=np.array([float(np.median(col[np.isfinite(col)])) if np.isfinite(col).any() else 0 for col in fit.T])
    def transform(a):
        missing=~np.isfinite(a);return np.concatenate([np.where(missing,med,a),missing.astype(float)],axis=1)
    train=transform(fit);mu=train.mean(axis=0);scale=train.std(axis=0);scale[scale==0]=1
    model=Ridge(alpha=p["learner"]["alpha"]).fit((train-mu)/scale,yf)
    residual=yc-model.predict((transform(cal)-mu)/scale)
    x=np.array([[np.nan if v is None else v for v in masked_features(values,lookup[latest],sid,mask)]])
    center=float(model.predict((transform(x)-mu)/scale)[0]);qs=values[latest]*np.exp(center+np.quantile(residual,[.1,.5,.9]))
    if not np.isfinite(qs).all() or np.any(qs<=0) or not np.all(qs[:-1]<=qs[1:]):raise ValueError("Invalid positive quantiles")
    return list(map(float,qs)),{"fit_pairs":len(yf),"calibration_pairs":8,"last_fit_origin":dates[-9],"last_calibration_origin":dates[-1],"model":"Ridge(alpha=10), chronological held-out residuals","weights_sha256":digest({"coef":model.coef_.tolist(),"intercept":float(model.intercept_),"median":med.tolist(),"mean":mu.tolist(),"scale":scale.tolist()})}
def issue(snapshots,origin,issued_at,reference_rows,pilot=False):
    p=config();at=utc(issued_at);day=at.date().isoformat()
    if pilot:
        if origin!=day:raise ValueError("Pilot cannot be backdated")
        cutoff=max(s["captured_at"] for s in snapshots if utc(s["captured_at"])<=at)
    else:
        if origin not in p["origins"]:raise ValueError("Unregistered origin")
        cutoff=origin+"T"+p["origin_cutoff_utc"]+"+00:00"
        if not utc(cutoff)<=at<=utc(origin+"T"+p["issuance_end_utc"]+"+00:00"):raise ValueError("Outside issuance window")
    eligible=asof_snapshots(snapshots,cutoff);current=eligible[-1] if eligible else None
    record={"schema_version":6,"study_id":p["study_id"],"origin_date":origin,"information_cutoff":cutoff,"issued_at":issued_at,"registration_sha256":digest(p),"source_sha":__import__("os").environ.get("GITHUB_SHA"),"kind":"cold_start_reference_pilot" if pilot else "primary_factorial","input_snapshot_hashes":[digest(s) for s in eligible],"rows":[],"failures":[],"new_optimizer_updates":0,"outcome_status":"pending","provider_cost_usd":None}
    if not current or current["prices"]["date"]!=origin:record["status"]="pending_no_current_snapshot";return record
    for r in reference_rows:
        qs=[r[k] for k in ("q10","q50","q90")]
        if r["origin_date"]!=origin or qs!=sorted(qs) or any(not math.isfinite(v) or v<=0 for v in qs):raise ValueError("Reference mismatch")
        if r["target_date"]!=(date.fromisoformat(origin)+timedelta(days=r["horizon_days"])).isoformat():raise ValueError("Reference target mismatch")
        record["rows"].append({**r,"cohort":"reference_pilot" if pilot else "direct_reference"})
    if not pilot:
        for target in current["prices"]["cohort"]:
            sid=target["id"]
            for h in p["horizons"]:
                for mask in p["learner"]["feature_masks"]:
                    qs,metadata=predict_arm(eligible,sid,cutoff,h,mask)
                    if qs is None:record["failures"].append({"series_id":sid,"horizon_days":h,"mask":mask,**metadata});continue
                    record["rows"].append({"series_id":sid,"family":target["family"],"origin_date":origin,"target_date":(date.fromisoformat(origin)+timedelta(days=h)).isoformat(),"horizon_days":h,"forecaster":"signals_"+mask,"mask":mask,"cohort":"primary","q10":qs[0],"q50":qs[1],"q90":qs[2],"fit":metadata})
    keys=[(r["series_id"],r["horizon_days"],r["forecaster"]) for r in record["rows"]]
    if len(keys)!=len(set(keys)):raise ValueError("Duplicate forecast cells")
    record["status"]="issued_reference_pilot" if pilot and record["rows"] else "issued_primary" if any(r.get("cohort")=="primary" for r in record["rows"]) else "pending_primary_readiness"
    return record
def pinball(y,row):return sum(max(q*(y-row[k]),(q-1)*(y-row[k])) for q,k in ((.1,"q10"),(.5,"q50"),(.9,"q90")))/3
def evaluate(record,snapshots,now,expected_hash=None):
    p=config();at=utc(now)
    if expected_hash and digest(record)!=expected_hash:raise ValueError("Commitment changed")
    if record["registration_sha256"]!=digest(p):raise ValueError("Protocol changed")
    if utc(record["issued_at"])>at:raise ValueError("Future issuance")
    scores=[];missing=[]
    if any(s.get("protocol_sha256")!=record["registration_sha256"] for s in snapshots):raise ValueError("Incompatible truth protocol")
    for r in record["rows"]:
        target=r["target_date"];maturity=utc(target+"T23:59:59.999999+00:00")
        if at<=maturity:missing.append({"series_id":r["series_id"],"target_date":target,"reason":"outcome_not_mature"});continue
        matches=[s for s in snapshots if s["prices"]["date"]==target and utc(s["captured_at"])<=at and row_for(s,r["series_id"]) and utc(row_for(s,r["series_id"])["fetched_at"]).date().isoformat()==target]
        if not matches:missing.append({"series_id":r["series_id"],"target_date":target,"reason":"compatible_truth_missing"});continue
        truth=min(matches,key=lambda s:s["captured_at"]);y=row_for(truth,r["series_id"])["value"]
        scores.append({**{k:r[k] for k in ("series_id","family","forecaster","horizon_days","target_date","cohort")},"pinball":pinball(y,r),"covered":r["q10"]<=y<=r["q90"],"width":r["q90"]-r["q10"],"truth":y,"truth_snapshot_sha256":digest(truth),"n":1})
    return {"schema_version":6,"commitment_sha256":digest(record),"origin_date":record["origin_date"],"evaluated_at":now,"status":"completed" if scores and not missing else "pending" if not scores else "partially_mature","cells":scores,"missing":missing,"primary_accuracy_claim":None,"classification":record["kind"]}
def paired(cells,candidate,reference,horizon=7):
    a={(c["series_id"],c["target_date"],c["horizon_days"]):c for c in cells if c["forecaster"]==candidate and c["horizon_days"]==horizon and c["cohort"]=="primary"}
    b={(c["series_id"],c["target_date"],c["horizon_days"]):c for c in cells if c["forecaster"]==reference and c["horizon_days"]==horizon}
    keys=sorted(set(a)&set(b));loss=sum(a[k]["pinball"] for k in keys)/len(keys) if keys else None;base=sum(b[k]["pinball"] for k in keys)/len(keys) if keys else None
    return {"candidate":candidate,"reference":reference,"cells":len(keys),"candidate_pinball":loss,"reference_pinball":base,"difference":loss-base if keys else None,"skill":1-loss/base if keys and base else None,"coverage_numerator":sum(a[k]["covered"] for k in keys),"coverage_denominator":len(keys),"mean_interval_width":sum(a[k]["width"] for k in keys)/len(keys) if keys else None}
def readiness(snapshots):
    if not snapshots:return {"status":"gated","reason":"no_snapshots","new_optimizer_updates":0}
    latest=max(snapshots,key=lambda s:s["captured_at"]);days=len({s["prices"]["date"] for s in snapshots});periods={s["bls"]["latest_period"] for s in snapshots if s.get("bls")}
    events={e["id"]:e for s in snapshots for e in s.get("events",[]) if e.get("publication_verified")}
    return {"status":"gated" if days<56 else "awaiting_matured_pair_and_variation_checks","retained_price_days":days,"required_price_days":56,"minimum_matured_pairs":32,"bls_periods_first_observed":len(periods),"bls_periods_for_group_attribution":3,"verified_news_events":len(events),"human_checked_extraction_labels":0,"weight_training":"gated; no independent new task evidence or checked extraction labels","new_optimizer_updates":0,"reason":"Prospective collection began now; historical source vintages must not be invented"}
