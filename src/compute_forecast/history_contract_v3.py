"""Public contextual history and paired traces; never a benchmark input adapter."""
from __future__ import annotations
import hashlib,json,math
from datetime import date
HISTORY_RUN="d88016f5bd0e40169f22939c68b5ae12"
APPROVED={
"afhubbard.hyperscaler_spot.A100_40GB.spot.median":"A100 40GB",
"afhubbard.hyperscaler_spot.T4.spot.median":"T4",
}
LICENSE_SHA="5935a23bebd1f3add38258ebd4167ad55ca9a001bfb88e32396b36b77152f7cb"
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,allow_nan=False).encode()).hexdigest()
def validate_history(h):
    if h["kind"]!="independent_historical_context" or h["benchmark_overlay_allowed"] or h["benchmark_input_claim"]:raise ValueError("Context cannot become benchmark inputs")
    if h["source"]["license_sha256"]!=LICENSE_SHA or h["source"]["license"]!="CC BY 4.0":raise ValueError("Explicit upstream permission required")
    if h["source"]["private_pack_values_published"] or h["cutoff"]!="2026-11-06":raise ValueError("Publication boundary")
    if {s["benchmark_series_context"] for s in h["series"]}!=set(APPROVED):raise ValueError("Unapproved hardware mapping")
    for s in h["series"]:
        if s["unit"]!="USD per GPU-hour" or s["market"]!="hyperscaler spot advertised offers" or s["benchmark_overlay_allowed"]:raise ValueError("Incompatible contract")
        points=s["points"];dates=[p["date"] for p in points]
        if dates!=sorted(set(dates)) or any(d>"2026-11-06" for d in dates):raise ValueError("Duplicate or post-cutoff observations")
        if any(not isinstance(p["value"],(int,float)) or not math.isfinite(p["value"]) or p["value"]<=0 for p in points):raise ValueError("Invalid observations")
        if not points or digest(points)!=s["points_sha256"]:raise ValueError("Observation hash mismatch")
        span=(date.fromisoformat(dates[-1])-date.fromisoformat(dates[0])).days+1
        if s["observations"]!=len(points) or s["missing_calendar_days"]!=span-len(points):raise ValueError("Missingness disagreement")
    return h
def validate_assets(p):
    validate_history(p["history_context"])
    pairs=p["paired_traces"]["pairs"]
    if len(pairs)!=4 or len({p["task_id"] for p in pairs})!=4:raise ValueError("Paired task scope")
    for pair in pairs:
        for condition in ("feedback","hidden"):
            t=pair[condition]
            if len(t["revealed"])!=6 or len(set(t["revealed"]))!=6 or t["n_cells"]!=3:raise ValueError("Trace budget")
            if not math.isfinite(t["pinball"]):raise ValueError("Invalid trace score")
    text=json.dumps(p,allow_nan=False)
    if any(token in text for token in ("tinker://","TINKER_API_KEY","Authorization","permitted_private_method_context")):raise ValueError("Private content")
    return p
