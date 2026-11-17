# Market-state v19: campaign in progress

Status checked 2026-11-17 09:01:16 UTC. The final six-run comparison has not yet been published.

The [registered campaign](https://github.com/howdymary/mochi-demo/actions/runs/44041295208) has completed all three price-only runs and market-context seed 17. The remaining market-context runs are still executing. All completed runs made 59 optimizer updates. Price-only selected update 30 for each seed; market-context seed 17 selected update 59 using development seven-day pinball.

| Condition | Seed | Selected update | Retrospective seven-day pinball |
|---|---:|---:|---:|
| Price-only | 17 | 30 | 0.015557662085394464 |
| Price-only | 29 | 30 | 0.016804250775319517 |
| Price-only | 43 | 30 | 0.013900696347035037 |
| Market context | 17 | 59 | 0.016692375478225007 |

The first matched seed does not show an information benefit: market context has higher loss than price-only. Do not extrapolate from one seed or select a new configuration on these outcomes.

These are **24 seven-day cases, eight source-defined groups, three reused and dependent dates**. Official drift scores 0.016702906140694442 on the same new targets. The numerical learner's market-context condition also failed to improve loss in the fixed retrospective comparison.

[Measured live progress](../results/market-state-v19/progress/latest.json) contains actual saved checkpoint probabilities, source histories and original selections. Its timestamp can precede this status snapshot. The final publisher will reconstruct all six runs and replace this provisional summary only after they complete.

The continuing open source still reported November 16 at retrieval on November 17, 08:52 UTC. That capture is ineligible for a November 17 origin. Thirty eligible retained days and a compatible contract cohort are required before the new panel can issue forecasts.

The experiment is running; prospective improvement is not yet established.
