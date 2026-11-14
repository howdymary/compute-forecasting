"""Tinker baseline-choice warmup using completed, official starter experiments.

This integration study is separate from the six-trial, 24-configuration search study.
No final-period observations or outcomes enter this program.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import math
import os
import random
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from uuid import NAMESPACE_URL, uuid5

METHODS = ("last_value", "last_value_empirical", "drift", "seasonal_naive")
MODEL = "Qwen/Qwen3.5-4B"


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")


def read_run_csv(volume, report, name):
    prefix = PurePosixPath(report["artifact_prefix"])
    if prefix.parts[:3] != ("/", "data", "runs") or ".." in prefix.parts:
        raise RuntimeError("Untrusted artifact prefix")
    relative = "/" + str(prefix.relative_to("/data") / name)
    raw = b"".join(volume.read_file(relative))
    expected = next((item["sha256"] for item in report["artifacts"] if item["path"] == name), None)
    if expected is None or hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError("Run artifact digest mismatch: " + name)
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
    return reader.fieldnames, list(reader)


def history_features(rows, origin):
    ordered = sorted((date.fromisoformat(row["date"]), float(row["value"])) for row in rows)
    if any(day > origin for day, _ in ordered):
        raise RuntimeError("REFUSED: history contains a later observation")
    recent = [(day, value) for day, value in ordered if day >= origin - timedelta(days=28)]
    if not recent or any(not math.isfinite(value) or value <= 0 for _, value in recent):
        return None
    changes = [math.log(v2 / v1) for (d1, v1), (d2, v2) in zip(recent, recent[1:]) if (d2-d1).days == 1]
    lookup = dict(recent)
    latest_day, latest = recent[-1]
    def relative_change(lag):
        earlier = lookup.get(latest_day - timedelta(days=lag))
        return math.log(latest / earlier) if earlier else None
    return {
        "observations_in_last_28_calendar_days": len(recent),
        "unique_values_in_window": len({value for _, value in recent}),
        "age_of_latest_observation_days": (origin-latest_day).days,
        "consecutive_daily_changes": len(changes),
        "fraction_unchanged": sum(abs(value) < 1e-12 for value in changes)/len(changes) if changes else None,
        "mean_daily_log_change": statistics.mean(changes) if changes else None,
        "std_daily_log_change": statistics.pstdev(changes) if len(changes) > 1 else None,
        "log_change_1_day": relative_change(1),
        "log_change_3_days": relative_change(3),
        "log_change_7_days": relative_change(7),
    }


def prepare_cases(report, volume, split):
    expected_origin = "2026-07-24" if split == "train" else "2026-08-08"
    if report["cutoff"] != expected_origin or report["is_synthetic"] or not report["refusal_check_passed"]:
        raise RuntimeError("REFUSED: unexpected or unverified source experiment")
    if split == "train" and report["label_cutoff"] > "2026-07-31":
        raise RuntimeError("REFUSED: training outcomes cross the registered boundary")
    if report["label_cutoff"] >= "2026-09-27":
        raise RuntimeError("REFUSED: final-period outcomes cannot enter warmup")
    columns, history = read_run_csv(volume, report, "history.csv")
    if not {"series_id", "date", "value"}.issubset(columns or []):
        raise RuntimeError("Unexpected starter history schema")
    grouped = {}
    for row in history:
        grouped.setdefault(row["series_id"], []).append(row)
    origin = date.fromisoformat(expected_origin)
    features = {series: history_features(rows, origin) for series, rows in grouped.items()}
    scores, result_ids = {}, []
    for method in METHODS:
        name = "report_" + method + ".json"
        source = report["reports"][name]
        if source["forecast_validation"]["n_problems"] or source["cells"]["missing_forecast"]:
            raise RuntimeError("REFUSED: source baseline forecasts were incomplete or invalid")
        source_digest = next(item["sha256"] for item in report["artifacts"] if item["path"] == name)
        result_ids.append(str(uuid5(NAMESPACE_URL, source_digest)))
        for series in source["per_series"]:
            for horizon in (1, 3, 7):
                entry = series["by_horizon"].get(str(horizon), {})
                loss = entry.get("pinball")
                if entry.get("n_cells", 0) and loss is not None and math.isfinite(loss):
                    scores.setdefault((series["series_id"], horizon), {})[method] = float(loss)
    cases = []
    for (series_id, horizon), losses in sorted(scores.items()):
        if set(losses) != set(METHODS) or features.get(series_id) is None:
            continue
        case_id = hashlib.sha256((expected_origin + "|" + series_id + "|" + str(horizon)).encode()).hexdigest()[:20]
        best = min(losses.values())
        teacher = next(method for method in METHODS if losses[method] <= best + 1e-6)
        cases.append({
            "case_id": case_id,
            "dataset_sha256": report["archive_sha256"],
            "source_run_id": report["run_id"],
            "source_code_sha": report.get("code_sha"),
            "source_attribution": report["source_attribution"],
            "transform_note": "Derived normalized history statistics and measured baseline-choice labels.",
            "split": split,
            "origin": expected_origin,
            "series_id": series_id,
            "observation": {"horizon_days": horizon, "history_statistics": features[series_id]},
            "eligible_config_ids": list(METHODS),
            "chosen_config_id": teacher,
            "teacher_result_ids": result_ids,
            "training_data_cutoff": report["label_cutoff"] + "T23:59:59+00:00",
            "teacher_rule_version": "minimum_rounded_report_pinball_with_1e-6_ties_v1",
            "losses_for_evaluator_only": losses,
        })
    if not cases:
        raise RuntimeError("No eligible measured cases were available")
    return cases


def question(case):
    return (
        "Choose one official forecasting configuration for an anonymized daily advertised rental-rate series. "
        "Choose the method expected to minimize mean pinball loss across the 0.1, 0.5 and 0.9 quantiles "
        "at the requested horizon. Only historical statistics are shown; outcomes and untested scores are hidden.\n"
        + json.dumps(case["observation"], sort_keys=True, allow_nan=False)
    )


def choices(case):
    ordered = list(METHODS)
    random.Random(int(case["case_id"][:8], 16)).shuffle(ordered)
    return [(method, "Official Pacific starter configuration: " + method) for method in ordered]


async def train_and_evaluate(train_cases, development_cases, output_dir, epochs, learning_rate):
    import tinker
    from tinker import types
    from tinker_cookbook import model_info, renderers
    from tinker_cookbook.recipes.decisions import Decision, DecisionRenderer, decision_choice_datums, sample_decision

    output_dir = Path(output_dir)
    service = tinker.ServiceClient(display_name="Compute Forecast: measured baseline-choice warmup")
    trainer = await service.create_lora_training_client(base_model=MODEL, rank=16, seed=42)
    tokenizer = trainer.get_tokenizer()
    renderer = renderers.get_renderer(model_info.get_recommended_renderer_name(MODEL), tokenizer)
    decision_renderer = DecisionRenderer(renderer)
    decisions = {case["case_id"]: Decision(question(case), choices(case)) for case in [*train_cases, *development_cases]}
    data = list(decision_choice_datums(decision_renderer, [(decisions[case["case_id"]], case["chosen_config_id"]) for case in train_cases]))
    baseline_sampler = await service.create_sampling_client(base_model=MODEL)
    semaphore = asyncio.Semaphore(8)
    comparisons, updates, checkpoints = [], [], []

    async def evaluate(sampler, label):
        async def one(case):
            async with semaphore:
                distribution = await sample_decision(sampler, decision_renderer.render(decisions[case["case_id"]]))
            if set(distribution) != set(METHODS) or any(not math.isfinite(v) or v < 0 for v in distribution.values()):
                raise RuntimeError("Invalid decision distribution")
            selected = max(METHODS, key=lambda method: (distribution[method], -METHODS.index(method)))
            return {"case_id": case["case_id"], "selected_config_id": selected,
                    "probabilities": distribution, "diagnostic_pinball": case["losses_for_evaluator_only"][selected]}
        rows = await asyncio.gather(*(one(case) for case in development_cases))
        result = {"policy": label, "cases": len(rows), "temporal_origins": 1,
                  "diagnostic_mean_pinball": statistics.mean(row["diagnostic_pinball"] for row in rows),
                  "chosen_config_counts": {method: sum(row["selected_config_id"] == method for row in rows) for method in METHODS},
                  "traces": rows}
        comparisons.append(result)
        write_json(output_dir / (label + "-development.json"), result)
        return result

    await evaluate(baseline_sampler, "starting_policy")
    for epoch in range(1, epochs+1):
        order = list(range(len(data)))
        random.Random(42+epoch).shuffle(order)
        for start in range(0, len(order), 32):
            batch = [data[i] for i in order[start:start+32]]
            forward = trainer.forward_backward(batch, loss_fn="cross_entropy")
            optimization = trainer.optim_step(types.AdamParams(learning_rate=learning_rate))
            forward_result = await forward
            await optimization
            updates.append({"epoch": epoch, "batch_examples": len(batch), "metrics": forward_result.metrics})
            write_json(output_dir / "training-updates.json", updates)
        state = await trainer.save_state("warmup_epoch_" + str(epoch))
        weights = await trainer.save_weights_for_sampler("warmup_epoch_" + str(epoch))
        checkpoints.append({"epoch": epoch, "state_path": state.path, "sampler_path": weights.path})
        write_json(output_dir / "checkpoints.json", checkpoints)
        sampler = await service.create_sampling_client(model_path=weights.path)
        await evaluate(sampler, "sft_epoch_" + str(epoch))
    references = {}
    for method in METHODS:
        references[method] = statistics.mean(case["losses_for_evaluator_only"][method] for case in development_cases)
    rng = random.Random(42)
    random_loss = statistics.mean(case["losses_for_evaluator_only"][rng.choice(METHODS)] for case in development_cases)
    report = {
        "schema_version": "1", "study_kind": "baseline_choice_warmup_not_main_search_study",
        "dataset_sha256": train_cases[0]["dataset_sha256"],
        "training_source_run_id": train_cases[0]["source_run_id"],
        "development_source_run_id": development_cases[0]["source_run_id"],
        "source_attribution": train_cases[0]["source_attribution"],
        "inference_decisions": len(development_cases) * (epochs + 1),
        "training_examples_seen": len(train_cases) * epochs,
        "model": MODEL, "lora_rank": 16, "epochs": epochs, "learning_rate": learning_rate,
        "training_examples": len(train_cases), "training_temporal_origins": 1,
        "development_examples": len(development_cases), "development_temporal_origins": 1,
        "budget_per_case": 1, "main_six_trial_search_study_complete": False,
        "training_data_last_label": "2026-07-31", "development_origin": "2026-08-08",
        "final_period_opened": False,
        "metric_note": "Diagnostic losses use the official report's rounded per-cell metrics; main evaluation must rerun the official scorer.",
        "limitation": "One training origin and one development origin; series and horizons are dependent. This does not establish improved research ability.",
        "reference_diagnostic_losses": references, "seeded_random_diagnostic_loss": random_loss,
        "comparisons": [{key: value for key, value in row.items() if key != "traces"} for row in comparisons],
        "checkpoints": checkpoints, "actual_training_updates": len(updates),
        "training_cost_status": "unavailable", "training_cost_value": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code_sha": os.environ.get("GITHUB_SHA"),
    }
    write_json(output_dir / "warmup-report.json", report)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as stream:
            stream.write("# Genuine Tinker training warmup\n\n")
            stream.write("Completed experiments supplied training labels. Final evaluation remains sealed.\n\n")
            stream.write("This is a one-choice baseline warmup, separate from the main six-trial search study.\n\n")
            stream.write("~~~json\n" + json.dumps(report, indent=2, allow_nan=False) + "\n~~~\n")
    print(json.dumps(report, indent=2, allow_nan=False))


def main(argv=None):
    import modal
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-report", required=True)
    parser.add_argument("--development-report", required=True)
    parser.add_argument("--output-dir", default="artifacts/policy-warmup")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    args = parser.parse_args(argv)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    volume = modal.Volume.from_name("compute-forecast-data", version=2)
    train_cases = prepare_cases(json.loads(Path(args.training_report).read_text()), volume, "train")
    development_cases = prepare_cases(json.loads(Path(args.development_report).read_text()), volume, "development")
    write_json(output / "training-examples.json", [{key: value for key, value in row.items() if key != "losses_for_evaluator_only"} for row in train_cases])
    write_json(output / "development-evaluation-manifest.json", {"case_count": len(development_cases), "origin": "2026-08-08", "final_period_opened": False})
    asyncio.run(train_and_evaluate(train_cases, development_cases, output, args.epochs, args.learning_rate))


if __name__ == "__main__":
    main()
