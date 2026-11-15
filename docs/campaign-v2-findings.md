# Compute Forecast v2: measured findings

V2 is a separate retrospective study. The original frozen SFT result remains 0.01781945 versus 0.01735406 for the starting policy (2.68% worse); its official 111-row submission has not changed.

**All six selected SFT checkpoints lower loss versus starting weights on the new retrospective evaluation; the development-selected operational checkpoint scores 0.01156980 versus 0.01499533 (22.84% lower).** Five of six feedback-hidden controls tie the corresponding trained procedure, so incremental feedback value remains unresolved. RL and the complete-metadata GP comparison are still running. This is a progress report, not a claim of completed reward-learning improvement.

## What was actually run

- A registered 42-configuration numerical grid across 18 origins, including validation-support origins: 756 method-origin results from 18 completed Modal origin executions.
- Six Qwen3.5-4B rank-16 Tinker SFT runs: hard/soft objectives, seeds 17/29/43, 100 optimizer updates each, checkpoints 0/20/50/100. Total: 600 SFT updates across six models, not 600 updates to one model.
- Three exploratory RL runs selected their SFT parents by development loss only. Sampling-iteration ceilings and actual optimizer updates are reported separately.
- Current-methodological Exa evidence, fresh operational numerical research, authored past.dev exchanges and controlled inference-time context ablations.
- Matched price-value removal, actual preprocessing-availability audit, and a timestamped prospective manifest with outcomes pending.

Training has nine eligible series-origin tasks over six dates; development has six tasks over three dates. Selector evaluation has four tasks over **three dependent dates and 12 series-horizon cells**, all A100 40GB or A100 SXM 80GB. A100 40GB contributes three cells and SXM 80GB nine cells. These are not 12 independent market histories. The full numerical-grid table has 15 cells and cannot be directly compared with the selector table.

The evaluation dates (August 29, September 5/12) were previously inspected during v1 development. New weights and checkpoint selection exclude them, but this is not an untouched or prospective test. The original September 27–October 25 final and restricted November 7–13 competition outcomes are excluded from v2.

## Controlled selector results

Every selector receives the same 42-arm pool, common persistence starts and four additional choices. The final forecaster minimizes revealed matured validation loss. Cached numerical feedback is explicit; six result reveals are not six new backtests or equal training expenditure.

| Procedure | Pinball ↓ | Skill against last value |
| --- | ---: | ---: |
| Starting policy | 0.01499533 | 5.74% |
| Development-selected SFT (soft / 17, update 100) | 0.01156980 | 27.27% |
| Hard SFT mean, seeds 17/29/43 | 0.01156980 | 27.27% |
| Soft SFT mean, seeds 17/29/43 | 0.01113861 | 29.98% |
| Static, training-validation ranked | 0.01213654 | 23.71% |
| Static, exhaustive training-outcome selected | 0.01404649 | 11.70% |
| Random search, 100-seed mean | 0.01353609 | 14.91% |
| GP, original encoding | 0.01220091 | 23.30% |
| Single forecaster selected on training (drift) | 0.01326771 | 16.60% |
| Official last-value reference | 0.01590833 | 0.00% |
| GP, complete metadata | Pending final analysis | — |

| Objective / seed | Selected update | Development pinball | Evaluation pinball | Versus starting | 80% coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| hard / 17 | 20 | 0.01125387 | 0.01156980 | -22.84% | 75.0% |
| soft / 17 | 100 | 0.00905034 | 0.01156980 | -22.84% | 75.0% |
| hard / 29 | 20 | 0.01125387 | 0.01156980 | -22.84% | 75.0% |
| soft / 29 | 20 | 0.01092629 | 0.01027624 | -31.47% | 83.3% |
| hard / 43 | 20 | 0.01125387 | 0.01156980 | -22.84% | 75.0% |
| soft / 43 | 50 | 0.01125387 | 0.01156980 | -22.84% | 75.0% |

