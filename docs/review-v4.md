# Review v4: explaining and extending the evidence

## Verified descriptive findings

The operational development-selected SFT checkpoint (soft seed17, update100) reveals the same four tree configurations on all four retrospective evaluation tasks. Feedback hiding changes their order in four tasks, but not their final selected configurations or recorded losses. Replaying a fixed four-tree portfolio reproduces all four terminal choices and losses with the original validation-based tie rules.

This portfolio was identified after evaluation. It is a post-hoc explanatory comparator, not an originally registered baseline or independent forecasting result. Raw quantile rows are absent from these public evaluation artifacts, so prediction equality remains null. Equal pinball loss alone does not prove identical predictions.

[Derived findings](../results/review-v4/findings.json) and [reproduction manifest](../results/review-v4/manifest.json) retain the exact public archive/member hashes. The official CSV and original v1/v2 configurations are unchanged.

## Contribution notebook

Research → Findings links the mean loss difference to actual series, origin, horizon and cell-level results. Each group contributes n_group/n_total × (candidate loss − reference loss); every partition sums to the reported difference. Its comparisons all use the same 12-cell selector cohort. The separate 15-cell numerical grid is excluded.

Green lowers loss; amber raises it. A zero persistence loss makes relative skill undefined; absolute differences remain visible. The task trace distinguishes changed ordering, reveal membership, terminal choice and measured loss. Research pins retain their exact selected numbers, scope and artifact hash in browser memory until reload.

## Registered successor experiments

- [Prospective selector protocol](../configs/prospective-selector-v4.json): eight weekly origins, frozen starting/SFT/static/GP/random selectors, equal six-result budgets, direct persistence/empirical/Chronos references, and separately identified licensed source cohorts. Existing November16/18/22 commitments remain unchanged.
- [Interval, learning and feedback protocols](../configs/review-v4-experiments.json): one horizon-specific empirical interval, quantitative training readiness, and a matched evidence/criticism design.
- Further training is gated: the original pack supplies9 distinct training tasks across6 dates, only4 with reachable terminal reward variation. Engineering diversity thresholds are not power calculations or guarantees of generalization.
- A new prospective result requires vintage-correct inputs, an issuance timestamp before resolution, and audited compatible truth after maturity. A registered pipeline is not an accuracy result.

## Reproduce without accounts

Use the GitHub Actions workflow **Reconstruct and publish review v4**, or run on a hosted runner:

~~~sh
python -m pip install -e '.[dev]' modal numpy scipy scikit-learn
python -m compute_forecast.review_v4
~~~

The reconstruction downloads only the existing 2 MB public derived research archive, verifies its full ZIP hash and every indexed member hash, and checks all committed source snapshots against their manifest. It needs no source-pack, model, Modal or Tinker credentials. The result is written to the hosted runner's artifacts directory. The synthetic contract fixture is labeled synthetic and contains no purported market observations.

Numerical re-fitting still needs a licensed compatible dataset. Restoring an original sampler needs account access. Newly trained checkpoints are stochastic and must receive new run identities. Project-wide code licensing is not newly granted; source-specific licenses and attribution continue to apply.

## Methodological precedents

[Rolling-origin evaluation](https://otexts.com/fpp3/tscv.html), [AIRA search/evaluation analysis](https://arxiv.org/abs/2507.02554), [MetaBO](https://github.com/boschresearch/MetaBO), [adaptive conformal inference](https://arxiv.org/abs/2106.00170), [Tinker decisions](https://tinker-docs.thinkingmachines.ai/cookbook/recipes/decisions/), and [Modal invocation semantics](https://modal.com/docs/guide/function-invocation-methods). These precedents motivate the controls; this project does not claim to invent them.

## Execution and future operation

The successor implementation lives in:
- review_v4.py: public archive/member verification, tie-aware mechanism reconstruction and exact matched contributions.
- prospective_panel_v4.py: a separate weekly issuer and locked scorer; original v2 date guards are unchanged.
- vintage_v4.py: immutable licensed-source captures, source-object hashes, first capture and revision receipts.
- interval_v4.py: recency-weighted horizon residual quantiles, fixed180-day window, 28-day half-life, minimum 30 residuals and 20 effective residuals.
- learning_v4.py: data-gated SFT/RL, checkpoint zero, development-only selection, saved optimizer/RNG state and separate iteration/update counts.
- feedback_v4.py: six registered prompt interventions on frozen samplers; real Exa source discovery and authored past.dev records.
- review_remote_v4.py: bounded remote execution, private retention and atomic public operation receipts.

The interval amendment was fixed before its first execution to avoid simply duplicating the existing unweighted empirical baseline. Its three June/July diagnostic dates are a training-period descriptive check, not an independent test or a basis for retuning. The separate forward interval arm remains pending.

The new source panel uses previous-day inputs, so validation origins are 8 and 15 days earlier. Their seven-day targets have matured by the current previous-day cutoff. Missing actual historical capture vintages make a selector task pending; a current download cannot repair an old vintage. Initial registered origins may therefore be ineligible while collection accumulates.

All v4 selectors share the same 42 identifiers and six-result budget. Custom numerical models reuse the existing implementations; the new independent-source reference adapters have their own explicit definitions and are not asserted to reproduce official starter baselines. Missing auxiliary identities generate explicit empirical-reference fallbacks. Chronos remains a direct comparator outside the selector pool.

**Run registered review v4 operations** validates all contracts, retains a licensed context vintage, measures training readiness, runs the fixed interval diagnostic on Modal, and evaluates the six-condition retrospective experiment using actual frozen Tinker samplers. The inference experiment changes no weights and reveals existing numerical results; it does not run new backtests.

**Capture and issue registered prospective panel v4** captures daily within a finite November15–January20 window and issues only on the eight registered weekly origins, within two UTC hours. GitHub scheduling and source availability are external dependencies. A missed deadline is a failure or pending case, never a backdated forecast.

**Train a gated successor policy v4** is a manual authenticated workflow. The current task set fails the gate and creates no training client. A broader, separately registered task set is required before new optimization. Evaluated resources, optimizer resumes and all private model paths remain in the account's private volume; public reports contain hashed resource identifiers.

Existing November16/18/22 baseline/Chronos commitments retain their original evaluator and November 23 time gate. The new panel has separate identities and cannot overwrite those forecasts.

## Source access confirmation

A read-only Modal audit on November15 reverified the complete Pacific archive: 284,917,807 bytes, SHA256 f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c, all 672 manifest entries. The pack includes rental observations, AWS spot ticks, hardware fundamentals, capability tables, index prints and market-implied baseline data. The limited A100 policy cohort reflects origin/catalog/label-maturity eligibility, not a missing pack. [Access audit](https://github.com/howdymary/compute-forecasting/actions/runs/43749203252).

The event permits supplementary sources. Current methodological evidence is timestamped and separated from historical market observations. Any later market-news feature needs an independently recorded availability time and its own registered comparison.

## Executed results

The [v4 findings and status](review-v4-findings.md) report the completed interval and48-episode prompt-intervention diagnostics. [Supplementary market context](market-context-v4.md) is a separate forward-only evidence lane. The public operation verifier reconstructs denominators, interval arithmetic and changed-behavior claims without credentials.
