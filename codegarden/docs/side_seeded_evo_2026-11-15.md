# Seeded full-graph evolution — 15 November 2026

Best independently verified cardinality remains **226**. No227 construction or new global record was found.

## Evidence

- Source: `ba138d58184108d137751c751393bfc9380950a4`.
- [Execution 43757250902](https://github.com/howdymary/compute-forecasting/actions/runs/43757250902).
- Runtime artifacts: `codegarden/artifacts/side_research/seeded_evo_001/` on branch `codegarden-side-seeded-evo-001`.
- Upstream KaMIS: `2e4b3861b8063f05e8520434b97ce59e21ca49e7`.
- Protected descendant and LCS verifier sources remain frozen and unchanged. Worker and host verification both accepted every returned226 witness.

The experiment bypassed root kernelization in an explicitly selected seeded mode, retaining the identity labels of all65,536 words and disabling recursive reduction. Each run loaded eight far-apart verified226 parents. The root-identity marker, all eight inserted parent sizes, and initialization/evolution markers were observed in every native log. Parent lists, verification reports and file hashes are retained in plans and worker results.

The original strict population insertion gate was compared with a treatment that allowed distinct equal-size offspring to enter the existing ILS and nearest eligible non-best replacement path. Duplicate rejection was retained. The treatment changed a heuristic gate, not code validity.

| Run | Seed | Policy | Verified size | Native wall seconds | Peak child RSS KiB |
| --- | ---: | --- | ---: | ---: | ---: |
| Paired control | 2271142 | strict | 226 | 469.654 | 10,403,260 |
| Paired treatment | 2271142 | neutral | 226 | 450.539 | 10,403,604 |
| Additional exploration | 2271143 | strict | 226 | 441.594 | 10,188,600 |

The first pair used identical parents and configured resources. Both had a420-second soft search budget and a720-second hard process deadline. Soft deadline polling occurs after work units, so actual runtimes differ and exceed420; this is not an exact equal-CPU comparison. The fresh-seed run is exploration.

All final witnesses belonged to the recorded152-array family. The neutral treatment logged four equal-size candidate considerations. That counter does **not** prove four successful replacements or increased population diversity. There was no cardinality improvement and no demonstrated policy benefit.

Native graph and policy fixtures passed before remote execution, including independent graph comparisons, both seeded modes on a small graph, and rejection of a conflicting parent. The full graph hash remained `de8221d0814e5fcb303f529d423e801713af1cbcd61e309d8a9937a6aad08564`.

## Research decisions and memory

Exa was called in `side_seeded_evo/experiment.py::main` to research population diversity and equal-fitness replacement. Queries, source links and execution events are retained in the artifacts.

The strategist actually retrieved ten documents carrying source `codegarden-startup-43755774242-analyst`, and those documents were included in the Tinker prompt. Tinker used untrained Qwen/Qwen3.5-4B inference:3,855 prompt tokens and two output tokens. It selected strict for the fresh-seed exploration. This is a real strategy-selection call, not training or a learned-policy improvement.

The analyst submitted the result once under `codegarden-seeded-evo-43757250902-analyst`, ingestion `d5db16e3-5eb6-4441-a9fe-9f0590b94224`. The recorded checkpoint is processing. Resume that handle instead of submitting a duplicate. Role identities are software roles in serialized controllers, not independent assistant agents.

## Scope and next test

This is a bounded heuristic negative: these runs returned no improvement. It does not exhaust the full graph, a neighborhood, or all seeded trajectories, and supplies no mathematical upper bound.

A separate [hard-versus-elastic target227 batch](https://github.com/howdymary/compute-forecasting/actions/runs/43757985058), source `58ebdf4186954af3bf6c386c2768defadb6224aa`, is active. It compares full-universe hard packing, elastic cap2, and Tinker-selected cap32 with the same seed and8CPU/1,800-second budgets. Positive collision energy is explicitly invalid. This batch has passed504 independent descendant checks and exact small-instance solver comparisons; it has not yet returned a verified227 witness.

A fresh arena observation at20:18:29 UTC showed kgrey solution2778 at226, witness SHA-256 `417e3dab220270af47121962faa0af62d37d77668f79d1b38889fcc7e4a63efa`. The observation and response hash are retained in `side_elastic/hypothesis.json`. It is an arena observation, not an exhaustive literature/global-record audit.

No provider billing dashboards or balances were queried. Other projects and protected verifier files were not changed. The main goal remains open.
