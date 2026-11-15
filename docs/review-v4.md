# Review v4: explaining and extending the evidence

## Verified descriptive findings

The operational development-selected SFT checkpoint (soft seed17, update100) reveals the same four tree configurations on all four retrospective evaluation tasks. Feedback hiding changes their order in four tasks, but not their final selected configurations or recorded losses. Replaying a fixed four-tree portfolio reproduces all four terminal choices and losses with the original validation-based tie rules.

This portfolio was identified after evaluation. It is a post-hoc explanatory comparator, not an originally registered baseline or independent forecasting result. Raw quantile rows are absent from these public evaluation artifacts, so prediction equality remains null. Equal pinball loss alone does not prove identical predictions.

[Derived findings](../results/review-v4/findings.json) and [reproduction manifest](../results/review-v4/manifest.json) retain the exact public archive/member hashes. The official CSV and original v1/v2 configurations are unchanged.

## Contribution notebook

Research → Findings links the mean loss difference to actual series, origin, horizon and cell-level results. Each group contributes n_group/n_total × (candidate loss − reference loss); every partition sums to the reported difference. Its comparisons all use the same12-cell selector cohort. The separate15-cell numerical grid is excluded.

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

The reconstruction downloads only the existing2MB public derived research archive, verifies its full ZIP hash and every indexed member hash, and checks all committed source snapshots against their manifest. It needs no source-pack, model, Modal or Tinker credentials. The result is written to the hosted runner's artifacts directory. The synthetic contract fixture is labeled synthetic and contains no purported market observations.

Numerical re-fitting still needs a licensed compatible dataset. Restoring an original sampler needs account access. Newly trained checkpoints are stochastic and must receive new run identities. Project-wide code licensing is not newly granted; source-specific licenses and attribution continue to apply.

## Methodological precedents

[Rolling-origin evaluation](https://otexts.com/fpp3/tscv.html), [AIRA search/evaluation analysis](https://arxiv.org/abs/2507.02554), [MetaBO](https://github.com/boschresearch/MetaBO), [adaptive conformal inference](https://arxiv.org/abs/2106.00170), [Tinker decisions](https://tinker-docs.thinkingmachines.ai/cookbook/recipes/decisions/), and [Modal invocation semantics](https://modal.com/docs/guide/function-invocation-methods). These precedents motivate the controls; this project does not claim to invent them.