The gain is uneven: selected SFT loss on A100 40GB is 0.00290788 versus 0.00254829 for the starting policy, approximately 14.1% worse. Pooled improvement comes from A100 SXM 80GB, which contributes nine of the 12 cells. One-day last-value reference loss is zero on this evaluation, so one-day skill is undefined rather than an invented percentage.

Checkpoints are selected by development pinball with earlier-update ties, including update zero. A global operational checkpoint uses development loss across all six runs, then earlier update, seed and objective. The best evaluation seed is not substituted for that rule.

[All 24 saved SFT checkpoint IDs, seeds, development scores and artifact links](campaign-v2-checkpoints.json) are retained. IDs hash private resource paths rather than weight contents; model resources stay in the owner's Tinker account. RL states will be added after their evaluation reports finish.

## Incremental RL result

The initial attempt completed ten genuine RL optimizer updates and thirteen sampled groups for each of seeds 17/29 before Tinker's free checkpoint-storage cap closed the clients; seed 43 could not create a client. Cleanup removed only 26 consumed rollout samplers. The continuation restores the exact Adam/RNG prefixes, discards no optimizer work and counts the existing thirteen groups within the original 60-group limit. Evaluated/frozen checkpoints remain intact. [Recovery amendment](../configs/campaign-v2-storage-recovery.json), [failed attempt](https://github.com/howdymary/compute-forecasting/actions/runs/43671941385), [cleanup receipt](https://github.com/howdymary/compute-forecasting/actions/runs/43677120366), [continuation](https://github.com/howdymary/compute-forecasting/actions/runs/43677499284). Final RL performance is pending; these updates alone establish no accuracy gain.

The exploratory amendment was fixed before RL updates, after seed-17 SFT evaluation had been observed. The primary SFT protocol stayed fixed. Training-only curriculum eligibility uses reachable clipped-reward variation; actor observations do not expose terminal future loss. Four genuinely sampled trajectories share each task, with recorded conditional action propensities and a group-mean reward baseline. Constant groups do not update weights; five consecutive constant groups stop the run.

RL's reference is its frozen SFT parent. Beating the untrained model alone would not establish incremental RL value. Temporary rollout samplers have one-hour TTLs; evaluated states and private optimizer-recovery snapshots are retained.

## Controls and limitations of the apparent gain

Five of six SFT runs have identical forecast loss with agent feedback hidden. Several still change their action sequences, so a loss tie does not prove a static action policy. Soft/seed 29 worsens from 0.01027624 to 0.01082398 without observations. Adding the fixed critic worsens soft/seed 17 to 0.01315182 and soft/seed 29 to 0.01479314; adding source metadata worsens soft/seed 29 to 0.01333005. Other SFT ablation losses tie. These inference-time context additions can also shift the prompt distribution; they do not establish that research evidence or criticism is universally harmful.

The no-observation condition hides history summaries and revealed validation scores from the experiment-selection agent while retaining its tested-arm IDs and budget. The final deterministic forecaster chooser still uses revealed matured validation in every condition. A tie therefore limits claims about feedback **to experiment selection**, not about removing validation from the complete forecasting procedure.

The stronger static control enumerates all 91,390 portfolios of four additional arms, chooses using training-period future outcomes only, and uses the same revealed-validation final chooser at evaluation. It preserves the original weaker training-validation-ranked static control.

The original GP control aliased auxiliary representations/reference identities. Its result remains retained; the additional complete-encoding control keeps acquisition, kernel, starts, iteration order and budget unchanged. It was added after some SFT evaluations and is an additional retrospective control, not a replacement preregistered result.

The selected SFT policies lower mean-origin loss on each of the three evaluation dates, and leave-one-origin-out pooled differences remain negative. That describes this tiny observed set only. The largest contribution comes from September 12.

The training teacher's inner-validation versus subsequent-loss rank correlations range from −0.291 to 0.748 across nine correlated training tasks. The validation-oracle choice performs worse than starting persistence on three tasks, better on one and ties on five. This objective mismatch is a reason to test future-loss rewards; additional imitation updates alone do not solve it.

