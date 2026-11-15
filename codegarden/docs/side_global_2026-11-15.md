# CodeGarden whole-universe search: 15 November 2026

Best independently verified cardinality remains **226**. No 227-word construction or new global record was found. This batch compared a cold evolutionary search with two warm local searches over all 65,536 length-16 words.

## Reproduction and provenance

- Search source: `9f31a85bfe50d8b9f0dc480b5b8584021e3a1537`.
- Execution: [GitHub Actions 43753466573](https://github.com/howdymary/compute-forecasting/actions/runs/43753466573).
- Published execution artifacts: `07cb2bcb3f74f91567294ac323507eec3fd1b2c8`, under `codegarden/artifacts/side_research/global_001/`.
- Upstream KaMIS: `2e4b3861b8063f05e8520434b97ce59e21ca49e7`. The existing documented saturating plateau decrement patch was retained.
- Protected descendant and pairwise-LCS verifier sources remained frozen at `ce5eab1859c271686876ee5c2d21c0e0a5316d67`.
- Reproduced 226-word incumbent SHA-256: `417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa`.
- The last arena observation, 19:18 UTC on this date, showed kgrey solution 2778, score 226, with this same witness hash. This is an arena comparison, not an exhaustive global-record audit.

## Representation and portability checks

The whole-universe conflict graph contains 65,536 vertices and 80,964,349 undirected edges. Its text SHA-256 is `de8221d0814e5fcb303f529d423e801713af1cbcd61e309d8a9937a6aad08564`. The descendant incidence has 2,244,608 entries. CSR storage is 648,239,088 bytes; the conservative solver resource gate allowed the profiled instance.

Both executables were rebuilt with generic x86-64 targeting, static OpenMP archives, no native instruction flags, and no dynamic interpreter. The two binaries passed a four-cycle smoke test, including on the actual Modal worker hosts. Graph-generation correctness was checked against literal-string deletion sets for 9,736 small-instance pairs. The large graph was held in an ephemeral Modal volume; results and native logs were retained separately.

## Observed outcomes

| Method | Seed | Native time limit | Wall seconds | Returned verified size |
| --- | ---: | ---: | ---: | ---: |
| Cold ReduMIS evolution | 2271138 | 180 s soft / 360 s hard | 360.028 | No witness |
| Warm ILS, default force candidates = 4 | 2271137 | 180 s | 196.148 | 226 |
| Warm ILS, selected force candidates = 1 | 2271137 | 180 s | 199.858 | 226 |

Both warm runs returned the identical known 226-word code and passed the two protected checkers. The Tinker-selected parameter was actually applied, but this single paired comparison showed **no cardinality gain**. A final best-witness export cannot establish which neutral states the search may have visited.

The cold process was killed and reaped by Python's hard subprocess timeout. The historical raw field `OBSERVATION_TIMEOUT` must be interpreted as **hard process termination**, not an asynchronous observation timeout. Peak child RSS was 18,346,880 KiB (17.497 GiB). It produced no witness and supports no cardinality claim.

The complete 2,346-character native log ends during separator-pool construction. It contains neither the flushed pool-completion marker nor the Initialization/Evolution headings. Inspection of the pinned source confirms pool construction precedes population initialization and evolution. Partition/separator weights in that log are preprocessing statistics, not code sizes or mathematical upper bounds. No impossibility or neighborhood-exhaustion claim follows from this run.

The separate accept-new-incumbent job was correctly skipped because no candidate reached 227.

## Actual sponsor use and memory

Exa was called for current documentation and search-method evidence; extracted source provenance and events are retained in the execution artifacts. Two actual past.dev records from `codegarden-lp-43750749052-analyst` were retrieved and included in the Tinker prompt.

Tinker used untrained Qwen/Qwen3.5-4B inference (1,065 input tokens, four output tokens) to select uniform forcing. This is a strategy selection experiment, not a trained-policy improvement. Modal ran the graph build and the three CPU search workers with distinct durable outputs.

The analyst submitted these results to past.dev under `codegarden-global-43753466573-analyst`, ingestion `62d1bb2d-81fe-4e1e-ad11-5cb5728af7e7`. The saved postprocessing checkpoint reports processing, not completed or failed. Resume that handle rather than submitting a duplicate. Earlier cross-role recall is real; this pending write does not establish later cross-role reuse.

No provider balances or billing dashboards were queried for this batch. Bounded per-experiment usage records remain in the artifacts.

## Next test, not yet run

The queued hypothesis in `global_001/next_hypothesis.json` is to reduce partition/separator counts and initial population/round size so the cold full-universe method reaches actual evolution within its deadline. This changes a heuristic configuration, not the code validity rules. The proposed settings have **not yet been implemented or executed**.

The next experiment should explicitly record entry into population initialization and evolution. A hard timeout without a witness remains unresolved. The primary goal remains open.
