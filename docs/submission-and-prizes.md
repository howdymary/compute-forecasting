# Submission and sponsor evidence

Verified against the signed-in [event Resources page](https://iterate.inc/ai-research?tab=resources) on November 14, 2026. The schedule says Sunday 14:00 PT and another submission section says 14:30. We use **November 15, 14:00 PT (22:00 UTC)** as the conservative deadline. Teams must be on the event platform by Sunday noon; team registration is a separate user action.

## Evidence matrix

| Entry | Requirement | Actual artifact / status |
| --- | --- | --- |
| Pacific / Track 2 | H100/A100 rental targets, 1/3/7 days, q10/q50/q90, official scorer | [Final run and 111-row export](https://github.com/howdymary/compute-forecasting/actions/runs/43653016797): all 37 official headline series. Future competition truth not loaded. |
| Pacific | Reproducible entrypoint and findings | [Passing remote reproduction](https://github.com/howdymary/compute-forecasting/actions/runs/43647264275); README; configs/release-freeze.json. Main policy result is negative and preserved. |
| Pacific | Separate 2–3-year rental and resale outlook | outlook.md and outlook-scenarios.json in the submission artifact. Assumption-based normalized indices, not calibrated probabilities; no resale-dollar anchor. |
| Tinker / overall research | Genuine supported-model training | [50-update, five-checkpoint Qwen3.5-4B LoRA SFT run](https://github.com/howdymary/compute-forecasting/actions/runs/43648086958); training examples, client versions and saved checkpoints. This is SFT, not RL. The resources page does not list a separate Tinker challenge with additional eligibility rules. |
| Exa | At least one Exa API call inside the main research loop; show sources and how used; repo points to call site | research_loop.py calls Exa, writes dated evidence to past.dev, and the scientist uses recalled evidence for configuration selection. [Actual run](https://github.com/howdymary/compute-forecasting/actions/runs/43649141181); Evidence view shows sources and decisions. This bounded current-methods loop is separate from historical benchmarking. Exa centrality is for sponsor judges to assess; the numerical forecaster itself does not search the web. |
| past.dev | More than one agent writes and reads; another agent's record is actually used | Same actual run: evidence_researcher, forecast_scientist and skeptic each write/read. Required source IDs must appear in actual recall responses; decision events carry used_memory_source_ids. Memory gain is not claimed or required. |
| Modal | Substantive training, inference or parallel experiments | [26-origin numerical grid](https://github.com/howdymary/compute-forecasting/actions/runs/43644639332), parallel final folds and public ASGI deployment. Run/call timings are preserved. Billed cost is unavailable, not estimated. |
| Originator | Work directly on hackwithori.com or upload development sessions for agent review / pre-scoring | **Not completed.** No private session has been uploaded. The event page confirms one of these development/session routes is needed; repository source alone does not establish this requirement. Exact upload format and review acceptance remain unverified. Any session upload needs separately authorized content and destination. |
| Overall | Public repository, working demo, honest results, research rigor, interpretation and reproducibility | compute-observatory branch, live observatory, frozen provenance, held-out results, failed pilots and limitations. Sponsor integration does not guarantee a prize. |

## Where memory lives

past.dev stores the shared, authored current-methods records and recalled source provenance. GitHub/Modal JSON artifacts store numerical results, run manifests and evaluation traces. Markdown stores documentation. The historical forecasting policy reads matured numerical observations, not current-methods memory or web excerpts. There is no measured memory-ablation gain.

The research loop reveals **previously completed, hash-verified** training-period experiments. Its cache_hit flag is true and new_numerical_execution is false. Numerical grid execution on Modal is real and separately inspectable. Do not describe a cached reveal as a new backtest.

## Submission package

The event asks for one track plus chosen challenges, repository link, short project description and a **two-minute video on YouTube, Drive or Loom**. A generated MP4 or Modal URL is a delivery artifact, not proof of satisfying that hosting requirement. Upload the reviewed public demo video to one of those destinations before submitting the form. No event submission or private session upload is performed automatically.

Select Track 2 / Pacific and, where supported by the form, Exa, past.dev and Modal. Originator remains pending until its development/session requirement is actually satisfied.

Short description:

> Compute Forecast is an auditable GPU rental forecasting experiment. We compare 24 data/model configurations, train a small Tinker policy to select experiments, and evaluate it against fixed and random search under the same six-trial reveal budget. The frozen SFT policy did not outperform the starting model on five rolling dates. Our observatory exposes every score, actual decision replay, Exa source and cross-agent past.dev record, alongside a complete official forecast export.

## Judge questions

**Did training help?** Not against the starting policy here: final pinball is 0.01781945 versus 0.01735406, about 2.68% worse. Fixed search is 0.01733246. We retained all checkpoints and random seeds.

**Is this millions of independent examples?** No. There are millions of offer rows, but only five training, six development and five final temporal decision origins. Final evaluation contains 30 scored series/horizon cells and substantial dependence.

**Is the agent autonomously doing arbitrary research?** No. It chooses bounded configurations. Numerical tools score them deterministically; the current-methods loop separately uses evidence and criticism. All six-trial comparisons have equal information and reveal budgets, not equal billed cost.

**What is new?** An inspectable empirical evaluation and integration on the supplied pack. Normalization has prior art, including Silicon Data and SemiAnalysis. We do not claim to invent it or prove a forecasting breakthrough.

**Did you see the future?** The official export never loads competition future truth. Historical folds enforce matured labels. The source pack is nevertheless retrospective and frozen after the origin; real-time historical availability and pretrained knowledge cannot be fully established.
