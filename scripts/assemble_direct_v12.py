"""Reconstruct public direct-forecast results from retained permitted artifacts."""
from __future__ import annotations
import argparse,hashlib,json,os,pathlib,statistics,urllib.request
from datetime import datetime,timezone
from compute_forecast.direct_forecast_v12 import digest,cell_loss,summarize,matched
def load(path):return json.loads(path.read_text())
def assemble(inputs,output):
    root=pathlib.Path(inputs);out=pathlib.Path(output);out.mkdir(parents=True,exist_ok=True)
    p=load(pathlib.Path("configs/direct-forecast-v12.json"))
    audits=list(root.rglob("audit.json"));audit=next((load(f) for f in audits if load(f).get("protocol_sha256")==digest(p)),None)
    if not audit:raise ValueError("Matching permission-filtered audit unavailable")
    datasets=list(root.rglob("dataset.json"));dataset=next((load(f) for f in datasets if digest(load(f))==audit["dataset_sha256"]),None)
    if not dataset:raise ValueError("Input dataset hash mismatch")
    states=[];cases=[];files={}
    for seed in p["model"]["seeds"]:
        result_files=list(root.rglob("seed-"+str(seed)+"/result.json"))
        if not result_files:result_files=list(root.rglob("direct-v12-seed-"+str(seed)+"-*/result.json"))
        if not result_files:result_files=[f for f in root.rglob("result.json") if load(f).get("study_id")==p["study_id"] and load(f).get("seed")==seed]
        if not result_files:continue
        f=result_files[0];state=load(f)
        if state["protocol_sha256"]!=digest(p) or state["dataset_sha256"]!=digest(dataset):raise ValueError("Run input mismatch")
        directory=f.parent;selected=load(directory/"evaluation-selected.json");base=load(directory/"evaluation-base.json")
        for report in (selected,base):
            for r in report["cells"]:
                assert abs(cell_loss(r["outcome"],[r["q10"],r["q50"],r["q90"]])-r["loss"])<1e-10
            assert summarize(report["cells"])==report["summary"]
        assert matched(selected["cells"],base["cells"])==state["comparison_to_base"]
        chosen=min(state["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
        assert chosen==state["selected"],"Selection changed after evaluation"
        for cp in state["checkpoints"]:
            dev=load(directory/("development-"+str(cp["update"])+".json"))
            assert dev["summary"]==cp["development"]
        for g in state["references"].values():
            assert g["summary"]==summarize(g["cells"])
            assert g["comparison"]==matched(selected["cells"],g["cells"])
        for t in dataset["groups"]["retrospective"]:
            key=t["task_id"];sc=[r for r in selected["cells"] if r["task_id"]==key];bc=[r for r in base["cells"] if r["task_id"]==key]
            if len(sc)!=3 or len(bc)!=3:raise ValueError("Case denominator mismatch")
            cases.append({"id":key+"-"+str(seed),"task_id":key,"seed":seed,"series_id":t["series_id"],"metadata":t["metadata"],"origin":t["origin"],"unit":p["data"]["unit"],"history":t["context"],"history_sha256":digest(t["context"]),"base":bc,"trained":sc,"checkpoint_update":chosen["update"],"artifact":"seed-"+str(seed)+"/evaluation-selected.json","classification":"Additional retrospective case; not prospective"})
        states.append(state)
        for path in sorted(directory.glob("*.json")):
            raw=path.read_bytes()
            # Actual private resource paths must never enter a public report.
            assert b"tinker://" not in raw
            relative="seed-"+str(seed)+"/"+path.name;files[relative]=raw.decode()
    evidence_files=list(root.rglob("source-audit.json"));evidence=load(evidence_files[0]) if evidence_files else None
    incomplete=[]
    for seed in p["model"]["seeds"]:
        if any(s["seed"]==seed for s in states):continue
        candidates=[f for f in root.rglob("progress.json") if load(f).get("seed")==seed]
        if candidates:
            s=load(candidates[0]);incomplete.append({"seed":seed,"optimizer_updates":s.get("optimizer_updates",0),"checkpoints":s.get("checkpoints",[]),"status":"evaluation_blocked","reason":"Original workflow stopped at the persistent checkpoint-storage limit; no final evaluation claimed"})
        else:incomplete.append({"seed":seed,"optimizer_updates":0,"checkpoints":[],"status":"training_blocked","reason":"Original training client could not be created because checkpoint storage was full"})
    status="completed" if len(states)==len(p["model"]["seeds"]) else "partial" if states else "evaluation_blocked"
    report={"schema_version":12,"study_id":p["study_id"],"status":status,"created_at":datetime.now(timezone.utc).isoformat(),"publication_source_sha":os.environ.get("GITHUB_SHA"),"training_workflow_run_id":os.environ.get("TRAINING_RUN_ID","43952200479"),"protocol":p,"protocol_sha256":digest(p),"audit":audit,"runs":states,"incomplete_runs":incomplete,"cases":cases,"supplementary":evidence,"prospective":{"status":"pending","reason":"Registered weekly panel requires fresh compatible retained price history and forecasts committed before outcomes. No prospective accuracy established."},"scientific_boundary":"Historical dates were previously accessible; results are additional retrospective analyses. These weights predict prices directly, separate from the earlier experiment selector.","source_attribution":"Pacific Machines (2026), gpu-price-pack v0.1.1-handover. CC BY 4.0 compilation; exact component source and contract metadata retained. Marketplace asks excluded."}
    report_raw=json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+"\n"
    if "tinker://" in report_raw:raise ValueError("Private model resource path in public report")
    (out/"report.json").write_text(report_raw)
    for name,raw in files.items():
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(raw)
    (out/"audit.json").write_text(json.dumps(audit,indent=2)+"\n")
    manifest={"study_id":p["study_id"],"files":[{"path":str(f.relative_to(out)),"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size} for f in sorted(out.rglob("*")) if f.is_file()]}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    lines=["# Direct GPU-price forecasting v12 findings","","Additional post-event retrospective study. Prospective improvement is not established.","",f"Data: {audit['phase_tasks']['training']} training tasks; {audit['phase_tasks']['development']} development tasks; {audit['phase_tasks']['retrospective']} retrospective tasks. A task contains three dependent horizon cells.","","| Seed | Updates | Selected update | 7-day base loss | 7-day selected loss |","| --- | ---: | ---: | ---: | ---: |"]
    for s in states:lines.append(f"| {s['seed']} | {s['optimizer_updates']} | {s['selected']['update']} | {s['base']['primary_pinball']:.8f} | {s['retrospective']['primary_pinball']:.8f} |")
    lines+=["","Different collectors, configurations and instruments retain separate IDs. The primary loss is USD-per-GPU-hour quantile pinball; lower is better. Source windows overlap and the three evaluation origins are dependent.","","Checkpoint selection uses development only and includes the unadapted base at update zero. A selected base means trained checkpoints did not earn promotion. Additional RL is not established.","","Supplementary evidence accuracy is not established. Current source access and archived-vintage eligibility are separate from forecasting value.","","[Protocol](../configs/direct-forecast-v12.json) · [Methods](direct-forecast-v12.md) · [Public artifacts](../results/direct-v12/README.md)"]
    (out/"findings.md").write_text("\n".join(lines)+"\n")
    print(json.dumps({"status":status,"completed_seeds":[s["seed"] for s in states],"tasks":audit["phase_tasks"],"report_sha256":hashlib.sha256(report_raw.encode()).hexdigest()}))
def main():
    q=argparse.ArgumentParser();q.add_argument("--inputs",required=True);q.add_argument("--output",required=True);a=q.parse_args();assemble(a.inputs,a.output)
if __name__=="__main__":main()
