# Direct GPU-price forecasting: diagnosis and publication plan

Prepared 16 November 2026 Pacific time. This is a post-event, post-hoc analysis of the frozen direct-evidence-v14 study. No new training, inference, market outcomes, checkpoint selection, or prospective protocol changes were performed.

## Research question and verdict

Why did LoRA fine-tuning improve training cross-entropy and the selected development score while worsening retrospective seven-day quantile pinball loss?

The numerical increase is real in the retained artifacts: six of six development-selected fine-tuned models lose to their corresponding untuned control on the same 22 seven-day cases. Mean loss rises from 0.0409712518122 to 0.0462887606778, a difference of 0.00531750886555 or 12.9786%. This is a small historical case study, not evidence that fine-tuning generally harms forecasting.

The strongest supported explanation is a change in the forecast distribution that transfers poorly across sources and market periods. Quantile offsets around the median account for 92.1074% of the increase under an exact two-factor loss decomposition. This identifies where the loss changed, not the causal reason that optimization changed those offsets. Training-distribution mismatch and a small, partly unstable development selection are plausible contributors. They have not been isolated experimentally.

Do not call this universal overconfidence: seven-day intervals widened in five of six runs. Do not attribute it to the older fixed-seed bug: v14 used distinct stochastic samples. No evidence establishes a future accuracy benefit from BLS, news, or infrastructure.

## Evidence inventory and integrity

Canonical source snapshot: a3aaaad76b3f972fa72659fed925e14784653528.
Frozen training source: bf4908f6626e8313f8b4b75a450213fb4cff8e0b.

