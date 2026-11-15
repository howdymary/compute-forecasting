# Compute Forecast

**Explore archived GPU rental forecasts and test explicit long-term pricing scenarios.**

[Experimental Research v2](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/experimental) adds a separate, measured campaign: 42 numerical configurations, hard/soft Tinker SFT across three seeds, reward-gated RL, Exa-guided fresh Modal executions, a strict price-predictor ablation and a timestamped prospective log. Runs and negative results appear as they complete. [Implementation, cutoffs and interpretation](docs/campaign-v2-implementation.md). This does not replace the frozen submission or establish H100 policy performance.

[Open the research observatory](https://howdymary--compute-forecast-observatory-web.us-east.modal.run) · [Two-minute demo video](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/files/demo.mp4) · [Frozen evaluation and official forecast export](https://github.com/howdymary/compute-forecasting/actions/runs/43653016797) · [Source branch](https://github.com/howdymary/compute-forecasting/tree/compute-observatory)

The pricing-first Explore view puts a large interactive chart at the center of the product. Switch between the exact submitted 1/3/7-day quantiles and separate 12/24/36-month rental or resale scenarios. Adjust annual assumptions, inspect any month with mouse/touch/keyboard, and optionally supply your own rental-dollar anchor. All 37 source series have verified names and USD/GPU-hour units. Historical prices remain unpublished while redistribution permission is unresolved.

[Pricing controls, formulas and data contract](docs/pricing-observatory.md) · [Verified deployment](https://github.com/howdymary/compute-forecasting/actions/runs/43658918382) · [Independent desktop/mobile checks](https://github.com/howdymary/compute-forecasting/actions/runs/43659021941). Research, Methods and Downloads keep the evidence and limitations accessible without crowding the chart.

We compare data representations for forecasting **advertised GPU rental offers**, then ask whether a Tinker-trained experiment-selection policy outperforms starting, fixed and random search under the same six-trial budget. The numerical forecasts and scores come from deterministic tools and the Pacific starter kit. The language model selects experiments; it does not invent prices or scores.

## Measured result

The main result is negative: supervised fine-tuning did not improve experiment selection over the starting model on this small frozen evaluation.

| Frozen policy / procedure | Pooled pinball ↓ | Skill against last value |
| --- | ---: | ---: |
| Fixed search | 0.01733246 | 15.998% |
| Starting Qwen3.5-4B policy | 0.01735406 | 15.893% |
| Frozen SFT epoch 1 | 0.01781945 | 13.638% |
| Random search, seed 42 | 0.01891276 | 8.339% |

SFT was **2.68% worse than the starting policy**. Five random seeds are retained, including one that ties SFT. These are five dependent rolling origins and **30 scored series × horizon cells**, not 30 independent experiments. The exploratory moving-block interval for trained minus starting mean-origin loss is [0, 0.00139616]; its tiny temporal sample does not support a generalization guarantee.

The final dates were September 27 and October 4, 11, 18, 25. We committed [the selection freeze](configs/release-freeze.json) before opening their numerical results. Later rolling decisions can use matured earlier outcomes, with weights and the procedure frozen. No additional training occurs in the final job. All unsuccessful checkpoints and failed engineering pilots remain in Actions.

## Representation findings

Across the same five frozen dates, the best individual candidate was level-target Ridge with fixed-basket features, 56 days and alpha 1 (0.01722556 pinball). Across matched settings, target-only features had lower mean configuration loss (0.01914378) than fixed-basket (0.01976813) or raw composition (0.02122474). This descriptive comparison does not establish a universal normalization benefit. It was aggregated after final opening and does not change the official submission. [All 28 methods and factor marginals](docs/representation-findings.md) are retained.

## What was built

- A browser observatory with forecast quantiles, all candidate scores, saved-checkpoint comparisons, actual policy trace replays and cross-agent provenance.
- **24 Ridge configurations**: level/log target, target-only/raw-composition/fixed-basket features, 28/56-day window, alpha 1/100. Official targets remain unchanged. Chronological residuals estimate quantiles; preprocessing is fit on past data only.
- A genuine Tinker LoRA run on **Qwen/Qwen3.5-4B**: rank 16, learning rate 1e-4, five saved checkpoints, **50 optimizer updates**, 160 training prefix examples, 320 datums, 1,600 datum presentations. Five training and six development dates. Training examples do not multiply independent temporal coverage.
- An equal-budget search protocol: two common initial experiments plus four additional choices. A bounded hierarchy chooses family and then parameters. Starting and trained policies receive the same observations, candidate space and budget. Fixed search and five random seeds use the same numerical results. The numerical grid is precomputed on Modal; the six-trial budget counts result reveals, not equal wall-clock or dollar expenditure.
- An Exa → scientist → skeptic → next-decision demonstration using **past.dev**. Three roles actually write and read; required source IDs are checked in real recall results. Cached experiment reveals are labeled as such. This current-methods loop is separate from benchmark observations; no memory performance gain is claimed.
- An official November 6 submission with **111 rows across 37 headline series**, 1/3/7-day horizons, q10/q50/q90. Full-catalog development selection chose the unmodified official **last_value_empirical** method. Export schema, positivity, quantile ordering and full coverage passed. The exporter never loads November 7–13 competition truth.
- A separate 2–3-year rental and resale scenario note. Assumptions are explicit; scenario ranges are not calibrated confidence intervals, and resale has no observed dollar-price anchor.

An earlier 15-update Tinker integration warmup is retained separately. It is not the main study. This project uses **supervised fine-tuning, not reinforcement learning**.

## What the data measures

Pacific Machines (2026), **gpu-price-pack v0.1.1-handover**. Archive SHA-256:

~~~text
f0b52af28c52545732208bcc4905facd9b941aa5779da683e1d9884c283b7c7c
~~~

The pack contains about 3.78 million advertised offer rows. Those are neither executed transaction prices nor proof of capacity availability. Physical GPU resale is a separate scenario analysis.

The policy/representation experiment uses the eligible **afhubbard headline daily-statistics H100/A100 target subset**. Eligibility is narrow: only 19 of 26 attempted development origins qualify, and only one or two series may exist at a given origin. The actual final policy evaluation contains **A100 40GB and A100 SXM 80GB only**; no H100 series is eligible in that final subset. It therefore does not establish H100 policy performance. The separate complete-catalog official export includes the required H100/A100 targets. The observatory displays actual GPU metadata per origin. The complete official headline catalog is used separately for the competition CSV. Do not generalize this subset to every GPU or provider.

The canonical history and scorer remain official. Every historical origin has its own cutoff; labels must mature before they are exposed. No random row split or current-news price feature is used. Weekly index windows with ambiguous availability are excluded. Missing raw composition values and coverage are explicit. The provider/SKU/region/GPU identity proxy does not prove perfect hardware normalization. The AWS archive gap is not interpolated.

This is a **retrospective frozen data vintage**, published after the November 6 origin. It does not prove that each historical value or revision was accessible in real time. Masking dates and SKUs reduces obvious model knowledge shortcuts but cannot eliminate pretrained knowledge contamination.

Provider/configuration normalization is established practice. We credit [Silicon Data](https://www.silicondata.com/products/silicon-index) and [SemiAnalysis](https://semianalysis.com/gpu-pricing-index/). Our contribution is an inspectable empirical evaluation on this pack; we do not claim to have invented normalization or established the first forecasting benchmark.

## Reproduce remotely

All project code is on **compute-observatory**. Do not use or modify metagame. This project was developed directly through GitHub; no workstation checkout is required.

1. Supply authorized access to the official Pacific starter/data archive. The remote pipeline verifies the archive and all 672 manifest entries before using it. The pack stays in a private Modal Volume.
2. Configure GitHub Actions secrets: MODAL_TOKEN_ID, MODAL_TOKEN_SECRET and TINKER_API_KEY. The separate evidence workflow also requires EXA_API_KEY and PAST_API_KEY. Never commit their values.
3. In Actions, run **Reproduce verified Compute Forecast experiments** on compute-observatory. The default reproduces the starter integration and two-date representation smoke. Enable **full_grid** for all registered training/development origins and **train_policy** for the genuine five-checkpoint SFT experiment.
4. The single entrypoint inside the hosted runner is:

~~~bash
python -m compute_forecast reproduce --full-grid --train-policy
~~~

It fails closed outside the authorized GitHub Actions branch. Training requires usable Tinker access and actual account quota. Existing credits do not remove service rate limits. Stochastic service behavior can change exact trained checkpoints; saved run artifacts preserve the reported run.

5. Selection and final evaluation are separate: **Prepare measured release freeze** creates a reviewable configuration from completed development artifacts; commit it before **Evaluate frozen policy and export submission**. Reproducing the existing frozen final requires access to its saved Tinker sampler checkpoint. Independent users can retrain and create their own separately identified freeze. Do not tune using the reported final period and continue calling it untouched.
6. **Publish frozen research release** validates the exact successful source runs, projects an allowlisted public payload, publishes derived files, deploys on Modal and verifies the public content hashes. Public web containers have no raw-data mount or account API credentials.

The end-to-end remote entrypoint [passed](https://github.com/howdymary/compute-forecasting/actions/runs/43647264275). All 64 Python contract and numerical tests passed in the pricing release validation. Compilation, browser-script syntax, forecast file hashing and public-health checks are captured by Actions. Resolved client versions and per-call timings are retained with each run.

## Execution receipts

| Artifact | Actual remote run |
| --- | --- |
| Archive / starter / deliberate future-history refusal | [43637893251](https://github.com/howdymary/compute-forecasting/actions/runs/43637893251) |
| 26-origin representation grid | [43644639332](https://github.com/howdymary/compute-forecasting/actions/runs/43644639332) |
| Main 50-update Tinker training | [43648086958](https://github.com/howdymary/compute-forecasting/actions/runs/43648086958) |
| Full-headline development method selection | [43646617180](https://github.com/howdymary/compute-forecasting/actions/runs/43646617180) |
| Exa / past.dev / scientist / skeptic | [43649141181](https://github.com/howdymary/compute-forecasting/actions/runs/43649141181) |
| Freeze producer | [43652218020](https://github.com/howdymary/compute-forecasting/actions/runs/43652218020) |
| Frozen evaluation and 111-row export | [43653016797](https://github.com/howdymary/compute-forecasting/actions/runs/43653016797) |

Grid execution took 10m13s, main training 18m13s and frozen evaluation plus export 8m25s end to end in their reported workflows. These include client and setup overhead, not pure accelerator time. Actual billed Tinker/Modal costs are **unavailable**; no invented dollar amounts are reported. Exa returns request cost where available. Rate-limit failures and their targeted retries remain visible.

## Files and architecture

- src/compute_forecast/starter_probe.py: official archive verification and starter execution on Modal.
- representation_study.py: seeded, bounded chronological numerical experiments.
- search_policy.py: demonstrations, Tinker SFT, equal-budget development comparisons.
- freeze_contract.py / final_evaluation.py: frozen access guard and final evaluation, with no training.
- export_submission.py: official forecast CSV and separate long-term scenarios.
- research_loop.py: current-methods Exa and cross-agent past.dev integration.
- release_payload.py / release_web.py: allowlisted research results and the credential-free public service.
- pricing_contract.py / pricing_publish.py / explore_ui.py: verified chart data, scenario calculations and the pricing-first interface. The earlier release_ui.py remains as the prior interface source.
- configs/release-freeze.json: actual checkpoint and numerical source hashes selected before final results.
- docs/: research protocol, scope amendments and demo / sponsor evidence notes.

The captioned silent [two-minute demo](https://howdymary--compute-forecast-observatory-web.us-east.modal.run/files/demo.mp4) records actual public results and saved policy traces. [Desktop/mobile browser validation and the video publication receipt](https://github.com/howdymary/compute-forecasting/actions/runs/43656275785) passed with zero page errors or failed public requests. The event requires uploading the reviewed video to YouTube, Drive or Loom; generating this MP4 does not submit the entry.

The public UI is plain HTML/CSS/JavaScript and SVG. FastAPI serves it on Modal. JSON artifacts and two Volumes provide sufficient storage; there is no database or agent framework. Model inference, deterministic experiment execution and UI replay are distinct components. Replay animates actual saved traces and is labeled as recorded.

## Attribution and data restrictions

The pack describes compilation licensing as **CC BY 4.0, owner's default pending confirmation**, with upstream terms and unresolved owner decisions. We do not represent that as an unconditional redistribution permission. Raw pack files and third-party source excerpts stay outside this public repository. Preserve the pack's source and license metadata when reproducing through authorized access. EWLuda is not used.

Dependencies include Modal, Tinker and tinker-cookbook, NumPy, FastAPI/Starlette/Uvicorn, pytest and the official Pacific starter; their own licenses apply. Exa and past.dev are hosted services. No private development session is uploaded to Originator by this project.

[Live demo guide](docs/demo.md) · [Sponsor evidence and remaining event actions](docs/submission-and-prizes.md) · [Measured status](docs/measured-status.md)

## Public claim

**Compute Forecast is an auditable GPU rental forecasting experiment. We trained a small policy with Tinker to choose experiments, compared it with fixed and random search under equal budgets, and found no improvement over the starting policy on five frozen rolling dates. Every score and decision has a reproducible trail.**
