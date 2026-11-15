"""Locked prospective evaluator. It never retrieves outcomes or runs before maturity."""
from __future__ import annotations
import hashlib,json,math
from datetime import datetime,timedelta,timezone
from pathlib import Path
NOT_BEFORE=datetime(2026,11,23,tzinfo=timezone.utc)
BASELINE_SHA="428296e044ca0a5c362ee5b96d9488c6fe47cd59be6a3d70000ac2c51cbf29d2"
CHRONOS_SHA="3b1dcd48ab1382cc7266d8e4eb61a7a47fbb6dfdebc28ff3decbc841db769c53"
def canonical(v):return json.dumps(v,sort_keys=True,allow_nan=False).encode()
def clock_gate(now):
    if now.tzinfo is None or now<NOT_BEFORE:raise ValueError("Future outcomes remain sealed until 2026-11-23T00:00:00Z")
def key(r):return r["series_id"],r["target_date"],int(r["horizon_days"])
def score_locked(baseline,chronos,truth,now):
    clock_gate(now)
    for value,sha in ((baseline,BASELINE_SHA),(chronos,CHRONOS_SHA)):
        if hashlib.sha256(canonical(value)).hexdigest()!=sha:raise ValueError("Committed forecast changed")
    left={key(r):r for r in baseline["rows"]};right={key(r):r for r in chronos["rows"]}
    if len(left)!=42 or len(right)!=42 or set(left)!=set(right):raise ValueError("Unmatched commitment cells")
    if baseline["data_cutoff"]!="2026-11-06" or chronos["data_cutoff"]!="2026-11-06":raise ValueError("Information cutoff changed")
    if truth.get("schema_version")!=1 or truth.get("identity_audit",{}).get("status")!="verified" or not truth.get("source_urls") or not truth.get("collection_vintage"):raise ValueError("A separately audited, sourced truth artifact is required")
    if truth.get("measurement")!="advertised_rental_offer_rate" or truth.get("unit")!="USD per GPU-hour" or truth.get("statistic")!="exact_registered_series_daily_median":raise ValueError("Incompatible target")
    actual={key(r):r for r in truth["rows"]}
    if len(actual)!=len(truth["rows"]):raise ValueError("Duplicate future observations")
    missing=set(left)-set(actual)
    if missing:return {"status":"pending_missing_outcomes","required_cells":42,"available_cells":42-len(missing),"missing_keys":[list(k) for k in sorted(missing)],"scores":None}
    values={}
    for label,rows in (("empirical_baseline",left),("chronos2",right)):
        losses=[];covered=[];width=[]
        for k in sorted(left):
            y=float(actual[k]["value"]);r=rows[k];qs=[float(r[q]) for q in ("q10","q50","q90")]
            if not math.isfinite(y) or any(not math.isfinite(q) for q in qs) or qs!=sorted(qs):raise ValueError("Invalid future scoring values")
            losses.append(sum(max(q*(y-p),(q-1)*(y-p)) for q,p in zip((.1,.5,.9),qs))/3)
            covered.append(qs[0]<=y<=qs[2]);width.append(qs[2]-qs[0])
        values[label]={"pinball":sum(losses)/42,"coverage":sum(covered)/42,"mean_width":sum(width)/42,"n_cells":42}
    return {"status":"scored_locked_commitments","scores":values,"scored_at":now.isoformat(),"baseline_commitment":BASELINE_SHA,"chronos_commitment":CHRONOS_SHA,"truth_sha256":hashlib.sha256(canonical(truth)).hexdigest(),"limitations":["Three dependent future dates; 42 cells are not independent cases","Both models use a stale November 6 snapshot","Truth identity and publication permission require separate review; no raw values are published"]}
def main():
    # Gate precedes argument parsing and every forecast/truth read.
    clock_gate(datetime.now(timezone.utc))
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--baseline",required=True);parser.add_argument("--chronos",required=True);parser.add_argument("--truth",required=True);parser.add_argument("--output",required=True)
    args=parser.parse_args()
    result=score_locked(*[json.loads(Path(p).read_text()) for p in (args.baseline,args.chronos,args.truth)],datetime.now(timezone.utc))
    Path(args.output).write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
if __name__=="__main__":main()
