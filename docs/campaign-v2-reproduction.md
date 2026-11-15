# Compute Forecast v2: remote runbook and artifact index

This document covers the separate retrospective v2 campaign on `compute-observatory`. It does not authorize changing `metagame`, the frozen v1 numerical modules, release freeze, official CSV or original reported results.

## Read and verify without account credentials

- [Explore prices](https://howdymary--compute-forecast-observatory-web.us-east.modal.run): archived November 6 benchmark and explicitly assumed long-term paths.
- [Experimental Research](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/experimental): measured checkpoints, selector scores, operational execution traces, ablations and provider receipts.
- [Public experimental JSON](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/api/experimental): the same allowlisted data used by the interface.
- The research download appears after the measured finalizer and archive finish. Its URL, byte count, member hashes and whole-ZIP SHA-256 are in the public `artifact_archive` manifest. The immutable run-specific URL is preferred over `latest.zip`.
- [Official CSV](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/files/forecasts.csv): SHA-256 `67a043255a716db6bc9b73cd28f9258c30fb299fd8671a9ee3430c0d94cadd80`. It has 111 rows across 37 headline series. V2 does not replace it.

Derived scores and decisions are public. Raw offer histories, exact private model-resource paths, credentials, private sessions and restricted source excerpts are excluded. Independent numerical reruns require authorized pack access; replaying retained decisions does not require claiming access to those inputs.

## Canonical source revisions

| Component | Immutable source |
| --- | --- |
| Original protected release | `2a9eecc96d5084b7c8b6c805487628eb6981ba28` |
| Registered 42-arm grid and six SFT runs | `a147797ec4557a337e2157ac60857d575e121630` |
| Frozen exploratory RL amendment and parent comparison | `1fcac48af4ce3f548a9a29cc9bc48bb5d5084889` |
| Final additional controls and provider ledger | `a241dd28b1d7b362b2e9ec1d6ff67b5a8106a199` |
| Durable archive and download route | `89cb3384430d586be3d25b351c25443c40e6199f` |

The UI deployment revision can be newer than the numerical campaign revision. Every retained report names its own source and grid SHA. A documentation or display change does not retroactively change a model run.

## Run and artifact index

Workflow status is authoritative; a queued or running job is not a completed result.

| Purpose | Run | Artifact / evidence |
| --- | --- | --- |
| Registered grid and all six SFT runs | [43665821333](https://github.com/howdymary/compute-forecasting/actions/runs/43665821333) | `campaign-v2-grid`; `campaign-v2-policy-{hard,soft}-{17,29,43}` |
| Methodological Exa evidence | [43665112830](https://github.com/howdymary/compute-forecasting/actions/runs/43665112830) | 41 search receipts, source IDs and current-method scope |
| Initial fresh research cycles | [43665969971](https://github.com/howdymary/compute-forecasting/actions/runs/43665969971) | Calibration and composition traces; actual Modal call IDs |
| Response to uninformative zero-loss task | [43667727748](https://github.com/howdymary/compute-forecasting/actions/runs/43667727748) | Training-origin change and new numerical executions |
| Trained operational research cycle | [43670267628](https://github.com/howdymary/compute-forecasting/actions/runs/43670267628) | `campaign-v2-live-43670267628`; development-only selection receipt |
| Saved-checkpoint inference probe | [43670397299](https://github.com/howdymary/compute-forecasting/actions/runs/43670397299) | Real restored-policy inference; no new backtest claimed |
| Three-seed RL extension | [43671941385](https://github.com/howdymary/compute-forecasting/actions/runs/43671941385) | `campaign-v2-rl-{17,29,43}`; parent freeze, trajectories, gates |
| First paired/static analysis | [43671951167](https://github.com/howdymary/compute-forecasting/actions/runs/43671951167) | Retained intermediate analysis |
| Matched price-value ablation | [43669746825](https://github.com/howdymary/compute-forecasting/actions/runs/43669746825) | Same formulation/preprocessing/missingness; price-value removal |
| Eligible feature audit | [43669085854](https://github.com/howdymary/compute-forecasting/actions/runs/43669085854) | Counts for actual primary/prequential fits |
| Compact feature publication | [43669865616](https://github.com/howdymary/compute-forecasting/actions/runs/43669865616) | Eighteen-origin coverage/imputation summary |
| Corrected UTC prospective log | [43669981910](https://github.com/howdymary/compute-forecasting/actions/runs/43669981910) | 42 private predictions, 14 series; public timestamp/hash |
| Measured finalization | [43672927148](https://github.com/howdymary/compute-forecasting/actions/runs/43672927148) | `campaign-v2-final-43672927148`: controls, final live snapshot, usage, PNG-only UI checks |
| Durable derived archive | [43674118172](https://github.com/howdymary/compute-forecasting/actions/runs/43674118172) | `campaign-v2-archive-43674118172`; public ZIP/member checksums |

GitHub artifacts expire after 30 days. The archive copies an allowlisted subset to the public Modal volume and a private retained release directory. The public server mounts only the public volume and verifies archive bytes before serving them. Hosting availability still depends on the project account.

## Reproduce on hosted services

Use existing authorized GitHub Actions secrets: `MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, `TINKER_API_KEY`; evidence/live research also needs `EXA_API_KEY` and `PAST_API_KEY`. Their values never belong in chat, source or artifacts. Existing credits do not remove rate or quota limits.

1. Verify authorized `gpu-price-pack` access in the private Modal volume. Expected pack SHA-256 is `f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c`; verify all 672 archive manifest entries.
2. Inspect `configs/campaign-v2.json` and the two explicit amendments. Preserve training, development and evaluation boundaries. Never use original final-period or restricted competition outcomes for new selection.
3. Run **Run registered v2 forecasting and policy campaign** on `compute-observatory`. It validates contracts, runs numerical backtests on six Modal workers, then trains hard/soft policies for seeds 17/29/43 with at most two jobs concurrently. Each SFT run has exactly 100 finite updates and development evaluations at 0/20/50/100.
4. The three-seed RL workflow waits for the entire canonical SFT campaign. It selects each seed's development-best SFT parent and freezes that choice before sampling. Its 60 sampling-iteration ceiling is distinct from actual optimizer updates. Zero-update reward gates are valid reportable outcomes.
5. The analysis/finalizer waits for exact source runs before publication. It adds the exact training-selected static portfolio, fixed-forecaster comparison, paired date sensitivity and complete-encoding GP. It verifies all nine reports, protected source hashes and original CSV.
6. The archive workflow waits for the measured finalizer, filters derived JSON, creates a member manifest and verifies the public download. No raw data publication is required.

These workflows intentionally reference the canonical run IDs above. A new independent replication must record its own immutable source, protocol/run IDs and publication destination; do not silently overwrite canonical manifests. Service stochasticity may change newly trained checkpoints. The retained original checkpoints and traces identify what was actually reported.

## Launch a judge-selected operational question

In GitHub Actions, open **Run an authenticated live research question** on `compute-observatory`.

- `question`: `calibration` or `composition`.
- `policy`: `development_selected` or `starting`.
- The trained policy is selected across all six SFT runs by development loss, then earlier update, seed and objective. Evaluation loss is excluded.
- The loop uses an eligible July 18 training-period task. Alternative requests execute fresh on Modal and receive actual call IDs, durations, numerical outcomes and deterministic criticism.
- Public question controls filter streams; they do not let unauthenticated visitors spend sponsor credits. The workflow link requires GitHub authorization.
- This operational evidence/observation context differs from the controlled cached-grid study. Its live result demonstrates execution and adaptation, not a causal estimate of trained-policy accuracy.

## Recovery, cancellation and limits

Workflows have finite timeouts, bounded concurrency and public run links. Cancel only the specific owned run in GitHub Actions. Do not cancel unrelated jobs on the shared branch. Modal application contexts clean up ephemeral applications; persistent artifacts remain on volumes.

Private policy manifests retain the actual checkpoint resources. SFT evaluated checkpoints are at 0/20/50/100. RL saves optimizer recovery state every ten useful updates plus RNG state; temporary rollout samplers have one-hour TTLs. Checkpoints and data must remain accessible for a resumed experiment. A fresh restart is a new identified run, not a continuation manufactured from a displayed curve.

The registered deadline is November 15, 2026 14:00 PT (22:00 UTC). Stop launching campaigns by 12:30 PT (20:30 UTC), reserving at least 90 minutes for evaluation, documentation and verification. Later work must be labeled post-event.

## Interpret the artifacts correctly

- **Automation:** completed requested numerical executions and recorded role transitions.
- **Adaptation:** decisions or hypotheses changed after measured feedback/criticism; counterfactual action traces are reported separately from score differences.
- **Learning:** compare selected trained checkpoints with starting weights on the same retrospective evaluation tasks; RL's incremental comparison uses its own SFT parent.
- **Forecast value:** compare the same cells, candidates and budgets with numerical/search controls. A 15-cell full-grid table is not the 12-cell selector table.
- No-observation ties limit claims about feedback. Evidence/critic additions are inference-time prompt changes; negative results do not establish that external research is universally harmful.
- The effective evaluation is three dependent dates, four eligible series-origin tasks and 12 scored series-horizon cells. It is not 12 independent market histories or H100 policy evidence.
- Provider-reported usage can lag. Unknown costs/credit balances are not zero. Partial closed-hour Modal receipts, attributed Tinker sessions and Exa request receipts have different scopes.
- Prospective predictions use a nine-day-old November 6 snapshot. Their UTC targets are November 16/18/22; outcomes will not mature before the event. Numerical rows remain private pending publication review.
