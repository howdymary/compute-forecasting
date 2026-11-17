# Continued training: results in plain language

Completed November 17, 2026. This is a post-event, retrospective study. **Prospective improvement is not yet established.**

[Interactive training and price forecasts](https://howdymary--compute-forecast-evidence-v14-web.us-east.modal.run/continuation) · [Registered methods](ce-continuation-v21.md) · [Full six-run findings](ce-continuation-v21-findings.md) · [Compact verified release summary](../results/ce-continuation-v21/diagnostics/44161946789/release-summary.json)

## What finished

All six runs completed 100 additional optimizer updates each: **600 updates in total**. Three used the original 314 historical training windows; three used an expanded collection of 3,837 windows. Each restored the same Qwen3.5-4B LoRA model and Adam state, kept the same 19 possible future-price levels, and used a lower learning rate. The three ordering seeds change the order of examples; they do not create new independent market outcomes or independent initial models.

The expanded data adds real configuration and temporal coverage from the same collector in Pacific's pack. It does not add news, new providers, or thousands of independent price experiments.

## Did it improve the existing model?

**No continuation beat the frozen incumbent on the registered seven-day endpoint.** Lower quantile pinball loss means a better combination of forecast location and uncertainty.

| Model | Retrospective seven-day loss | Change from incumbent |
| --- | ---: | ---: |
| Frozen existing model, v19 update 30 | 0.01555766 | Reference |
| Continue on original data, mean of three orderings | 0.01795385 | 15.4% worse |
| Continue on expanded data, mean of three orderings | 0.01793920 | 15.3% worse |

Expanded-data continuation had only 0.08% lower average loss than same-data continuation. It was worse in two of three matched orderings and better in one. This does not demonstrate a reliable benefit from the extra corpus. Under the fixed budget, the expanded arm also saw a smaller fraction of its corpus; the result does not establish that more data is generally harmful.

The comparison contains **24 seven-day cases: eight provider/configuration groups on October 25, 28 and 30, 2026**. These dates were already examined and are dependent. The three orderings reuse the same market outcomes. Means across orderings are descriptive, not estimates based on independent market trials.

## What changed in the forecasts?

Every selected continuation improved its development score, but those gains did not transfer to the later retrospective dates. None selected its final update 100: development selection chose update 20 or 50.

All six selected continuations produced narrower seven-day intervals and worse median-price absolute error. The incumbent covered 20 of 24 outcomes inside its q10–q90 interval; the continuations covered 18–20. Much of the extra loss came from lower-tail protection on falling A100 prices, rather than the unchanged-price cases.

In the nine changed-price cases, all six continuations assigned a higher average probability to no change than the incumbent did. This is consistent with harmful concentration around familiar price patterns and weak temporal transfer. It is **not proof of a unique cause**. Entropy did not fall uniformly, so “all uncertainty collapsed” would also be inaccurate.

The read-only audits found no evidence that checkpoint restoration, parsing or random sampling caused this result. The restored parent reproduced all 120 retained forecast vectors exactly. Current quantiles are calculated deterministically from the full categorical probabilities. All six selected retrospective evaluations had zero recorded failures and no out-of-support outcomes.

[Probability and loss-contribution diagnostics](../results/ce-continuation-v21/diagnostics/44161946789/diagnostics.json) · [Quantile contribution figure](../results/ce-continuation-v21/diagnostics/44161946789/loss-contributions.png) · [Exact exposure audit](../results/ce-continuation-v21/exposure/44161097117/exposure.json)

## Was there any useful improvement?

Yes, at a different horizon: **five of six continuations improved one-day probabilistic loss, two improved three-day loss, and none improved seven-day loss**. This motivates a separate horizon-specific investigation. It does not change the registered primary result. One-day median-price error did not improve.

The existing incumbent had already improved seven-day retrospective loss by about **29.7% versus its corresponding untuned model on these same cases**: 0.02214536 to 0.01555766. That earlier historical gain remains intact. This round established that longer continuation did not improve on that trained checkpoint.

The official multiplicative drift reference scored 0.01670291 on these cases. The incumbent beat it; all six continuations did not. Numerical controls retain the actual starter-kit definitions.

## What should we try next?

Keep the existing model as the reference. The next proposed training test is one short continuation with a penalty for departing too far from the incumbent's full price probabilities. It asks whether useful tail protection can be retained while learning from observed prices.

Use the same parent, original corpus, first 20 ordering-17 batches, learning rate and optimizer restoration as the completed ordinary-CE control. Fix an added KL penalty before execution, run at most 20 new updates, and reuse the existing ordinary-CE update-20 checkpoint as the control after compatibility checks. Fix update 20 as the primary endpoint. This proposal is **not yet registered or executed**.

Beating the deteriorated ordinary continuation would show reduced harm. It would not establish improvement over the incumbent. That stronger claim requires beating the incumbent on separately registered later observations.

A subsequent, distinct test could specialize training by horizon, motivated by the one-day/seven-day disagreement. Do not combine both changes in the same mechanism test. [Detailed next-test proposal and primary sources](ce-continuation-v21-next-steps.md).

## What remains future-dependent?

The existing v21 future protocol is unchanged: 16 weekly origins from **December 20, 2026**, with analysis no earlier than **April 12, 2027 UTC**. As of the November 17 readiness check, **zero origins have been issued**. The eligible issuance window has not opened, and the required compatible fresh contract cohort is not yet available. No future accuracy has been demonstrated.

The original seed-17 future model lock remains unchanged after publishing the other orderings. It retains the development-selected candidates; retrospective results did not replace them. Any new anchored challenger requires a separate registration. [Actual future readiness and model lock](../results/ce-continuation-v21/future/44161097194/index.json).

## Verification and reproduction

The final report SHA-256 is `7e5a1f9bb18f89162285a1a4fc1b69ee9bf0ab001544117bdab330982b9659ce`.

From an environment with the repository's declared Python dependencies installed:

```bash
python -m compute_forecast.verify_continuation_v21
python scripts/diagnose_ce_continuation_v21.py
```

These reconstruct public arithmetic from retained permitted artifacts without service credentials. Training requires authorized numerical inputs and private model resources. Stochastic optimization is not promised to regenerate byte-identical weights. Resource identity hashes are not checksums of weight bytes.

- [Completed four-run remainder and combined publication](https://github.com/howdymary/mochi-demo/actions/runs/44144492740).
- [Public arithmetic and final distribution audit](https://github.com/howdymary/mochi-demo/actions/runs/44161946789): six runs, 600 updates, unchanged pilot model lock.
- [Foundation checks](https://github.com/howdymary/mochi-demo/actions/runs/44161946868): 248 passed, six skipped; skips are not counted as passes.
- [Live desktop/mobile validation](https://github.com/howdymary/mochi-demo/actions/runs/44161275998): numerical agreement, interaction checks and 24 concurrent HTTP/2 responses, all 200.
- Inspected [desktop PNG](../results/ce-continuation-v21/validation/44161275998/live-desktop.png) and [mobile PNG](../results/ce-continuation-v21/validation/44161275998/live-mobile.png).
- [Validation record and PNG hashes](../results/ce-continuation-v21/validation/44161275998/validation.json).

All checkpoint trajectories, original selections, successful and negative results remain versioned. The official submission and earlier frozen studies are preserved. No new optimization was performed by the release diagnostics. Provider-reported charges are unavailable and remain null.
