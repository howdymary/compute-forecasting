"""Descriptive diagnostics from already public, frozen experimental results.

No model calls, new experiment selection, interval recalibration or raw-data access.
"""
from __future__ import annotations
import math
from datetime import datetime,timezone

CONDITIONS={"no_observation":"selected_no_observation","with_criticism":"selected_with_criticism","with_evidence":"selected_with_method_evidence"}
def metric(report,label):
    return next((m for m in report.get("comparisons",[]) if m.get("policy")==label),None)
def interval_summary(m):
    if not m:return None
    n=m.get("n_cells");coverage=m.get("coverage");width=m.get("mean_width")
    if not isinstance(n,int) or n<=0:raise ValueError("Positive scored-cell count required")
    for value in (coverage,width,m.get("pinball")):
        if value is not None and not math.isfinite(value):raise ValueError("Nonfinite diagnostic")
    if coverage is not None and not 0<=coverage<=1:raise ValueError("Invalid coverage")
    if width is not None and width<0:raise ValueError("Invalid width")
    covered=None if coverage is None else round(coverage*n)
    if covered is not None and not math.isclose(covered,coverage*n,abs_tol=1e-8):raise ValueError("Coverage disagrees with cell count")
    return {"pinball":m.get("pinball"),"coverage":coverage,"covered_cells":covered,"n_cells":n,"mean_width":width,"nominal_coverage":.8,"coverage_gap":None if coverage is None else coverage-.8}
def build(data):
    reports=data.get("policy_reports",[])
    if len({p["run_id"] for p in reports})!=len(reports):raise ValueError("Duplicate report identity")
    analysis={p["run_id"]:p for p in data.get("analysis",{}).get("policies",[])}
    calibration=[];feedback=[]
    for p in sorted(reports,key=lambda p:(p["mode"],p["seed"],p["objective"])):
        selected=metric(p,"selected_"+p["mode"]+"_"+p["objective"])
        if not selected:continue
        identity={k:p[k] for k in ("run_id","mode","seed","objective","selected_update","actual_optimizer_updates")}
        ref_label="sft_parent" if p["mode"]=="rl" else "starting_policy"
        calibration.append({**identity,"selected":interval_summary(selected),"reference_policy":ref_label,"reference":interval_summary(metric(p,ref_label)),"by_horizon":{str(h):interval_summary(m) for h,m in selected.get("by_horizon",{}).items()},"by_series":{str(s):interval_summary(m) for s,m in selected.get("by_series",{}).items()}})
        traces={r["condition"]:r for r in analysis.get(p["run_id"],{}).get("ablations",[])}
        for condition,label in CONDITIONS.items():
            variant=metric(p,label)
            if not variant:continue
            trace=traces.get(condition)
            feedback.append({**identity,"condition":condition,"primary_pinball":selected["pinball"],"variant_pinball":variant["pinball"],"variant_minus_primary":variant["pinball"]-selected["pinball"],"same_forecast_loss":math.isclose(variant["pinball"],selected["pinball"],abs_tol=1e-12,rel_tol=0),"matched_tasks":trace.get("tasks") if trace else None,"changed_action_sequences":trace.get("tasks_with_changed_action_sequence") if trace else None,"changed_final_choices":trace.get("tasks_with_changed_selected_forecaster") if trace else None,"trace_status":"measured" if trace else "pending matched trace analysis"})
    cycles=[c for c in data.get("autonomy_runs",[]) if c.get("status")=="completed"]
    protocol=data.get("protocol",{})
    result={"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),"kind":"descriptive_audit_of_saved_results","source":{"summary_sha":data.get("source_sha"),"summary_published_at":data.get("published_at"),"analysis_sha":data.get("analysis",{}).get("code_sha")},"scope":{"evaluation_dates":data.get("analysis",{}).get("evaluation_temporal_origins",protocol.get("evaluation_origins",[])),"series":"A100 40GB and A100 SXM 80GB only","independent_population_interval":False,"retrospective_reused_dates":True,"nominal_interval":"q10–q90; central 80% nominal coverage"},"calibration":calibration,"feedback":feedback,"ledger":{"registered_candidates":data.get("forecasting",{}).get("registry_count"),"common_starts_per_task":2,"additional_choices_per_task":4,"cached_result_reveals_per_task":6,"completed_sft_runs":sum(p["mode"]=="sft" for p in reports),"completed_rl_runs":sum(p["mode"]=="rl" for p in reports),"completed_sft_optimizer_updates":sum(p["actual_optimizer_updates"] for p in reports if p["mode"]=="sft"),"completed_rl_optimizer_updates":sum(p["actual_optimizer_updates"] for p in reports if p["mode"]=="rl"),"completed_operational_cycles":len(cycles),"operational_trials":sum(c.get("actual_trials",len(c.get("trials",[]))) for c in cycles),"fresh_operational_modal_calls":sum(c.get("new_executions",0) for c in cycles),"verified_cross_role_reads":sum(c.get("actual_cross_role_reads",0) for c in cycles),"budget_caveat":"Equal online cached result reveals do not mean equal wall time, spend, offline training or independent market evidence."},"limitations":["Coverage and mean width describe the same few dependent cells; no population calibration guarantee or binomial confidence interval is justified.","Feedback loss ties do not imply identical action sequences. Action counts require matched saved traces; pending counts remain null.","The deterministic final chooser still uses matured validation in feedback-hidden arms.","These audits do not tune models, select new winners, alter frozen forecasts or evaluate restricted future truth."]}
    return result
