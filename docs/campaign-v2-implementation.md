# Compute Forecast v2: implementation and interpretation

This campaign is separate from the frozen Pacific submission. The branch is `compute-observatory`; the numerical v1 modules, release freeze, CSV and published negative result remain unchanged. No recording workflows are part of this campaign.

## Registered comparison

[Protocol](../configs/campaign-v2.json) was committed before new training. Numerical source for the controlled grid and SFT campaign: `a147797ec4557a337e2157ac60857d575e121630`. The [campaign run](https://github.com/howdymary/compute-forecasting/actions/runs/43665821333) evaluates 42 registered configurations at 18 origins, including validation-support dates.

Training origins: June 20/27, July 4/11/18/24. All training reward labels end by July 31. Development: August 8/15/22. Evaluation: August 29, September 5/12. The last two folds at origin minus 7 and 14 days supply matured validation labels.

These dates reuse previously inspected v1 development data. Evaluation is retrospective, temporally dependent, and withheld from new weight updates and checkpoint selection; it is not untouched. The original September 27–October 25 final and restricted November 7–13 outcomes are excluded.

The eligibility audit found earlier daily-statistics policy tasks still cover A100 40GB and A100 SXM 80GB. Additional H100 daily targets appear at the November snapshot. The new policy study must not be described as H100 policy evaluation.

## Numerical registry

Four official references; 24 original Ridge configurations; four direct regularized autoregressions; two EWMA levels with prequential residual quantiles; four quantile histogram gradient-boosting configurations; two fixed convex mixtures; two auxiliary-price ablations.

Gradient boosting uses quantile loss, deterministic seeds and disabled automatic early stopping. Preprocessing and residuals mature at each numerical origin. Official per-cell scoring, original targets and units remain authoritative. Fallbacks, crossing repairs and missing observations are reported rather than hidden.

The `coverage_level/log` arms remove auxiliary price indices and changes while retaining target price history. A **separate strict diagnostic** removes target level/returns and all auxiliary price predictors, retaining only availability and coverage. Historical target labels necessarily remain prices. It is outside the frozen 42-arm selector pool and cannot retroactively change policy scores.

## Training and reward

Six controlled SFT runs: hard and soft conditional categorical cross-entropy, seeds 17/29/43, learning rate 3e-5, LoRA rank 16, Qwen3.5-4B, 100 finite updates, saved states at 0/20/50/100. Both objectives use the same Tinker decision-distribution datum interface and menu with at most six choices per stage. Hard targets imitate the training-only inner-validation teacher. Soft targets encode near-ties using a training-only scale.

The policy sees history/availability summaries and revealed matured validation scores, never later reward outcomes or untested scores. Two persistence trials are common; four further configurations are selected. The final forecaster minimizes revealed validation loss. Static, 100 random seeds and fixed-kernel GP expected-improvement selectors use the same candidate pool and six-trial budget.

Checkpoints are selected by development official pinball with earlier-update ties, including update zero. Private manifests persist the actual Tinker checkpoint paths; public IDs are hashes. The selection freeze is written before policy evaluation. Checkpoint files and frozen inputs support recovery without rerunning numerical experiments.

The RL workflow selects the development-best SFT objective within each seed; alphabetic objective breaks ties. It records that choice before reward training. RL is gated by reachable training terminal-reward variation and valid action probabilities. The actor samples actual bounded actions and records their normalized propensities. Four trajectories share a task; the reward baseline is their mean. Reward is negative subsequent training-period forecast loss divided by a training-only scale, clipped to [-5,5]. A clipped conditional categorical policy-gradient loss is implemented through Tinker's supported custom-loss API. Soft-label SFT is not RL.

RL has at most 60 rollout-update iterations per seed. Constant sampled reward groups do not update weights; five initial constant groups stop the run. An audit of all reachable final selections can rule out RL before rollouts. A gated run with zero optimizer updates must be reported as such.

## Evidence and operational autonomy

[Evidence collection](https://github.com/howdymary/compute-forecasting/actions/runs/43665112830) retains 41 search receipts (40 distinct method searches plus a Snapshot capability probe), 76 unique sources and privately retrieved response bodies. The initial retention failure is disclosed; search metadata survived and contents were subsequently re-retrieved rather than claiming the original bodies were recovered.

Exa Snapshot request acceptance does not establish historical page validity, entitlement, ranking vintage, numerical-data vintage or absence of model pretraining contamination. All current evidence remains methodological context, outside historical market inputs. The controlled policy evidence ablation supplies source metadata; the operational loop also reads retrieved method highlights privately.

[Fresh research cycles](https://github.com/howdymary/compute-forecasting/actions/runs/43665969971) address calibration and composition. Scientist choices use actual revealed results, Exa evidence and deterministic criticism. Each requested alternative executes fresh on Modal. Training rollouts use cached numerical grid results and explicitly have different execution semantics.

past.dev records maintain authorship, ingestion IDs, parent records and actual recalled source IDs. Cross-role recall is counted only when the required source is returned. A local authored-record fallback is disclosed when recall fails. Context counterfactuals remove evidence and criticism jointly; they establish neither separate causal effect nor general research ability.

## Product, publication and prospective log

[Experimental Research](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/experimental) polls allowlisted public results. The web container mounts only the public volume and has no sponsor API secrets. It exposes no cost-incurring public endpoint. Question selection filters real running or recorded streams; authenticated GitHub operators can launch new bounded jobs.

The existing pricing-first Explore screen and official export stay available. Experimental curves are development-selection metrics; evaluation tables use excluded new-training dates but remain retrospective.

A prospective log is issued using the verified November 6 snapshot. Its actual issuance date, later target dates, input age, effective lead, source hash and outcome-pending status are explicit. It uses empirical matured differences at the effective calendar lead. It is not a current quote feed or a calibrated guarantee. Numerical rows remain private pending publication review; a timestamped manifest and hash are public.

Provider receipts are read without billing mutations. Tinker attributed gross estimates and any verifiable Modal usage are separate from credits, invoices and remaining balances. Unknown values remain null. Public usage omits session identifiers and account-level raw reports.

## Remote operations

All archives, dependencies, tests and artifacts are created on hosted GitHub runners or Modal, never on the workstation. Source commits are immutable; branch updates use leases. Full grid concurrency is six; the separate diagnostic is capped at four. Each workflow has a finite timeout and explicit run links for cancellation. Modal run contexts clean up ephemeral applications; private results and checkpoints persist.

Relevant workflows: `research-v2-audit.yml`, `research-v2-evidence.yml`, `research-v2-campaign.yml`, `research-v2-autonomy.yml`, `research-v2-rl.yml`, `research-v2-price-free.yml`, `research-v2-prospective.yml`, `research-v2-publish.yml`, `research-v2-usage.yml`, and `validate-experimental-v2.yml`.

The browser check creates PNGs only. It asserts desktop/mobile overflow, real selectors, keyboard focus, reduced motion, API privacy and the unchanged official forecast SHA. Existing foundation and pricing checks remain required.

## Official implementation references

- [Tinker supported models and pricing](https://tinker-docs.thinkingmachines.ai/tinker/models/)
- [Decision models and bounded distributions](https://github.com/thinking-machines-lab/tinker-cookbook/tree/main/tinker_cookbook/recipes/decisions)
- [Tinker checkpoints](https://tinker-docs.thinkingmachines.ai/tinker/howto/checkpoints/)
- [Tinker custom losses](https://tinker-docs.thinkingmachines.ai/tinker/losses/custom/)
- [Modal remote execution](https://modal.com/docs/guide/remote-functions)
- [Modal billing receipts](https://modal.com/docs/guide/billing)
- [Exa Snapshot](https://exa.ai/docs/search/snapshot)
- [Histogram quantile gradient boosting](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html)
