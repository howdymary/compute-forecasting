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


## Completed campaign and research explorer update

The original snapshot above remains a dated record. The canonical campaign has now completed all six SFT runs (600 optimizer updates) and three RL runs (99 updates:41,36,22). All three development selections returned RL update0, the frozen SFT parent, with no incremental RL gain. The original frozen v1 negative result and official export remain unchanged.

The [research explorer methods and source audit](research-explorer-v3.md) add independently licensed historical **context** for A10040GB and T4 (234 observed dates each, Jan12–Nov6;65 missing dates each). Strict numerical identity with the competition series was not established. Exact competition history remains unpublished; the contextual observations are never joined to the official forecast.

A separately registered Chronos-2 control scored0.012113554233974892 pinball on the same12 eligible cells, versus starting selector0.014995328587716763 and operational SFT0.011569797542840439. This is an additional retrospective comparison, outside the frozen42-arm registry. The [control artifact](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/api/chronos-control) preserves the model/weights revision, exact cell keys, timings and future forecast commitment. Prospective targets Nov16/18/22 remain pending; the locked evaluator cannot run before Nov23UTC and no future outcomes were loaded.

The deployed notebook adds checkpoint trajectories, matched series/horizon comparisons, coverage–width views, real paired feedback traces and separate resource units. [Research UI validation](https://github.com/howdymary/compute-forecasting/actions/runs/43691563100) and [notebook validation](https://github.com/howdymary/compute-forecasting/actions/runs/43691563067) passed at1512/390/320px with source values, touch/keyboard, immutable pins, preserved focus/disclosures, delayed research loading, no page overflow, concurrent atomic publication and strict HTTP/numerical assertions. Both stress harnesses used8 measured simultaneous callers, HTTP/2 pooling and zero retries; all12 and21 requests returned200. The remote foundation had105 passing tests and one existing optional dependency skip. PNGs were inspected; no recording jobs were run.
