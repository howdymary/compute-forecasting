"""Bounded price-dynamics methods. Inputs must already be origin-safe.
No candidate changes the official starter drift or frozen selector pool.
"""
from __future__ import annotations
from datetime import date,timedelta,datetime,timezone
import hashlib,json,math,random,statistics
Q=(.1,.5,.9)
def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
def quantile(xs,q):
    xs=sorted(map(float,xs))
    if not xs or any(not math.isfinite(v) for v in xs):raise ValueError("Invalid samples")
    p=(len(xs)-1)*q;a=int(p);b=min(a+1,len(xs)-1)
    return xs[a]+(xs[b]-xs[a])*(p-a)
def ordered(qs):
    if len(qs)!=3 or any(not math.isfinite(x) or x<=0 for x in qs) or qs!=sorted(qs):
        raise ValueError("Invalid quantiles")
    return qs
def history(values,origin):
    values={str(k):float(v) for k,v in values.items()}
    if any(k>origin or not math.isfinite(v) or v<=0 for k,v in values.items()):
        raise ValueError("Future or invalid price input")
    return values
def state(values,at):
    ds=sorted(d for d in values if d<=at)
    if not ds:raise ValueError("No anchor")
    tail=ds[-30:];level=values[ds[-1]];prev=values[ds[-2]] if len(ds)>1 else level
    return ((level>prev)-(level<prev),(level>statistics.median(values[d] for d in tail))-(level<statistics.median(values[d] for d in tail)))
def increments(values,origin,h,window=120):
    values=history(values,origin);out=[]
    lo=date.fromisoformat(origin)-timedelta(days=window)
    for d in sorted(values):
        start=date.fromisoformat(d);end=(start+timedelta(days=h)).isoformat()
        if start>=lo and end<=origin and end in values:
            out.append((math.log(values[end]/values[d]),state(values,d),end))
    return out
def compatible(meta):
    # No dollar levels pooled. Exact configurations remain separate series.
    return tuple(meta.get(k) for k in ("source_id","instrument_class","pricing_tier","family","unit"))
def weighted_quantile(xs,ws,q):
    pairs=sorted(zip(xs,ws));threshold=q*sum(ws);total=0.
    for v,w in pairs:
        total+=w
        if total>=threshold:return v
    return pairs[-1][0]
def pooled(values,meta,panels,origin,h,fallback,window=120,strength=40,minimum=12):
    values=history(values,origin)
    if origin not in values:return ordered(list(fallback)),{"fallback":"missing_exact_anchor"}
    own=increments(values,origin,h,window);current=state(values,origin)
    cond=[r for r in own if r[1]==current]
    active=cond if len(cond)>=minimum else own
    donors=[]
    for sid,p in sorted(panels.items()):
        if sid==meta["series_id"] or compatible(p["meta"])!=compatible(meta):continue
        rows=increments(p["values"],origin,h,window)
        matched=[r for r in rows if r[1]==current]
        rows=matched if len(matched)>=minimum else rows
        if len(rows)>=minimum:donors.append(rows)
    if len(active)<minimum and not donors:return ordered(list(fallback)),{"fallback":"insufficient_own_and_compatible_changes"}
    weight=len(active)/(len(active)+strength) if active else 0.
    if not donors:weight=1.
    xs=[];ws=[]
    if active:
        xs.extend(r[0] for r in active);ws.extend([weight/len(active)]*len(active))
    for rows in donors:
        xs.extend(r[0] for r in rows);ws.extend([(1-weight)/len(donors)/len(rows)]*len(rows))
    if not xs or sum(ws)<=0:return ordered(list(fallback)),{"fallback":"empty_distribution"}
    qs=[values[origin]*math.exp(weighted_quantile(xs,ws,q)) for q in Q]
    return ordered(qs),{"fallback":None,"own_changes":len(own),"conditioned_changes":len(cond),"state_used":len(cond)>=minimum,"donor_series":len(donors),"own_weight":weight,"samples_are_dependent":True}
def replay(days,origin,h,fallback,coverage=None,minimum=12,window=120,seed=20261116):
    """Replay only transitions with observed endpoints and identifiable current offers.
    Membership churn requires an explicit complete-collection attestation at both endpoints.
    Otherwise membership changes are rejected, never interpreted as market exits.
    """
    if any(d>origin for d in days):raise ValueError("Future offers")
    coverage=coverage or {};today=days.get(origin,{})
    known={}
    for d,quotes in sorted(days.items()):
        if d<=origin:known.update(quotes)
    diag={"fallback":None,"scenarios":0,"rejected_membership_uncertain":0,"rejected_missing_current_identity":0,"composition_scenarios":0}
    if not today:return ordered(list(fallback)),{**diag,"fallback":"no_observed_current_offers"}
    simulations=[];changes=[]
    lo=(date.fromisoformat(origin)-timedelta(days=window)).isoformat()
    for start,before in sorted(days.items()):
        end=(date.fromisoformat(start)+timedelta(days=h)).isoformat()
        if start<lo or end>origin or end not in days:continue
        after=days[end]
        if not set(today)<=set(before):
            diag["rejected_missing_current_identity"]+=1;continue
        churn=set(before)!=set(after)
        complete=coverage.get(start) is True and coverage.get(end) is True
        if churn and not complete:
            diag["rejected_membership_uncertain"]+=1;continue
        scenario={}
        for key,p in today.items():
            if key in after:scenario[key]=p*after[key]/before[key]
            elif complete:pass
            else:raise AssertionError("Unverified market exit")
        if complete:
            for key in set(after)-set(before):
                # An entrant's historical level is not a current quote: use only a
                # current observed anchor for that identity. Unknown entrants are gated.
                if key not in known:continue
                scenario[key]=known[key]  # internal historical state, not a fabricated observed quote
        if not scenario:continue
        simulations.append(statistics.median(scenario.values()))
        changes.append({"from":start,"to":end,"repriced":sum(before[k]!=after[k] for k in set(before)&set(after)),"observed_added":len(set(after)-set(before)),"observed_removed":len(set(before)-set(after)),"complete_collection_attested":complete})
        if churn:diag["composition_scenarios"]+=1
    # Finite deterministic empirical replay; a seed determines retained trace ordering,
    # not extra invented samples or an artificial increase in sample size.
    random.Random(seed).shuffle(changes)
    diag.update(scenarios=len(simulations),trace=changes[:8])
    if len(simulations)<minimum:
        return ordered(list(fallback)),{**diag,"fallback":"insufficient_verified_replay_scenarios"}
    return ordered([quantile(simulations,q) for q in Q]),diag
