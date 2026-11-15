# CodeGarden service-backed research checkpoint

Research date: 2026-11-15. **Goal unfinished. Best independently checked code remains the arena's reproduced 226-word construction. No 227-word code and no new global record are claimed.**

## Actual services used

- **Exa:** two MCP research searches, two MCP page-fetch batches, and a genuine REST search in the remote controller. Primary sources include San Segundo, Artieda and Strash, *Efficiently Enumerating all Maximal Cliques with Bit-Parallelism*, arXiv:1801.00202, and the CliSAT author repository. The tested method adapts static maximum-degree-first ordering to exact maximum-clique repair; it does not reproduce the original maximal-clique enumeration algorithm.
- **past.dev:** analyst and researcher role identities wrote actual records. The researcher recalled the analyst's exact source before the REST research query. Two later ingestions exceeded the observation window; recovery retrieved their original ingestion IDs through scoped request records, confirmed all three original ingestions completed, and let the strategist recall the researcher's exact source. No ingestion was restarted or duplicated. These are three software role identities, not multiple independent assistant agents.
- **Tinker:** Qwen/Qwen3.5-4B selected `degree_desc` with an exact valid response, using 810 prompt tokens and three output tokens. This was inference with an untrained policy. No training or trained-policy benefit is claimed.
- **Modal:** six CPU workers compared original and decreasing-degree orderings on three identical paired repair models. Each used one CPU, 1 GiB memory, a 30-second solver budget and a 90-second function timeout; maximum concurrent containers was four. A portable static C++ binary was built without host-native CPU flags. Every literal pool hash matched the independent Python model; every exported retained witness passed both protected checkers in the worker and on the host.

## Results

| Pool and removal count | Original ordering | Tinker-selected decreasing-degree ordering |
| --- | --- | --- |
| 779 candidates, remove 32 | Timeout at 30.001 s, 9,441,281 nodes | Completed encoded negative at 0.618 s, 121,235 nodes |
| 803 candidates, remove 32 | Timeout at 30.001 s, 5,864,449 nodes | Completed encoded negative at 1.956 s, 369,255 nodes |
| 3,151 candidates, remove 64 | Timeout at 30.015 s, 1,858,561 nodes | Timeout at 30.008 s, 2,054,145 nodes |

Each model fixes the recorded outside incumbent words and requires one recorded outside pivot. Its repair pool includes every universe word compatible with those fixed words and pivot. A completed negative applies only to that literal model. Native absence results have no independent formal proof certificate. Timeouts remain open.

The ordering change substantially improved completion on two models but did not improve code cardinality. This is evidence for choosing a solver strategy, not achievement of the mathematical objective or proof that an LLM policy beats every fixed strategy.

The kernel passed 352 brute-enumerated graph fixtures and 64 deletion-generator fixtures. A fresh verifier-only acceptance job was configured and correctly skipped because no 227-word candidate was produced.

## Provenance and reproducibility

- Research source: `9474663bece6004216919a020a43bdf93b65b523`.
- Research run: https://github.com/howdymary/compute-forecasting/actions/runs/43748900357
- Completed research artifacts: `1e04ba3b1a1c21e564f3781881b80f2206ef175c/codegarden/artifacts/side_research/services_001/`.
- Recovery source: `6b0239837fdcec7c0f046d668e43dae8c893bf2b`.
- Recovery run: https://github.com/howdymary/compute-forecasting/actions/runs/43749604059
- Exact recovered source IDs and ingestion statuses: `artifacts/side_research/memory_recovery_001/`.
- Queued next hypothesis and retired literal model definitions: `artifacts/side_research/memory_recovery_001/next_research_queue.json`.
- Protected checkers remain unchanged. Any future claimed 227-word construction must pass fresh isolated acceptance using checker source `ce5eab1859c271686876ee5c2d21c0e0a5316d67`.

Exa's exact REST call is in `side_services/cycle.py::exa_search`; memory calls are `write_memory` and `recall`; Tinker is `tinker_choose`; Modal is the nested `worker` function in `main`. Sources, pool definitions, parameters, binary hashes, role reads, action selection, output witnesses and protected verification reports are inspectable data.

The live arena check at 18:50:39 UTC still returned kgrey's solution2778 at226, with witness SHA-256 `417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa`. The literature search did not find a newer explicit227, but the global audit remains incomplete. Historical literature comparisons are separate from the current arena.

## Preservation and user steering

The latest user instruction removed BoundForge spending coordination and requested no further cost checks. The new cycle used its own bounded request journal, made no billing/balance queries, bought no credits, and changed no replenishment or plan settings. Historical holds were not silently declared actual spend or released.

All work and artifacts are under CodeGarden, except the already authorized isolated GitHub launcher. The main CodeGarden branch remains unchanged, as do protected verifiers and other project files. Source and artifact mutations are confined to separate research branches. No project files or environments were written on the workstation.

The remaining primary task is to find and independently accept a code of at least227, or rigorously audit and independently verify another new global construction record.