Reported hindsight regret is the loss gap to the best future-scoring configuration among the 42 arms, evaluated after selection. That oracle arm need not be reachable under the fixed final validation chooser. It is not an attainable-performance guarantee.

Training-seed ranges and leave-one-origin-out changes describe sensitivity on these same three dependent dates. They are not population confidence intervals. Pretrained knowledge and frozen-pack vintage remain uncontrolled limitations even though the model sees bounded state summaries rather than later outcomes.

## Numerical forecasting and price information

On the separate 15-cell numerical-grid evaluation, tree_28_3 and tree_28_7 score 0.01335719 with five fallback cases each. Tree_56_3 scores 0.01353057 with no fallbacks. Empirical persistence/drift score 0.01412099, and the official last-value reference scores 0.02024667. The best tree row was identified after evaluation; it is not a preregistered winner or a replacement submission.

Across the three numerical development dates, empirical persistence/drift score best (0.01101059). Across numerical training dates, they also score best (0.00386106). This stability of a simple baseline is part of the result, even though retrospective evaluation contains better-scoring tree candidates.

A matched diagnostic fits absolute-level and log-level Ridge models with the same 56-day window, alpha 100, train-only imputation, original missingness flags and prequential residual calibration. Removing nine price-value predictors increases evaluation loss from 0.02037651 to 0.02903200 (level) and 0.02138023 to 0.03128927 (log), approximately 42.5% and 46.3%. This is a conditional diagnostic on 15 cells, not a universal claim about market mechanisms.

The earlier strict price-free diagnostic also changed the target/anchor formulation. It remains as a historical unmatched result; the matched design addresses that confound.

The feature audit covers actual primary and prequential fits at 18 origins. Evaluation auxiliary imputation is approximately 0.018% for raw-composition features and 3.03% for fixed-basket features. Repeated masks across alpha settings are not independent data. Neither the audit nor alternative representations change official target definitions.

The v1 representation finding remains mixed: the best individual candidate used fixed-basket features, while target-only features had lower mean loss across matched settings. No universal normalization benefit is claimed; Silicon Data and SemiAnalysis are credited precedents.

## Operational autonomy and evidence

Four completed cycles executed 24 numerical trials through 20 fresh Modal function calls and recorded 33 verified cross-role memory reads. Each common persistence call computes two references; four subsequent calls compute requested alternatives. New executions are new computation on the same training-period observations, not independent market histories.

The initial July 24 cycles found zero-loss persistence. A skeptic objection led the starting scientist to choose July 18 from eligible non-flat training cases, using actual reference feedback. Its best measured diagnostic was fixed-basket level Ridge (0.00746641), versus empirical persistence 0.00822406.

The operational trained cycle restored the development-selected soft/seed 17 update 100 checkpoint `ef9cf57b88d0bbe9ef3d`. It requested five fresh numerical calls, recorded eight verified memory reads, and changed two of four choices under context removal and two under results removal. It ultimately selected empirical persistence 0.00822406; none of its four requested alternatives beat persistence. This is evidence of real execution and state-sensitive decisions, not a live forecasting improvement. The operational prompt/evidence context differs from the controlled selector evaluation, so comparison with the earlier starting cycle is not causal.

Forty distinct methodological searches plus one Snapshot capability probe produced 41 search receipts and 76 unique source URLs. Raw retrieved bodies remain private. The initial retention failure is disclosed; subsequent content retrieval did not recover the original bodies verbatim.

Snapshot request acceptance does not verify historical entitlement, historical page validity or ranking vintage. Current content stays outside historical market inputs. The controlled evidence ablation adds fixed source metadata, while operational agents also receive privately retrieved methodological highlights. This does not make all evidence conditions equivalent.

Memory records preserve role authorship, record IDs and required source-ID recall checks. Canonical authored text is used after verification or a disclosed local-record fallback. Cross-role use establishes provenance, not a measured memory-system performance improvement. The skeptic is bounded deterministic code, not an independently trained researcher.

## Prospective commitment and publication

