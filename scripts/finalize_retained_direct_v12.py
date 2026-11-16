"""Finalize the earliest retained complete predictions; no new model sampling."""
import argparse,json,pathlib,os
from compute_forecast.direct_forecast_v12 import digest,summarize,matched,cell_loss
from compute_forecast.train_direct_v12 import reference_cells,write,now,cfg
p=argparse.ArgumentParser();p.add_argument("--inputs",required=True);p.add_argument("--output",required=True);p.add_argument("--seed",type=int,required=True);a=p.parse_args()
root=pathlib.Path(a.inputs);out=pathlib.Path(a.output);out.mkdir(parents=True,exist_ok=True);protocol=cfg()
dataset=json.loads((root/"dataset.json").read_text());repair=json.loads((root/"reference-repair.json").read_text())
assert dataset["protocol_sha256"]==digest(protocol)==repair["protocol_sha256"]
assert digest(dataset["baselines"])==repair["original_rows_sha256"] and repair["existing_rows_unchanged"]
directory=root/"retained";state=json.loads((directory/"progress.json").read_text())
assert state["seed"]==a.seed and state["optimizer_updates"]==100
for f in directory.glob("*.json"):write(out/f.name,json.loads(f.read_text()))
selection=json.loads((directory/"selection.json").read_text());dev100=json.loads((directory/"development-100.json").read_text())
cp=selection["selected"] if selection["selected"]["update"]==100 else {"update":100,"checkpoint_id":None,"checkpoint_identity_type":"private_retained_training_state_not_required_for_public_arithmetic","development":dev100["summary"],"is_base":False}
assert cp["development"]==dev100["summary"]
state["checkpoints"]=[c for c in state["checkpoints"] if c["update"]!=100]+[cp]
selected=min(state["checkpoints"],key=lambda c:(c["development"]["primary_pinball"],c["update"]))
assert selected==selection["selected"],"Original development-only selection must remain unchanged"
measured=json.loads((directory/"evaluation-selected.json").read_text());base=json.loads((directory/"evaluation-base.json").read_text())
for report in (measured,base):
    assert summarize(report["cells"])==report["summary"]
    for r in report["cells"]:assert abs(cell_loss(r["outcome"],[r["q10"],r["q50"],r["q90"]])-r["loss"])<1e-10
references={}
for method in protocol["evaluation"]["references"]:
    cells=reference_cells(dataset["groups"]["retrospective"],repair["rows"],method)
    references[method]={"summary":summarize(cells),"cells":cells,"comparison":matched(measured["cells"],cells)}
state.update(status="completed",completed_at=now(),selected=selected,retrospective=measured["summary"],base=base["summary"],comparison_to_base=matched(measured["cells"],base["cells"]),references=references,recovery={"original_training_run_id":"43952200479","first_retained_evaluation_run_id":"43957658444","finalization_run_id":os.environ["GITHUB_RUN_ID"],"new_optimizer_updates":0,"new_samples":0,"selection_unchanged":True,"reference_repair_source_sha":repair["source_sha"]},source_attribution="Pacific Machines (2026), gpu-price-pack v0.1.1-handover. CC BY 4.0 compilation; approved collector and instrument identities retained.")
case=sorted(dataset["groups"]["retrospective"],key=lambda t:(t["series_id"],t["origin"]))[0]
state["illustrative_case"]={"selection":"Lexicographically first eligible retrospective task; independent of performance","task_id":case["task_id"],"metadata":case["metadata"],"origin":case["origin"],"history":case["context"],"target_dates":case["target_dates"],"outcomes":case["outcomes"]}
write(out/"result.json",state);write(out/"progress.json",state);write(out/"reference-repair.json",repair)
print("DIRECT_RETAINED_EVALUATION_FINALIZED "+json.dumps({"seed":a.seed,"optimizer_updates":100,"new_samples":0,"selected_update":selected["update"],"base":base["summary"],"trained":measured["summary"],"relative_to_base":state["comparison_to_base"]},indent=2))
