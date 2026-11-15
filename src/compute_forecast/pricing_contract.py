"""Public pricing contract: exact frozen forecasts, catalog metadata and explicit scenarios."""
from __future__ import annotations
import csv,hashlib,io,json,math
from datetime import date,timedelta
PACK_SHA="f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c"
FORECAST_SHA="67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80"
SOURCES={"fastgpu_daily":"FastGPU","gpurentalprices":"GPU Rental Prices","afhubbard":"Hubbard"}
MARKETS={"hyperscaler_spot":"Hyperscaler spot","neocloud_rate_card":"Neocloud on demand","neocloud_spot":"Neocloud spot","marketplace_ask":"Marketplace asks"}
COMPARISON_FIELDS=("gpu_model","instrument_class","pricing_tier","statistic","instance_type","az_global_id","product_description")
def scenario_path(rate,months,start=100):
    if not all(math.isfinite(x) for x in (rate,months,start)) or not -1<rate<=1 or months not in (12,24,36) or start<=0:raise ValueError("Invalid scenario assumptions")
    return [{"month":m,"value":start*(1+rate)**(m/12)} for m in range(months+1)]
def build(metadata,csv_bytes,outlook,code_sha):
    if metadata["dataset_sha256"]!=PACK_SHA or metadata["history_publication_permitted"] is not False:raise ValueError("Unverified metadata or publication boundary")
    if hashlib.sha256(csv_bytes).hexdigest()!=FORECAST_SHA:raise ValueError("Frozen CSV hash mismatch")
    source_rows=list(csv.DictReader(io.StringIO(csv_bytes.decode())))
    if len(source_rows)!=111 or len(metadata["series"])!=37:raise ValueError("Incomplete headline coverage")
    grouped={}
    for r in source_rows:
        if r["origin_date"]!="2026-11-06" or int(r["horizon_days"]) not in (1,3,7):raise ValueError("Unsupported forecast date or horizon")
        qs=[float(r[k]) for k in ("q10","q50","q90")]
        if any(not math.isfinite(v) or v<=0 for v in qs) or qs!=sorted(qs):raise ValueError("Invalid quantiles")
        h=int(r["horizon_days"])
        point={"horizon_days":h,"date":(date(2026,11,6)+timedelta(days=h)).isoformat(),**dict(zip(("q10","q50","q90"),qs))}
        grouped.setdefault(r["series_id"],[]).append(point)
    series=[]
    for m in metadata["series"]:
        sid=m["series_id"];points=sorted(grouped.pop(sid,[]),key=lambda r:r["horizon_days"])
        if [r["horizon_days"] for r in points]!=[1,3,7]:raise ValueError("Missing or duplicate target forecast")
        if m["statistic"]!="median_usd_per_gpu_hour":raise ValueError("Unverified units: "+m["statistic"])
        key=json.dumps([m[k] for k in COMPARISON_FIELDS],separators=(",",":"))
        series.append({"id":sid,"label":m["gpu_model"]+" · "+MARKETS.get(m["instrument_class"],m["instrument_class"])+" · "+SOURCES.get(m["source_id"],m["source_id"]),"gpu_model":m["gpu_model"],"market":MARKETS.get(m["instrument_class"],m["instrument_class"]),"source":SOURCES.get(m["source_id"],m["source_id"]),"source_id":m["source_id"],"source_url":m["source_url"],"licence_id":m["licence_id"],"pricing_tier":m["pricing_tier"],"instrument_class":m["instrument_class"],"statistic":m["statistic"],"unit":"USD per GPU-hour","unit_code":"usd_per_gpu_hour","comparison_key":key,"forecasts":points})
    if grouped:raise ValueError("Forecast target absent from verified catalog")
    if outlook["kind"]!="assumption_driven_scenario_not_fitted_forecast" or outlook["reference_date"]!="2026-11-06" or outlook["reference_index"]!=100 or outlook["scenario_probabilities"] is not None or outlook["confidence_level"] is not None:raise ValueError("Unverified scenario contract")
    if len(outlook["assumptions"])!=3:raise ValueError("Expected three published assumption paths")
    for case in outlook["assumptions"]:
        for year in (2,3):
            expected=next(r for r in outlook["results"] if r["scenario"]==case["scenario"] and r["years"]==year)
            for instrument,rate in (("rental",case["rental_annual_change"]),("resale",-case["resale_annual_depreciation"])):
                value=scenario_path(rate,year*12)[-1]["value"]
                if not math.isclose(value,expected[instrument+"_index"],rel_tol=1e-12):raise ValueError("Published scenario endpoints disagree")
    result={"schema_version":1,"code_sha":code_sha,"dataset_sha256":PACK_SHA,"forecast_csv_sha256":FORECAST_SHA,"metadata_catalog_sha256":metadata["source_catalog_sha256"],"metadata_run_id":43657301892,"origin_date":"2026-11-06","origin_cutoff_utc":"2026-11-06T23:59:59+00:00","measurement":"advertised_rental_offer_rate","series":sorted(series,key=lambda r:(r["gpu_model"],r["market"],r["source"])),"history":{"status":"not_published","points":[],"reason":metadata["history_reason"]},"outlook":outlook,"comparison_note":"Aligned GPU, market, tier and statistic only. Each source may sample different providers; these are source-level median series, not matched individual offers.","method":"last_value_empirical","source_attribution":"Pacific Machines (2026), gpu-price-pack v0.1.1-handover; upstream source attribution retained."}
    return validate(result)
def validate(r):
    if set(r)!={"schema_version","code_sha","dataset_sha256","forecast_csv_sha256","metadata_catalog_sha256","metadata_run_id","origin_date","origin_cutoff_utc","measurement","series","history","outlook","comparison_note","method","source_attribution"}:raise ValueError("Unexpected pricing payload")
    if r["schema_version"]!=1 or r["dataset_sha256"]!=PACK_SHA or r["forecast_csv_sha256"]!=FORECAST_SHA or len(r["code_sha"])!=40:raise ValueError("Pricing identity mismatch")
    if r["history"]["points"] or r["history"]["status"]!="not_published":raise ValueError("Historical publication is not authorized")
    if len(r["series"])!=37 or len({s["id"] for s in r["series"]})!=37:raise ValueError("Incomplete series catalog")
    for s in r["series"]:
        if s["unit_code"]!="usd_per_gpu_hour" or [p["horizon_days"] for p in s["forecasts"]]!=[1,3,7]:raise ValueError("Unverified plotting units or horizons")
        for p in s["forecasts"]:
            values=[p[k] for k in ("q10","q50","q90")]
            if any(not math.isfinite(v) or v<=0 for v in values) or values!=sorted(values):raise ValueError("Invalid plotted quantiles")
    encoded=json.dumps(r,allow_nan=False)
    if len(encoded)>150000 or any(k in encoded for k in ("api_key","token_secret","Authorization","tinker://","rental_observations")):raise ValueError("Unexpected private or oversized pricing payload")
    return r