The corrected manifest was issued November 15 at 02:55:42 UTC, using a November 15 UTC origin and target dates November 16/18/22. It contains 42 predictions across 14 H100/A100 series, based on a nine-day-old November 6 snapshot. Its numerical rows remain private pending publication review; outcomes are pending and do not mature before the event.

Forecast commitment: `428296e044ca0a5c362ee5b96d9488c6fe47cd59be6a3d70000ac2c51cbf29d2`. Hash basis is UTF-8 Python `json.dumps(private_record, sort_keys=True, allow_nan=False)` with default separators and `ensure_ascii=True`; manifest-only fields are excluded. This is not the pretty-printed file-byte hash.

An earlier Pacific/UTC-misaligned manifest is retained as superseded. The corrected first target UTC day starts strictly after issuance.

The pack measures advertised rental offers, not transactions or available capacity. Histories remain unpublished while licensing/upstream redistribution terms are unresolved. Dollar rental units are USD/GPU-hour; physical resale remains a separate assumption-based scenario without an observed dollar anchor.

## Usage, validation and artifacts

Verified completed SFT work is 600 optimizer updates across six runs. The grid used 18 fresh origin functions and approximately 41.04 summed function-minutes, excluding autonomy, client setup and policy inference. The six SFT client runtimes sum to approximately 231.69 minutes including their evaluations; these are not billed GPU minutes. Final RL counts and native provider receipts are pending. The earlier provider ledger is partial: Modal $0.05712 from already closed billing hours, Tinker cost unavailable, and Exa $0.28 for 40 costed search receipts, excluding later contents/autonomy requests. These are not total campaign costs or remaining balances. No balance is verified and no billing settings changed.

Completed episodes validate every bounded action menu before execution. This does not establish a complete count of failed underlying API calls: SDK retries are not fully instrumented, so their total remains unknown. The autonomous memory calls retain actual HTTP status receipts; engineering failures and targeted retries remain visible in Actions.

[Foundation validation](https://github.com/howdymary/compute-forecasting/actions/runs/43677499285) and [desktop/mobile UI validation](https://github.com/howdymary/compute-forecasting/actions/runs/43677709072) passed. Checks cover real API numerical values, keyboard focus, reduced motion, no horizontal page overflow and outage/retry recovery. The phase badge distinguishes completed SFT from pending RL/controls. Original numerical modules, release freeze and recording files retain their original Git blob hashes; the official CSV retains its published SHA-256. Final measured verification remains [queued behind the continuation](https://github.com/howdymary/compute-forecasting/actions/runs/43677709126). PNG inspection only; no recording job.

The [durable derived archive](https://github.com/howdymary/compute-forecasting/actions/runs/43677783872) waits for final verification. It will preserve member/ZIP checksums, actual reports, traces, failed prefixes, cleanup receipts and exact client versions. Raw offers, private model paths, restricted excerpts and credentials are excluded. Until that workflow finishes, use the canonical run links in the runbook; no completed archive is claimed.

The [remote runbook](campaign-v2-reproduction.md) links immutable sources, workflow artifacts and private-access prerequisites. The public web container has no raw-data mount or sponsor API secrets. Authenticated GitHub workflows launch paid work; public controls filter real running/recorded streams.

## What can be claimed

- **Automation:** demonstrated bounded, fresh numerical execution and provenance across four completed cycles.
- **Adaptation:** demonstrated state-sensitive choices and a research-origin change after criticism, without claiming that every changed choice improves the outcome.
- **Learning:** all six SFT-selected procedures lower loss versus starting weights on three reused, dependent dates; the effect is uneven across series. Incremental RL performance is pending.
- **Forecast value:** SFT is competitive with the specified controls on exactly matched cases. The complete-encoding GP comparison is pending; there is no official competition-outcome score or broad market generalization claim.

No v2 winner replaces the frozen official submission. No H100 policy result, independently calibrated future interval, broad research intelligence gain or competition leaderboard win is established. The prospective outcome log is a commitment to future measurement, not an already scored success.