def calibrate(base,past,origin,h,window=90,minimum=24):
    """Quantile-wise signed forecast-error correction, separately by horizon.
    Only stored forecasts and labels matured by origin enter each correction.
    No exchangeable-conformal coverage claim is made.
    """
    ordered(list(base));lo=(date.fromisoformat(origin)-timedelta(days=window)).isoformat()
    eligible=[]
    for r in past:
        if r["origin"]>=origin or r["target"]>origin:
            raise ValueError("Unmatured calibration label or later forecast")
        if r["horizon"]==h and lo<=r["target"]<=origin:eligible.append(r)
    if len(eligible)<minimum:return list(base),{"fallback":"insufficient_matured_forecast_errors","n":len(eligible),"crossing_corrected":False}
    correction=[quantile([r["truth"]-r["quantiles"][i] for r in eligible],q) for i,q in enumerate(Q)]
    raw=[base[i]+correction[i] for i in range(3)]
    repaired=sorted(max(1e-8,x) for x in raw)
    return ordered(repaired),{"fallback":None,"n":len(eligible),"correction":correction,"crossing_corrected":raw!=repaired,"last_label":max(r["target"] for r in eligible),"coverage_guarantee":False}
def loss(qs,y):
    ordered(list(qs))
    return sum(max(q*(y-p),(q-1)*(y-p)) for q,p in zip(Q,qs))/3
def summarize(cells,method,horizon=None):
    rows=[r for r in cells if r["method"]==method and (horizon is None or r["horizon"]==horizon)]
    if not rows:return {"method":method,"horizon":horizon,"n":0,"loss":None}
    return {"method":method,"horizon":horizon,"n":len(rows),"origins":len({r["origin"] for r in rows}),"series":len({r["series_id"] for r in rows}),"loss":statistics.mean(r["loss"] for r in rows),"coverage":statistics.mean(r["quantiles"][0]<=r["truth"]<=r["quantiles"][2] for r in rows),"width":statistics.mean(r["quantiles"][2]-r["quantiles"][0] for r in rows),"fallbacks":sum(bool(r["diagnostic"].get("fallback")) for r in rows)}
def paired(cells,candidate,reference,h=7,draws=2000,seed=17):
    a={(r["series_id"],r["origin"],r["horizon"]):r for r in cells if r["method"]==candidate and r["horizon"]==h}
    b={(r["series_id"],r["origin"],r["horizon"]):r for r in cells if r["method"]==reference and r["horizon"]==h}
    if set(a)!=set(b):raise ValueError("Unmatched cohort")
    origins=sorted({k[1] for k in a})
    diffs=[statistics.mean(a[k]["loss"]-b[k]["loss"] for k in a if k[1]==o) for o in origins]
    if not diffs:return None
    # Four-origin moving-block bootstrap preserves local temporal dependence.
    blocks=[diffs[i:i+4] for i in range(len(diffs)) if diffs[i:i+4]]
    rng=random.Random(seed);means=[]
    for _ in range(draws):
        sample=[]
        while len(sample)<len(diffs):sample.extend(rng.choice(blocks))
        means.append(statistics.mean(sample[:len(diffs)]))
    reference_loss=statistics.mean(b[k]["loss"] for k in b)
    return {"candidate":candidate,"reference":reference,"horizon":h,"n":len(a),"temporal_origins":len(origins),"difference":statistics.mean(diffs),"block_bootstrap_95":[quantile(means,.025),quantile(means,.975)],"bootstrap_block_origins":4,"reference_loss":reference_loss,"skill":None if reference_loss==0 else 1-statistics.mean(a[k]["loss"] for k in a)/reference_loss,"interpretation":"Retrospective descriptive uncertainty; not an independent confirmatory test"}
def validate_commitment(commitment,now):
    now=now if isinstance(now,datetime) else datetime.fromisoformat(now)
    issued=datetime.fromisoformat(commitment["issued_at"])
    cutoff=datetime.fromisoformat(commitment["cutoff"])
    deadline=datetime.fromisoformat(commitment["deadline"])
    if not cutoff<=issued<=deadline or issued>now:raise ValueError("Issuance timestamp")
    if any(datetime.fromisoformat(p["resolution_at"])<=issued for p in commitment["forecasts"]):raise ValueError("Outcome already resolved")
    if not commitment.get("snapshot_sha256") or not commitment.get("configuration_sha256"):raise ValueError("Unbound commitment")
    for r in commitment["forecasts"]:ordered(r["quantiles"])
    return True
