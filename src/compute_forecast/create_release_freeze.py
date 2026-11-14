"""Create a reviewable freeze only from successful, measured development runs."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from .freeze_contract import PACK_SHA,FINAL_ORIGINS,BASELINES,numerical_code_hashes,validate_freeze


def create_freeze(policy,baseline,policy_run,baseline_run,trained_policy_source):
    for run,name in ((policy_run,"Train full six-trial Tinker research policy"),(baseline_run,"Select official full-headline baseline")):
        if run["conclusion"]!="success" or run["head_branch"]!="compute-observatory" or run["name"]!=name:
            raise ValueError("REFUSED: source workflow did not succeed on the authorized branch")
    if policy["code_sha"]!=policy_run["head_sha"] or baseline["code_sha"]!=baseline_run["head_sha"]:
        raise ValueError("REFUSED: source revision mismatch")
    current=(Path(__file__).parent/"search_policy.py").read_bytes()
    if hashlib.sha256(current).hexdigest()!=hashlib.sha256(trained_policy_source).hexdigest():
        raise ValueError("REFUSED: policy implementation changed after training")
    if policy["study_kind"]!="six_trial_experiment_selection" or policy["final_period_opened"] is not False or policy["actual_training_updates"]<=0 or policy["epochs"]!=5:
        raise ValueError("REFUSED: genuine completed five-checkpoint training is required")
    if policy["trial_budget_per_task"]!=6 or tuple(policy["common_initial_trials"])!=("last_value","last_value_empirical"):
        raise ValueError("REFUSED: inconsistent experiment budget")
    if baseline["dataset_sha256"]!=PACK_SHA or baseline["selection_phase"]!="development" or baseline["final_period_opened"] is not False or baseline["last_development_label"]!="2026-09-19":
        raise ValueError("REFUSED: baseline selection used an unsupported period")
    best_policy=min((r for r in policy["comparisons"] if r["policy"].startswith("sft_epoch_")),key=lambda r:r["pooled_pinball"])["policy"]
    if best_policy!=policy["selected_checkpoint_on_development"]:raise ValueError("REFUSED: checkpoint was not selected by the frozen development rule")
    epoch=int(best_policy.rsplit("_",1)[1]);checkpoint=next(c for c in policy["checkpoints"] if c["epoch"]==epoch)
    if len(policy["checkpoints"])!=5:raise ValueError("REFUSED: not all five actual checkpoints were saved")
    chosen=min(baseline["methods"],key=lambda r:(r["pooled_pinball"],BASELINES.index(r["method"])))
    if chosen["method"]!=baseline["selected_method"]:raise ValueError("REFUSED: official method differs from measured selection")
    freeze={"schema_version":"1","frozen_at":datetime.now(timezone.utc).isoformat(),"dataset_sha256":PACK_SHA,"protocol_version":"hierarchical-six-trial-v4","final_origins":list(FINAL_ORIGINS),"trial_budget":6,"common_initial":["last_value","last_value_empirical"],"policy_model":policy["model"],"policy_checkpoint_label":best_policy,"policy_checkpoint":checkpoint["sampler_path"],"policy_training_run_id":policy_run["id"],"policy_training_source_sha":policy_run["head_sha"],"policy_training_temporal_origins":policy["training_temporal_origins"],"policy_development_temporal_origins":policy["development_temporal_origins"],"policy_actual_training_updates":policy["actual_training_updates"],"official_method":baseline["selected_method"],"official_selection_run_id":baseline_run["id"],"official_selection_source_sha":baseline_run["head_sha"],"official_selection_last_label":"2026-09-19","numerical_code_sha256":numerical_code_hashes(),"freeze_producer_source_sha":os.environ.get("GITHUB_SHA"),"final_truth_opened":False,"note":"Selection used development data; final numerical outcomes have not been opened by this release pipeline. Retrospective data-vintage and pretraining limitations remain."}
    return validate_freeze(freeze)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--inputs",default="inputs");parser.add_argument("--output",default="artifacts/release-freeze.json")
    args=parser.parse_args();root=Path(args.inputs)
    policy=json.loads((root/"policy/search-policy/search-report.json").read_text());baseline=json.loads((root/"baseline/development-baseline-selection.json").read_text())
    policy_run=json.loads((root/"policy-run.json").read_text());baseline_run=json.loads((root/"baseline-run.json").read_text())
    result=create_freeze(policy,baseline,policy_run,baseline_run,(root/"trained-policy-source.py").read_bytes())
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+"\n")
    with open(os.environ["GITHUB_STEP_SUMMARY"],"a") as f:
        f.write("# Verified release freeze — commit before final evaluation\n\nThe configuration below is derived from successful measured development runs. No final evaluation is executed by this workflow.\n\n~~~json\n"+json.dumps(result,indent=2)+"\n~~~\n")