- [Registered v14 protocol](../configs/direct-evidence-v14-final.json).
- [Frozen source report and retained samples](../results/evidence-v14/runs/43966729631-publication-43978179779/).
- [Source report](../results/evidence-v14/runs/43966729631-publication-43978179779/report.json), SHA-256 6eebe9964df27727d77c1fb46c99b8777bc41ad21d675518b66904fc9e1f5fcb.
- [Corrected resource audit](../results/evidence-v14/runs/43966729631-publication-43978179779/resource-profile.json).
- [Artifact-only diagnostic configuration](../configs/direct-v14-diagnosis-v16.json).
- [Versioned diagnostic results](../results/direct-v16/runs/43997050518/diagnosis.json), SHA-256 b5fab0887db0a4cce32c1a40202fa4af3778e4973f78638b316a8feb968eeeaf.
- [Diagnostic manifest](../results/direct-v16/runs/43997050518/manifest.json).
- [Remote reconstruction](https://github.com/howdymary/mochi-demo/actions/runs/43997050518).
- [Existing future-transfer protocol](evidence-future-v15.md).

The repository's supplied URL redirects to howdymary/mochi-demo. All new files are on compute-observatory. Official exports, existing studies, checkpoint identities, original selections, video, protected outcomes, and the November 23 gate are unchanged.

### What was trained

Qwen/Qwen3.5-4B, LoRA rank 16, learning rate 0.00005, batch 16, non-thinking renderer qwen3_5_disable_thinking, seeds 17/29/43, two arms: price-only and price+BLS. Each run completed 100 optimizer updates; 600 total. Checkpoints 0/20/50/100 were evaluated on development seven-day pinball; earliest update breaks exact ties. The original selections were 50/50/20 for price-only and 50/50/50 for BLS.

Inputs were source-specific daily posted-rental medians from Pacific's pack, with dates, exact hardware/instrument identity, gaps and current-price anchors. Outputs were three realized log-price changes, for 1/3/7 days. Sampled vectors were exponentiated and multiplied by the origin price; linear empirical quantiles were taken in dollar-price space. Quantiles in log space followed by exponentiation are not in general the same finite-sample linear-quantile calculation.

BLS features were an original-release electricity-distribution PPI level, month-over-month log change and release age. News and infrastructure features were excluded. This is price versus price+BLS, not a completed news-value experiment.

Training used 326 tasks, six series, 125 distinct origins, with labels matured by September 19. Development used 20 tasks on September 27 and October 4. Retrospective evaluation used 22 tasks on October 11/18/25, ten series, and 66 horizon cells per model. The seven-day primary endpoint contains 22 cases; repeating them across six runs produces 132 model-case observations, not 132 independent market experiments.

### Engineering checks

The existing verifier reconstitutes quantiles, scores, coverage, widths, matched cells, original checkpoint selection, baseline comparisons, model locks and sample hashes. The diagnostic additionally binds the private prepared dataset by hash, checks context dates and training label maturity, and reconstructs loss contributions.

The trainer's completion_tokens field is normalized loss-weight mass. The corrected audit gives 278,950 positive-weight token presentations and 13,129,439 full-sequence token presentations across the six runs; these are deterministic batch reconstructions, not provider billing receipts. Each run presented 1,600 examples. Within each seed, both input arms have identical task-order hashes. Training sequences range from 770 to 1,577 tokens for price-only and 869 to 1,676 for BLS, below the 6,144-token limit; supervised positions range from 23 to 44. There is no evidence of training-example truncation or one-token supervision.

Training and sampling use the same configured renderer. The training client pipelines forward_backward and optim_step in the order recommended by [official Tinker documentation](https://tinker-docs.thinkingmachines.ai/tinker/howto/concurrency_async/). Merely submitting the optimizer before awaiting the preceding future is not an update-order bug.

Original tokenizer and base-weight revisions were not captured. Reconstructing with a later tokenizer cannot establish byte-for-byte identity with the original tokenization. Full raw malformed outputs and per-token loss decompositions were not retained, so we cannot precisely divide the cross-entropy gain into syntax and numerical-token gains.

The price-only seed-43 process saved its completed 100-update result and uploaded its nine artifacts before exiting 134 in teardown. Its saved arithmetic verifies. This is an orchestration warning, not evidence of missing numerical updates; optimization must not be repeated to repair publication.

## Exact result and decomposition

All losses and contributions below have the official USD-per-GPU-hour pinball scale. Positive trained-minus-base values are worse.

| Condition | Seed | Selected update | Untuned | Selected SFT | Difference |
|---|---:|---:|---:|---:|---:|
| Price | 17 | 50 | 0.0404197012 | 0.0477927968 | +0.0073730956 |
| Price | 29 | 50 | 0.0409373831 | 0.0457100622 | +0.0047726791 |
| Price | 43 | 20 | 0.0416452982 | 0.0455410125 | +0.0038957142 |
| Price+BLS | 17 | 50 | 0.0410085122 | 0.0478923485 | +0.0068838363 |
| Price+BLS | 29 | 50 | 0.0425310699 | 0.0458036581 | +0.0032725882 |
| Price+BLS | 43 | 50 | 0.0392855463 | 0.0449926860 | +0.0057071397 |

Mean selected loss is 0.0463479572 for price-only and 0.0462295642 for BLS. BLS-minus-price is +0.0000995517, +0.0000935959 and -0.0005483265 by seed: two worse, one better. Its mean advantage is only 0.0001183930, approximately 0.255% of price-only loss. The corresponding untuned conditions also vary because inputs and stochastic samples differ. A BLS benefit is not established.

| Horizon | Mean untuned | Mean selected SFT | Difference | Base coverage | SFT coverage | Base width | SFT width |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 day | 0.0236319494 | 0.0255439903 | +0.0019120409 | 52.27% | 41.67% | 0.0289391 | 0.0009469 |
| 3 days | 0.0299860641 | 0.0335021968 | +0.0035161327 | 51.52% | 42.42% | 0.0449847 | 0.0229049 |
| 7 days | 0.0409712518 | 0.0462887607 | +0.0053175089 | 37.88% | 40.91% | 0.0694020 | 0.0999752 |

Coverage is measured against nominal 80% intervals, with inclusive endpoints and point masses. These dependent-case percentages do not establish population calibration.

Each partition below independently sums to +0.00531750886555. Partitions must not be added to each other.

| Partition | Group | Weighted contribution |
|---|---|---:|
| Quantile, after one-third scoring weight | q10 | +0.002452643125 |
| | q50 | +0.000188647536 |
| | q90 | +0.002676218204 |
| Collector | afhubbard | +0.001185437786 |
| | fastgpu_daily | +0.003970805147 |
| | gpurentalprices | +0.000161265932 |
| Origin | October 11 | +0.001635973271 |
| | October 18 | +0.002066150473 |
| | October 25 | +0.001615385121 |
| Outcome diagnostic | Unchanged price | +0.001354953242 |
| | Changed price | +0.003962555623 |
| GPU family | A100 | +0.004330737710 |
| | H100 | +0.000986771156 |
| Instrument | Hyperscaler spot | +0.004322234303 |
| | Neocloud rate card | +0.000995274563 |

The contribution formula is group cell count / total repeated cells times the group's mean loss difference. [Per-cell and every-series tables](../results/direct-v16/runs/43997050518/cell-contributions.csv) retain seed, condition, horizon, source, origin and all three quantile terms. No joint cells were inferred from marginal summaries. A relative-to-anchor loss diagnostic also remains positive (+0.0029423636); the official score is unchanged.

The tails supply 96.4523% of the score increase, but a median shift also changes tail scores. Therefore we separately exchange each forecast's median and its dollar offsets around that median, scoring all four combinations. All 132 seven-day counterfactuals remain positive and ordered. Exact symmetric two-factor attribution gives:
- Median location: +0.000419687485 (7.8926%).
- Quantile-offset shape: +0.004897821380 (92.1074%).

This is an accounting identity at the saved forecasts, not a causal attribution to an optimizer, data source or representation.

## Ranked explanations and competing evidence

| Rank | Explanation and confidence | Supporting evidence | Contradiction or unresolved alternative | Smallest discriminating test |
|---|---|---|---|---|
| 1 | Distribution/readout change: high confidence about location of harm, moderate about mechanism | 92.1% shape attribution; q10/q90 drive 96.5%; short-horizon zero-return concentration; poor coverage | Seven-day width rises in 5/6 and the zero atom does not uniformly increase; not universal mode collapse | Frozen median-preserving tail recalibration; no training |
| 2 | Source and return-regime mismatch: moderate | FastGPU has zero training tasks, 12/22 evaluation cases and 74.67% of deterioration; 5/22 outcomes fall outside observed training return range | Seen-source cases still worsen; FastGPU appears in development and one FastGPU series improves | Date-matched source-inclusion intervention on a later eligible cohort |
| 3 | Weak transfer of checkpoint selection: moderate | Only two development dates; 4/6 choices change under one-origin removal; selected development gains do not transfer; every update-100 development score is worse than update zero | Two runs select the same checkpoint after either origin removal; degradation is positive at each retrospective origin | Register multiple development-origin blocks and a later evaluation; original selections remain frozen |
| 4 | Objective/representation mismatch: plausible, unconfirmed | Training CE decreases strongly; invalid samples fall, but pinball worsens; decimal-token errors need not track numerical distance | Likelihood is a proper distribution objective under appropriate modeling; successful Chronos work uses CE; no held-out numeric-versus-syntax loss retained | Matched numeric-span versus full-assistant loss-mask experiment |
| 5 | Flat-price and overlapping-example imbalance: plausible contributor | 292/326 one-day labels are zero; adjacent context Jaccard medians exceed 0.95; only 42 H100 training examples | Seven-day training has 172 changed vectors; 296 distinct value histories; not all exact duplicates; seven-day unchanged cases supply only 25.5% of harm | Source/date-controlled learning task with natural event prevalence and explicit weights |
| 6 | Monte Carlo quantile noise: secondary, not excluded | 64-sample empirical quantiles; development selection varies under retained-vector resampling | All six conditional 2.5–97.5% bootstrap percentile intervals for deterioration remain positive | Small fixed repeat-inference subset, selected by metadata rather than error |
| 7 | Truncation, masks, parsing, orchestration: little support as primary explanation | Tokenizer revision and raw invalid-output limitations remain | Sequences below limit, positive-weight counts 23–44, invalid outputs decrease, no fallbacks, score reconstruction passes, completed results precede exit 134 | Archive exact token IDs/weights and add contract tests before a new run |
| 8 | Base-model contamination: unknown | Public historical targets and unknown pretraining cutoff | No evidence that these particular prices were in pretraining; cannot infer contamination from base accuracy | Outcomes observed after registration, with exact model revision and immutable inputs |

Training mean first-ten versus last-ten minibatch CE declines in all six runs, but these are different batches, not held-out likelihood comparisons. Numerical-versus-format learning and exact gradient causality remain unknown.

The untuned model is mostly persistence-like in its median (106/132 seven-day medians equal the anchor) but not an exact persistence distribution. Its mean pinball 0.0409713 beats last-value 0.0500909 on these cases. Selected SFT beats last-value by about 7.6% but loses to empirical-last-value/seasonal-naive at 0.0452824. Drift is 0.0464751. Numerical controls have wider intervals and 50% coverage; none is well calibrated on this tiny panel. These are matched descriptive numbers, not leaderboard claims.

## Uncertainty and effective evidence

Training seeds, sampling requests and market outcomes are different uncertainty sources. The six runs reuse the same 22 target cases and three market origins. Within each input condition, the untuned weights are shared across the three seed-labelled runs; their differing baseline scores arise from separate stochastic inference draws. Consequently, variation between seed-labelled contrasts cannot be attributed entirely to training-seed variability. No market-level significance claim is justified.

The v16 conditional bootstrap resamples each retained vector pool 1,000 times with fixed outcomes. All six deterioration percentile ranges are positive, approximately:
- Price 17: [0.004837, 0.010092].
- Price 29: [0.002100, 0.008030].
- Price 43: [0.001728, 0.006794].
- BLS 17: [0.004384, 0.009825].
- BLS 29: [0.000953, 0.007027].
- BLS 43: [0.002866, 0.009029].

These are conditional Monte Carlo diagnostics, not confidence intervals for future markets. They cannot reveal modes absent from saved vectors or establish independence of unseeded requests. Leaving each market origin out keeps the mean difference positive, between 0.005062 and 0.005961; three dependent dates still provide little external validity.

Four development checkpoint selections change under omission of one of two dates. Conditional retained-vector selection frequencies for the originally selected checkpoint range from 47.5% to 98.2%. These are post-hoc sensitivity checks, never revised selections.

## Three follow-up experiments, proposed and not launched

### 1. Frozen readout and sampling audit — run next

Hypothesis: much of the deterioration is a repairable error in quantile offsets rather than a loss of central forecasting information.

Intervention: preserve each saved forecast median and rescale its lower/upper log-price offsets. Register the nine pairs of multipliers from {0.5, 1, 2} × {0.5, 1, 2}, including the identity control. Apply the same fitting procedure and search budget to untuned and SFT models; do not repair only SFT. Positivity and quantile ordering follow from scaling ordered log offsets around a positive median. Keep all original forecasts and metrics.

Reuse direct_forecast_v12.py, verify_evidence_v14.py, retained development/evaluation JSON and the v16 counterfactual tables. Proposed new module: scripts/evaluate_tail_readout_v17.py; proposed config: configs/direct-tail-readout-v17.json. These filenames are proposals and are not implemented by this diagnosis.

Budgets: zero optimizer updates; zero inference requests for the first stage; at most nine candidates per frozen model. Select only on the original 20 development cases using seven-day pinball, with identity preferred on ties. Report leave-one-development-origin sensitivity. Evaluate exactly the existing 22 seven-day cases once as an additional post-hoc diagnostic, never an untouched test.

A prespecified optional inference validation can use one case per series, earliest eligible origin, ten cases; seed 17 only, both input arms and both base/selected weights, four fresh requests of 64 vectors per model-case at the unchanged temperature 0.8: 10,240 vectors maximum, four-hour timeout, concurrency four. Retain every request, no outcome-based resampling or favorable-repeat stopping. This optional stage estimates request variability, not market uncertainty.

Report pinball, paired loss differences, median error, coverage, width, source/origin splits, invalid samples and conditional variability. A useful descriptive success is recovery of at least half the original SFT-minus-base gap with positive recovery in at least two of three origins; report the full result even if this criterion fails. Do not expand the multiplier grid after viewing evaluation.

A positive result would establish that a small readout change repairs part of this historical loss, not why SFT learned the wrong distribution. A negative result would rule out this bounded repair and favor more substantial data/objective changes. Freeze any future challenger before later compatible aggregate outcomes arrive. Do not alter the existing future contract-transfer comparison.

### 2. Numerical supervision versus format supervision

Hypothesis: full-assistant CE uses substantial supervision to learn formatting and common output tokens without improving numerical distribution quality.

Run a new matched pair on price-only inputs: original last-assistant-token mask versus a verified numeric-span mask. Keep examples, order, base revision, renderer, rank, LR, batch, update count and sampling budget equal. Normalize each example's nonzero weights to the same mass. Supervise only tokens overlapping audited numeric-value spans in the intervention; reject ambiguous offset mapping rather than silently masking wrong text. Full JSON generation and parsing remain required at inference; syntax failures count using the same fallback.

Reuse train_evidence_v14.py and profile_evidence_v14.py contracts but use a new versioned trainer and study ID. Pin actual current weight/tokenizer revisions for both arms; because the original revisions are missing, this is a new matched replication, not a bitwise recreation.

Budget: three seeds, two masks, maximum 100 updates each (600 new updates only in a later authorized task); checkpoints 0/20/50/100. At most 64 vectors per task/checkpoint and the same 20 development/22 retrospective tasks. Do not launch this experiment until span fixtures, exact token/weight archives and immutable configs pass. Twelve-hour campaign cap and no automatic extension.

Selection remains development-only with checkpoint zero eligible. The primary contrast is mask effect on seven-day pinball, accompanied by held-out full-output and numeric-token CE, validity, median error and interval diagnostics. Existing October dates are descriptive only. An accuracy claim needs a newly registered later cohort.

Success requires improvement across at least two seeds without hiding increased invalid outputs, followed by a later compatible test; otherwise publish the negative mask result. This tests supervision allocation. It does not by itself establish that CE is unsuitable, that a distance-based objective is better, or that numeric JSON is differentiable with respect to pinball.

### 3. Source-coverage and temporal-transfer intervention

Hypothesis: including eligible target-source histories improves transfer relative to the original collector-skewed training mixture.

Use later training origins where every included source genuinely has adequate past context and all labels have matured. Match total example count, origin strata, optimization budget and metadata. Compare an original-style source mixture with a preregistered source-balanced mixture that includes FastGPU. Keep natural changed/unchanged frequencies within the selected source/time strata; do not oversample price changes without explicitly changing and correcting the training distribution.

The initial target is still exact collector medians, not the four individual-provider contracts. The original September cutoff cannot be repaired with later FastGPU rows. If continuing compatible collector medians are unavailable, complete registration and capture validation and leave this intervention pending. An individual-contract cohort is a separate transfer study.

Reuse source-vintage capture, evidence_v14.py, the prospective commitment/evaluator patterns and exact starter-kit baselines. Preserve every existing panel and the November 23 gate; create a separate challenger registration.

Budget: price-only initially, two data mixtures × three seeds × at most 100 updates; at most 326 examples per arm if enough naturally eligible examples exist. Fix the final number before execution. Use at least four non-overlapping development-origin blocks when data permits, then eight weekly future origins with locked analyses only after the last seven-day outcome matures. This is a duration commitment, not a power guarantee. Register missingness/stopping rules and do not extend because results are unfavorable.

At most seven LM states (shared base plus six fitted models), ten eligible series, eight origins and 64 vectors: 35,840 prospective vectors; deterministic numerical controls do not use that inference budget. Prespecify dollar pinball as primary and per-source/anchor-normalized diagnostics as secondary. Report origin-block paired differences and correlated-series dependence. Unknown provider charges remain unknown.

Success is a reproducible paired gain on subsequent compatible observations; an inconclusive eight-origin result remains inconclusive. A negative result would show that this bounded source-inclusion intervention is insufficient, rather than proving that more data never helps. Do not conflate source inclusion with a BLS benefit.

## Primary-source positioning

No published scores below are compared numerically with this GPU cohort.

| Work and status | Target, data and evaluation | Relevant result or limitation | What to adopt; what differs here |
|---|---|---|---|
| [Gruver et al., LLMTime](https://arxiv.org/html/2310.07820), NeurIPS 2023 | Numerical-string extrapolation on varied time-series datasets, zero-shot probabilistic forecasts | Tokenization, scaling and predictive density matter; an LLM's large size alone is insufficient | Explicit numeric-representation and probability/readout checks. Our small LoRA GPU study has different targets and metric aggregation |
| [Ansari et al., Chronos](https://arxiv.org/html/2403.07815), TMLR 2024 | Scaled, quantized time-series vocabulary; CE training and sampling across 42 datasets | Fine-tuning can improve aggregate forecasting; it is not inherently harmful and CE is not inherently invalid | Strong numerical/foundation-model controls and exact sampling protocol. Chronos is trained for time series, unlike our post-trained language model |
| [Tan et al.](https://proceedings.neurips.cc/paper_files/paper/2024/hash/6ed5bf446f59e2c6646d23058c86424b-Abstract-Conference.html), NeurIPS 2024 | Ablations of three LLM-based forecasting architectures | Removing/replacing the LLM often matches or improves those systems | Attribute gains to tested mechanisms; do not assume the LLM is necessary. Their architectures differ from direct JSON return sampling |
| [Chernov](https://arxiv.org/html/2409.15367), NeurIPS 2024 time-series workshop | Chronos-Small fine-tuning on 22 zero-shot datasets, Wasserstein versus CE | Better point estimates can accompany worse aggregate probabilistic scores | Report medians and distribution scores separately; do not import a point-focused loss as a guaranteed calibration fix |
| [Gneiting & Raftery](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf), JASA 2007 | Proper-scoring-rule theory | Distribution quality requires suitable scoring; sharpness and calibration differ | Preserve pinball as the primary endpoint and report coverage with width. This theory does not prove our finite SFT run should improve |
| [Aksu et al., GIFT-Eval](https://arxiv.org/html/2410.10393), NeurIPS 2024 time-series workshop | Diverse benchmark; explicitly separated pretraining data and non-overlapping rolling test windows | Fair splits and contamination control are material to foundation-model comparisons | Separate pretraining uncertainty, development selection and later outcomes. Our three reused dates are much weaker evidence |
| [Thinking Machines direct forecasting example](https://thinkingmachines.ai/news/inkling-2-small/), official vendor demonstration, 5 November 2026 | Tinker/Qwen3.5-4B forecasts on non-GPU time-series tasks; SFT and separate RL trials | Sampling details materially changed the apparent score; an RL attempt worsened results | Recheck sampling and keep SFT/RL effects distinct. Vendor-internal results are not an independent GPU-price validation |

Workshop publication status is verified on the [official accepted-paper list](https://tsalm-workshop.github.io/neurips-2024/accepted-papers/). The Qwen [official model card](https://huggingface.co/Qwen/Qwen3.5-4B) identifies post-trained weights; it does not establish that GPU-price outcomes were excluded from training. Current papers inform diagnosis, not historical forecast inputs.

## Publication package

### Defensible contribution

An auditable negative case study of direct language-model GPU-rental forecasting, comparing six matched LoRA runs and reconstructing how distribution changes, source coverage and development selection relate to deterioration. It releases retained forecast arithmetic and exact accounting, without claiming a confirmed universal cause or future accuracy.

### Restrained title options

1. When Fine-Tuning Worsens GPU Rental-Price Forecasts
2. A Reproducible Negative Result in Direct Language-Model Forecasting
3. Forecast Medians Were Not the Main Problem: Diagnosing a Small GPU-Price Study

### Draft abstract

We study direct GPU rental-price forecasting with a post-trained Qwen3.5-4B model fine-tuned using LoRA. Six matched runs compare price history with price history plus original-vintage electricity-distribution PPI features. Checkpoints are selected on two development origins and evaluated retrospectively on 22 seven-day cases spanning ten A100/H100 series and three reused, dependent origins. Every selected fine-tuned model has higher quantile pinball loss than its untuned control; the mean increase is 13.0%. Reconstruction from retained samples attributes 96.5% of the score increase to the lower and upper quantile terms. An exact median/offset counterfactual attributes 92.1% to quantile-offset changes. Collector coverage differs substantially between training and evaluation, and four checkpoint choices change when one development origin is removed. These diagnostics locate failure but do not identify its causal training mechanism. The small, mixed PPI contrast and historical evaluation establish neither a supplementary-evidence benefit nor prospective accuracy. We provide auditable artifacts and prespecified follow-up tests.

### Results and limitations outline

1. Exact advertised-price targets, source population and instrument distinctions.
2. Registered direct-training and sampling protocol; separate the earlier selector study.
3. Six paired losses and strong numerical references.
4. Quantile and median/shape decomposition.
5. Source/time composition and observed return shifts.
6. Development selection and conditional sampling sensitivity.
7. BLS contrast with seed-specific results.
8. Failure accounting, token audit and completed-run teardown warning.
9. Limits: three reused origins, correlated series, stochastic inference, unknown original tokenizer/weights revision and pretraining contamination.
10. Proposed future tests, without outcomes or positive-result promises.

### Figures and tables

| Figure/table | Question | Exact artifact |
|---|---|---|
| [Paired loss](../results/direct-v16/runs/43997050518/paired-loss.png) | Does every selected run lose to its corresponding base? | diagnosis.json runs/by_horizon/7; public v14 evaluations |
| [Loss contributions](../results/direct-v16/runs/43997050518/loss-contributions.png) | Which collector and quantile account for the increase? | cell-contributions.csv and contribution-source.csv |
| [Source mixture](../results/direct-v16/runs/43997050518/source-mixture.png) | Does training represent evaluation collectors? | diagnosis.json composition; hash-bound private prepared dataset |
| [Sample distributions](../results/direct-v16/runs/43997050518/sample-distributions.png) | How did return distributions change in two illustrative cases? | Retained seed-17 price-only vectors; largest/lowest loss-difference cases selected post-hoc, explicitly nonrepresentative |
| Median/shape table | Are tails merely moving with the median? | location-shape-counterfactuals.csv; four score combinations, no new model output |
| Development sensitivity table | Is checkpoint choice stable? | diagnosis.json development_selection and retained development-0/20/50/100.json |
| Matched control table | Is the model competitive with simple numerical controls? | diagnosis.json native_references, exact matched cells and starter-kit implementation |
| Cohort/return table | What distribution changed across phases? | diagnosis.json target_returns, target_returns_by_source and composition |

All four PNGs were inspected at rendered resolution. No videos were created. The ECDFs have unmodified data and full sample support; their post-hoc selection must accompany any public reuse. Do not use them as a representative-case claim.

### Claims

Retain:
- Direct forecasting weights were actually optimized through Tinker.
- All six selected models worsened seven-day loss on the retained retrospective cohort.
- The major measured deterioration lies in quantile offsets.
- This study makes unsuccessful runs and arithmetic inspectable.

Narrow:
- “Fine-tuning hurts” to this model, dataset, training and sampling protocol.
- “BLS helps” to a small mixed historical contrast, with no established benefit.
- “Overfitting” to an unconfirmed explanation supported by weak transfer and distribution mismatch.
- “Calibrated intervals” to empirical coverage/width diagnostics on a tiny cohort.

Remove or postpone:
- Prospective improvement, superiority on all GPUs, market-news benefits, infrastructure benefits, universal causal explanations and general research intelligence.
- The earlier selector's 22.8% result as evidence for this direct forecaster.

### Reproducibility and release checklist

- Public source and diagnostic manifests with exact SHA-256 values.
- Data/target provenance, source-specific units and CC BY attribution.
- Frozen baseline definitions, config, selections and retained forecast vectors.
- Correct distinction between loss-weight mass, supervised positions and provider usage.
- Public arithmetic verification with no model credentials or prepared-data access.
- Private prepared-data composition rerun clearly distinguished from public verification.
- Exact original tokenizer/weight revision marked unavailable, never invented.
- Stochastic regeneration distinguished from exact saved-sample reconstruction.
- Failed parses, negative runs and teardown warnings preserved.
- No private checkpoint paths, credentials, restricted raw inputs or development prompts.
- Existing official CSV hash and prospective gates unchanged.

Credential-free verification, after obtaining the public repository remotely:
~~~sh
PYTHONPATH=src python scripts/verify_direct_v16_public.py --root .
~~~
The matching GitHub Actions workflow is “Verify public direct-forecast diagnosis v16.” It uses only Python's standard library and committed permitted artifacts. Full private dataset-composition reproduction additionally requires the original prepared dataset or authorized pack reconstruction, NumPy and Matplotlib; see diagnose-direct-v16.yml. Neither path invokes training or inference.

## Execution and future-data plan

Now: publish this diagnosis as a technical note with its data card, paired table, four figures, manifest and verification command. A useful negative result does not need to be converted into a success story.

Next: implement the bounded tail-readout evaluator and lock its candidate grid and development rule before evaluating. This task is not yet executed. If its result is negative, publish that boundary rather than launch a broad sweep.

Then: choose the numerical-mask or source-coverage study based on the diagnostic result and data readiness. Keep each intervention separate and retain checkpoint zero. Do not launch both merely to consume credits.

Future: maintain the exact existing contract-transfer commitments and November gates. A separate challenger on compatible aggregate targets must be registered before issuance, with frozen inputs/models, eight weekly origins, matured seven-day labels and a fixed analysis date. Missing collection remains missing. If aggregate collection is unavailable, state that the original target's prospective test is blocked; the individual-contract panel cannot silently substitute for it.

A workshop submission would be stronger after one controlled intervention and a later compatible cohort. The current material is suitable for a transparent technical report or research blog, with historical and causal limitations prominent. No publication acceptance or future gain is promised.

## First precise engineering task

Create the proposed scripts/evaluate_tail_readout_v17.py and configs/direct-tail-readout-v17.json. Read only the immutable v14 sample artifacts; verify hashes; implement median-preserving positive log-offset scaling over the fixed nine candidates; apply the same development-only selection to base and SFT; export every candidate and selected mapping, original scores, calibration failures, paired origin/source contributions and an explicit post-hoc label. Add synthetic ordering/positivity/identity tests and a remote workflow with zero model credentials, zero optimizer updates and zero inference calls. The acceptance gate is exact identity reconstruction and no evaluation data entering selection. Do not modify the existing future registration.

The strongest explanation is distribution transfer failure concentrated in the tails, with source/temporal mismatch and fragile development selection as plausible contributors. The next experiment should test the smallest frozen readout repair. Even if it fails, the six-run negative result and its auditable decomposition remain responsible material to publish.
