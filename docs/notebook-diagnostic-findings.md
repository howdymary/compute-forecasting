# Notebook diagnostic snapshot

This is a post-hoc descriptive audit of the already public results at 2026-11-15T06:07:42.782540+00:00. It contains six completed SFT reports and one completed RL report, not the final three-seed RL campaign. [Exact diagnostic snapshot](notebook-diagnostic-snapshot.json) records the source revisions, counts and formulas. It does not select new models or change the official forecast.

## Uncertainty tradeoff

The starting policy covers 7/12 cells (58.33%) with mean q10–q90 width 0.07693120 USD per GPU-hour. Five selected SFT checkpoints cover 9/12 cells (75%); soft/seed 29 covers 10/12 (83.33%). Their mean widths are approximately 0.08111–0.08159, versus 0.07693 starting. Coverage is higher alongside wider intervals. These are the same 12 cells over three dependent A100 dates; neither the nominal 80% interval nor this observed fraction establishes population calibration. The operational checkpoint was selected on development, not this coverage result.

## Feedback does not have one meaning

5/6 SFT feedback-hidden arms have the same forecast loss as their primary condition. Of those tied runs, 3 change action sequences; their selected final forecaster stays the same. Soft/seed 17 changes all four action sequences while keeping the same final choices and loss. This refines the interpretation: equal loss does not mean every policy is behaviourally static, and changed actions do not by themselves demonstrate forecasting value.

Soft/seed 29 changes three of four sequences and two final choices when feedback is hidden; loss rises by 0.0005477337. This is a small retrospective contrast, not a general causal proof that feedback improves research ability. The final deterministic chooser still uses matured validation in both conditions.

## Work units

The current ledger records 6 cached result reveals per selector task, 600 optimizer updates across completed SFT reports, and 41 updates in the completed RL report. Separately, 4 operational cycles contain 24 trials through 20 fresh Modal calls and 33 verified cross-role reads. These categories are not interchangeable and do not imply equal end-to-end cost or independent market observations.

The first [remote notebook validation](https://github.com/howdymary/compute-forecasting/actions/runs/43683991615) matched diagnostics to saved public results and measured a 1.0387-second HTTP roundtrip. It did not measure pure CPU latency, a zero-dollar serving cost, or new predictive performance.

[Peer comparison and missing Chronos-2 baseline](notebook-peer-review.md) · [Post-hoc improvement register](notebook-improvements.json) · [Live study notes](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/#research)
