"""Assemble the paired study from actual saved predictions, retaining every attempt."""
import argparse,hashlib,json,os,pathlib,statistics
from datetime import datetime,timezone
from compute_forecast.direct_forecast_v12 import digest,cell_loss,summarize,matched,price_quantiles
def load(p):return json.loads(p.read_text())
def verify_prediction(value):
    assert value["summary"]==summarize(value["cells"])
    flat=[]
    for task in value["tasks"]:
        assert task["sampling_seed"] is None
        flat.extend(task["cells"])
        for row in task["cells"]:
            assert abs(row["loss"]-cell_loss(row["outcome"],[row["q10"],row["q50"],row["q90"]]))<1e-12
    assert flat==value["cells"]
def build(inputs,output):
    root=pathlib.Path(inputs);out=pathlib.Path(output);out.mkdir(parents=True,exist_ok=True)
    p=load(pathlib.Path("configs/direct-evidence-v14-final.json"))
    dataset=next(load(f) for f in root.rglob("dataset.json") if load(f).get("study_id")==p["study_id"])
    audit=next(load(f) for f in root.rglob("audit.json") if load(f).get("study_id")==p["study_id"])
    assert digest(dataset)==audit["dataset_sha256"] and dataset["protocol_sha256"]==digest(p)
    states=[];files={};development={};results={}
    for arm in p["arms"]:
        for seed in p["model"]["seeds"]:
            candidates=[f for f in root.rglob("result.json") if load(f).get("study_id")==p["study_id"] and load(f).get("arm")==arm and load(f).get("seed")==seed]
            if not candidates:continue
            assert len(candidates)==1,"Duplicate completed arm/seed"
            path=candidates[0];state=load(path);directory=path.parent
            assert state["protocol_sha256"]==digest(p) and state["dataset_sha256"]==digest(dataset)
            chosen=min(state["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
            assert chosen==state["selected"]
            for cp in state["checkpoints"]:
                dev=load(directory/("development-"+str(cp["update"])+".json"));verify_prediction(dev)
                assert dev["summary"]==cp["development"]
                development[(arm,seed,cp["update"])]=dev
            selected=load(directory/"evaluation-selected.json");base=load(directory/"evaluation-base.json")
            for value in (selected,base):verify_prediction(value)
            assert selected["summary"]==state["retrospective"] and base["summary"]==state["base"]
            anchors={t["task_id"]:t["anchor"] for phase in ("development","retrospective") for t in dataset["groups"][phase]}
            for value in [selected,base]+[development[(arm,seed,c["update"])] for c in state["checkpoints"]]:
                for task in value["tasks"]:
                    expected=price_quantiles(task["sample_returns"],anchors[task["task_id"]]) if not task["fallback"] else [[anchors[task["task_id"]]]*3 for _ in (1,3,7)]
                    assert expected==[[r[k] for k in ("q10","q50","q90")] for r in task["cells"]]
            assert matched(selected["cells"],base["cells"])==state["comparison_to_base"]
            states.append(state);results[(arm,seed)]=selected
            for f in directory.glob("*.json"):
                raw=f.read_text();assert "tinker://" not in raw
                files[arm+"/seed-"+str(seed)+"/"+f.name]=raw
    cases=[]
    for t in sorted(dataset["groups"]["development"],key=lambda t:(t["series_id"],t["origin"])):
        forecasts=[]
        for (arm,seed,update),value in sorted(development.items()):
            found=next(r for r in value["tasks"] if r["task_id"]==t["task_id"])
            forecasts.append({"arm":arm,"seed":seed,"update":update,"cells":found["cells"],"distinct_vectors":found["distinct_vectors"],"valid_samples":found["valid_samples"],"fallback":found["fallback"],"source_artifact":arm+"/seed-"+str(seed)+"/development-"+str(update)+".json"})
        cases.append({"task_id":t["task_id"],"series_id":t["series_id"],"origin":t["origin"],"metadata":t["metadata"],"history":t["context"],"history_sha256":digest(t["context"]),"anchor":t["anchor"],"bls":t["bls"],"target_dates":t["target_dates"],"outcomes":t["outcomes"],"forecasts":forecasts,"classification":"Development case; first case selected lexicographically, not by performance"})
    incomplete=[]
    for arm in p["arms"]:
        for seed in p["model"]["seeds"]:
            if any(r["arm"]==arm and r["seed"]==seed for r in states):continue
            found=[f for f in root.rglob("progress.json") if load(f).get("study_id")==p["study_id"] and load(f).get("arm")==arm and load(f).get("seed")==seed]
            progress=load(found[0]) if found else None
            incomplete.append({"arm":arm,"seed":seed,"optimizer_updates":progress.get("optimizer_updates") if progress else None,"checkpoints":progress.get("checkpoints",[]) if progress else [],"status":"retained_partial_attempt" if progress else "no_retained_attempt_yet"})
            if found:
                for f in found[0].parent.glob("*.json"):
                    raw=f.read_text();assert "tinker://" not in raw
                    files[arm+"/seed-"+str(seed)+"/"+f.name]=raw
    execution=load(root/"workflow.json") if (root/"workflow.json").exists() else None
    comparisons=[]
    for seed in p["model"]["seeds"]:
        if all((arm,seed) in results for arm in p["arms"]):
            a=results[("price_evidence",seed)];b=results[("price_only",seed)]
            primary=matched([r for r in a["cells"] if r["horizon_days"]==7],[r for r in b["cells"] if r["horizon_days"]==7])
            comparisons.append({"seed":seed,"candidate":"price_evidence","reference":"price_only","all_horizons":matched(a["cells"],b["cells"]),"seven_day":primary})
    status="completed" if len(states)==6 else "partial" if states else "awaiting_training"
    memory_files=sorted(pathlib.Path("results/evidence-v14/audits").glob("*/memory.json"),key=lambda f:int(f.parent.name))
    memory=None
    if memory_files:
        f=memory_files[-1];value=load(f)
        memory={"path":str(f),"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"status":value["status"],"eligibility":value["eligibility"],"changed_after_criticism":value["changed_after_criticism"],"decisions":value["decisions"],"actual_diagnostics":value["actual_diagnostics"]}
    report={"study_id":p["study_id"],"schema_version":14,"status":status,"created_at":datetime.now(timezone.utc).isoformat(),"protocol":p,"protocol_sha256":digest(p),"dataset_sha256":digest(dataset),"audit":audit,"runs":states,"development_cases":cases,"comparisons":comparisons,"expected_runs":6,"incomplete_runs":incomplete,"execution":execution,"memory":memory,"task_anchors":{t["task_id"]:t["anchor"] for phase in ("development","retrospective") for t in dataset["groups"][phase]},"news_used":False,"infrastructure_used":False,"source_attribution":"Pacific Machines(2026), gpu-price-pack v0.1.1-handover, approved CC BY4.0 source derivatives; US Bureau of Labor Statistics, original archived monthly PPI releases","interpretation":"Price versus price+BLS; retrospective. Three dependent evaluation dates and seed replicates do not establish prospective accuracy or a news benefit.","prospective":{"status":"pending","outcomes_loaded":False,"protocol":"configs/evidence-v14-prospective.json"}}
    for name,raw in files.items():
        f=out/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(raw)
    for name,value in (("report.json",report),("audit.json",audit),("bls-vintages.json",load(next(root.rglob("bls-vintages.json"))))):
        (out/name).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    lines=["# Price history versus price plus BLS","",f"Study status: {status}. {len(states)}/6 matched training runs published.","","The model directly predicts1/3/7-day price changes. Supplementary inputs are original archived electricity-distribution PPI features. News and infrastructure features are not in this comparison.","","| Arm | Seed | Updates | Selected | Base7-day loss | Selected7-day loss | Coverage | Width |","| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for s in states:
        h=s["retrospective"]["by_horizon"]["7"];lines.append(f"| {p['arm_labels'][s['arm']]} | {s['seed']} | {s['optimizer_updates']} | {s['selected']['update']} | {s['base']['primary_pinball']:.8f} | {s['retrospective']['primary_pinball']:.8f} | {h['coverage']:.1%} | {h['width']:.6f} |")
    lines+=["",f"{audit['phase_tasks']['training']} overlapping training tasks;{audit['phase_tasks']['development']} development tasks;{audit['phase_tasks']['retrospective']} retrospective tasks,66 horizon cells and3 reused dependent origins. Seed runs replicate the same market outcomes.","","Checkpoint selection uses development only. All stochastic samples and failed outputs remain retained. A positive BLS effect is not assumed.","","Prospective improvement from supplementary evidence is not established.","","[Methods](evidence-v14.md) · [Protocol](../configs/direct-evidence-v14-final.json) · [Artifacts](../results/evidence-v14/README.md)"]
    (out/"findings.md").write_text("\n".join(lines)+"\n")
    manifest={"study_id":p["study_id"],"files":[{"path":str(f.relative_to(out)),"bytes":f.stat().st_size,"sha256":hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(out.rglob("*")) if f.is_file() and f.name!="manifest.json"]}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"status":status,"runs":len(states),"paired_seeds":len(comparisons),"dataset_sha256":digest(dataset)}),flush=True)
if __name__=="__main__":
    q=argparse.ArgumentParser();q.add_argument("--inputs",required=True);q.add_argument("--output",required=True);a=q.parse_args();build(a.inputs,a.output)
