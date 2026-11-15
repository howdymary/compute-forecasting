"""Descriptive aggregation of all frozen representation results; never selects a forecast."""
import argparse,json,math,os,re
from pathlib import Path
from .release_payload import read_one,PACK_SHA

def summarize(root):
    final=read_one(root,"final-report.json");grid=read_one(root,"final-numerical-grid.json")
    selected=[r for r in grid["origins"] if r["origin"] in final["final_origins"]]
    if len(selected)!=5 or {r["origin"] for r in selected}!=set(final["final_origins"]):raise ValueError("Missing frozen date")
    if any(r["status"]!="completed" or r["dataset_sha256"]!=PACK_SHA or not r["final_period_opened"] for r in selected):raise ValueError("Unverified numerical source")
    ids={m["config_id"] for m in selected[0]["results"]};methods=[]
    if len(ids)!=28 or any({m["config_id"] for m in r["results"]}!=ids for r in selected):raise ValueError("Incomplete candidate grid")
    for config in sorted(ids):
        rows=[next(m for m in r["results"] if m["config_id"]==config) for r in selected]
        cells=sum(r["exact_metrics"]["n_cells"] for r in rows)
        loss=sum(r["exact_metrics"]["pinball"]*r["exact_metrics"]["n_cells"] for r in rows)/cells
        horizons={}
        for horizon in ("1","3","7"):
            values=[r["by_horizon"][horizon] for r in rows]
            n=sum(v["n_cells"] for v in values)
            horizons[horizon]={"n_cells":n,"pinball":sum(v["pinball"]*v["n_cells"] for v in values)/n}
        row={"config_id":config,"pooled_pinball":loss,"n_cells":cells,"by_horizon":horizons}
        if config.startswith("ridge_"):
            match=re.fullmatch(r"ridge_(level|log)_(target_only|raw|fixed_basket)_(28|56)_(1|100)",config)
            if not match:raise ValueError("Unrecognized registered configuration")
            row["factors"]=dict(zip(("target_transform","features","window_days","alpha"),match.groups()))
        else:
            if not math.isclose(loss,final["forecaster_references"][config],abs_tol=1e-12):raise ValueError("Official reference aggregation mismatch")
        methods.append(row)
    marginal=[]
    for factor in ("target_transform","features","window_days","alpha"):
        candidates=[r for r in methods if "factors" in r]
        for value in sorted({r["factors"][factor] for r in candidates}):
            group=[r for r in candidates if r["factors"][factor]==value]
            marginal.append({"factor":factor,"value":value,"configurations":len(group),"mean_configuration_pinball":sum(r["pooled_pinball"] for r in group)/len(group)})
    return {"analysis_kind":"descriptive_aggregation_after_final_opening","forecast_selection_changed":False,"dataset_sha256":PACK_SHA,"final_origins":final["final_origins"],"temporal_origins":5,"observed_gpu_models":sorted({s["gpu_model"] for run in selected for s in run["primary_catalog"]}),"source_evaluation_sha":final["code_sha"],"source_run":"https://github.com/howdymary/compute-forecasting/actions/runs/43653016797","methods":sorted(methods,key=lambda r:r["pooled_pinball"]),"factor_marginals":marginal,"interpretation":"All registered configurations retained. Factor marginals average configuration losses; they are not ensemble predictions or independent observations. No candidate is selected for a revised submission from these final scores.","limitations":["Five dependent origins; narrow eligible target subset","Retrospective data vintage","No multiplicity-adjusted significance claim","Descriptive analysis does not establish causal effects of provider composition"]}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--inputs",default="inputs/final");a=p.parse_args();r=summarize(a.inputs)
    out=Path("artifacts");out.mkdir(exist_ok=True);(out/"representation-findings.json").write_text(json.dumps(r,indent=2)+"\n")
    text="# Frozen representation findings\n\nDescriptive aggregation of every registered configuration, after final opening. No forecast or checkpoint is changed. Five dependent dates; 30 scored cells per configuration.\n\n| Configuration | Pooled pinball |\n| --- | ---: |\n"+"\n".join("| "+m["config_id"]+" | "+format(m["pooled_pinball"],".8f")+" |" for m in r["methods"])+"\n\n## Descriptive factor marginals\n\n| Factor | Value | Configurations | Mean configuration pinball |\n| --- | --- | ---: | ---: |\n"+"\n".join("| "+m["factor"]+" | "+m["value"]+" | "+str(m["configurations"])+" | "+format(m["mean_configuration_pinball"],".8f")+" |" for m in r["factor_marginals"])+"\n\n"+r["interpretation"]+"\n"
    text+="\nObserved final GPU models: "+", ".join(r["observed_gpu_models"])+".\n"
    (out/"representation-findings.md").write_text(text)
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:f.write(text)
