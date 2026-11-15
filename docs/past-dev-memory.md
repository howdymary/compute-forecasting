# Shared research memory

The current GPU-value research loop uses three bounded model-driven roles: evidence researcher, forecast scientist and skeptic. They share one past.dev audience, with distinct author identities and task contexts. They use the same base model; these are not separately trained researchers.

## Verified execution

[Successful run 43758970371](https://github.com/howdymary/compute-forecasting/actions/runs/43758970371) completed on November 15, 2026. The [immutable memory report](../results/value-v5/runs/43758970371/memory.json) retains authored record IDs, ingestion IDs and completion states, recall receipts, content hashes, six actual Tinker decisions, and deterministic numerical results.

| Requirement | Observed evidence |
| --- | --- |
| More than one writer | Three successfully ingested writer identities |
| More than one reader | Three reader identities with verified cross-role recalls |
| Another agent's information used | Six recalls returned the required record ID; its exact canonical payload entered the consuming task |
| Actual main-project task | Benchmark-specific H100/A100 rental-premium diagnostic, criticism and next research question |
| Memory improves accuracy | Not established; not required for memory eligibility |

The API's semantic recall supplies provenance-bearing source IDs. After verifying the required source ID, the consumer resolves the exact numerical payload from the canonical record map. This prevents a semantic summary from changing a number. A canonical-text fallback is explicitly labeled and is never counted as successful recall.

The roles performed this actual sequence:

1. The skeptic wrote prior experimental limitations.
2. The researcher recalled that record, retrieved primary evidence through Exa, selected an economic mechanism, and wrote sourced facts.
3. The scientist recalled the researcher's evidence, selected a workload context, and executed a deterministic rental-premium / throughput calculation.
4. The skeptic recalled the experiment and evidence, then identified unmatched provider composition as the primary objection.
5. The scientist recalled the criticism and reconsidered the same publication actions.
6. The researcher recalled the final decision and selected workload-profile evidence as the next missing input.

The scientist withheld an overall economic preference both before and after criticism. Its action did **not** change. The run demonstrates shared-memory use, not an accuracy gain or a new learned-weight improvement.

## Why the first v5 setup failed

The original audience slug was 44 characters. past.dev accepts 2–40 characters, consisting of lowercase letters, digits and dashes, with a letter or digit at either end.

A [bounded API regression check](../results/value-v5/runs/43759581339/setup-diagnostic.json) isolated the failure:

| Request | HTTP result |
| --- | --- |
| 44-character audience, short identities | 400: audience-slug-invalid |
| Short audience, original 60–63-character identities | 201 |
| Short audience and short identities | 201 |

The earlier code retained only the exception class, obscuring this response. The fixed implementation uses a 30-character audience slug, validates its length before making a request, and retains status and sanitized error receipts. The workflow now fails its eligibility gate if memory operations fail. It cannot report a canonical fallback as a verified memory success.

The [failed run's report](../results/value-v5/runs/43758497959/memory.json) remains available. No successful records or recalls are attributed to that run.

## Storage and information boundaries

- **past.dev:** authored semantic evidence, numerical findings, criticism and next questions.
- **Immutable GitHub JSON:** exact configurations, numerical results, source hashes, authorship and recall receipts.
- **Markdown:** explanations and links to those artifacts.
- **Private Modal storage:** original source response bodies, private provider diagnostics and model resources.

The current research audience is separate from historical benchmark-safe evidence, prospective commitments and synthetic fixtures. A freshly retrieved page never becomes a November 6 forecasting input merely because it discusses an older event.

The original frozen studies, official CSV and prospective scoring gates are unchanged. Further training remains gated on informative tasks. Provider credit consumption is not evidence of research quality.

## Verify without account credentials

After installing this repository's package, run:

~~~sh
python -m compute_forecast.verify_value_v5
~~~

This verifies ingestion receipts, cross-role provenance, record hashes, decision inputs and the published arithmetic from committed permitted artifacts. Repeating provider calls requires authorized past.dev, Exa and Tinker access and a new run identity.
