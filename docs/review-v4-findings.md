# Review v4 findings and forward commitments

These analyses extend the archived studies. They do not replace the official export, reopen model selection, or make prospective accuracy claims.

## Completed mechanism audit

The original operational SFT (soft17/update100) reveals the same four additional tree configurations on all four evaluation tasks: tree_56_3, tree_56_7, tree_28_3 and tree_28_7. The original feedback-hidden replay changes all four orders but preserves all four terminal choices and losses. A fixed portfolio reconstructs each result using the original validation chooser and tie ordering.

The portfolio was discovered after evaluation. It is explanatory, not an originally registered control. Raw quantile equality is unknown because the public operational artifacts retain losses rather than full predictions.

The contribution notebook uses exactly 12 cells across four tasks, two A100 series and three dependent dates. SFT mean pinball is0.011569797542840439 versus0.014995328587716763 for the archived starting policy and0.01213653754659247 for training-selected static. The A10040 group worsens versus starting; A100 SXM improves. The separate 15-cell numerical grid, official 37-series submission and frozen v1 negative result retain their own scope.

## Completed controlled prompt-intervention diagnostic

[Versioned report](../results/review-v4/operations/43750529486/feedback.json), [execution](https://github.com/howdymary/compute-forecasting/actions/runs/43750529486).

This separately identified experiment used two frozen samplers, six conditions and four retrospective tasks: 48 episodes, 519 sampler decisions and 288 cached numerical reveals. It performed no new numerical fits or optimizer updates. All four required cross-role past.dev recalls were returned with their authored source IDs. Exa returned two retrieval receipts of $0.007 each; other provider costs are unknown.

| Condition | Starting mean pinball | Frozen SFT mean pinball |
|---|---:|---:|
| Numerical feedback only | 0.0147345881 | 0.0115697975 |
| Numerical scores hidden | 0.0150455673 | 0.0116199382 |
| Relevant evidence | 0.0150455673 | 0.0115697975 |
| Irrelevant evidence | 0.0149953286 | 0.0115700039 |
| Relevant criticism | 0.0138801802 | 0.0131518187 |
| Neutral text | 0.0134362252 | 0.0115697975 |

Lower is better. Relevant evidence leaves SFT's result unchanged; criticism worsens it. Neutral text changes some behavior and can improve the starting policy's score. This reused small cohort does not support a general claim that research evidence improves forecasts. Packet length was matched in characters, not tokens. Every behavior comparison separates changed order, changed membership, changed terminal choice and changed loss.

This new experiment uses a common intervention prompt and hides only numerical validation scores. The original archived ablation also removed additional summaries. The starting feedback-only score therefore need not match the archived starting score; neither run supersedes the other.

## Completed interval diagnostic

[Retained report](../results/review-v4/operations/43750529486/initialize.json).

A fixed recency-weighted same-lead residual interval was compared with unweighted empirical persistence on independently licensed A10040 and T4 history. Three June/July training-period origins provide18 cells.

| Measure | Recency weighted | Unweighted reference |
|---|---:|---:|
| Mean pinball | 0.0031587292 | 0.0033925472 |
| Inclusive interval coverage | 16/18 | 15/18 |
| Mean interval width | 0.0344922917 | 0.0280219778 |

There were no failed cells. These are dependent descriptive cases, not an independent calibration or accuracy result. The candidate uses a 180-day window, 28-day half-life, minimum 30 matured residuals and 20 effective residuals. No exchangeability guarantee is claimed. Its future arm remains locked and pending.

## Implementation status

| Improvement | Implemented evidence or pipeline | Outcome status |
|---|---|---|
| Mechanism and portfolio audit | Exact four-task reconstruction, original tie rules, null unavailable prediction comparison | Complete, descriptive |
| Prospective selector panel | Eight weekly origins, immutable snapshots and commitments, matched six-reveal selectors, locked scoring, separate A100/T4 cohorts | First origin November 23; outcomes pending |
| Gain-contribution notebook | Matched series/origin/horizon and cell views, linked traces, source-bound pins | Deployed; exact values checked remotely |
| Continuous vintage capture | Licensed adapter, append-only source and revision hashes, collection/failure receipts, finite daily schedule | Initial context retained; new captures recorded separately |
| Horizon interval experiment | Fixed method, maturity guards, diagnostic and prospective arm | Diagnostic complete; future accuracy pending |
| Learning readiness | Temporal split and reachable-reward audit; gated SFT/RL with checkpoint zero and development selection | Nine tasks, five flat rewards; no new training |
| Evidence/criticism controls | Actual retrieval, memory,48 inference episodes and behavior/loss measures | Complete, retrospective |
| Public reproduction | Hash-bound core reconstruction and credential-free operation arithmetic | Remote verification path; private access limits documented |

## Prospective eligibility

The new panel is separate from the existing November16/18/22 persistence–Chronos commitments and their November 23 scoring gate. It begins with weekly origins November 23 through January 11. A forecast must finish within two UTC hours of its origin, use a previously retained compatible snapshot, and bind its actual completion timestamp.

Two validation folds, 8 and 15 days earlier, require real capture vintages and matured seven-day labels. Missing captures remain pending; the first fully eligible selector case can be later than the first scheduled direct forecast. A10040 primary and T4 transfer scores remain separate. First-complete post-maturity truth vintage selection is fixed in advance.

[Supplementary current market context](market-context-v4.md) is a separate extra-information treatment. It cannot alter the archived benchmark or be pooled into the primary equal-information comparison.

## Public verification and limits

Run the credential-free **Verify public v4 arithmetic without credentials** workflow, or on a hosted runner:

~~~sh
python -m pip install -e .
python -m compute_forecast.reproduce_operations_v4
~~~

The existing review reconstruction additionally verifies the full public derived ZIP, indexed members, matched contributions and original chooser replay. Public arithmetic is reproducible without source-pack or model accounts. Re-fitting needs authorized source inputs; original sampler access needs the account's private resources. Raw evidence bodies, model paths and private sessions remain private.

The full Pacific pack was reverified privately:284,917,807 bytes and672 manifest entries. Limited policy-study coverage reflects eligible temporal cases, not absence of the full pack. The project's code has no newly granted blanket license; existing source-specific and third-party licenses remain in force.

## Validation notes

The credential-free verifier reconstructed all committed operation hashes, the18-cell interval arithmetic, 48 intervention episodes and 519 sampler calls. Source-to-screen checks retain exact values and the unchanged official CSV. A repeated HTTP/2 stress failure affected all eight streams after an idle client pool; a five-second idle expiry, HTTPX's documented default, is being validated without changing concurrency, retries or response assertions. This diagnostic status must not be reported as a server-side fix before the rerun completes.
 
The prompt-intervention sampler phase took396.85 seconds; that duration excludes earlier evidence retrieval, memory ingestion and environment setup. It is not an end-to-end cost estimate. Modal/Tinker/past.dev monetary costs remain unknown where no provider receipt is available.

Daily capture revalidates source ETags and byte counts, reuses hash-verified unchanged objects, and preserves the first retained content vintage. Cache reuse does not imply that a provider quote was refreshed. An ETag or input-hash mismatch fails collection visibly.

The first new source capture completed successfully on November15. Its initial downstream Chronos runtime check failed because a univariate axis was not removed. The correction is confined to the new adapter; the archived comparator and commitments are unchanged. The rerun retains this failure as execution evidence.

The synthetic runtime test also checks the registered short-window fallback: a28-day tree lacks the required24 matured labels at the eight-day effective lead and must use the declared empirical fallback. The56-day tree must execute natively. Market-news collection and numerical-runtime validation run independently; a numerical adapter check must not suppress evidence collection.
