"""Final evaluation requires a published selection and unchanged numerical code."""
from __future__ import annotations
import hashlib
import re
from datetime import datetime,timezone
from pathlib import Path

PACK_SHA="f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c"
FINAL_ORIGINS=("2026-09-27","2026-10-04","2026-10-11","2026-10-18","2026-10-25")
CODE_FILES=("starter_probe.py","representation_study.py","search_policy.py","select_baseline.py","freeze_contract.py","final_evaluation.py","export_submission.py")
BASELINES=("last_value","last_value_empirical","drift","seasonal_naive")

def numerical_code_hashes():
    root=Path(__file__).parent
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in CODE_FILES}

def validate_freeze(freeze):
    if freeze.get("schema_version")!="1" or freeze.get("dataset_sha256")!=PACK_SHA:
        raise ValueError("REFUSED: missing or incorrect release freeze")
    if freeze.get("final_truth_opened") is not False or tuple(freeze.get("final_origins",()))!=FINAL_ORIGINS:
        raise ValueError("REFUSED: final protocol was not frozen before evaluation")
    if freeze.get("trial_budget")!=6 or tuple(freeze.get("common_initial",()))!=("last_value","last_value_empirical"):
        raise ValueError("REFUSED: search budget changed after development")
    if freeze.get("policy_model")!="Qwen/Qwen3.5-4B" or not re.fullmatch(r"sft_epoch_[1-5]",freeze.get("policy_checkpoint_label","")):
        raise ValueError("REFUSED: unknown frozen policy")
    path=freeze.get("policy_checkpoint","")
    if not path.startswith("tinker://") or "/sampler_weights/" not in path:
        raise ValueError("REFUSED: actual saved sampler checkpoint is required")
    if freeze.get("official_method") not in BASELINES or freeze.get("official_selection_last_label")!="2026-09-19":
        raise ValueError("REFUSED: official method was not selected on development data")
    for key in ("policy_training_run_id","official_selection_run_id"):
        if not str(freeze.get(key,"")).isdigit():raise ValueError("REFUSED: source workflow evidence is required")
    frozen_at=datetime.fromisoformat(freeze["frozen_at"])
    if frozen_at.tzinfo is None or frozen_at>datetime.now(timezone.utc):
        raise ValueError("REFUSED: invalid actual freeze time")
    actual=numerical_code_hashes()
    if freeze.get("numerical_code_sha256")!=actual:
        raise ValueError("REFUSED: numerical or policy code changed after selection; do not tune on final outcomes")
    return freeze
