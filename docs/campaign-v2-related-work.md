# Related work and contribution boundary

Reviewed November 15, 2026 UTC during the hackathon. This is a targeted primary-source review, not an exhaustive systematic review. It is current methodological research: it does not add observations, rewards, teacher targets or new evidence packets to the frozen numerical/policy campaign.

The defensible contribution is an inspectable empirical study of advertised GPU rental offers and bounded experiment selection on a named frozen pack. It is not a new theory of GPU price normalization, a first GPU pricing dashboard, a new general research-agent architecture or proof of broad forecasting superiority.

## Closest precedents

| Area | Primary source and established contribution | Relationship to Compute Forecast |
| --- | --- | --- |
| GPU rental measurement | [Silicon Data's public index description](https://www.silicondata.com/products/silicon-index) describes standardized GPU-hour rates, adjustments for contract/hardware composition and provider-level aggregation. Its catalog also advertises predictive, forward-curve and residual-value products. | Pricing normalization and future-pricing products already exist. Our representation comparison keeps official targets fixed and measures specific empirical effects; it does not reproduce or outperform Silicon Data's proprietary index methodology. |
| GPU pricing observatories | [SemiAnalysis GPU Pricing Index](https://semianalysis.com/gpu-pricing-index/) is an existing index/interface with linked pricing APIs. | A polished pricing interface is useful product work, not a research novelty claim. No common-data accuracy comparison with its commercial products was performed. |
| Provider updates and index forecasting | [Synoptic, November 9, 2026](https://www.synoptic.com/blog/compute-futures-gpu-prices) describes provider updates as inputs customers can use to anticipate subsequent GPU-index readings. | The broader idea of forecasting GPU benchmarks from provider information is already publicly discussed. This vendor description is not an independently verified forecast-accuracy result. Its page postdates our November 6 benchmark origin and remains outside benchmark inputs. |
| Cloud spot-price forecasting | [Hidden Markov Model Based Spot Price Prediction for Cloud Computing](https://ieeexplore.ieee.org/abstract/document/8367382/) (2017 conference; indexed 2018) models older spot-price traces and compares with autoregression. | Cloud rental-price forecasting predates this project. Its auction-based framing and short-horizon VM setting is not a matched H100/A100 daily-rate benchmark; its reported scores cannot be compared with ours. The current [AWS documentation](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances.html) describes gradual EC2 price adjustment based on long-term supply/demand, illustrating why pricing regime and contract definitions matter. |
| Learned next-experiment policies | [MetaBO / Meta-Learning Acquisition Functions](https://arxiv.org/abs/1904.02642) (2019 preprint; ICLR 2020) uses RL to learn acquisition behavior from related optimization tasks within a GP-based loop. | Learning which experiment to evaluate next is established. Our small-model categorical policy, six-result budget and GPU-rate objective constitute a specific empirical setup, not a new acquisition-learning principle. |
| Learned optimization and reward design | [End-to-End Meta-Bayesian Optimisation with Transformer Neural Processes](https://arxiv.org/abs/2305.15930) (2023) studies joint learned optimization and sparse learning signals. [MetaDistill](https://proceedings.mlr.press/v306/han26x.html) (ICML 2026) uses expert optimization trajectories for pretrained optimizer behavior. | Demonstrations, learned search and RL refinement have prior art. Our reward-variation gates and teacher-alignment checks address validity in this particular environment; we did not reproduce these algorithms or establish superiority over them. |
| ML engineering agents | [MLE-bench](https://arxiv.org/abs/2410.07095) (2024) evaluates agents across 75 ML engineering competitions. Its [official repository](https://github.com/openai/mle-bench) provides evaluation/resource guidance and recommends repeated seeds. | Our bounded configuration selection is much narrower than end-to-end model engineering. Three training seeds measure stochastic variation on the same dates, not independent market evidence. Results are not comparable to MLE-bench medal rates. |
| Research agents as search policies | [AI Research Agents for Machine Learning](https://arxiv.org/abs/2507.02554) (2025) explicitly studies how search policies and operators interact in MLE-bench. | An evidence/experiment/criticism loop is not itself novel. Our contribution must come from the concrete measurement, controls, actual tool execution and inspectable outcomes. |
| Method discovery versus tuning | [MLS-Bench](https://arxiv.org/abs/2605.08678) (2026) evaluates whether improvements transfer across controlled settings and scales, distinguishing engineering-style tuning from generalizable method discovery. | Selecting from 42 established configurations does not establish invention of a new forecasting method or general research ability. Our three dependent evaluation dates cannot support that claim. |
| Prospective evaluation | [ForecastBench](https://arxiv.org/abs/2409.19839) (2024/ICLR 2025) and its [current methodology](https://www.forecastbench.org/about/) use questions that resolve after forecasting and an automated resolution process. | Reused historical dates must remain labeled retrospective. Our prospective hash is a commitment to future scoring, not an already measured result; its stale inputs and outcomes beyond the event remain explicit. ForecastBench's binary/Brier methodology is not substituted for Pacific's quantile/pinball scorer. |

The commercial-source statements above describe what their own public materials say. They do not verify market coverage, proprietary algorithms, execution availability or comparative forecasting performance. We do not redistribute their PDFs, restricted excerpts or raw data.

## What this project adds

1. **A reproducible measurement path for this pack.** Contract identity, units, history eligibility, label maturity, imputation and fallbacks are made visible before interpreting scores. Millions of offer rows do not become millions of independent forecast cases.
2. **A controlled selector study.** Starting weights, hard/soft SFT, incremental RL, random search, two specified GP encodings and training-selected static controls share the candidate pool, eligible cases and online result-reveal budget. Offline training costs still differ.
3. **Mechanistic checks on an apparent improvement.** Feedback hiding, fixed evidence/critic additions, teacher-to-future alignment and a matched price-value ablation help distinguish a better prior over methods from the incremental use of results. Negative results remain first-class artifacts.
4. **An operational trace with real execution.** Exa evidence, authored cross-role records, fresh Modal backtests and subsequent choices are recorded separately from cached training feedback. Changed choices and completed weight updates are not automatically labeled useful scientific adaptation.
5. **A public artifact trail with honest access limits.** Source and derived traces are inspectable; numerical replication requires authorized raw-pack access, and private model resources remain in the owner's account. This is not a claim that every underlying input is freely redistributable.

These are empirical and engineering contributions. Whether they warrant a research publication depends on stronger independent evaluation and what the completed results show, not on sponsor spending or interface polish.

## Claims we do not make

- First GPU rental forecast, first normalized price index or first agentic research workflow.
- Superiority over commercial index forecasts, MetaBO, broader AutoML systems or published agent leaderboards without matched replication.
- H100 policy performance from the A100-only selector cases.
- General research intelligence or a causal accuracy gain from Exa, memory or criticism.
- An untouched test from dates already inspected in v1, or measured prospective accuracy before outcomes mature.
- A learned or probabilistic long-term pricing model when the displayed paths are explicit compounded assumptions.

## Next evidence that would change the claim

The strongest next test is a precommitted prospective evaluation after the November 16/18/22 outcomes mature, followed by broader independent periods and eligible provider/GPU contracts. Keep inputs vintage-correct, compare the same cells and budgets, preserve unsuccessful trials and report uncertainty at the temporal/provider level. More optimization updates on nine correlated training tasks cannot substitute for this evidence.

The present [measured findings](campaign-v2-findings.md), [protocol](../configs/campaign-v2.json) and [remote artifact index](campaign-v2-reproduction.md) define what was actually tested.
