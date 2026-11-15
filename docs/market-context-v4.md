# Supplementary market context

This forward-only lane asks which bounded research question to investigate next. It does not rewrite the November 6 benchmark, infer prices from announcements, or establish improved forecasting accuracy.

## Sources and interpretation

The source registry is [market-context-v4.json](../configs/market-context-v4.json). It includes primary announcements about manufacturing, cloud configurations and deployments, and Berkeley Lab energy and interconnection research. The registry records authored summaries and source-specific caveats. A capacity announcement is not delivered rental capacity; hardware throughput, electricity use and GPU-hour prices measure different things.

Exa retrieves those pages and discovers recent provider announcements. Raw response bodies stay on the private Modal data volume. Public records contain links, retrieval timestamps, response/content hashes, attributed summaries, availability status and provider-reported usage where returned. Missing retrievals remain missing. The current page contents become available at retrieval, never retrospectively on their publication dates.

## Research decisions and memory

The starting small model makes one bounded research-planning choice and a second choice after a fixed scope criticism. The alternatives are collecting a fresh price vintage, auditing configuration substitution, testing announcement lags, or auditing power constraints. No numerical hypothesis is marked successful by that decision.

Researcher, scientist and skeptic roles write authored records to past.dev and attempt cross-role recall. Public receipts distinguish a verified returned source ID from a canonical-text fallback. A changed planning choice is behavior, not evidence of better forecasting. The two decisions are not a controlled causal evaluation.

## Future forecasting use

The registered prospective panel retains its primary equal-information selector comparison. A separate exploratory frozen-SFT arm can consume retrieved market summaries available before issuance and at most seven days old. It uses the same six numerical reveals, but has extra information and inference work, which must be reported separately. It cannot be pooled into the primary equal-information claim.

The daily source capture and weekly research collection have a finite January 20, 2027 end. Current news is kept outside the original historical benchmark and the retrospective prompt-intervention study.

## Execution and reproduction

[The remote workflow](../.github/workflows/market-context-v4.yml) retrieves evidence, records two real Tinker decisions, retains private inputs on Modal, and publishes only safe metadata and decisions. Versioned public reports are under `results/review-v4/market/` and the live operations endpoint. Provider charges remain unknown unless a provider returns them.
