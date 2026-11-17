"""Credential-free reconstruction of categorical continuation forecasts and model selection."""
import hashlib,json,pathlib
from datetime import date,timedelta
from .probability_v18 import digest,support,quantiles,crps,summarize
from .direct_forecast_v12 import cell_loss
from .continuation_v21 import selection
def verify_evaluation(value,levels,reference=None):
    rows=value["cells"];keys={(r["task_id"],r["horizon_days"]) for r in rows}
    assert len(keys)==len(rows)
    if reference is not None:
        expected={(r["task_id"],r["horizon_days"]):(r["anchor"],r["outcome"],r["target_date"],r["prompt_sha256"]) for r in reference["cells"]}
        assert {(r["task_id"],r["horizon_days"]):(r["anchor"],r["outcome"],r["target_date"],r["prompt_sha256"]) for r in rows}==expected
    for r in rows:
        z=support(r["anchor"],levels);assert z==r["support_prices"]
        assert quantiles(r["probabilities"],z)==[r[k] for k in ("q10","q50","q90")]
        assert r["target_date"]==(date.fromisoformat(r["origin"])+timedelta(days=r["horizon_days"])).isoformat()
        assert abs(cell_loss(r["outcome"],[r[k] for k in ("q10","q50","q90")])-r["loss"])<1e-12
        assert abs(crps(r["probabilities"],z,r["outcome"])-r["crps"])<1e-12
    assert summarize(rows)==value["summary"]
def verify(r):
    assert r["study_id"]=="ce-continuation-v21" and digest(r["protocol"])==r["protocol_sha256"]
    assert "tinker://" not in json.dumps(r) and "private_paths" not in json.dumps(r)
    p=r["protocol"];parent_raw=pathlib.Path(p["parent"]["report_path"]).read_bytes()
    assert hashlib.sha256(parent_raw).hexdigest()==p["parent"]["report_sha256"]
    parent=json.loads(parent_raw);assert r["log_levels"]==parent["log_levels"] and len(r["log_levels"])==19 and 0 in r["log_levels"]
    for phase in ("development","retrospective"):verify_evaluation(r["baseline"][phase],r["log_levels"])
    seen=set()
    for run in r["runs"]:
        state=run["state"];assert (state["arm"],state["seed"]) not in seen;seen.add((state["arm"],state["seed"]))
        assert state["protocol_sha256"]==digest(p) and state["dataset_sha256"]==r["audit"]["dataset_sha256"]
        assert state["training_corpus_sha256"]==r["audit"]["training_corpus_sha256"][state["arm"]]
        assert state["parent_id"]==p["parent"]["checkpoint_id"] and state["optimizer_restore"]=="weights_and_optimizer"
        assert state["optimizer_updates"]==p["model"]["max_updates"]==100
        assert state["example_presentations"]==state["supervised_answer_positions"]==1600
        assert state["selected"]==selection(state["checkpoints"])
        assert [c["update"] for c in state["checkpoints"]]==p["model"]["checkpoints"]
        assert run["development"]["0"]==r["baseline"]["development"]
        for cp in state["checkpoints"]:
            value=run["development"][str(cp["update"])];verify_evaluation(value,r["log_levels"],r["baseline"]["development"])
            assert value["summary"]==cp["development"]
        verify_evaluation(run["retrospective"],r["log_levels"],r["baseline"]["retrospective"])
        assert run["retrospective"]["summary"]==state["retrospective"]
        assert state["unique_horizon_examples_presented"]+state["repeated_horizon_presentations"]==1600
    for case in r["cases"]:
        for cp in case["checkpoints"]:
            for row in cp["rows"]:
                assert row["task_id"]==case["task_id"] and row["origin"]==case["origin"]
                assert [row[k] for k in ("q10","q50","q90")]==quantiles(row["probabilities"],row["support_prices"])
    assert r["new_optimizer_updates"]==sum(v["state"]["optimizer_updates"] for v in r["runs"])
    assert hashlib.sha256(pathlib.Path("results/frozen-v1/forecasts.csv").read_bytes()).hexdigest()==p["preservation"]["official_csv_sha256"]
    return {"status":"passed","completed_runs":len(r["runs"]),"updates":r["new_optimizer_updates"],"primary_cases":len([x for x in r["baseline"]["retrospective"]["cells"] if x["horizon_days"]==7]),"prospective_accuracy":"not established"}
def main():
    pointer=json.loads(pathlib.Path("results/ce-continuation-v21/latest.json").read_bytes());raw=pathlib.Path(pointer["report_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==pointer["report_sha256"];print(json.dumps(verify(json.loads(raw))))
if __name__=="__main__":main()
